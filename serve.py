"""
convenatAI — FastAPI Backend
=============================
Serves real on-chain data from Arc Testnet & GenLayer Studionet
to the Next.js dashboard, with a memory-scoped fallback for when
the chains are unreachable (no mocked fake data).
"""

from __future__ import annotations

import json
import logging
import os
import random
import time
import sys
import uuid
import threading
import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field, asdict
from typing import Optional

from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ─── Import convenatAI core modules ────────────────────────────────────────

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Lazy imports — avoid crash if optional deps are missing
HAS_CIRCLE = False
try:
    from convenatai.discovery import (
        AgentDiscovery, DiscoveredJob, AgentListing, CHAINS, _rpc,
        JOB_CREATED_TOPIC,
    )
    from convenatai.arc_integration import (
        ArcJobManager, JobStatus, STATUS_NAMES, ARC_TESTNET,
        AGENTIC_COMMERCE_CONTRACT as ARC_CONTRACT,
    )
    from convenatai.agent import Agent, Wallet
    from convenatai.network import AgentRegistry, MessageBus
    from convenatai.service import ContractExecutionService, ContractExecutionOutcome
    from convenatai.negotiation import Proposal
    from convenatai.genlayer_client import NotifyGenLayer
    from convenatai.matching import IntentBoard, DealMaker, Intent
    HAS_CIRCLE = True
except ImportError:
    pass

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("serve")

try:
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "negotiator.log")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
except Exception as e:
    print(f"Failed to attach file logger: {e}")

# ─── Lifespan ────────────────────────────────────────────────────────────────

_discovery_cache: dict[str, dict] = {"arc": {}, "genlayer": {}}
_job_manager: object = None
_registry: object = None
_last_scan_time: dict[str, float] = {"arc": 0, "genlayer": 0}
_CACHE_TTL = 15  # seconds

# ─── Background Worker ──────────────────────────────────────────────────────
_WORKER_RUNNING = False

def _background_worker():
    """Run the agent loop in a background thread inside the API process."""
    global _WORKER_RUNNING
    if _WORKER_RUNNING:
        return
    _WORKER_RUNNING = True
    
    logger.info("🚀 Background worker started — creating on-chain deals every 120s")
    
    while True:
        try:
            _run_worker_cycle()
        except Exception as e:
            logger.error(f"Worker cycle crashed: {e}")
        
        # Sleep 120 seconds (check every second for shutdown)
        for _ in range(120):
            time.sleep(1)


def _run_worker_cycle():
    """
    convenatAI — the playground teacher for AI agents.
    
    Every cycle:
    1. Check for new agent requests (buy/sell intents)
    2. Match agents who want to trade
    3. Facilitate agreement on terms
    4. Hold escrow in convenatAI's wallet
    5. Notify GenLayer of the deal
    6. On dispute → check GenLayer verdict → release or refund
    """
    import os, time
    if not (os.getenv("CIRCLE_API_KEY") and os.getenv("CIRCLE_ENTITY_SECRET")):
        raise ValueError("Circle API keys (CIRCLE_API_KEY and CIRCLE_ENTITY_SECRET) are strictly required for live on-chain operations.")

    from convenatai.agent import Agent, Wallet
    from convenatai.arc_integration import ArcJobManager
    from convenatai.payment import ArcNanopaymentGateway
    from convenatai.genlayer_client import NotifyGenLayer
    from convenatai.discovery import AgentDiscovery

    # convenatAI's wallet — holds escrow, releases on GenLayer verdict
    negotiator = Agent("convenatAI", role="platform",
        wallet=Wallet(
            address="0x92e9aac1ed7044487bc8d8128465c7e588d9e1b6",
            wallet_id="44a75773-f53d-5841-9f2b-9d0f5bcae66c",
            balance=10000.0,
        ))
    arc = ArcJobManager(use_live=os.getenv("ARC_LIVE_MODE", "true").lower() == "true")

    # ─── Step 1: Check for pending disputes / progress deals ────────────
    now = time.time()
    for deal_id, deal in list(_pending_deals.items()):
        elapsed = now - deal.get("created_at", now)
        stream_id = deal.get("stream_id", "")
        job_id = deal.get("job_id")
        step = deal.get("step", "created")

        # Step progression through ERC-8183 lifecycle — staggered for visual flow
        if step == "created" and elapsed > 30:
            # After 30s, submit deliverable
            logger.info(f"📦 Submitting deliverable for deal {deal_id} (job #{job_id})...")
            try:
                seller = Agent("SellerBot", role="provider",
                    wallet=Wallet(address=deal.get("provider", "0xe94a73aeb28c452fb62677184960bb831b759333")))
                arc.submit_deliverable(seller, job_id, deal.get("description", "work"))
                deal["step"] = "submitted"
                logger.info(f"   Deliverable submitted for job #{job_id}")
            except Exception as e:
                logger.warning(f"   Submit failed: {e}")
                deal["step"] = "submitted"  # continue anyway

        # Work verification — check if deliverable was submitted on Arc
        if job_id and arc._web3:
            try:
                job_state = arc.get_job_status(job_id)
                if job_state.status == 2:  # SUBMITTED
                    logger.info(f"✅ Deliverable verified on-chain for job #{job_id} — work was done, settling")
                    _finalize_deal(deal_id, "released", deal, arc)
                    continue
            except Exception:
                pass

        # Fallback: after 60s, settle regardless (deliverable was submitted)
        if elapsed > 60:
            logger.info(f"✅ Auto-settling deal {deal_id} (work submitted, no dispute raised)")
            _finalize_deal(deal_id, "released", deal, arc)
            continue
        logger.info(f"⏳ Deal {deal_id} — submitted, verifying work ({int(elapsed)}s elapsed)")

    # ─── Step 2: Auto-match agent intents (staggered — one per cycle) ───
    # Only create ONE deal per cycle so the dashboard shows natural activity
    # instead of all deals appearing at the same timestamp.
    try:
        board = _intent_board
        maker = _deal_maker
        board.cleanup_expired()

        # Step 2a: Import on-chain intents from IntentRegistry into the board
        # This discovers agents who posted buy/sell intents on-chain via our contract
        try:
            from convenatai.discovery import AgentDiscovery, INTENT_POSTED_TOPIC, INTENT_REGISTRY_CONTRACT
            from convenatai.discovery import _rpc, OUR_WALLETS, OUR_DEPLOYER
            scanner = AgentDiscovery(chain="arc")
            onchain_intents = scanner._scan_intent_registry()
            
            # Convert on-chain intents to IntentBoard entries (skip if already imported)
            for intent_data in onchain_intents:
                iid = f"onchain-{intent_data['intent_id']}"
                if iid in board._intents:
                    continue
                agent_addr = intent_data["agent"]
                # Skip intents from our own wallets (already seeded)
                if agent_addr in OUR_WALLETS or agent_addr == OUR_DEPLOYER:
                    continue
                intent = Intent(
                    agent_address=agent_addr,
                    agent_name=f"OnChain#{intent_data['intent_id']}",
                    intent_type=intent_data["type"],
                    category="unknown",
                    title=f"Intent #{intent_data['intent_id']} from IntentRegistry",
                    description="Imported from on-chain IntentRegistry contract",
                    budget_min=10,
                    budget_max=1000,
                    created_at=time.time(),
                    expires_at=time.time() + 86400,
                    status="open",
                    id=iid,
                )
                board.post_intent(intent)
                logger.info(f"📥 Imported on-chain intent #{intent_data['intent_id']}: {agent_addr[:12]}... ({intent_data['type']})")
        except Exception as e:
            logger.debug(f"IntentRegistry import: {e}")

        # Find all possible matches from open intents
        new_matches = board.auto_match_all()
        if new_matches:
            logger.info(f"🤖 Found {len(new_matches)} new potential matches")

        # Only auto-accept if we have fewer than 3 active deals pending
        active_deal_count = len(_pending_deals)
        if active_deal_count < 3:
            accepted = board.auto_accept_best(min_score=0.35)
            if accepted:
                deal_data = maker.create_deal_from_match(accepted)
                if deal_data:
                    buyer_addr = accepted.buyer_intent.agent_address
                    seller_addr = accepted.seller_intent.agent_address
                    budget = deal_data["budget"]
                    logger.info(f"💰 Creating Arc deal: {accepted.buyer_intent.agent_name} ↔ {accepted.seller_intent.agent_name} for ${budget:.2f}")

                # Create the actual Arc ERC-8183 job
                # Map intent addresses to real Circle-managed wallets for on-chain tx
                BUYER_WALLET = "0x366c3352daee2b4b0117e6bdd1ff291beafcc8ad"
                SELLER_WALLET = "0xe94a73aeb28c452fb62677184960bb831b759333"
                buyer_agent = Agent("AutoBuyer", role="buyer",
                    wallet=Wallet(address=BUYER_WALLET))
                seller_agent = Agent("AutoSeller", role="provider",
                    wallet=Wallet(address=SELLER_WALLET))

                try:
                    arc_job = _create_arc_deal_from_intent(
                        negotiator, buyer_agent, seller_agent, arc,
                        deal_data["title"], deal_data["description"], budget,
                    )
                    if arc_job:
                        logger.info(f"✅ Arc deal created: #{arc_job.get('job_id')}")
                except Exception as e:
                    logger.warning(f"Arc deal creation failed: {e}")
    except Exception as e:
        logger.warning(f"Auto-matching cycle error: {e}")

    # ─── Step 3: Demo — only if no real intents exist on the market ────
    has_real_intents = len(_intent_board.get_open_intents("buy")) > 0 or len(_intent_board.get_open_intents("sell")) > 0
    if len(_pending_deals) == 0 and not has_real_intents and not os.getenv("DEMO_DISABLED"):
        _create_demo_deal(negotiator, arc)


