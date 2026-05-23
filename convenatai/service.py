from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import Optional

from .agent import Agent
from .negotiation import NegotiationSession, Proposal
from .payment import ArcNanopaymentGateway, NanopaymentStream, PaymentChannel
from .contract import LegalContract
from .arc_integration import ArcJobManager, ArcJobInfo, JobStatus, STATUS_NAMES
from .arc_identity import ArcIdentityManager


from .genlayer_client import NotifyGenLayer

class TransactionError(RuntimeError):
    pass


# ─── GenLayer Kill-Switch Result ─────────────────────────────────────────────

class KillSwitchTriggered(TransactionError):
    """Raised when GenLayer SLA evaluation fails and the kill-switch fires."""
    pass


@dataclass
class ContractExecutionOutcome:
    stream: NanopaymentStream
    channel: PaymentChannel
    contract: Optional["LegalContract"] = None
    status: str = "completed"  # "completed", "disputed", "failed"


class ContractExecutionService:
    def __init__(self, gateway: Optional[ArcNanopaymentGateway] = None,
                 logger: Optional[callable] = None,
                 arc_job_manager: Optional[ArcJobManager] = None,
                 identity_manager: Optional[ArcIdentityManager] = None):
        self.gateway = gateway or ArcNanopaymentGateway()
        self.logger = logger or print
        self.arc = arc_job_manager or ArcJobManager()
        self.identity = identity_manager or ArcIdentityManager()

    @property
    def mode_label(self) -> str:
        return "🔴 LIVE (Arc Testnet)" if self.arc.is_live else "🟡 LOCAL MOCK (no API keys)"

    async def negotiate(self, proposal: Proposal, max_rounds: int = 5) -> Proposal:
        if proposal.proposer.bus is None or proposal.responder.bus is None:
            raise TransactionError("Agents must be attached to a shared message bus before negotiation.")

        # Start agent handlers to process proposals
        agents = {proposal.proposer, proposal.responder}
        tasks = [asyncio.create_task(agent.handle_messages()) for agent in agents]
        try:
            agreement = await NegotiationSession(proposal, max_rounds).run_async()
            if agreement is None:
                raise TransactionError("Negotiation failed to reach agreement.")
            return agreement
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    def open_payment_channel(self, payer: Agent, payee: Agent, amount: float) -> PaymentChannel:
        return self.gateway.open_channel(payer, payee, amount)

    def stream_payments(self, channel: PaymentChannel, amount: float, duration: int, realtime: bool = False, delay_seconds: float = 0.0) -> NanopaymentStream:
        stream = NanopaymentStream(channel=channel, amount=amount, duration=duration)
        stream.start(realtime=realtime, delay_seconds=delay_seconds)
        return stream

    async def execute_trade(self, proposal: Proposal, treasury: Optional[Agent] = None, max_rounds: int = 5) -> ContractExecutionOutcome:
        """
        Orchestrates the convenatAI workflow:

        Mode A (local mock): Same as before — LegalContract + NanopaymentStream
        Mode B (Arc live):   ERC-8183 job lifecycle on Arc Testnet
        """
        self.logger(f"Initiating P2P negotiation for: {proposal.description}")
        agreement = await self.negotiate(proposal, max_rounds)

        # Funding logic via Treasury agent if required
        if treasury and agreement.proposer.wallet.available_balance() < agreement.price:
            needed = agreement.price - agreement.proposer.wallet.available_balance()
            if not treasury.wallet.transfer(agreement.proposer, needed):
                raise TransactionError(f"Treasury failed to fund {needed:.2f} to proposer.")
            self.logger(f"Treasury funded ${needed:.2f} to {agreement.proposer.name}.")

        self.logger(f"Agreement reached! Price: ${agreement.price:.2f}, Duration: {agreement.duration}")

        # Auto-register agents on ERC-8004 IdentityRegistry before execution
        self.logger("Registering agents on ERC-8004 IdentityRegistry...")
        try:
            agents_to_register = [agreement.proposer, agreement.responder]
            if treasury:
                agents_to_register.append(treasury)
            reg_results = self.identity.register_agents_auto(agents_to_register)
            for r in reg_results:
                self.logger(f"  Identity: {r['address'][:12]}... → {r['status']}")
        except Exception as e:
            self.logger(f"⚠️ Identity registration warning (non-fatal): {e}")

        if self.arc.is_live:
            return await self._execute_arc(agreement)
        else:
            return await self._execute_mock(agreement)

    async def _execute_mock(self, agreement: Proposal) -> ContractExecutionOutcome:
        """Local mock — uses LegalContract + NanopaymentStream, with GenLayer kill-switch."""
        # Create legal contract from agreement
        contract = LegalContract.from_proposal(agreement)
        agreement.proposer.sign(contract)
        agreement.responder.sign(contract)
        contract.activate()

        # Open Payment Channel
        channel = self.open_payment_channel(agreement.proposer, agreement.responder, agreement.price)

        self.logger("Notifying GenLayer SLA Monitor via LayerZero bridge...")
        gl_result = NotifyGenLayer.register_job(
            stream_id=f"stream-job-{agreement.proposer.name}-{id(channel)}",
            buyer_id=agreement.proposer.wallet.address or agreement.proposer.name,
            seller_id=agreement.responder.wallet.address or agreement.responder.name,
            description=agreement.description,
            quality_criteria=f"SLA: {agreement.description}, price=${agreement.price}, duration={agreement.duration} units",
            deliverable_uri=agreement.deliverable or "",
        )
        if gl_result.get("status") == "notified":
            self.logger(f"✅ GenLayer SLA monitor notified for stream: {gl_result['stream_id']}")
        else:
            self.logger(f"⚠️ GenLayer notification issued (RPC may be offline): {gl_result.get('error', 'unknown')}")

        # Start streaming
        stream = self.stream_payments(channel, agreement.price, agreement.duration)

        # Record delivery
        contract.report_delivery(agreement.duration)

        # Trigger GenLayer SLA evaluation after delivery
        stream_id = f"stream-job-{agreement.proposer.name}-{id(channel)}"
        gl_monitor = NotifyGenLayer.monitor_stream(
            stream_id=stream_id,
            deliverable_uri=agreement.deliverable or f"delivery-{stream_id}",
        )
        if gl_monitor.get("status") == "evaluated":
            self.logger(f"✅ GenLayer SLA evaluation completed for {stream_id}")
        else:
            self.logger(f"⚠️ GenLayer SLA evaluation attempted: {gl_monitor.get('error', 'ignored')}")

        # ─── KILL-SWITCH CHECK: Query GenLayer to see if SLA failed ───
        kill_switched = False
        job_status = NotifyGenLayer.get_job_status(stream_id)
        if job_status.get("error"):
            self.logger(f"⚠️ GenLayer status query failed (RPC may be offline): {job_status.get('error')}")
        else:
            is_active = job_status.get("result", {}).get("active", None)
            if is_active is not None:
                is_active_bool = is_active if isinstance(is_active, bool) else str(is_active).lower() in ("true", "1")
                if not is_active_bool:
                    self.logger("🚨 KILL-SWITCH TRIGGERED: GenLayer SLA evaluation failed! Terminating stream.")
                    kill_switched = True

        if kill_switched:
            # Kill switch: close channel immediately, cancel remaining payments
            stream.kill_stream()
            self.logger("🔴 Payment channel closed early due to SLA failure.")
            contract.settle(stream)
            self.logger("🔴 Deliverable rejected — SLA criteria not met.")
            return ContractExecutionOutcome(
                stream=stream,
                channel=channel,
                contract=contract,
                status="disputed",
            )

        # Normal flow: close channel and settle
        self.gateway.close_channel(channel)
        contract.settle(stream)

        return ContractExecutionOutcome(stream=stream, channel=channel, contract=contract)

    async def _execute_arc(self, agreement: Proposal) -> ContractExecutionOutcome:
        """Arc live mode — uses ERC-8183 on-chain job lifecycle with GenLayer kill-switch."""
        self.logger("Using Arc Testnet ERC-8183 job lifecycle...")

        # Step 1: Create job on Arc
        job = self.arc.create_job(
            client=agreement.proposer,
            provider=agreement.responder,
            description=agreement.description,
            budget_usd=agreement.price,
        )
        self.logger(f"Job {job.job_id} created: {agreement.description}")

        # Step 2: Set budget
        self.arc.set_budget(agreement.responder, job.job_id, agreement.price)

        # Step 3: Approve USDC + fund escrow
        self.arc.approve_and_fund(agreement.proposer, job.job_id, agreement.price)

        # Step 4: Open payment channel and stream (same as mock)
        channel = self.open_payment_channel(agreement.proposer, agreement.responder, agreement.price)
        stream = self.stream_payments(channel, agreement.price, agreement.duration)

        # Step 5: Submit deliverable
        deliverable_text = agreement.deliverable or f"deliverable-job-{job.job_id}"
        self.arc.submit_deliverable(agreement.responder, job.job_id, deliverable_text)

        # ─── GenLayer SLA Evaluation (Kill-Switch) ───
        stream_id = f"stream-arc-{job.job_id}"
        self.logger("Notifying GenLayer SLA Monitor for Arc job...")
        NotifyGenLayer.register_job(
            stream_id=stream_id,
            buyer_id=agreement.proposer.wallet.address or agreement.proposer.name,
            seller_id=agreement.responder.wallet.address or agreement.responder.name,
            description=agreement.description,
            quality_criteria=f"SLA: {agreement.description}, price=${agreement.price}, duration={agreement.duration} units",
            deliverable_uri=deliverable_text,
        )

        gl_monitor = NotifyGenLayer.monitor_stream(
            stream_id=stream_id,
            deliverable_uri=deliverable_text,
        )

        # Check if kill-switch triggered
        kill_switched = False
        job_status = NotifyGenLayer.get_job_status(stream_id)
        if job_status.get("error"):
            self.logger(f"⚠️ GenLayer status query failed: {job_status.get('error')}")
        else:
            is_active = job_status.get("result", {}).get("active", None)
            if is_active is not None:
                is_active_bool = is_active if isinstance(is_active, bool) else str(is_active).lower() in ("true", "1")
                if not is_active_bool:
                    self.logger("🚨 KILL-SWITCH TRIGGERED: GenLayer SLA evaluation failed!")
                    kill_switched = True

        if kill_switched:
            # Kill switch: close payment, reject deliverable on Arc
            stream.kill_stream()
            self.arc.complete_job(agreement.proposer, job.job_id, approved=False, reason="sla-failure")
            self.logger("🔴 Arc job rejected — SLA criteria not met.")

            # Create a lightweight contract-like object for reporting
            from .contract import LegalContract
            contract = LegalContract.from_proposal(agreement)

            return ContractExecutionOutcome(
                stream=stream,
                channel=channel,
                contract=contract,
                status="disputed",
            )

        # Normal completion
        self.gateway.close_channel(channel)

        # Step 6: Complete job (approve)
        self.arc.complete_job(agreement.proposer, job.job_id, approved=True)

        # Step 7: Release payment to provider
        self.arc.release_payment(job.job_id, agreement.responder, agreement.price)

        self.logger(f"Job {job.job_id} completed on Arc Testnet!")

        # Update reputation on ERC-8004 for successful completion
        try:
            self.identity.update_agent_reputation(
                agreement.proposer,
                agreement.responder.wallet.address or agreement.responder.name,
                min(100, 50 + int(agreement.price * 10)),  # score grows with deal value
            )
            self.logger(f"✅ Reputation updated for {agreement.responder.name}")
        except Exception as e:
            self.logger(f"⚠️ Reputation update warning (non-fatal): {e}")

        # Create a lightweight contract-like object for reporting
        from .contract import LegalContract
        contract = LegalContract.from_proposal(agreement)

        return ContractExecutionOutcome(stream=stream, channel=channel, contract=contract)
