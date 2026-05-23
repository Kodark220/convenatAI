"""Tests for Agent and Wallet classes."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from convenatai.agent import Agent, Wallet


def test_wallet_create():
    """Wallet can be created with a balance."""
    w = Wallet(balance=100.0)
    assert w.balance == 100.0
    assert w.reserved == 0.0
    assert w.available_balance() == 100.0


def test_wallet_deposit():
    """Wallet.deposit adds to balance."""
    w = Wallet(balance=50.0)
    w.deposit(25.0)
    assert w.balance == 75.0


def test_wallet_withdraw_sufficient():
    """Wallet.withdraw succeeds when balance covers the amount."""
    w = Wallet(balance=100.0)
    assert w.withdraw(40.0) is True
    assert w.balance == 60.0


def test_wallet_withdraw_insufficient():
    """Wallet.withdraw fails when balance is too low."""
    w = Wallet(balance=10.0)
    assert w.withdraw(20.0) is False
    assert w.balance == 10.0  # unchanged


def test_wallet_reserve():
    """Wallet.reserve reduces available balance."""
    w = Wallet(balance=100.0)
    assert w.reserve(30.0) is True
    assert w.reserved == 30.0
    assert w.available_balance() == 70.0


def test_wallet_reserve_insufficient():
    """Wallet.reserve fails when available balance is too low."""
    w = Wallet(balance=50.0)
    assert w.reserve(60.0) is False
    assert w.reserved == 0.0


def test_wallet_release():
    """Wallet.release returns reserved funds."""
    w = Wallet(balance=100.0)
    w.reserve(40.0)
    assert w.release(20.0) is True
    assert w.reserved == 20.0
    assert w.available_balance() == 80.0


def test_wallet_release_excessive():
    """Wallet.release fails when amount exceeds reserved."""
    w = Wallet(balance=100.0)
    w.reserve(10.0)
    assert w.release(20.0) is False


def test_wallet_transfer():
    """Wallet.transfer moves funds between wallets."""
    a = Wallet(balance=200.0)
    b = Wallet(balance=50.0)
    # Treat b as the recipient wallet holder — create minimal agents
    agent_a = Agent("A", "trader", wallet=a)
    agent_b = Agent("B", "broker", wallet=b)
    assert a.transfer(agent_b, 75.0) is True
    assert a.balance == 125.0
    assert b.balance == 125.0


def test_wallet_transfer_insufficient():
    """Wallet.transfer fails when balance is too low."""
    a = Wallet(balance=10.0)
    b = Wallet(balance=50.0)
    agent_a = Agent("A", "trader", wallet=a)
    agent_b = Agent("B", "broker", wallet=b)
    assert a.transfer(agent_b, 20.0) is False
    assert a.balance == 10.0
    assert b.balance == 50.0


def test_agent_create():
    """Agent can be created with a name, role, and wallet."""
    a = Agent("TestAgent", role="trader", wallet=Wallet(balance=500))
    assert a.name == "TestAgent"
    assert a.role == "trader"
    assert a.wallet.balance == 500.0
    assert a.trust_score == 100


def test_agent_create_default_wallet():
    """Agent creates a default wallet if none provided."""
    a = Agent("NoWalletAgent", role="broker")
    assert a.wallet is not None
    assert a.wallet.balance == 0.0


def test_agent_fund():
    """Agent.fund adds to wallet balance."""
    a = Agent("Agent", "trader", wallet=Wallet(balance=100))
    a.fund(50)
    assert a.wallet.balance == 150.0


def test_agent_propose():
    """Agent.propose creates a Proposal with correct fields."""
    buyer = Agent("Buyer", "trading", wallet=Wallet(balance=1000))
    seller = Agent("Seller", "broker", wallet=Wallet(balance=500))
    p = buyer.propose(
        responder=seller,
        description="Data feed access",
        price=10,
        duration=4,
        deliverable="signal",
    )
    assert p.proposer is buyer
    assert p.responder is seller
    assert p.price == 10
    assert p.duration == 4
    assert p.deliverable == "signal"


def test_agent_repr():
    """Agent repr shows name, role, balance."""
    a = Agent("MyAgent", "trader", wallet=Wallet(balance=250))
    r = repr(a)
    assert "MyAgent" in r
    assert "trader" in r
    assert "250" in r
