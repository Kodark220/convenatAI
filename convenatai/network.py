from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .agent import Agent


@dataclass
class Message:
    sender: str
    receiver: str
    type: str
    payload: Any
    session_id: Optional[str] = None


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: Dict[str, "Agent"] = {}

    def register(self, agent: "Agent") -> None:
        self._agents[agent.name] = agent
        print(f"Registered agent: {agent.name} ({agent.role})")

    def lookup(self, name: str) -> "Agent" | None:
        return self._agents.get(name)

    def list_agents(self) -> List["Agent"]:
        return list(self._agents.values())

    def find_by_role(self, role: str) -> List["Agent"]:
        return [agent for agent in self._agents.values() if agent.role == role]


class MessageBus:
    def __init__(self, registry: AgentRegistry) -> None:
        self.registry = registry
        self._queues: Dict[str, asyncio.Queue[Message]] = {}

    def register_agent(self, agent: "Agent") -> None:
        self.registry.register(agent)
        self._queues[agent.name] = asyncio.Queue()
        agent.attach_bus(self)

    def register_session(self, session_id: str) -> None:
        self._queues[session_id] = asyncio.Queue()

    def queue_for(self, name: str) -> asyncio.Queue[Message]:
        if name not in self._queues:
            raise RuntimeError(f"No message queue registered for {name}.")
        return self._queues[name]

    async def send(self, message: Message) -> None:
        queue = self._queues.get(message.receiver)
        if queue is None:
            raise RuntimeError(f"Receiver {message.receiver} is not registered on the bus.")
        await queue.put(message)

    async def broadcast(self, message: Message) -> None:
        for queue in self._queues.values():
            await queue.put(message)
