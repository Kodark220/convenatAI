"""Tests for Negotiation layer (Proposal, ProposalResponse, NegotiationSession)."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio

from convenatai.agent import Agent, Wallet
from convenatai.negotiation import Proposal, ProposalResponse, NegotiationSession
from convenatai.network import AgentRegistry, MessageBus


def test_proposal_create():
    """Proposal stores fields and auto-computes payment_schedule."""
    buyer = Agent("Buyer", "trading", wallet=Wallet(balance=1000))
    seller = Agent("Seller", "broker", wallet=Wallet(balance=500))
    p = Proposal(
        proposer=buyer,
        responder=seller,
        description="Data stream",
        price=12,
        duration=4,
        deliverable="signal",
    )
    assert p.price == 12
    assert p.duration == 4
    assert len(p.payment_schedule) == 4
    assert sum(p.payment_schedule) == 12.0  # 3+3+3+3


def test_proposal_with_updates():
    """Proposal.with_updates creates a new Proposal with overridden fields."""
    buyer = Agent("Buyer", "trading", wallet=Wallet(balance=1000))
    seller = Agent("Seller", "broker", wallet=Wallet(balance=500))
    p = Proposal(buyer, seller, "Data", 10, 4, "signal")
    p2 = p.with_updates(price=15, duration=6)
    assert p2.price == 15
    assert p2.duration == 6
    assert p2.proposer is buyer
    assert p2.description == "Data"
    # Original unchanged
    assert p.price == 10


def test_proposal_response_accepted():
    """ProposalResponse can represent an acceptance."""
    r = ProposalResponse(accepted=True)
    assert r.accepted is True
    assert r.declined is False
    assert r.counter is None


def test_proposal_response_declined():
    """ProposalResponse can represent a decline with reason."""
    r = ProposalResponse(declined=True, reason="Too expensive")
    assert r.declined is True
    assert r.accepted is False
    assert r.reason == "Too expensive"


def test_proposal_response_counter():
    """ProposalResponse can contain a counter-proposal."""
    buyer = Agent("Buyer", "trading", wallet=Wallet(balance=1000))
    seller = Agent("Seller", "broker", wallet=Wallet(balance=500))
    original = Proposal(buyer, seller, "Data", 10, 4, "signal")
    counter = original.with_updates(price=8)
    r = ProposalResponse(counter=counter)
    assert r.accepted is False
    assert r.counter is not None
    assert r.counter.price == 8


def test_negotiator_evaluate_accepts_good_terms():
    """Agent.evaluate returns accepted for reasonable terms."""
    buyer = Agent("Buyer", "trading", wallet=Wallet(balance=1000))
    seller = Agent("Seller", "broker", wallet=Wallet(balance=500))
    p = Proposal(buyer, seller, "Data", 10, 4, "signal")
    response = seller.evaluate(p)
    assert response.accepted is True


def test_negotiator_evaluate_declines_invalid():
    """Agent.evaluate declines proposals with zero/negative price or duration."""
    buyer = Agent("Buyer", "trading", wallet=Wallet(balance=1000))
    seller = Agent("Seller", "broker", wallet=Wallet(balance=500))
    p = Proposal(buyer, seller, "Bad", 0, 4, "signal")
    response = seller.evaluate(p)
    assert response.declined is True
    assert "Invalid terms" in response.reason


def test_negotiator_broker_counters_low_price():
    """Broker agents counter-offer when price is below 5."""
    buyer = Agent("Buyer", "trading", wallet=Wallet(balance=1000))
    broker = Agent("Broker", "broker", wallet=Wallet(balance=500))
    p = Proposal(buyer, broker, "Cheap data", 3, 4, "signal")
    response = broker.evaluate(p)
    assert response.accepted is False
    assert response.counter is not None
    assert response.counter.price >= 5


def test_negotiator_trading_counters_high_price():
    """Trading agents counter-offer when price exceeds 20."""
    buyer = Agent("Buyer", "trading", wallet=Wallet(balance=1000))
    seller = Agent("Seller", "trading", wallet=Wallet(balance=500))
    p = Proposal(buyer, seller, "Expensive data", 30, 4, "signal")
    response = seller.evaluate(p)
    assert response.accepted is False
    assert response.counter is not None
    assert response.counter.price < 30


def test_negotiation_session():
    """Full negotiation loop between agents via message bus reaches agreement."""
    async def run():
        registry = AgentRegistry()
        bus = MessageBus(registry)
        buyer = Agent("Buyer", "trading", wallet=Wallet(balance=1000))
        seller = Agent("Seller", "broker", wallet=Wallet(balance=500))
        bus.register_agent(buyer)
        bus.register_agent(seller)

        # Start handlers
        tasks = [
            asyncio.create_task(buyer.handle_messages()),
            asyncio.create_task(seller.handle_messages()),
        ]

        proposal = buyer.propose(
            responder=seller,
            description="Signal access",
            price=8,
            duration=4,
            deliverable="signal",
        )

        session = NegotiationSession(proposal)
        agreement = await session.run_async()
        assert agreement is not None
        assert agreement.price == 8

        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    asyncio.run(run())


def test_negotiation_session_reaches_max_rounds():
    """Negotiation returns None when max_rounds exhausted without agreement."""
    async def run():
        registry = AgentRegistry()
        bus = MessageBus(registry)
        # Both trading agents will counter high prices, creating a loop
        buyer = Agent("Buyer", "trading", wallet=Wallet(balance=1000))
        seller = Agent("Seller", "trading", wallet=Wallet(balance=500))
        bus.register_agent(buyer)
        bus.register_agent(seller)

        tasks = [
            asyncio.create_task(buyer.handle_messages()),
            asyncio.create_task(seller.handle_messages()),
        ]

        # High price that trading agents will counter downwards repeatedly
        proposal = buyer.propose(
            responder=seller,
            description="Expensive signal",
            price=100,  # Both are trading, so seller counters to 85, then roles flip
            duration=4,
            deliverable="signal",
        )

        session = NegotiationSession(proposal, max_rounds=2)
        agreement = await session.run_async()
        assert agreement is None  # No agreement within 2 rounds

        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    asyncio.run(run())
