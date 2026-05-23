"""
convenatAI — Live On-Chain Agent Worker
=========================================
Creates real ERC-8183 jobs on Arc Testnet every cycle.
No mock mode. No simulated deals. Every deal is a real blockchain transaction.
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

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("convenatAI.worker")

_shutdown = False

def _handle_signal(signum, frame):
    global _shutdown
    _shutdown = True
    logger.info("Shutdown signal received — finishing current cycle...")

signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="convenatAI — Live On-Chain Agent Worker")
    parser.add_argument("--interval", type=int, default=120, help="Loop interval in seconds")
    parser.add_argument("--price-min", type=float, default=10.0, help="Minimum deal price in USDC")
    parser.add_argument("--price-max", type=float, default=100.0, help="Maximum deal price in USDC")
    parser.add_argument("--duration", type=int, default=3, help="Stream duration in work units")
    parser.add_argument("--max-deals", type=int, default=2, help="Max deals per cycle")
    return parser.parse_args()


async def main():
    args = parse_args()

    # On Koyeb, CIRCLE_API_KEY and CIRCLE_ENTITY_SECRET come from env vars
    if not os.getenv("CIRCLE_API_KEY"):
        logger.error("CIRCLE_API_KEY not set — cannot run live mode")
        sys.exit(1)

    logger.info(f"{'='*60}")
    logger.info(f"  convenatAI LIVE Worker")
    logger.info(f"  Interval: {args.interval}s | Price: ${args.price_min}-{args.price_max}")
    logger.info(f"  Max deals/cycle: {args.max_deals}")
    logger.info(f"  Circle API: {'SET' if os.getenv('CIRCLE_API_KEY') else 'MISSING'}")
    logger.info(f"{'='*60}")

    # Import live modules
    from convenatai.agent import Agent, Wallet
    from convenatai.network import AgentRegistry, MessageBus
    from convenatai.negotiation import Proposal
    from convenatai.service import ContractExecutionService, TransactionError
    from convenatai.payment import ArcNanopaymentGateway
    from convenatai.arc_integration import ArcJobManager
    from convenatai.circle_client import list_wallets, HAS_CIRCLE

    logger.info(f"Circle SDK available: {HAS_CIRCLE}")

    # Bootstrap live service
    service = ContractExecutionService(
        gateway=ArcNanopaymentGateway(),
        arc_job_manager=ArcJobManager(use_live=True),
    )

    registry = AgentRegistry()
    bus = MessageBus(registry)

    agents = [
        Agent("TreasuryAgent",  role="treasury", wallet=Wallet(balance=10000.0)),
        Agent("TradingAgent",   role="trading",  wallet=Wallet(balance=2000.0)),
        Agent("DataBrokerAgent", role="broker",  wallet=Wallet(balance=1000.0)),
        Agent("AnalystAgent",    role="analyst", wallet=Wallet(balance=800.0)),
        Agent("ValidatorAgent",  role="validator", wallet=Wallet(balance=500.0)),
    ]

    # Register agents with their Circle wallets
    logger.info("Provisioning agent wallets on Arc Testnet...")
    try:
        service.arc.provision_agent_wallets(agents)
    except Exception as e:
        logger.warning(f"Wallet provisioning skipped (may already be registered): {e}")

    for agent in agents:
        bus.register_agent(agent)
    logger.info(f"Registered {len(agents)} agents")

    cycle_count = 0
    while not _shutdown:
        cycle_count += 1
        logger.info(f"── Cycle #{cycle_count} ──")
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")

        # Replenish Treasury if low
        treasury = next((a for a in agents if a.role == "treasury"), agents[0])
        if treasury.wallet.balance < 100:
            treasury.wallet.deposit(5000.0)
            logger.info(f"Treasury replenished: +$5000.00 USDC")

        # Pick random client-provider pair
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
                deliverable=f"https://api.convenantai.xyz/deliverables/{random.getrandbits(32):08x}",
            )

            logger.info(f"🚀 Creating LIVE on-chain deal: {client.name} → {provider.name} | ${price} USDC | {description[:30]}...")

            try:
                outcome = await service.execute_trade(proposal, treasury=treasury)
                stream = outcome.stream
                logger.info(f"✅ LIVE DEAL COMPLETED: ${stream.amount:.2f} streamed, {stream.delivered_units}/{stream.duration} units")
            except TransactionError as exc:
                logger.warning(f"Deal failed: {exc}")
                continue
            except Exception as exc:
                logger.error(f"Unexpected error: {exc}")
                continue

        # Log balances
        for a in agents:
            logger.info(f"  Balance | {a.name}: ${a.wallet.balance:.2f} USDC")

        total = sum(a.wallet.balance for a in agents)
        logger.info(f"[{ts}] Cycle #{cycle_count} done — pool: ${total:.2f} USDC")

        # Wait for next cycle
        for _ in range(args.interval):
            if _shutdown:
                break
            await asyncio.sleep(1)

    logger.info("=== Worker stopped ===")
    for a in agents:
        logger.info(f"  Final | {a.name}: ${a.wallet.balance:.2f} USDC")


if __name__ == "__main__":
    asyncio.run(main())
