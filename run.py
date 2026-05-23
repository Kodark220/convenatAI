"""
convenatAI — End-to-End Demo
============================
Demonstrates the full coordination layer flow:

  1. DISCOVERY   — Agents find each other on the registry
  2. NEGOTIATION — P2P counter-offer loop until agreement
  3. STREAM      — Arc nanopayment channel opens, USDC streams tick-by-tick
  4. ENFORCE     — GenLayer SLA monitor is notified (bridge hook)
  5. SETTLE      — Channel closes, final balances printed

Drop your CIRCLE_API_KEY + CIRCLE_ENTITY_SECRET into .env
to go fully live on Arc Testnet. Without keys, falls back
to local mock math so you can still run the demo offline.
"""

import argparse
import asyncio
import logging
import os
from dotenv import load_dotenv

from convenatai.agent import Agent, Wallet
from convenatai.network import AgentRegistry, MessageBus
from convenatai.negotiation import Proposal
from convenatai.service import ContractExecutionService, TransactionError
from convenatai.payment import ArcNanopaymentGateway
from convenatai.arc_integration import ArcJobManager

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("convenatai.run")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="convenatAI — Agent coordination layer demo.")
    parser.add_argument("--price", type=float, default=1500.0, help="Opening offer price in USDC")
    parser.add_argument("--duration", type=int, default=5, help="Stream duration in work units")
    parser.add_argument("--description", type=str, default="Twitter sentiment data stream", help="Deal description")
    parser.add_argument("--deliverable", type=str, default="https://api.example.com/sentiment/live", help="Deliverable URI (used by GenLayer SLA monitor)")
    parser.add_argument("--live", action="store_true", help="Use live Arc Testnet mode (requires funded wallets)")
    return parser.parse_args()


async def main(args: argparse.Namespace):
    # ------------------------------------------------------------------ #
    # 0. Bootstrap                                                         #
    # ------------------------------------------------------------------ #
    service = ContractExecutionService(
        gateway=ArcNanopaymentGateway(),
        arc_job_manager=ArcJobManager(use_live=args.live),
    )
    mode = "🔴 LIVE (Arc Testnet)" if service.arc.is_live else "🟡 LOCAL MOCK (no API keys)"
    print(f"\n{'='*58}")
    print(f"  convenatAI — Agent Economic Coordination Layer")
    print(f"  Mode: {mode}")
    print(f"{'='*58}\n")

    registry = AgentRegistry()
    bus = MessageBus(registry)

    # Create agents
    treasury = Agent("TreasuryAgent", role="treasury", wallet=Wallet(balance=5000.0))
    trader   = Agent("TradingAgent",  role="trading",  wallet=Wallet(balance=500.0))
    broker   = Agent("DataBrokerAgent", role="broker", wallet=Wallet(balance=200.0))

    if service.arc.is_live:
        service.arc.provision_agent_wallets([treasury, trader, broker])
        print(f"\n   Arc wallets provisioned — use small amounts (prices in USDC)")
        print(f"   Client: {trader.wallet.address}")
        print(f"   Provider: {broker.wallet.address}")

    for agent in [treasury, trader, broker]:
        bus.register_agent(agent)

    # ------------------------------------------------------------------ #
    # 1. DISCOVERY                                                         #
    # ------------------------------------------------------------------ #
    print("[1] DISCOVERY — Agents online")
    for agent in registry.list_agents():
        addr = agent.wallet.address if agent.wallet.address else "LocalMock"
        print(f"    • {agent.name:20s} role={agent.role:10s}  wallet={addr}")

    # ------------------------------------------------------------------ #
    # 2. NEGOTIATION                                                       #
    # ------------------------------------------------------------------ #
    print(f"\n[2] NEGOTIATION — TradingAgent opens offer at ${args.price:.2f} USDC")
    proposal = Proposal(
        proposer=trader,
        responder=broker,
        description=args.description,
        price=args.price,
        duration=args.duration,
        deliverable=args.deliverable,
    )

    # ------------------------------------------------------------------ #
    # 3–5. STREAM + ENFORCE + SETTLE                                       #
    # ------------------------------------------------------------------ #
    print(f"\n[3] EXECUTION — Handing off to ContractExecutionService...")
    try:
        outcome = await service.execute_trade(proposal, treasury=treasury)
    except TransactionError as exc:
        logger.error(f"Transaction failed: {exc}")
        return

    # ------------------------------------------------------------------ #
    # 6. FINAL STATE                                                       #
    # ------------------------------------------------------------------ #
    print(f"\n[4] FINAL BALANCES")
    for agent in [treasury, trader, broker]:
        print(f"    • {agent.name:20s}  ${agent.wallet.balance:.2f} USDC")

    stream = outcome.stream
    print(f"\n[5] STREAM SUMMARY")
    print(f"    Total streamed : ${stream.amount:.2f} USDC")
    print(f"    Units delivered: {stream.delivered_units}/{stream.duration}")
    print(f"    Completed      : {stream.completed}")
    print(f"\n{'='*58}")
    print(f"  ✅ convenatAI deal settled successfully.")
    print(f"{'='*58}\n")


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args))

