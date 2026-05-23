"""Tests for Arc Identity Manager (ArcIdentityManager in mock mode)."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from convenatai.agent import Agent, Wallet
from convenatai.arc_identity import ArcIdentityManager


def test_identity_manager_mock_mode():
    """ArcIdentityManager starts in mock mode when use_live=False."""
    mgr = ArcIdentityManager(use_live=False)
    assert mgr.is_live is False


def test_register_agent_identity():
    """Registering an agent identity works in mock mode."""
    mgr = ArcIdentityManager(use_live=False)
    agent = Agent("TestAgent", "trader", wallet=Wallet(balance=100))
    result = mgr.register_agent_identity(agent)
    assert result["status"] == "registered"
    assert result["address"] == "TestAgent"  # no real address, uses name


def test_register_agent_identity_with_address():
    """Registration uses wallet address when available."""
    mgr = ArcIdentityManager(use_live=False)
    agent = Agent("TestAgent", "trader", wallet=Wallet(balance=100))
    agent.wallet.address = "0x1234567890abcdef"
    result = mgr.register_agent_identity(agent, "did:example:agent")
    assert result["status"] == "registered"
    assert result["address"] == "0x1234567890abcdef"
    assert result["metadata_uri"] == "did:example:agent"


def test_get_agent_identity_found():
    """Getting identity returns stored info after registration."""
    mgr = ArcIdentityManager(use_live=False)
    agent = Agent("Agent", "trader", wallet=Wallet(balance=100))
    mgr.register_agent_identity(agent)
    info = mgr.get_agent_identity("Agent")
    assert info.registered is True
    assert "did:convenatai:Agent:trader" in info.metadata_uri


def test_get_agent_identity_not_found():
    """Getting identity for unregistered agent returns unregistered info."""
    mgr = ArcIdentityManager(use_live=False)
    info = mgr.get_agent_identity("0xUnknown")
    assert info.registered is False
    assert info.metadata_uri == ""


def test_is_agent_registered():
    """is_agent_registered reflects registration status correctly."""
    mgr = ArcIdentityManager(use_live=False)
    agent = Agent("RegAgent", "broker", wallet=Wallet(balance=100))
    assert mgr.is_agent_registered("RegAgent") is False
    mgr.register_agent_identity(agent)
    assert mgr.is_agent_registered("RegAgent") is True


def test_get_reputation_default():
    """Unregistered agents get score=0 reputation."""
    mgr = ArcIdentityManager(use_live=False)
    rep = mgr.get_agent_reputation("0xUnregistered")
    assert rep.score == 0
    assert rep.onchain is False


def test_update_reputation():
    """Updating reputation stores and returns the new score."""
    mgr = ArcIdentityManager(use_live=False)
    caller = Agent("Admin", "admin", wallet=Wallet(balance=1000))
    caller.wallet.address = "0xAdmin"
    result = mgr.update_agent_reputation(caller, "0xTargetAgent", 85)
    assert result["status"] == "updated"
    assert result["score"] == 85

    # Verify retrieval
    rep = mgr.get_agent_reputation("0xTargetAgent")
    assert rep.score == 85


def test_validate_agent_default():
    """Unregistered agents are not validated in mock mode."""
    mgr = ArcIdentityManager(use_live=False)
    val = mgr.validate_agent("0xUnknown")
    assert val.is_valid is False


def test_validate_registered_agent():
    """Registered agents are valid in mock mode."""
    mgr = ArcIdentityManager(use_live=False)
    agent = Agent("ValidAgent", "trader", wallet=Wallet(balance=100))
    mgr.register_agent_identity(agent)
    val = mgr.validate_agent("ValidAgent")
    assert val.is_valid is True


def test_set_agent_validation():
    """Setting validation status works in mock mode."""
    mgr = ArcIdentityManager(use_live=False)
    caller = Agent("Admin", "admin", wallet=Wallet(balance=1000))
    result = mgr.set_agent_validation(caller, "0xAgent", True)
    assert result["status"] == "updated"
    assert result["valid"] is True

    val = mgr.validate_agent("0xAgent")
    assert val.is_valid is True


def test_register_agents_auto():
    """register_agents_auto registers multiple agents in batch."""
    mgr = ArcIdentityManager(use_live=False)
    a1 = Agent("A1", "trader", wallet=Wallet(balance=100))
    a2 = Agent("A2", "broker", wallet=Wallet(balance=200))
    results = mgr.register_agents_auto([a1, a2])
    assert len(results) == 2
    assert results[0]["status"] == "registered"

    # Second call skips already registered
    results2 = mgr.register_agents_auto([a1, a2])
    assert results2[0]["status"] == "already_registered"


def test_get_full_profile():
    """get_full_profile returns identity, reputation, and validation."""
    mgr = ArcIdentityManager(use_live=False)
    agent = Agent("ProfileAgent", "trader", wallet=Wallet(balance=100))
    mgr.register_agent_identity(agent)

    profile = mgr.get_full_profile("ProfileAgent")
    assert "identity" in profile
    assert "reputation" in profile
    assert "validation" in profile
    assert profile["identity"]["registered"] is True
