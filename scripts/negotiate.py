"""
convenatAI — Autonomous Agent: Scan & Negotiate

An agent that:
1. Scans Arc Testnet for Open jobs
2. Picks one to bid on
3. Negotiates with the provider/responder
4. Creates a deal
"""

from __future__ import annotations
import asyncio
import logging
import os
import sys

# Ensure we can import convenatai
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from convenatai.agent import Agent, Wallet
from convenatai.network import AgentRegistry, MessageBus
from convenatai.negotiation import Proposal
from convenatai.service import ContractExecutionService, TransactionError
from convenatai.payment import ArcNanopaymentGateway
from convenatai.arc_integration import ArcJobManager, JobStatus, STATUS_NAMES
from convenatai.discovery import AgentDiscovery, DiscoveredJob

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("convenatAI.bot")


def pick_best_job(jobs: list[DiscoveredJob], my_address: str) -> DiscoveredJob | None:
    """Pick the best Open job that isn't ours."""
    candidates = [j for j in jobs 
                  if j.client.lower() != my_address.lower()
                  and j.provider.lower() != my_address.lower()]
    
    if not candidates:
        return None
    
    # Just pick the first valid candidate
    return candidates[0]


async def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║     convenatAI — Autonomous Agent Negotiator            ║
║     Scans Arc Testnet, finds jobs, negotiates deals     ║
╚══════════════════════════════════════════════════════════╝
""")
    
    # ── Step 1: Scan for open jobs ──────────────────────────────────
    print("[1] 🔍 Scanning Arc Testnet for open jobs...")
    discovery = AgentDiscovery()
    jobs = discovery.scan_recent_jobs(lookback_blocks=5000)
    
    open_jobs = discovery.get_open_jobs()
    print(f"    Found {len(open_jobs)} open jobs, {len(discovery.get_agents())} unique agents")
    
    if not open_jobs:
        print("    No open jobs found. Try a wider scan.")
        return
    
    # ── Step 2: Pick a job ─────────────────────────────────────────
    my_wallet = "0x1505102c7247b0e3323e689cb5bc6a142dff4408"
    target = pick_best_job(open_jobs, my_wallet)
    
    if not target:
        print("    All open jobs are ours. Nothing to negotiate.")
        return
    
    print(f"\n[2] 🎯 Picked job #{target.job_id}")
    print(f"    Client: {target.client}")
    print(f"    Provider: {target.provider}")
    
    # ── Step 3: Set up agents ───────────────────────────────────────
    print("\n[3] 🤖 Setting up agents...")
    
    registry = AgentRegistry()
    bus = MessageBus(registry)
    
    # My agent — the negotiator
    me = Agent(
        "AutoNegotiator",
        role="trading",
        wallet=Wallet(balance=500.0),
    )
    me.wallet.address = my_wallet
    
    # The provider we want to negotiate with
    provider = Agent(
        "OnChainProvider",
        role="broker",
        wallet=Wallet(balance=200.0),
    )
    provider.wallet.address = target.provider
    
    bus.register_agent(me)
    bus.register_agent(provider)
    
    print(f"    🤖 AutoNegotiator (me): {me.wallet.address}")
    print(f"    🤖 Provider (them):     {provider.wallet.address}")
    
    # ── Step 4: Propose a deal ──────────────────────────────────────
    print(f"\n[4] 💬 Proposing deal to provider of job #{target.job_id}...")
    
    proposal = Proposal(
        proposer=me,
        responder=provider,
        description=f"Let's work together on job #{target.job_id}",
        price=8.0,
        duration=3,
        deliverable="data_stream",
    )
    
    # ── Step 5: Negotiate & Execute ────────────────────────────────
    print("\n[5] 🤝 Starting negotiation...")
    
    service = ContractExecutionService(
        gateway=ArcNanopaymentGateway(),
        arc_job_manager=ArcJobManager(use_live=False),
    )
    
    try:
        outcome = await service.execute_trade(proposal)
        print(f"\n    ✅ Deal reached!")
        print(f"    Contract: {outcome.contract.agreement_id}")
        print(f"    State: {outcome.contract.state.value}")
        print(f"    Streamed: ${outcome.stream.amount:.2f}")
        
    except TransactionError as e:
        print(f"\n    ❌ Negotiation failed: {e}")
        return
    
    # ── Summary ─────────────────────────────────────────────────────
    print(f"""
╔══════════════════════════════════════════════════════════╗
║  ✅ Deal Summary                                         ║
║                                                          ║
║  Discovered job #{target.job_id} on Arc Testnet            ║
║  Negotiated with provider at {target.provider[:12]}...  ║
║  Reached agreement at ${outcome.stream.amount:.2f}         ║
║  Stream completed: {outcome.stream.completed}                        ║
╚══════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    asyncio.run(main())
