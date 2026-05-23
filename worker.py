"""
convenatAI — Persistent Agent Worker
=====================================
Runs 24/7 on OCI: discovers jobs, negotiates deals, executes trades.
Loops continuously with configurable interval.
"""

import argparse
import asyncio
import logging
import os
import random
import signal
import sys
import time
from datetime import datetime, timezone
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
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("convenatAI.worker")

# ─── Global shutdown flag ────────────────────────────────────────────────────
_shutdown = False

def _handle_signal(signum, frame):
    global _shutdown
    _shutdown = True
    logger.info(f"Signal {signum} received — shutting down gracefully...")

signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="convenatAI — 24/7 Agent Worker")
    parser.add_argument("--interval", type=int, default=120,
                        help="Loop interval in seconds (default: 120)")
    parser.add_argument("--live", action="store_true",
                        help="Use live Arc Testnet mode")
    parser.add_argument("--price-min", type=float, default=50.0,
                        help="Minimum deal price in USDC")
    parser.add_argument("--price-max", type=float, default=500.0,
                        help="Maximum deal price in USDC")
    parser.add_argument("--duration", type=int, default=3,
                        help="Stream duration in work units")
    parser.add_argument("--max-deals", type=int, default=3,
                        help="Max deals per cycle")
    parser.add_argument("--treasury-start", type=float, default=10000.0,
                        help="Starting balance for TreasuryAgent")
    return parser.parse_args()


async def worker_cycle(service, registry, bus, agents, args) -> int:
    """
    One cycle of the agent worker:
    1. Check pool balance — replenish Treasury if needed
    2. Pick random client-provider pair
    3. Negotiate and execute trades
    """
    deals_done = 0
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")

    logger.info(f"[{ts}] Worker cycle starting...")

    # Find TreasuryAgent and replenish if low
    treasury = next((a for a in agents if a.role == "treasury"), agents[0])
    if treasury.wallet.balance < 100:
        replenish = args.treasury_start / 2
        treasury.wallet.deposit(replenish)
        logger.info(f"Treasury replenished: +${replenish:.2f} USDC")

    online = registry.list_agents()
    logger.info(f"Agents online: {len(online)}")

    # Build client-provider pairs (skip Treasury as client)
    clients = [a for a in agents if a.role in ("trading", "analyst")] or agents
    providers = [a for a in agents if a.role in ("broker", "validator")] or agents

    for _ in range(min(args.max_deals, len(agents))):
        if _shutdown:
            break

        client = random.choice(clients)
        provider = random.choice([p for p in providers if p.name != client.name] or providers)

        price = round(random.uniform(args.price_min, args.price_max), 2)
        description = random.choice([
            "Twitter sentiment data stream",
            "Market analysis report",
            "Price prediction model",
            "Risk assessment feed",
            "Trading signal aggregation",
        ])

        proposal = Proposal(
            proposer=client,
            responder=provider,
            description=description,
            price=price,
            duration=args.duration,
            deliverable=f"https://api.convenat.ai/deliverables/{random.getrandbits(32):08x}",
        )

        logger.info(f"Deal: {client.name} → {provider.name} | ${price} USDC | {description[:30]}...")

        try:
            outcome = await service.execute_trade(proposal, treasury=treasury)
            stream = outcome.stream
            logger.info(f"✅ Deal done: ${stream.amount:.2f} streamed, {stream.delivered_units}/{stream.duration} units")
            deals_done += 1
        except TransactionError as exc:
            logger.warning(f"Deal failed: {exc}")
            continue
        except Exception as exc:
            logger.error(f"Unexpected error: {exc}")
            continue

    for a in online:
        logger.info(f"  Balance | {a.name}: ${a.wallet.balance:.2f} USDC")

    logger.info(f"[{ts}] Cycle done — {deals_done} deals")
    return deals_done


async def main():
    args = parse_args()
    mode = "LIVE" if args.live else "MOCK"
    logger.info(f"{'='*60}")
    logger.info(f"  convenatAI Worker — Mode: {mode}")
    logger.info(f"  Interval: {args.interval}s | Price: ${args.price_min}-{args.price_max}")
    logger.info(f"  Max deals/cycle: {args.max_deals}")
    logger.info(f"{'='*60}")

    service = ContractExecutionService(
        gateway=ArcNanopaymentGateway(),
        arc_job_manager=ArcJobManager(use_live=args.live),
    )

    registry = AgentRegistry()
    bus = MessageBus(registry)

    agents = [
        Agent("TreasuryAgent",  role="treasury", wallet=Wallet(balance=args.treasury_start)),
        Agent("TradingAgent",   role="trading",  wallet=Wallet(balance=2000.0)),
        Agent("DataBrokerAgent", role="broker",  wallet=Wallet(balance=1000.0)),
        Agent("AnalystAgent",    role="analyst", wallet=Wallet(balance=800.0)),
        Agent("ValidatorAgent",  role="validator", wallet=Wallet(balance=500.0)),
    ]

    if service.arc.is_live:
        logger.info("Live mode — provisioning Circle wallets...")
        service.arc.provision_agent_wallets(agents)

    for agent in agents:
        bus.register_agent(agent)
    logger.info(f"Registered {len(agents)} agents")

    cycle_count = 0
    while not _shutdown:
        cycle_count += 1
        logger.info(f"── Cycle #{cycle_count} ──")
        try:
            deals = await worker_cycle(service, registry, bus, agents, args)
            total = sum(a.wallet.balance for a in agents)
            logger.info(f"Cycle #{cycle_count}: {deals} deals, pool: ${total:.2f} USDC")
        except Exception as exc:
            logger.error(f"Cycle #{cycle_count} crashed: {exc}", exc_info=True)

        for _ in range(args.interval):
            if _shutdown:
                break
            await asyncio.sleep(1)

    logger.info("=== Worker stopped ===")
    for a in agents:
        logger.info(f"  Final | {a.name}: ${a.wallet.balance:.2f} USDC")


if __name__ == "__main__":
    asyncio.run(main())
