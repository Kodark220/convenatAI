from __future__ import annotations
import logging
import os
from dataclasses import dataclass, field
from typing import Any, List, Optional, TYPE_CHECKING
from dotenv import load_dotenv

from .network import Message

load_dotenv()

# Try to load Circle configuration from environment
HAS_CIRCLE = bool(os.getenv("CIRCLE_API_KEY") and os.getenv("CIRCLE_ENTITY_SECRET"))

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .network import MessageBus
    from .negotiation import Proposal, ProposalResponse

from .negotiation import Proposal, ProposalResponse


@dataclass
class Wallet:
    """
    Agent Wallet representing either a real Arc Developer-Controlled Wallet
    or a local mock if API keys are absent.
    """
    address: Optional[str] = None
    wallet_id: Optional[str] = None
    balance: float = 0.0
    reserved: float = 0.0

    def __post_init__(self):
        if HAS_CIRCLE and not self.address:
            self._provision_arc_wallet()

    def _provision_arc_wallet(self):
        logger.info("Provisioning Arc Developer-Controlled Wallet for agent...")
        try:
            from .circle_client import create_wallets
            wallets = create_wallets(count=1)
            if wallets:
                self.address = wallets[0].address
                self.wallet_id = wallets[0].wallet_id
                logger.info(f"Arc Wallet provisioned: {self.address}")
            else:
                logger.error("No wallets returned from Circle API")
        except Exception as e:
            logger.error(f"Failed to provision Arc wallet: {e}")

    def deposit(self, amount: float) -> None:
        self.balance += amount

    def withdraw(self, amount: float) -> bool:
        if amount > self.balance:
            return False
        self.balance -= amount
        return True

    def reserve(self, amount: float) -> bool:
        if amount > self.available_balance():
            return False
        self.reserved += amount
        return True

    def release(self, amount: float) -> bool:
        if amount > self.reserved:
            return False
        self.reserved -= amount
        return True

    def transfer(self, recipient: "Agent", amount: float) -> bool:
        if not self.withdraw(amount):
            return False
        recipient.wallet.deposit(amount)
        return True

    def available_balance(self) -> float:
        return self.balance - self.reserved


class Agent:
    def __init__(self, name: str, role: str, wallet: Optional[Wallet] = None, capabilities: Optional[List[str]] = None):
        self.name = name
        self.role = role
        self.wallet = wallet or Wallet()
        self.capabilities = capabilities or []
        self.trust_score = 100
        self.bus: Optional["MessageBus"] = None
        self._pending_messages: List[Message] = []
        self.arc_agent_id: Optional[str] = None

    def register_onchain_identity(self, metadata_uri: str = "ipfs://example"):
        """Registers the agent on Arc using ERC-8004 IdentityRegistry."""
        if not HAS_CIRCLE or not self.wallet.address:
            logger.warning("Cannot register onchain identity without Arc wallet.")
            return

        IDENTITY_REGISTRY = "0x8004A818BFB912233c491871b3d84c89A494BD9e"
        logger.info(f"Registering {self.name} onchain identity on Arc...")
        
        try:
            from .circle_client import create_contract_execution_transaction
            response = create_contract_execution_transaction(
                wallet_address=self.wallet.address,
                contract_address=IDENTITY_REGISTRY,
                abi_function_signature="register(string)",
                abi_parameters=[metadata_uri],
            )
            logger.info(f"{self.name} registered identity. Tx ID: {response.get('id')}")
            # Note: A real app would poll for the tx hash and fetch the agent ID from the Transfer event.
        except Exception as e:
            logger.error(f"Failed to register identity: {e}")

    def attach_bus(self, bus: "MessageBus") -> None:
        self.bus = bus

    async def send_message(self, receiver: str, msg_type: str, payload: Any, session_id: Optional[str] = None) -> None:
        if self.bus is None:
            raise RuntimeError("Agent is not attached to a message bus.")
        message = Message(sender=self.name, receiver=receiver, type=msg_type, payload=payload, session_id=session_id)
        logger.debug("%s sending %s to %s session=%s", self.name, msg_type, receiver, session_id)
        print(f"{self.name} sending {msg_type} to {receiver}")
        await self.bus.send(message)

    async def receive_message(self, *, type: Optional[str] = None, session_id: Optional[str] = None, type_filter: Optional[set] = None) -> Message:
        if self.bus is None:
            raise RuntimeError("Agent is not attached to a message bus.")

        for index, pending in enumerate(self._pending_messages):
            if (type is None or pending.type == type) and (session_id is None or pending.session_id == session_id) and (type_filter is None or pending.type in type_filter):
                return self._pending_messages.pop(index)

        queue = self.bus.queue_for(self.name)
        while True:
            message = await queue.get()
            if (type is None or message.type == type) and (session_id is None or message.session_id == session_id) and (type_filter is None or message.type in type_filter):
                return message
            self._pending_messages.append(message)

    async def handle_messages(self) -> None:
        """Background task to process incoming messages."""
        while True:
            message = await self.receive_message(type_filter={"proposal", "contract_sign"})
            await self.process_message(message)

    async def process_message(self, message: Message) -> None:
        logger.debug("%s processing %s from %s session=%s", self.name, message.type, message.sender, message.session_id)
        if message.type == "proposal":
            proposal: Proposal = message.payload
            response = self.evaluate(proposal)
            print(f"{self.name} evaluated proposal: accepted={response.accepted}, declined={response.declined}, counter={response.counter is not None}")
            receiver = message.session_id or message.sender
            await self.send_message(receiver, "response", response, message.session_id)
        elif message.type == "contract_sign":
            contract: "Contract" = message.payload
            self.sign(contract)
            await self.send_message(message.sender, "signed", contract, message.session_id)
        elif message.type == "response":
            # Response messages are handled by the negotiation session, not by agents
            pass

    def propose(
        self,
        responder: "Agent",
        description: str,
        price: float,
        duration: int,
        deliverable: str,
        payment_schedule: Optional[List[float]] = None,
    ) -> Proposal:
        return Proposal(
            proposer=self,
            responder=responder,
            description=description,
            price=price,
            duration=duration,
            deliverable=deliverable,
            payment_schedule=payment_schedule,
        )

    def evaluate(self, proposal: Proposal) -> ProposalResponse:
        if proposal.price <= 0 or proposal.duration <= 0:
            return ProposalResponse(declined=True, reason="Invalid terms")

        if self.role == "broker":
            if proposal.price < 5:
                counter_price = max(proposal.price * 1.5, 5)
                return ProposalResponse(counter=proposal.with_updates(price=counter_price))
            return ProposalResponse(accepted=True)

        if self.role == "trading":
            if proposal.price > 20:
                counter_price = max(proposal.price * 0.85, 20)
                return ProposalResponse(counter=proposal.with_updates(price=counter_price))
            return ProposalResponse(accepted=True)

        return ProposalResponse(accepted=True)

    def sign(self, contract: "Contract") -> None:
        contract.sign(self)

    def fund(self, amount: float) -> None:
        self.wallet.deposit(amount)

    def __repr__(self) -> str:
        addr = self.wallet.address if self.wallet.address else "LocalMock"
        return f"Agent(name={self.name}, role={self.role}, address={addr}, balance={self.wallet.balance})"
