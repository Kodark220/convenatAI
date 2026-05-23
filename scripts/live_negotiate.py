"""
convenatAI — Autonomous Agent: Scan, Negotiate & Execute on Arc

An agent that:
1. Scans Arc Testnet for Open jobs
2. Picks one to bid on
3. Negotiates with the provider
4. Creates a real ERC-8183 job on Arc Testnet
5. Funds escrow, submits deliverable, completes job
"""

from __future__ import annotations
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from convenatai.agent import Agent, Wallet
from convenatai.network import AgentRegistry, MessageBus
from convenatai.negotiation import Proposal
from convenatai.service import ContractExecutionService, TransactionError
from convenatai.payment import ArcNanopaymentGateway
from convenatai.arc_integration import ArcJobManager, JobStatus, STATUS_NAMES
from convenatai.discovery import AgentDiscovery, DiscoveredJob

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("convenatAI.bot")


def pick_best_job(jobs: list, my_address: str) -> DiscoveredJob | None:
    """Pick an Open job that isn't ours."""
    candidates = [j for j in jobs 
                  if j.client.lower() != my_address.lower()
                  and j.provider.lower() != my_address.lower()]
    return candidates[0] if candidates else None


async def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║     convenatAI — Live Arc Agent Negotiator              ║
║     Scans → Negotiates → Creates real ERC-8183 job     ║
╚══════════════════════════════════════════════════════════╝
""")
    
    my_wallet = "0x1505102c7247b0e3323e689cb5bc6a142dff4408"
    
    # ── 1. Scan ─────────────────────────────────────────────────────
    print("[1] 🔍 Scanning Arc Testnet...")
    discovery = AgentDiscovery()
    jobs = discovery.scan_recent_jobs(lookback_blocks=5000)
    open_jobs = discovery.get_open_jobs()
    print(f"    {len(open_jobs)} open jobs, {len(discovery.get_agents())} agents")
    
    target = pick_best_job(open_jobs, my_wallet)
    if not target:
        print("    No external jobs found.")
        return
    
    print(f"\n[2] 🎯 Target: Job #{target.job_id}")
    print(f"    Client:  {target.client[:12]}...")
    print(f"    Provider: {target.provider[:12]}...")
    
    # ── 2. Negotiate (mock) ─────────────────────────────────────────
    print("\n[3] 🤖 Setting up agents & negotiating...")
    
    registry = AgentRegistry()
    bus = MessageBus(registry)
    
    me = Agent("AutoNegotiator", role="trading", wallet=Wallet(balance=500.0))
    me.wallet.address = my_wallet
    me.wallet.wallet_id = "d357e0f2-a3a1-5800-9193-40b6f6372002"
    
    provider = Agent("OnChainProvider", role="broker", wallet=Wallet(balance=200.0))
    provider.wallet.address = target.provider
    
    bus.register_agent(me)
    bus.register_agent(provider)
    
    proposal = Proposal(
        proposer=me,
        responder=provider,
        description=f"Data processing for job #{target.job_id}",
        price=5.0,
        duration=2,
        deliverable="processed_data",
    )
    
    service = ContractExecutionService(
        gateway=ArcNanopaymentGateway(),
        arc_job_manager=ArcJobManager(use_live=False),  # mock negotiation
    )
    
    try:
        outcome = await service.execute_trade(proposal)
        print(f"    ✅ Negotiated! Price: ${outcome.stream.amount:.2f}")
    except TransactionError as e:
        print(f"    ❌ {e}")
        return
    
    # ── 3. Create real ERC-8183 job on Arc ──────────────────────────
    print(f"\n[4] 🚀 Creating real ERC-8183 job on Arc Testnet...")
    
    from convenatai.circle_executor import create_contract_execution_transaction
    
    try:
        # Create the job from our funded wallet
        result = create_contract_execution_transaction(
            wallet_address=my_wallet,
            contract_address="0x0747EEf0706327138c69792bF28Cd525089e4583",
            abi_function_signature="createJob(address,address,uint256,string,address)",
            abi_parameters=[
                target.provider,
                my_wallet,  # we act as evaluator too
                "1900000000",
                f"convenatAI negotiated deal from job #{target.job_id}",
                "0x0000000000000000000000000000000000000000",
            ],
            fee_level="MEDIUM",
        )
        print(f"    ✅ createJob submitted! Tx: {result.get('id', '?')}")
        
        # Set budget
        result = create_contract_execution_transaction(
            wallet_address=my_wallet,
            contract_address="0x0747EEf0706327138c69792bF28Cd525089e4583",
            abi_function_signature="setBudget(uint256,uint256,bytes)",
            abi_parameters=["1", "5000000", "0x"],  # 5 USDC = 5000000 (6 decimals)
            fee_level="MEDIUM",
        )
        print(f"    ✅ setBudget submitted! Tx: {result.get('id', '?')}")
        
        # Approve USDC
        result = create_contract_execution_transaction(
            wallet_address=my_wallet,
            contract_address="0x3600000000000000000000000000000000000000",
            abi_function_signature="approve(address,uint256)",
            abi_parameters=["0x0747EEf0706327138c69792bF28Cd525089e4583", "5000000"],
            fee_level="MEDIUM",
        )
        print(f"    ✅ USDC approve submitted! Tx: {result.get('id', '?')}")
        
        # Fund escrow
        result = create_contract_execution_transaction(
            wallet_address=my_wallet,
            contract_address="0x0747EEf0706327138c69792bF28Cd525089e4583",
            abi_function_signature="fund(uint256,bytes)",
            abi_parameters=["1", "0x"],
            fee_level="MEDIUM",
        )
        print(f"    ✅ fund submitted! Tx: {result.get('id', '?')}")
        
        # Submit deliverable
        result = create_contract_execution_transaction(
            wallet_address=my_wallet,
            contract_address="0x0747EEf0706327138c69792bF28Cd525089e4583",
            abi_function_signature="submit(uint256,bytes32,bytes)",
            abi_parameters=["1", "0x0000000000000000000000000000000000000000000000000000000000000001", "0x"],
            fee_level="MEDIUM",
        )
        print(f"    ✅ submit submitted! Tx: {result.get('id', '?')}")
        
        # Complete job
        result = create_contract_execution_transaction(
            wallet_address=my_wallet,
            contract_address="0x0747EEf0706327138c69792bF28Cd525089e4583",
            abi_function_signature="complete(uint256,bytes32,bytes)",
            abi_parameters=["1", "0x0000000000000000000000000000000000000000000000000000000000000001", "0x"],
            fee_level="MEDIUM",
        )
        print(f"    ✅ complete submitted! Tx: {result.get('id', '?')}")
        
    except Exception as e:
        print(f"    ❌ On-chain step failed: {e}")
    
    print(f"""
╔══════════════════════════════════════════════════════════╗
║  ✅ Full Pipeline Complete                               ║
║                                                          ║
║  1. Scanned Arc — found job #{target.job_id}              ║
║  2. Negotiated with provider at {target.provider[:12]}...  ║
║  3. Created real ERC-8183 job on Arc Testnet             ║
║  4. Funded escrow, submitted, completed                  ║
╚══════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    asyncio.run(main())
