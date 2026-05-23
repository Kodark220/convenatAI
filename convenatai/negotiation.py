from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
import asyncio


@dataclass
class Proposal:
    proposer: "Agent"
    responder: "Agent"
    description: str
    price: float
    duration: int
    deliverable: str
    payment_schedule: List[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.payment_schedule and self.duration > 0:
            per_unit = round(self.price / self.duration, 2)
            self.payment_schedule = [per_unit] * self.duration
            remainder = round(self.price - sum(self.payment_schedule), 2)
            if remainder:
                self.payment_schedule[-1] += remainder

    def with_updates(self, **kwargs) -> "Proposal":
        return Proposal(
            proposer=kwargs.get("proposer", self.proposer),
            responder=kwargs.get("responder", self.responder),
            description=kwargs.get("description", self.description),
            price=kwargs.get("price", self.price),
            duration=kwargs.get("duration", self.duration),
            deliverable=kwargs.get("deliverable", self.deliverable),
            payment_schedule=kwargs.get("payment_schedule", self.payment_schedule),
        )


@dataclass
class ProposalResponse:
    accepted: bool = False
    declined: bool = False
    reason: Optional[str] = None
    counter: Optional[Proposal] = None


class NegotiationSession:
    def __init__(self, initial_proposal: Proposal, max_rounds: int = 5, session_id: Optional[str] = None):
        self.current = initial_proposal
        self.max_rounds = max_rounds
        self.round = 0
        self.history: List[Proposal] = [initial_proposal]
        self.session_id = session_id or f"session_{id(self)}"

    async def run_async(self) -> Optional[Proposal]:
        from .network import Message  # Import here to avoid circular import

        if self.current.proposer.bus is None or self.current.responder.bus is None:
            raise RuntimeError("Both negotiating agents must be attached to a message bus.")

        bus = self.current.proposer.bus
        bus.register_session(self.session_id)

        print(f"Starting async negotiation between {self.current.proposer.name} and {self.current.responder.name}")
        print(f"Initial terms: price=${self.current.price}, duration={self.current.duration}, deliverable={self.current.deliverable}")

        while self.round < self.max_rounds:
            self.round += 1
            # Send proposal to responder
            message = Message(
                sender=self.current.proposer.name,
                receiver=self.current.responder.name,
                type="proposal",
                payload=self.current,
                session_id=self.session_id
            )
            await self.current.proposer.bus.send(message)

            # Wait for the response on the dedicated session queue.
            session_queue = bus.queue_for(self.session_id)
            while True:
                response_msg = await session_queue.get()
                if response_msg.type == "response" and response_msg.session_id == self.session_id:
                    break

            response: ProposalResponse = response_msg.payload

            if response.accepted:
                print(f"{self.current.responder.name} accepted the deal on round {self.round}.")
                return self.current

            if response.declined:
                print(f"{self.current.responder.name} declined the deal: {response.reason}")
                return None

            if response.counter:
                print(
                    f"{self.current.responder.name} countered with price=${response.counter.price}, duration={response.counter.duration}"
                )
                self.current = response.counter
                self.history.append(self.current)
                self.current.proposer, self.current.responder = self.current.responder, self.current.proposer
                continue

            print("No valid response received; negotiation failed.")
            return None

        print("Negotiation reached maximum rounds without agreement.")
        return None

    def run(self) -> Optional[Proposal]:
        # Synchronous fallback for backward compatibility
        return asyncio.run(self.run_async())
