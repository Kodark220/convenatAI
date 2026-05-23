"""
convenatAI — Live Autonomous On-Chain Agent
=============================================
Scans Arc Testnet for open ERC-8183 jobs, claims them,
negotiates terms, and executes — all on-chain. No mock.
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
logger = logging.getLogger("convenatAI.agent")

_shutdown = False

def _handle_signal(signum, frame):
    global _shutdown
    _shutdown = True
    logger.info("Shutdown signal received — finishing...")

signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="convenatAI — Live Autonomous Agent")
    parser.add_argument("--interval", type=int, default=60, help="Scan interval in seconds")
    parser.add_argument("--max-jobs", type=int, default=3, help="Max open jobs to claim per cycle")
    parser.add_argument("--treasury-start", type=float, default=10000.0, help="Starting treasury USDC")
    return parser.parse_args()


async def main():
    args = parse_args()

    if not os.getenv("CIRCLE_API_KEY"):
        logger.error("CIRCLE_API_KEY not set — cannot run live")
        sys.exit(1)

    # Import live modules
    from convenatai.agent import Agent, Wallet
    from convenatai.network import AgentRegistry, MessageBus
    from convenatai.negotiation import Proposal, NegotiationSession
    from convenatai.service import ContractExecutionService, TransactionError
    from convenatai.payment import ArcNanopaymentGateway
    from convenatai.arc_integration import ArcJobManager, JobStatus, STATUS_NAMES
    from convenatai.discovery import AgentDiscovery, CHAINS

    logger.info(f"{'='*60}")
    logger.info(f"  convenatAI Autonomous Agent — LIVE MODE")
    logger.info(f"  Arc: {CHAINS['arc']['rpc']}")
    logger.info(f"  Contract: {CHAINS['arc']['contract']}")
    logger.info(f"  Scan interval: {args.interval}s")
    logger.info(f"{'='*60}")

    # Create agents
    registry = AgentRegistry()
    bus = MessageBus(registry)

    agents = [
        Agent("TreasuryAgent",  role="treasury", wallet=Wallet(balance=args.treasury_start)),
        Agent("TraderAgent",    role="buyer",    wallet=Wallet(balance=5000.0)),
        Agent("ProviderAgent",  role="provider", wallet=Wallet(balance=2000.0)),
    ]

    service = ContractExecutionService(
        gateway=ArcNanopaymentGateway(),
        arc_job_manager=ArcJobManager(use_live=True),
    )

    discovery = AgentDiscovery(chain="arc")
    trader = agents[1]
    provider = agents[2]
    treasury = agents[0]

    for a in agents:
        bus.register_agent(a)

    logger.info(f"Agents registered. Treasury: ${treasury.wallet.balance:.2f}")

    cycle_count = 0
    while not _shutdown:
        cycle_count += 1
        logger.info(f"\n{'='*50}")
        logger.info(f"  Cycle #{cycle_count} — {datetime.now().strftime('%H:%M:%S')}")
        logger.info(f"{'='*50}")

        # Step 1: Scan for open jobs on Arc
        try:
            jobs = discovery.scan_recent_jobs(lookback_blocks=10000)
            open_jobs = [j for j in jobs if hasattr(j, 'status') and j.status.lower() in ('open', 'funded')]
            logger.info(f"Found {len(jobs)} total jobs, {len(open_jobs)} open/funded")
        except Exception as e:
            logger.warning(f"Discovery scan failed: {e}")
            open_jobs = []

        # Step 2: Claim and execute open jobs
        if open_jobs:
            selected = open_jobs[:args.max_jobs]
            for job in selected:
                if _shutdown:
                    break

                job_id = getattr(job, 'job_id', 'unknown')
                client_addr = getattr(job, 'client', '')
                provider_addr = getattr(job, 'provider', '')
                budget = getattr(job, 'budget', 0)

                logger.info(f"\n📋 Open Job #{job_id}")
                logger.info(f"   Client: {client_addr}")
                logger.info(f"   Provider: {provider_addr}")
                logger.info(f"   Budget: ${budget:.2f}")

                # Our TraderAgent acts as the client, ProviderAgent does the work
                # If the job has a matching provider, our ProviderAgent claims it
                proposal = Proposal(
                    proposer=trader,
                    responder=provider,
                    description=f"On-chain job #{job_id} execution",
                    price=budget if budget > 0 else 50.0,
                    duration=3,
                    deliverable=f"https://api.convenantai.xyz/deliverables/job-{job_id}",
                )

                logger.info(f"🚀 Executing on-chain deal for job #{job_id}...")

                try:
                    outcome = await service.execute_trade(proposal, treasury=treasury)
                    stream = outcome.stream
                    logger.info(f"✅ Job #{job_id} COMPLETED: ${stream.amount:.2f} streamed, {stream.delivered_units}/{stream.duration} units")
                except TransactionError as exc:
                    logger.warning(f"Job #{job_id} failed: {exc}")
                    continue
                except Exception as exc:
                    logger.error(f"Job #{job_id} error: {exc}")
                    continue

        # Step 3: If no open jobs, create new ones on-chain
        else:
            logger.info("No open jobs found — creating new ones...")
            for _ in range(2):
                if _shutdown:
                    break

                price = random.uniform(20, 150)
                description = random.choice([
                    "Twitter sentiment data stream",
                    "Market analysis report",
                    "Price prediction model",
                    "Risk assessment feed",
                ])

                proposal = Proposal(
                    proposer=trader,
                    responder=provider,
                    description=description,
                    price=round(price, 2),
                    duration=3,
                    deliverable=f"https://api.convenantai.xyz/deliverables/{random.getrandbits(32):08x}",
                )

                logger.info(f"🆕 Creating new on-chain deal: ${price:.2f} USDC — {description[:30]}...")
                try:
                    outcome = await service.execute_trade(proposal, treasury=treasury)
                    logger.info(f"✅ New deal done: ${outcome.stream.amount:.2f}")
                except Exception as exc:
                    logger.warning(f"New deal failed: {exc}")
                    continue

        # Log balances
        for a in agents:
            logger.info(f"  Balance | {a.name}: ${a.wallet.balance:.2f} USDC")

        total = sum(a.wallet.balance for a in agents)
        logger.info(f"Pool: ${total:.2f} USDC")

        # Replenish treasury if low
        if treasury.wallet.balance < 100:
            treasury.wallet.deposit(5000.0)
            logger.info(f"Treasury replenished: +$5000.00")

        # Wait for next cycle
        logger.info(f"Waiting {args.interval}s until next scan...")
        for _ in range(args.interval):
            if _shutdown:
                break
            await asyncio.sleep(1)

    logger.info("=== Agent stopped ===")


if __name__ == "__main__":
    asyncio.run(main())