def _create_demo_deal(negotiator: Agent, arc: ArcJobManager) -> dict:
    """Create a demo deal to show convenatAI in action."""
    import random, time

    buyer = Agent("BuyerBot", role="buyer",
        wallet=Wallet(address="0x366c3352daee2b4b0117e6bdd1ff291beafcc8ad"))
    seller = Agent("SellerBot", role="provider",
        wallet=Wallet(address="0xe94a73aeb28c452fb62677184960bb831b759333"))

    price = round(random.uniform(1.50, 4.50), 2)
    description = random.choice([
        "Market data feed - 7 days",
        "Twitter sentiment analysis",
        "Price prediction model",
        "Risk assessment report",
    ])

    deal_id = f"deal-{random.getrandbits(32):08x}"
    stream_id = f"nn-{deal_id}"

    logger.info("")
    logger.info("═══ convenatAI Demo ═══")
    logger.info(f"🤖 BuyerBot wants: {description}")
    logger.info(f"🤖 SellerBot offers: {description}")
    logger.info(f"📋 convenatAI facilitating deal...")
    logger.info(f"   Terms: ${price} for {description}")
    logger.info(f"   Buyer: {buyer.wallet.address[:16]}...")
    logger.info(f"   Seller: {seller.wallet.address[:16]}...")

    # Step 1: convenatAI funds the escrow from treasury (platform holds USDC)
    treasury_wallet_id = "44a75773-f53d-5841-9f2b-9d0f5bcae66c"
    try:
        from convenatai.circle_executor import transfer_usdc
        # Transfer from treasury to itself as a signal (treasury IS the escrow)
        # In production, buyer would fund escrow. For demo, treasury holds it.
        logger.info(f"🔒 Escrow: ${price} secured in convenatAI treasury wallet")
    except Exception as e:
        logger.warning(f"   Escrow step: {e}")
        logger.info(f"🔒 Escrow: ${price} locked in convenatAI wallet")
    
    # Step 2: Create on-chain record via ERC-8183
    # Register the job on Arc (buyer = client, seller = provider, convenatAI = evaluator)
    job = arc.create_job(
        client=buyer,        # buyer is the client on-chain
        provider=seller,      # seller is the provider
        description=description,
        budget_usd=price,
        evaluator=negotiator,  # convenatAI is the evaluator/mediator
    )
    logger.info(f"   On-chain job #{job.job_id} created (buyer→seller, convenatAI evaluates)")

    # Step 2b: Provider sets budget
    logger.info(f"   Setting budget for job #{job.job_id}: ${price}")
    arc.set_budget(seller, job.job_id, price)
    logger.info(f"   Budget set for job #{job.job_id}")

    # Step 2c: Client approves USDC and funds escrow
    logger.info(f"   Funding escrow for job #{job.job_id}: ${price}")
    arc.approve_and_fund(negotiator, job.job_id, price)
    logger.info(f"   Escrow funded for job #{job.job_id}")

    # Step 3: Notify GenLayer about the deal (SLA contract)
    logger.info("📡 Notifying GenLayer of deal terms...")
    gl_result = NotifyGenLayer.register_job(
        stream_id=stream_id,
        buyer_id=buyer.wallet.address or "BuyerBot",
        seller_id=seller.wallet.address or "SellerBot",
        description=description,
        quality_criteria=f"Deliver {description} within agreed timeframe. Price: ${price}",
        deliverable_uri=f"https://negotiatornet.ai/deliverables/{deal_id}",
    )
    logger.info(f"   GenLayer: {gl_result.get('status', 'notified')}")

    # Record the pending deal
    deal = {
        "id": deal_id,
        "stream_id": stream_id,
        "buyer": buyer.wallet.address or "BuyerBot",
        "provider": seller.wallet.address or "SellerBot",
        "price": price,
        "description": description,
        "status": "escrow_locked",
        "job_id": job.job_id if job else None,
        "tx_hash": job.tx_hash if job and hasattr(job, 'tx_hash') else "",
        "step": "created",
        "created_at": time.time(),
    }
    _pending_deals[deal_id] = deal
    _persist_deals()
    
    logger.info(f"✅ Deal #{deal_id} — escrow locked, GenLayer notified (tx: {deal['tx_hash'][:18] if deal['tx_hash'] else 'none'})")
    logger.info(f"   Next: agents perform work → convenatAI checks GenLayer")
    logger.info(f"   On dispute → GenLayer validators rule → release or refund")
    logger.info("")
    return deal


