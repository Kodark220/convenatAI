"""Tests for Network layer (AgentRegistry, MessageBus)."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio

from convenatai.agent import Agent, Wallet
from convenatai.network import AgentRegistry, MessageBus, Message


def test_registry_register_and_lookup():
    """AgentRegistry stores and retrieves agents by name."""
    registry = AgentRegistry()
    agent = Agent("Alice", "trader", wallet=Wallet(balance=100))
    registry.register(agent)
    assert registry.lookup("Alice") is agent
    assert registry.lookup("Bob") is None


def test_registry_list():
    """AgentRegistry.list_agents returns all registered agents."""
    registry = AgentRegistry()
    a1 = Agent("A1", "trader", wallet=Wallet(balance=100))
    a2 = Agent("A2", "broker", wallet=Wallet(balance=200))
    registry.register(a1)
    registry.register(a2)
    agents = registry.list_agents()
    assert len(agents) == 2
    assert a1 in agents
    assert a2 in agents


def test_registry_find_by_role():
    """AgentRegistry.find_by_role filters agents by role."""
    registry = AgentRegistry()
    a1 = Agent("A1", "trader", wallet=Wallet(balance=100))
    a2 = Agent("A2", "broker", wallet=Wallet(balance=200))
    a3 = Agent("A3", "broker", wallet=Wallet(balance=300))
    registry.register(a1)
    registry.register(a2)
    registry.register(a3)
    brokers = registry.find_by_role("broker")
    assert len(brokers) == 2
    assert a2 in brokers
    assert a3 in brokers
    assert a1 not in brokers


def test_message_create():
    """Message dataclass stores fields correctly."""
    msg = Message(sender="A", receiver="B", type="proposal", payload={"price": 10}, session_id="sess-1")
    assert msg.sender == "A"
    assert msg.receiver == "B"
    assert msg.type == "proposal"
    assert msg.payload == {"price": 10}
    assert msg.session_id == "sess-1"


def test_message_bus_register_agent():
    """MessageBus.register_agent registers agent and attaches bus."""
    registry = AgentRegistry()
    bus = MessageBus(registry)
    agent = Agent("Alice", "trader", wallet=Wallet(balance=100))
    bus.register_agent(agent)
    assert registry.lookup("Alice") is agent
    assert agent.bus is bus


def test_message_bus_send_and_receive():
    """Messages sent via bus are received by the correct agent."""
    async def run():
        registry = AgentRegistry()
        bus = MessageBus(registry)
        alice = Agent("Alice", "trader", wallet=Wallet(balance=100))
        bob = Agent("Bob", "broker", wallet=Wallet(balance=100))
        bus.register_agent(alice)
        bus.register_agent(bob)

        msg = Message(sender="Alice", receiver="Bob", type="proposal", payload="hello")
        await bus.send(msg)

        queue = bus.queue_for("Bob")
        received = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert received.sender == "Alice"
        assert received.type == "proposal"
        assert received.payload == "hello"

    asyncio.run(run())


def test_message_bus_broadcast():
    """MessageBus.broadcast sends to all registered queues."""
    async def run():
        registry = AgentRegistry()
        bus = MessageBus(registry)
        alice = Agent("Alice", "trader", wallet=Wallet(balance=100))
        bob = Agent("Bob", "broker", wallet=Wallet(balance=100))
        bus.register_agent(alice)
        bus.register_agent(bob)

        msg = Message(sender="System", receiver="*", type="broadcast", payload="alert")
        await bus.broadcast(msg)

        q_alice = bus.queue_for("Alice")
        q_bob = bus.queue_for("Bob")
        received_a = await asyncio.wait_for(q_alice.get(), timeout=1.0)
        received_b = await asyncio.wait_for(q_bob.get(), timeout=1.0)
        assert received_a.payload == "alert"
        assert received_b.payload == "alert"

    asyncio.run(run())


def test_message_bus_unknown_receiver():
    """Sending to unregistered receiver raises RuntimeError."""
    async def run():
        registry = AgentRegistry()
        bus = MessageBus(registry)
        alice = Agent("Alice", "trader", wallet=Wallet(balance=100))
        bus.register_agent(alice)

        msg = Message(sender="Alice", receiver="Unknown", type="proposal", payload="x")
        try:
            await bus.send(msg)
            assert False, "Should have raised"
        except RuntimeError as e:
            assert "Unknown" in str(e)

    asyncio.run(run())
