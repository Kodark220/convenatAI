from __future__ import annotations
import argparse
import asyncio
from convenatai.agent import Agent, Wallet
from convenatai.network import AgentRegistry, MessageBus
from convenatai.negotiation import Proposal
from convenatai.service import ContractExecutionService, TransactionError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Negotiate and settle an agent contract.")
    parser.add_argument("--price", type=float, default=1200.0, help="Total contract price")
    parser.add_argument("--duration", type=int, default=5, help="Contract duration in work units")
    parser.add_argument("--description", type=str, default="Signal access contract", help="Contract description")
    parser.add_argument("--deliverable", type=str, default="signal_stream", help="Deliverable description")
    return parser.parse_args()


async def main(args: argparse.Namespace):
    registry = AgentRegistry()
    bus = MessageBus(registry)

    treasury = Agent("TreasuryAgent", role="treasury", wallet=Wallet(balance=5000))
    trader = Agent("TradingAgent", role="trading", wallet=Wallet(balance=1500))
    broker = Agent("DataBrokerAgent", role="broker", wallet=Wallet(balance=2000))

    bus.register_agent(treasury)
    bus.register_agent(trader)
    bus.register_agent(broker)

    print("\n[1] Discovery")
    print("Available agents:")
    for agent in registry.list_agents():
        print(f" - {agent.name} ({agent.role}) wallet=${agent.wallet.balance:.2f}")

    print("\n[2] Negotiation")
    proposal = Proposal(
        proposer=trader,
        responder=broker,
        description=args.description,
        price=args.price,
        duration=args.duration,
        deliverable=args.deliverable,
    )

    service = ContractExecutionService()
    try:
        outcome = await service.execute_trade(proposal, treasury=treasury)
    except TransactionError as exc:
        print(f"Transaction failed: {exc}")
        return

    print("\n[5] Final balances")
    for agent in [treasury, trader, broker]:
        print(f" - {agent.name}: ${agent.wallet.balance:.2f}")
    print(f"\nContract {outcome.contract.agreement_id} status: {outcome.contract.state.value}")