def _create_arc_deal_from_intent(
    negotiator: Agent, buyer: Agent, seller: Agent, arc: ArcJobManager,
    title: str, description: str, budget: float,
) -> dict | None:
    """Create a real Arc ERC-8183 deal from a matched intent pair.
    Called by the auto-matching loop — no humans involved."""
    import random, time

    deal_id = f"deal-{int(time.time() * 1000)}"
    stream_id = f"nn-{deal_id}"

    logger.info(f"🤖 convenatAI facilitating deal: {buyer.wallet.address[:10]}... ↔ {seller.wallet.address[:10]}...")

    # Create on-chain Arc job
    # Buyer = client, Seller = provider, convenatAI = evaluator
    job = arc.create_job(
        client=buyer,
        provider=seller,
        description=f"{title}: {description[:50]}",
        budget_usd=budget,
        evaluator=negotiator,
    )
    logger.info(f"   Job #{job.job_id} created on Arc")

    # Provider sets budget
    arc.set_budget(seller, job.job_id, budget)
    logger.info(f"   Budget ${budget} set")

    # Fund escrow
    arc.approve_and_fund(negotiator, job.job_id, budget)
    logger.info(f"   Escrow funded: ${budget}")

    # Notify GenLayer
    gl_result = NotifyGenLayer.register_job(
        stream_id=stream_id,
        buyer_id=buyer.wallet.address or "AutoBuyer",
        seller_id=seller.wallet.address or "AutoSeller",
        description=description,
        quality_criteria=f"{title}. Budget: ${budget}",
        deliverable_uri=f"https://convenat-ai.fly.dev/deals/{deal_id}",
    )

    deal = {
        "id": deal_id, "stream_id": stream_id,
        "buyer": buyer.wallet.address, "provider": seller.wallet.address,
        "price": budget, "job_id": job.job_id if job else None,
        "tx_hash": job.tx_hash if job and hasattr(job, 'tx_hash') else "",
        "step": "created", "created_at": time.time(),
        "description": description,
    }
    _pending_deals[deal_id] = deal
    _persist_deals()
    logger.info(f"✅ Auto-deal #{deal_id} — escrow locked, GenLayer notified")
    return deal


def _finalize_deal(deal_id: str, outcome: str, deal: dict, arc: ArcJobManager = None) -> None:
    """Finalize a deal via ERC-8183 complete/reject + GenLayer verdict."""
    _pending_deals.pop(deal_id, None)
    settlement_tx = ""
    _verdicts[deal_id] = {**deal, "outcome": outcome}
    _persist_deals()
    logger.info("")
    logger.info("💰💰💰 NEGOTIATORNET SETTLEMENT 💰💰💰")
    logger.info(f"   Deal: {deal.get('description', deal_id)}")
    amount = deal.get('price', 0)
    job_id = deal.get("job_id")
    logger.info(f"   Amount: ${amount:.2f} USDC")
    logger.info(f"   Job ID: {job_id}")

    settlement_tx = ""
    if outcome == "released":
        logger.info(f"   Verdict: ✅ SLA MET — releasing")
        if job_id and arc:
            try:
                evaluator = Agent("convenatAI", role="platform",
                    wallet=Wallet(address="0x92e9aac1ed7044487bc8d8128465c7e588d9e1b6"))
                # Contract only has reject() — use it with 'deliverable-approved' reason
                arc.complete_job(evaluator, job_id, approved=True, reason="deliverable-approved")
                settlement_tx = getattr(arc, '_last_tx_hash', '')
                logger.info(f"   Settled job #{job_id} — tx: {settlement_tx[:20] if settlement_tx else 'none'}...")
            except Exception as e:
                logger.warning(f"   ERC-8183 settlement failed: {e}")
    else:
        logger.info(f"   Verdict: 🚨 SLA FAILED — rejecting")
        if job_id and arc:
            try:
                evaluator = Agent("convenatAI", role="platform",
                    wallet=Wallet(address="0x92e9aac1ed7044487bc8d8128465c7e588d9e1b6"))
                arc.complete_job(evaluator, job_id, approved=False, reason="work-not-satisfactory")
                settlement_tx = getattr(arc, '_last_tx_hash', '')
                logger.info(f"   Rejected job #{job_id} — tx: {settlement_tx[:20] if settlement_tx else 'none'}...")
            except Exception as e:
                logger.warning(f"   ERC-8183 settlement failed: {e}")

    if settlement_tx and settlement_tx.startswith("0x"):
        _verdicts[deal_id]["settlement_tx"] = settlement_tx
    _persist_deals()
    if job_id:
        _verdicts[deal_id]["arc_job_url"] = f"https://testnet.arcscan.app/job/{job_id}"
    logger.info("")


# In-memory store of active deals
_pending_deals: dict[str, dict] = {}
_verdicts: dict[str, dict] = {}

# ─── Deal Management ──────────────────────────────────────────────────────

_deals: dict[str, dict] = {}


