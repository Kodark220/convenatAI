from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional

from .agent import Agent
from .negotiation import Proposal


class ContractState(Enum):
    DRAFT = "draft"
    PENDING = "pending"
    ACTIVE = "active"
    FULFILLED = "fulfilled"
    BREACHED = "breached"
    CANCELLED = "cancelled"
    ARBITRATED = "arbitrated"


@dataclass
class ContractClause:
    description: str
    due_units: int
    unit_price: float
    total_price: float
    penalty_rate: float = 0.1
    completed_units: int = 0

    @property
    def remaining_units(self) -> int:
        return max(0, self.due_units - self.completed_units)

    def progress(self, units: int) -> None:
        self.completed_units = min(self.due_units, self.completed_units + units)

    @property
    def fulfilled(self) -> bool:
        return self.completed_units >= self.due_units


@dataclass
class ContractSignature:
    signer: Agent
    signed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Escrow:
    payer: Agent
    amount: float
    balance: float = 0.0

    def fund(self) -> None:
        if not self.payer.wallet.withdraw(self.amount):
            raise RuntimeError(f"{self.payer.name} cannot fund escrow for ${self.amount:.2f}.")
        self.balance += self.amount
        print(f"Escrow funded with ${self.amount:.2f} from {self.payer.name}.")

    def release(self, payee: Agent, amount: float) -> None:
        if amount > self.balance:
            raise RuntimeError("Escrow has insufficient funds.")
        self.balance -= amount
        payee.wallet.deposit(amount)
        print(f"Released ${amount:.2f} from escrow to {payee.name}.")

    def refund(self) -> None:
        if self.balance > 0:
            self.payer.wallet.deposit(self.balance)
            print(f"Refunded ${self.balance:.2f} from escrow back to {self.payer.name}.")
            self.balance = 0.0


@dataclass
class LegalContract:
    proposal: Proposal
    clauses: List[ContractClause] = field(default_factory=list)
    signatures: List[ContractSignature] = field(default_factory=list)
    state: ContractState = ContractState.DRAFT
    escrow: Escrow = field(init=False)
    created_at: datetime = field(default_factory=datetime.utcnow)
    work_completed: int = 0
    disputes: List[str] = field(default_factory=list)
    agreement_id: str = field(default_factory=lambda: f"contract-{datetime.utcnow().timestamp()}")

    def __post_init__(self) -> None:
        self.proposer = self.proposal.proposer
        self.responder = self.proposal.responder
        self.clauses = [
            ContractClause(
                description=self.proposal.description,
                due_units=self.proposal.duration,
                unit_price=round(self.proposal.price / max(self.proposal.duration, 1), 2),
                total_price=self.proposal.price,
            )
        ]
        self.escrow = Escrow(payer=self.proposal.proposer, amount=self.proposal.price)
        self.state = ContractState.DRAFT

    @classmethod
    def from_proposal(cls, proposal: Proposal) -> "LegalContract":
        return cls(proposal=proposal)

    def sign(self, agent: Agent) -> None:
        if agent not in {self.proposer, self.responder}:
            raise RuntimeError("Only contract parties may sign the contract.")
        if any(signature.signer is agent for signature in self.signatures):
            return
        self.signatures.append(ContractSignature(signer=agent))
        print(f"{agent.name} signed the legal contract.")
        if self.is_fully_signed() and self.state == ContractState.DRAFT:
            self.state = ContractState.PENDING
            print("Contract is fully signed and pending activation.")

    def is_fully_signed(self) -> bool:
        signers = {signature.signer for signature in self.signatures}
        return signers == {self.proposer, self.responder}

    def activate(self) -> None:
        if self.state != ContractState.PENDING:
            raise RuntimeError("Contract can only be activated from pending state.")
        if not self.is_fully_signed():
            raise RuntimeError("Contract must be signed by both parties before activation.")
        self.escrow.fund()
        self.state = ContractState.ACTIVE
        print(f"Contract {self.agreement_id} activated between {self.proposer.name} and {self.responder.name}.")

    def record_delivery(self, units: int) -> None:
        if self.state != ContractState.ACTIVE:
            raise RuntimeError("Contract is not active.")
        clause = self.clauses[0]
        clause.progress(units)
        self.work_completed += units
        print(f"Contract progress: {clause.completed_units}/{clause.due_units} units delivered.")
        if clause.fulfilled:
            self.state = ContractState.FULFILLED
            print("Contract has been fulfilled.")

    def report_delivery(self, delivered_units: int) -> None:
        self.record_delivery(delivered_units)

    def breach(self, reason: str) -> None:
        if self.state not in {ContractState.ACTIVE, ContractState.PENDING}:
            raise RuntimeError("Contract cannot be breached in its current state.")
        self.state = ContractState.BREACHED
        self.disputes.append(reason)
        print(f"Contract breached: {reason}")

    def cancel(self) -> None:
        if self.state in {ContractState.ACTIVE, ContractState.PENDING, ContractState.DRAFT}:
            self.state = ContractState.CANCELLED
            self.escrow.refund()
            print("Contract canceled and escrow funds refunded.")

    def settle(self, stream: "NanopaymentStream") -> None:
        if not stream.completed:
            raise RuntimeError("Cannot settle before payment stream completes.")
        if self.state == ContractState.FULFILLED:
            print("Contract settled successfully.")
        elif self.state == ContractState.ACTIVE:
            self.breach("Payment completed before confirmed fulfillment.")
        elif self.state == ContractState.BREACHED:
            print("Contract remains breached after payment completion.")

    def dispute(self, message: str) -> None:
        self.disputes.append(message)
        print(f"Dispute registered: {message}")


@dataclass
class Arbitrator:
    name: str = "GenLayer Judge"

    def adjudicate(self, contract: LegalContract, stream: "NanopaymentStream") -> ContractState:
        if contract.state not in {ContractState.BREACHED, ContractState.ACTIVE}:
            raise RuntimeError("Contract may only be arbitrated when active or breached.")
        clause = contract.clauses[0]
        if clause.fulfilled:
            contract.state = ContractState.FULFILLED
            print(f"{self.name} adjudicated: work completed, contract is fulfilled.")
        elif contract.work_completed >= clause.due_units * 0.75:
            contract.state = ContractState.ARBITRATED
            print(f"{self.name} adjudicated: partial delivery sufficient for payee despite dispute.")
        else:
            contract.state = ContractState.CANCELLED
            contract.escrow.refund()
            print(f"{self.name} adjudicated: insufficient delivery, funds refunded.")
        return contract.state