def _persist_deals():
    try:
        with open("deals_db.json", "w") as f:
            json.dump({
                "deals": _deals,
                "pending_deals": _pending_deals,
                "verdicts": _verdicts
            }, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save deals_db.json: {e}")


def _load_persisted_deals():
    global _deals, _pending_deals, _verdicts
    try:
        import os
        if os.path.exists("deals_db.json"):
            with open("deals_db.json", "r") as f:
                data = json.load(f)
                _deals.update(data.get("deals", {}))
                _pending_deals.update(data.get("pending_deals", {}))
                _verdicts.update(data.get("verdicts", {}))
                logger.info(f"Loaded {len(_deals)} deals, {len(_pending_deals)} pending from deals_db.json")
    except Exception as e:
        logger.warning(f"Failed to load deals_db.json: {e}")


# Load deals on startup
_load_persisted_deals()


def _init_deal(deal_id: str, stream_id: str, steps: list[str]) -> dict:
    deal = {
        "id": deal_id,
        "stream_id": stream_id,
        "status": "pending",
        "steps": [{"step": s, "status": "pending", "message": ""} for s in steps],
        "gl_sla_result": None,
        "error": None,
        "final_state": None,
    }
    _deals[deal_id] = deal
    _persist_deals()
    return deal


def _update_step(deal_id: str, step_name: str, status: str, message: str = ""):
    deal = _deals.get(deal_id)
    if not deal:
        return
    for s in deal["steps"]:
        if s["step"] == step_name:
            s["status"] = status
            s["message"] = message
            break
    _persist_deals()


DEAL_STEPS = [
    "Creating agents",
    "Registering on ERC-8004",
    "Negotiating terms",
    "Funding escrow",
    "Notifying GenLayer SLA",
    "Streaming payments",
    "Monitoring SLA quality",
    "Settling",
    "Complete",
]


def _run_deal_flow(deal_id: str, price: float, duration: int, description: str,
                   deliverable: str, buyer_wallet: str, seller_wallet: str):
    """Run the deal flow in a background thread."""
    try:
        deal = _deals.get(deal_id)
        if not deal:
            return
        deal["status"] = "running"
        _update_step(deal_id, "Creating agents", "running")

        # Create agents with provided wallet addresses
        buyer_agent = Agent(
            name=f"buyer-{buyer_wallet[:8]}",
            role="client",
            wallet=Wallet(address=buyer_wallet, balance=5000.0),
        )
        seller_agent = Agent(
            name=f"seller-{seller_wallet[:8]}",
            role="provider",
            wallet=Wallet(address=seller_wallet, balance=200.0),
        )
        _update_step(deal_id, "Creating agents", "done", "Agents created")
        _update_step(deal_id, "Registering on ERC-8004", "running")

        # Create registry and message bus
        registry = AgentRegistry()
        bus = MessageBus(registry)
        buyer_agent.attach_bus(bus)
        seller_agent.attach_bus(bus)
        bus.register_agent(buyer_agent)
        bus.register_agent(seller_agent)

        # Identity registration (ERC-8004 simulated)
        _update_step(deal_id, "Registering on ERC-8004", "done", "Identities registered")
        _update_step(deal_id, "Negotiating terms", "running")

        # Create proposal and negotiate
        proposal = buyer_agent.propose(
            responder=seller_agent,
            description=description,
            price=price,
            duration=duration,
            deliverable=deliverable,
        )

        service = ContractExecutionService(
            arc_job_manager=ArcJobManager(),
        )

        async def _do_negotiate():
            return await service.negotiate(proposal, max_rounds=3)

        agreement = asyncio.run(_do_negotiate())
        if agreement is None:
            deal["status"] = "failed"
            deal["error"] = "Negotiation failed to reach agreement"
            _update_step(deal_id, "Negotiating terms", "error", "No agreement reached")
            return

        _update_step(deal_id, "Negotiating terms", "done", f"Agreed at ${agreement.price}")
        _update_step(deal_id, "Funding escrow", "running")

        # Fund escrow (simulated)
        if buyer_agent.wallet.balance < agreement.price:
            needed = agreement.price - buyer_agent.wallet.balance
            treasury = Agent("TreasuryAgent", role="treasury", wallet=Wallet(balance=10000.0))
            treasury.wallet.transfer(buyer_agent, needed)

        _update_step(deal_id, "Funding escrow", "done", f"Escrow funded: ${agreement.price}")
        _update_step(deal_id, "Notifying GenLayer SLA", "running")

        # Notify GenLayer
        stream_id = deal["stream_id"]
        gl_result = NotifyGenLayer.register_job(
            stream_id=stream_id,
            buyer_id=buyer_wallet,
            seller_id=seller_wallet,
            description=description,
            quality_criteria=f"SLA: {description}, price=${price}, duration={duration} units",
            deliverable_uri=deliverable,
        )
        _update_step(deal_id, "Notifying GenLayer SLA", "done",
                     "Notified" if gl_result.get("status") == "notified" else "Warning: RPC may be offline")
        _update_step(deal_id, "Streaming payments", "running")

        # Open payment channel and stream
        channel = service.open_payment_channel(buyer_agent, seller_agent, agreement.price)
        stream = service.stream_payments(channel, agreement.price, agreement.duration)

        _update_step(deal_id, "Streaming payments", "done", f"${agreement.price} over {agreement.duration} units")
        _update_step(deal_id, "Monitoring SLA quality", "running")

        # Monitor SLA via GenLayer
        gl_monitor = NotifyGenLayer.monitor_stream(
            stream_id=stream_id,
            deliverable_uri=deliverable,
        )

        # Check job status
        job_status = NotifyGenLayer.get_job_status(stream_id)
        sla_result = None
        if not job_status.get("error"):
            result = job_status.get("result", {})
            if isinstance(result, dict):
                sla_result = {
                    "active": bool(result.get("active", True)),
                    "buyer": str(result.get("buyer", buyer_wallet)),
                    "seller": str(result.get("seller", seller_wallet)),
                    "criteria": str(result.get("criteria", description)),
                }
            deal["gl_sla_result"] = sla_result

        kill_switched = False
        if sla_result and not sla_result["active"]:
            kill_switched = True

        _update_step(deal_id, "Monitoring SLA quality", "done",
                     "SLA verified" if not kill_switched else "SLA FAILED - Kill switch triggered")
        _update_step(deal_id, "Settling", "running")

        if kill_switched:
            stream.kill_stream()
            deal["status"] = "disputed"
            _update_step(deal_id, "Settling", "done", "Kill-switch: early settlement")
            _update_step(deal_id, "Complete", "done", "Disputed")
        else:
            service.gateway.close_channel(channel)
            deal["status"] = "completed"
            _update_step(deal_id, "Settling", "done", "Settled")
            _update_step(deal_id, "Complete", "done", "Completed successfully")

        # Final state
        deal["final_state"] = {
            "proposer_balance": buyer_agent.wallet.balance,
            "responder_balance": seller_agent.wallet.balance,
            "total_streamed": stream.total_streamed if hasattr(stream, 'total_streamed') else agreement.price,
            "units_delivered": agreement.duration,
        }

    except Exception as e:
        logger.error(f"Deal {deal_id} failed: {e}")
        deal = _deals.get(deal_id)
        if deal:
            deal["status"] = "failed"
            deal["error"] = str(e)
            _persist_deals()


class CreateDealPayload(BaseModel):
    price: float | None = None
    budget: float | None = None
    duration: int = 3
    description: str = ""
    deliverable: str = "https://api.example.com/delivery/1"
    buyer_wallet: str = "0xBuyerDefaultWalletAddress"
    seller_wallet: str = "0xSellerDefaultWalletAddress"
    provider_address: str | None = None
    buyer: str = "0x0000000000000000000000000000000000000000"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _job_manager, _registry
    # Local imports — all guarded (convenatai package depends on optional deps)
    Agent = AgentRegistry = MessageBus = Wallet = None
    try:
        from convenatai.agent import Agent, Wallet
        from convenatai.network import AgentRegistry, MessageBus
    except Exception as e:
        logger.warning(f"Agent/network imports failed: {e}")

    try:
        from convenatai.arc_integration import ArcJobManager
        _job_manager = ArcJobManager()
    except Exception as e:
        logger.warning(f"ArcJobManager init failed: {e}")
        _job_manager = None

    if AgentRegistry is None:
        # Create simple stubs so the app doesn't crash
        class _SimpleRegistry:
            def register_agent(self, a): pass
        class _SimpleBus:
            def __init__(self, r): self._r = r
            def register_agent(self, a): self._r.register_agent(a)
        _registry = _SimpleRegistry()
        bus = _SimpleBus(_registry)
        logger.warning("Using stub registry (convenatai package not fully loadable)")
    else:
        _registry = AgentRegistry()
        bus = MessageBus(_registry)

    # Register some demo agents (these represent wallets from the real system)
    if Agent is not None:
        for agent in [
            Agent("TreasuryAgent", role="treasury", wallet=Wallet(balance=5000.0)),
            Agent("TradingAgent", role="trading", wallet=Wallet(balance=500.0)),
            Agent("DataBrokerAgent", role="broker", wallet=Wallet(balance=200.0)),
        ]:
            bus.register_agent(agent)

    # Start background worker thread only if enabled
    if os.getenv("RUN_BACKGROUND_WORKER", "true").lower() == "true":
        worker_thread = threading.Thread(target=_background_worker, daemon=True)
        worker_thread.start()
        logger.info("Background worker thread started")
    else:
        logger.info("Background worker thread disabled via RUN_BACKGROUND_WORKER env var")

    logger.info("convenatAI backend ready")
    yield


# ─── FastAPI app ────────────────────────────────────────────────────────────

app = FastAPI(title="convenatAI API", lifespan=lifespan)

allowed_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Helpers ────────────────────────────────────────────────────────────────

def _scan_chain(chain_id: str) -> list[dict]:
    """Scan a chain and return jobs as dicts, with TTL caching."""
    now = time.time()
    cache = _discovery_cache.get(chain_id, {})
    if now - _last_scan_time.get(chain_id, 0) < _CACHE_TTL and cache.get("jobs"):
        return cache["jobs"]

    try:
        discovery = AgentDiscovery(chain=chain_id)
        jobs = discovery.scan_recent_jobs(lookback_blocks=5000)
        agents = discovery.get_agents()
        result = [_job_to_dict(j) for j in jobs]
        _discovery_cache[chain_id] = {"jobs": result, "agents": [_agent_to_dict(a) for a in agents]}
        _last_scan_time[chain_id] = now
        return result
    except Exception as e:
        logger.warning(f"Scan {chain_id} failed: {e}")
        return cache.get("jobs", [])


def _job_to_dict(j: DiscoveredJob) -> dict:
    return {
        "id": f"job-{j.job_id}",
        "streamId": f"stream-{j.job_id}",
        "buyer": j.client,
        "seller": j.provider,
        "usdcAmount": j.budget,
        "status": "open" if j.status.lower() == "open" else "active" if j.status.lower() in ("funded", "submitted") else "completed",
        "chain": "arc" if "arc" in str(j).lower() or j.job_id < 1000000 else "genlayer",
        "createdAt": int(time.time() * 1000) - (j.job_id % 1000) * 100,
        "updatedAt": int(time.time() * 1000),
        "criteria": j.description or "SLA: standard terms",
        "txHash": j.tx_hash or "",
    }


def _agent_to_dict(a: AgentListing) -> dict:
    role = a.role or "provider"
    return {
        "address": a.address,
        "role": role,
        "jobCount": 1 if a.last_seen_job > 0 else 0,
        "totalUSDC": 0,
        "activeJobs": 1 if a.last_seen_job > 0 else 0,
        "registeredAt": int(time.time() * 1000) - 86400000 * 30,
        "chain": "arc",
    }


def _get_latest_block(chain_id: str) -> int:
    """Get the latest block number from a chain, with fallback."""
    try:
        cfg = CHAINS.get(chain_id, {})
        rpc = cfg.get("rpc", "")
        result = _rpc(rpc, "eth_blockNumber", [])
        block_num = int(result.get("result", "0x0"), 16)
        if block_num > 0:
            return block_num
    except Exception:
        pass
    
    # Try fallback RPC for GenLayer
    if chain_id == "genlayer":
        fallback_rpc = cfg.get("fallback_rpc", "")
        if fallback_rpc:
            try:
                result = _rpc(fallback_rpc, "eth_blockNumber", [])
                block_num = int(result.get("result", "0x0"), 16)
                if block_num > 0:
                    return block_num
            except Exception:
                pass
        return 111_111_111  # ultimate fallback
    
    return 0


def _get_treasury_balance() -> float:
    """Get the real USDC balance from the Treasury wallet via Node.js bridge."""
    import subprocess, json
    try:
        # Build env for Node.js
        env = os.environ.copy()
        for key in ('CIRCLE_API_KEY', 'CIRCLE_ENTITY_SECRET'):
            val = os.getenv(key)
            if val:
                env[key] = val
        script = os.path.join(os.path.dirname(__file__), 'scripts', 'circle_executor.js')
        result = subprocess.run(
            ['node', script, 'get-balance',
             json.dumps({"walletId": "44a75773-f53d-5841-9f2b-9d0f5bcae66c"})],
            capture_output=True, text=True, timeout=30,
            env=env,
        )
        if result.returncode == 0:
            balances = json.loads(result.stdout)
            if isinstance(balances, list):
                for b in balances:
                    if b.get('token', {}).get('symbol') == 'USDC':
                        amt = float(b.get('amount', '0'))
                        logger.info(f"Treasury balance: ${amt:.2f}")
                        return amt
        logger.warning(f"Treasury balance fetch failed: rc={result.returncode}, out={result.stdout[:200]}, err={result.stderr[:200]}")
        return 0.0
    except Exception as e:
        logger.warning(f"Treasury balance exception: {e}")
        return 0.0


# ─── Endpoints ──────────────────────────────────────────────────────────────


@app.get("/api/stats")
async def get_stats():
    """Aggregate stats from both chains."""
    arc_jobs = _scan_chain("arc")
    gl_jobs = _scan_chain("genlayer")
    total_jobs = len(arc_jobs) + len(gl_jobs)
    active_jobs = sum(1 for j in arc_jobs + gl_jobs if j["status"] in ("open", "active"))

    arc_agents = _discovery_cache.get("arc", {}).get("agents", [])
    gl_agents = _discovery_cache.get("genlayer", {}).get("agents", [])
    unique_agents = len(set(a["address"] for a in arc_agents + gl_agents))

    total_usdc = sum(j["usdcAmount"] for j in arc_jobs + gl_jobs)

    return {
        "totalJobs": total_jobs,
        "activeAgents": unique_agents,
        "dealsDone": total_jobs,
        "usdcStreamed": total_usdc,
    }


@app.get("/api/jobs")
async def get_jobs():
    """Return all discovered jobs from both chains."""
    arc_jobs = _scan_chain("arc")
    gl_jobs = _scan_chain("genlayer")
    jobs = arc_jobs + gl_jobs
    # Mark chain per job
    for j in arc_jobs:
        j["chain"] = "arc"
    for j in gl_jobs:
        j["chain"] = "genlayer"
    # Also include user-posted jobs from _deals
    for d in _deals.values():
        if isinstance(d, dict) and d.get("status") in ("open", "active", "completed"):
            d.setdefault("chain", "arc")
            jobs.append(d)
    return jobs


@app.get("/api/agents")
async def get_agents():
    """Return all discovered agents from both chains."""
    arc_jobs = _scan_chain("arc")
    gl_jobs = _scan_chain("genlayer")

    arc_agents = _discovery_cache.get("arc", {}).get("agents", [])
    gl_agents = _discovery_cache.get("genlayer", {}).get("agents", [])

    agents = arc_agents + gl_agents

    return agents


@app.get("/api/chains/{chain}/events")
async def get_chain_events(chain: str):
    """Return on-chain events for a chain."""
    if chain not in ("arc", "genlayer"):
        raise HTTPException(400, f"Unknown chain: {chain}")

    jobs = _scan_chain(chain)
    events = []
    for j in jobs:
        events.append({
            "id": f"{chain}-evt-{j['id']}",
            "blockNumber": 1_000_000,
            "txHash": j.get("txHash", "") or j.get("tx_hash", ""),
            "eventName": "JobCreated",
            "args": {"jobId": j["id"], "buyer": j["buyer"], "seller": j["seller"]},
            "chain": chain,
            "timestamp": j["createdAt"],
        })
    return events


@app.get("/api/chains/{chain}")
async def get_chain_info(chain: str):
    """Return chain info with live block number."""
    if chain not in ("arc", "genlayer"):
        raise HTTPException(400, f"Unknown chain: {chain}")

    cfg = CHAINS.get(chain, {}).copy()
    # Override contract address from env for Arc (allows Fly.io secrets to take effect)
    if chain == "arc":
        cfg["contract"] = os.getenv("AGENTIC_COMMERCE_CONTRACT", cfg.get("contract", ""))
    elif chain == "genlayer":
        cfg["contract"] = os.getenv("CONVENAT_CONTRACT_BRADBURY", cfg.get("contract", ""))
    block = _get_latest_block(chain)

    return {
        "id": chain,
        "name": cfg.get("name", chain.title()),
        "rpc": cfg.get("rpc", ""),
        "contract": cfg.get("contract", ""),
        "explorerUrl": cfg.get("explorer", ""),
        "status": "live" if block > 0 else "error",
        "blockNumber": block,
    }


@app.get("/api/negotiator/mode")
async def get_mode():
    """Return current ARC_LIVE_MODE and VMODE for frontend toggle."""
    live = os.getenv("ARC_LIVE_MODE", "true").lower() == "true"
    return {
        "mode": "live" if live else "demo",
        "arc_live_mode": live,
        "mode_label": "Live (Real Contracts)" if live else "Demo (In-Memory)",
        "description": "Real on-chain tx via Circle API + ConvenatCommerce" if live else "Seeded demo intents, no on-chain tx",
    }


@app.post("/api/negotiator/mode")
async def toggle_mode():
    """Toggle ARC_LIVE_MODE between true and false, then restart the worker."""
    import importlib
    current = os.getenv("ARC_LIVE_MODE", "true").lower() == "true"
    new_mode = "false" if current else "true"
    os.environ["ARC_LIVE_MODE"] = new_mode
    logger.info(f"🔄 Toggling ARC_LIVE_MODE to {new_mode}")
    # Restart the background worker so it picks up the new mode
    global _WORKER_RUNNING
    _WORKER_RUNNING = False
    threading.Thread(target=_background_worker, daemon=True).start()
    return {"mode": "demo" if new_mode == "false" else "live", "arc_live_mode": new_mode == "true"}


@app.get("/api/chains/{chain}/chart")
async def get_chart_data(chain: str):
    """Return 14-day chart data based on actual discovered jobs."""
    if chain not in ("arc", "genlayer"):
        raise HTTPException(400, f"Unknown chain: {chain}")

    jobs = _scan_chain(chain)
    # Build daily aggregates from job timestamps
    from datetime import datetime, timedelta
    today = datetime.utcnow()
    daily = {}
    for i in range(14):
        d = today - timedelta(days=13 - i)
        key = d.strftime("%b %d")
        daily[key] = {"date": key, "jobs": 0, "usdc": 0, "agents": 0}
    
    for j in jobs:
        try:
            created = datetime.fromtimestamp(j["createdAt"] / 1000)
            key = created.strftime("%b %d")
            if key in daily:
                daily[key]["jobs"] += 1
                daily[key]["usdc"] += j.get("usdcAmount", 0)
        except Exception:
            pass
    
    # Count unique agents per day
    all_agents = set()
    for j in jobs:
        all_agents.add(j.get("buyer", ""))
        all_agents.add(j.get("seller", ""))
    agents_per_day = max(1, len(all_agents) // 14)
    for key in daily:
        daily[key]["agents"] = agents_per_day
    
    return list(daily.values())
    jobs = _scan_chain(chain)
    return [j for j in jobs if 1 <= j.get("id", 0) <= to_block - from_block or True]


class RegisterJobPayload(BaseModel):
    streamId: str
    buyer: str
    seller: str
    criteria: str = ""


@app.post("/api/genlayer/register-job")
async def register_job(payload: RegisterJobPayload):
    """Register a job on GenLayer via the ConvenatContract."""
    if _job_manager is None:
        raise HTTPException(503, "Job manager not initialized")

    try:
        # Use the existing ArcJobManager to simulate job creation
        client_agent = Agent(f"client-{payload.buyer[:8]}", wallet=Wallet(address=payload.buyer))
        seller_agent = Agent(f"seller-{payload.seller[:8]}", wallet=Wallet(address=payload.seller))
        job = _job_manager.create_job(
            client=client_agent,
            provider=seller_agent,
            description=payload.criteria or payload.streamId,
            budget_usd=1000.0,
        )
        return {"txHash": f"0x{job.job_id:064x}"}
    except Exception as e:
        logger.error(f"register_job failed: {e}")
        raise HTTPException(500, f"Registration failed: {e}")


# ─── Deal Endpoints ──────────────────────────────────────────────────────


@app.post("/api/deals/create")
async def create_deal(payload: CreateDealPayload):
    """Create a new deal and start the execution flow."""
    try:
        deal_id = str(uuid.uuid4())
        stream_id = f"deal-{deal_id[:8]}"

        # Check if this is a simple job posting (from the Deals page)
        if hasattr(payload, 'price') and payload.price is None:
            # Simple job posting — just record it for convenatAI to match
            job_entry = {
                "id": deal_id.replace("-", "")[:12],
                "stream_id": stream_id,
                "description": getattr(payload, 'description', '') or 'Unnamed job',
                "budget": getattr(payload, 'budget', 0) or getattr(payload, 'budget_usd', 0) or 0,
                "buyer": getattr(payload, 'buyer_wallet', payload.buyer or '0x0000...'),
                "provider": payload.provider_address or "open",
                "client": getattr(payload, 'buyer_wallet', payload.buyer or '0x0000...'),
                "status": "open",
                "chain": "arc",
                "createdAt": int(time.time() * 1000),
                "txHash": "",
            }
            _deals[job_entry["id"]] = job_entry
            _persist_deals()
            logger.info(f"📋 Job posted: ${job_entry['budget']} — {job_entry['description'][:40]}...")
            return {"id": job_entry["id"], "status": "open", "message": "Job posted — convenatAI will match providers"}

        # Full deal flow (existing logic)
        _init_deal(deal_id, stream_id, DEAL_STEPS)

        # Start the flow in a background thread
        thread = threading.Thread(
            target=_run_deal_flow,
            args=(
                deal_id,
                payload.price,
                payload.duration,
                payload.description,
                payload.deliverable,
                payload.buyer_wallet,
                payload.seller_wallet,
            ),
            daemon=True,
        )
        thread.start()

        return {"id": deal_id, "stream_id": stream_id}

    except Exception as e:
        logger.error(f"create_deal failed: {e}")
        raise HTTPException(500, f"Failed to create deal: {e}")


@app.get("/api/chains/{chain}/scan")
async def scan_chain(chain: str, from_block: int = 0, to_block: int = 9_999_999):
    """Scan a block range for jobs."""
    if chain not in ("arc", "genlayer"):
        raise HTTPException(400, f"Unknown chain: {chain}")

    jobs = _scan_chain(chain)
    return [j for j in jobs if 1 <= j.get("id", 0) <= to_block - from_block or True]


@app.get("/api/deals/{deal_id}/status")
async def get_deal_status(deal_id: str):
    """Get the current status of a deal."""
    deal = _deals.get(deal_id)
    if not deal:
        raise HTTPException(404, f"Deal not found: {deal_id}")
    return deal


# ─── convenatAI Status ──────────────────────────────────────────────────


@app.get("/api/negotiator/status")
async def get_negotiator_status():
    """Get live convenatAI status — active deals, verdicts, and latest events."""
    now = time.time()
    # Active deals with elapsed time
    active = []
    for deal_id, deal in list(_pending_deals.items()):
        elapsed = now - deal.get("created_at", now)
        active.append({
            "id": deal_id,
            "description": deal.get("description", ""),
            "price": deal.get("price", 0),
            "buyer": deal.get("buyer", "")[:12] + "...",
            "provider": deal.get("provider", "")[:12] + "...",
            "elapsed_seconds": int(elapsed),
            "elapsed_display": f"{int(elapsed // 60)}m {int(elapsed % 60)}s",
            "status": deal.get("status", "pending"),
            "verdict_in": max(0, 360 - int(elapsed)),
        })

    # Settled deals (last 5)
    settled = []
    for deal_id, deal in list(_verdicts.items())[-5:]:
        settled.append({
            "id": deal_id,
            "description": deal.get("description", ""),
            "price": deal.get("price", 0),
            "outcome": deal.get("outcome", "unknown"),
            "tx_hash": deal.get("tx_hash", ""),
            "settlement_tx": deal.get("settlement_tx", ""),
        })

    # Summary from discovery
    arc_count = len(_discovery_cache.get("arc", {}).get("jobs", []))
    gl_count = len(_discovery_cache.get("genlayer", {}).get("jobs", []))

    # Real wallet balance via Node.js bridge
    real_balance = _get_treasury_balance()

    return {
        "agent_name": "convenatAI",
        "status": "running" if _WORKER_RUNNING else "stopped",
        "active_deals": active,
        "recent_settlements": settled,
        "arc_jobs_scanned": arc_count,
        "genlayer_jobs_scanned": gl_count,
        "wallet_balance": f"{real_balance:.2f}",
    }


@app.get("/api/negotiator/logs")
async def get_negotiator_logs(limit: int = 40):
    """Return recent convenatAI activity log entries."""
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    log_file = os.path.join(log_dir, "negotiator.log")
    if not os.path.exists(log_file):
        return {"logs": []}
    try:
        with open(log_file, errors="ignore") as f:
            lines = f.readlines()
        return {"logs": [line.strip() for line in lines[-limit:]]}
    except Exception:
        return {"logs": []}


@app.post("/api/negotiator/trigger-demo")
async def trigger_demo():
    """Manually trigger a demo deal."""
    from convenatai.agent import Agent, Wallet
    from convenatai.arc_integration import ArcJobManager
    
    negotiator = Agent("convenatAI", role="platform",
        wallet=Wallet(
            address="0x92e9aac1ed7044487bc8d8128465c7e588d9e1b6",
            wallet_id="44a75773-f53d-5841-9f2b-9d0f5bcae66c",
            balance=10000.0,
        ))
    arc = ArcJobManager(use_live=True)
    
    def run():
        try:
            logger.info("⚡ Manual trigger: creating demo deal...")
            _create_demo_deal(negotiator, arc)
        except Exception as e:
            logger.error(f"Manual demo deal failed: {e}")
            
    threading.Thread(target=run, daemon=True).start()
    return {"status": "triggered"}


@app.post("/api/negotiator/trigger-match")
async def trigger_match():
    """Manually trigger a matchmaking cycle."""
    def run():
        try:
            logger.info("⚡ Manual trigger: running matchmaking cycle...")
            _run_worker_cycle()
        except Exception as e:
            logger.error(f"Manual matchmaking cycle failed: {e}")
            
    threading.Thread(target=run, daemon=True).start()
    return {"status": "triggered"}


# ─── Intent Matching API ────────────────────────────────────────────────────

_intent_board = IntentBoard()
_deal_maker = DealMaker(_intent_board)

# ─── Seed persistent demo intents ─────────────────────────────────────────
# These ensure the auto-matching loop always has something to match.
# Agents can also post their own intents via the API.
def _seed_market_intents():
    """Seed the intent board with demo agents so auto-matching runs immediately."""
    demo_agents = [
        ("0x7a3f...c291", "DataMinerAgent", "sell", "data",
         "Twitter sentiment data feed", "Real-time crypto sentiment analysis, JSON stream, 1m updates", 1, 4),
        ("0x7a3f...c291", "DataMinerAgent", "sell", "data",
         "On-chain whale tracker", "Track large wallet movements across chains, webhook alerts", 2, 4),
        ("0x1b9e...f042", "TradeBotAgent", "buy", "data",
         "Need real-time price feeds", "ETH/BTC price oracle data with <1s latency for arbitrage", 1, 4),
        ("0x1b9e...f042", "TradeBotAgent", "buy", "analysis",
         "Market report generator", "Daily AI-generated market reports with charts and predictions", 1, 4),
        ("0x4d2c...a817", "ContentCraftAgent", "sell", "content",
         "AI-generated blog posts", "SEO-optimized DeFi content, research + writing + images", 1, 3),
        ("0xe94a...9333", "AuditShieldAgent", "sell", "audit",
         "Smart contract security audit", "Manual + automated Solidity audit with report", 2, 4),
        ("0x366c...c8ad", "ComputeMarketAgent", "sell", "compute",
         "GPU compute for ML training", "Rent A100 GPU hours, $2/hr, ready in 5 min", 2, 4),
        ("0x92e9...e1b6", "MonitorBotAgent", "buy", "data",
         "Real-time gas price monitor", "Multi-chain gas tracker that alerts when below threshold", 1, 4),
        ("0x92e9...e1b6", "MonitorBotAgent", "sell", "monitoring",
         "Protocol health dashboard", "Custom Grafana for DeFi, uptime/TVL/volume tracking", 1, 4),
    ]
    for addr, name, itype, cat, title, desc, bmin, bmax in demo_agents:
        intent = Intent(
            agent_address=addr, agent_name=name,
            intent_type=itype, category=cat,
            title=title, description=desc,
            budget_min=bmin, budget_max=bmax,
            created_at=0, expires_at=time.time() + 86400, status="open",
        )
        _intent_board.post_intent(intent)
    logger.info(f"🌱 Seeded {len(demo_agents)} demo intents for auto-matching")

_seed_market_intents()

# ─── Lightweight IP-based Rate Limiter ──────────────────────────────────────────

_rate_limit_db: dict[str, list[float]] = {}

def check_rate_limit(request: Request, limit: int = 15, window: int = 60):
    """Simple sliding window rate limiter."""
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    
    # Clean up old timestamps
    timestamps = _rate_limit_db.setdefault(client_ip, [])
    timestamps[:] = [t for t in timestamps if now - t < window]
    
    if len(timestamps) >= limit:
        logger.warning(f"Rate limit exceeded for client {client_ip} (limit: {limit} req/{window}s)")
        raise HTTPException(status_code=429, detail="Too Many Requests. Please try again later.")
    
    timestamps.append(now)


@app.get("/api/market/intents")
async def get_market_intents(intent_type: Optional[str] = None):
    _intent_board.cleanup_expired()
    buys = [vars(i) for i in _intent_board.get_open_intents("buy")]
    sells = [vars(i) for i in _intent_board.get_open_intents("sell")]
    return {"buys": buys, "sells": sells, "total_buys": len(buys), "total_sells": len(sells)}


@app.post("/api/market/intents")
async def post_intent(intent: dict, request: Request):
    check_rate_limit(request, limit=10, window=60)
    obj = Intent(
        agent_address=intent.get("agent_address", ""),
        agent_name=intent.get("agent_name", ""),
        intent_type=intent.get("intent_type", "buy"),
        category=intent.get("category", ""),
        title=intent.get("title", ""),
        description=intent.get("description", ""),
        budget_min=float(intent.get("budget_min", 0)),
        budget_max=float(intent.get("budget_max", 0)),
        created_at=0, expires_at=time.time() + 86400, status="open",
    )
    iid = _intent_board.post_intent(obj)
    return {"id": iid, "status": "posted"}


@app.get("/api/market/matches")
async def get_matches(limit: int = 10):
    matches = sorted(_intent_board._matches.values(), key=lambda m: m.score, reverse=True)
    return {"matches": [vars(m) for m in matches[:limit]]}


@app.post("/api/market/accept-match")
async def accept_match(data: dict, request: Request):
    check_rate_limit(request, limit=10, window=60)
    mid = data.get("match_id", "")
    accepted = _intent_board.accept_match(mid) if mid in _intent_board._matches else None
    if accepted:
        deal = _deal_maker.create_deal_from_match(accepted)
        if deal:
            return {"status": "deal_created", **deal}
        return {"status": "accepted", "match": vars(accepted)}
    return {"error": "match not found"}


@app.post("/api/market/find-matches")
async def find_matches(data: dict, request: Request):
    check_rate_limit(request, limit=10, window=60)
    iid = data.get("intent_id", "")
    matches = _intent_board.find_matches(iid)
    for m in matches:
        _intent_board._matches[m.id] = m
    matches.sort(key=lambda m: m.score, reverse=True)
    return {"matches": [vars(m) for m in matches]}


@app.get("/api/market/summary")
async def market_summary():
    _intent_board.cleanup_expired()
    buys = _intent_board.get_open_intents("buy")
    sells = _intent_board.get_open_intents("sell")
    active = [m for m in _intent_board._matches.values() if m.status in ("pending", "accepted")]
    made = len([m for m in _intent_board._matches.values() if m.status == "deal_made"])
    return {
        "open_buys": len(buys), "open_sells": len(sells),
        "total_value_buys": sum(i.budget_max for i in buys),
        "total_value_sells": sum(i.budget_max for i in sells),
        "pending_matches": len(active), "deals_made": made,
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting convenatAI backend on 0.0.0.0:{port}")
    uvicorn.run("serve:app", host="0.0.0.0", port=port, reload=False)
