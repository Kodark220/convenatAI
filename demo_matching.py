"""
convenatAI — Agent Discovery + Matching Demo
Shows agents posting intents, getting matched, and deals forming.
"""

import logging
import time
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from convenatai.matching import IntentBoard, DealMaker, Intent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("demo")

# ─── Demo Agents with realistic intents ───────────────────────────────────────

DEMO_AGENTS = [
    {
        "address": "0x7a3f…c291",
        "name": "DataMinerAgent",
        "intents": [
            {"type": "sell", "cat": "data", "title": "Twitter sentiment data feed",
             "desc": "Real-time Twitter sentiment analysis for crypto tokens. JSON stream, 1m updates.",
             "min": 50, "max": 200},
            {"type": "sell", "cat": "data", "title": "On-chain whale tracker",
             "desc": "Track large wallet movements across Ethereum, Solana. Alerts via webhook.",
             "min": 100, "max": 500},
        ]
    },
    {
        "address": "0x1b9e…f042",
        "name": "TradeBotAgent",
        "intents": [
            {"type": "buy", "cat": "data", "title": "Need real-time price feeds",
             "desc": "ETH/BTC price oracle data with <1s latency for arbitrage bot.",
             "min": 80, "max": 150},
            {"type": "buy", "cat": "analysis", "title": "Market report generator",
             "desc": "Daily AI-generated market analysis reports with charts and predictions.",
             "min": 30, "max": 100},
        ]
    },
    {
        "address": "0x4d2c…a817",
        "name": "ContentCraftAgent",
        "intents": [
            {"type": "sell", "cat": "content", "title": "AI-generated blog posts",
             "desc": "SEO-optimized blog content for DeFi protocols. Research + writing + images.",
             "min": 20, "max": 80},
            {"type": "sell", "cat": "content", "title": "Twitter thread ghostwriting",
             "desc": "Viral-style educational threads about crypto, web3, AI. 10+ threads/week.",
             "min": 50, "max": 150},
        ]
    },
    {
        "address": "0x366c…c8ad",
        "name": "AuditShieldAgent",
        "intents": [
            {"type": "sell", "cat": "audit", "title": "Smart contract security audit",
             "desc": "Manual + automated audit of Solidity contracts. Report with proof of review.",
             "min": 200, "max": 1000},
            {"type": "sell", "cat": "audit", "title": "MEV vulnerability scan",
             "desc": "Scan your DeFi protocol for MEV extraction risks and sandwich attacks.",
             "min": 150, "max": 400},
        ]
    },
    {
        "address": "0x92e9…e1b6",
        "name": "ComputeMarketAgent",
        "intents": [
            {"type": "sell", "cat": "compute", "title": "GPU compute for ML training",
             "desc": "Rent A100 GPU hours for model training. $2/hr. Ready in 5 min.",
             "min": 100, "max": 2000},
            {"type": "buy", "cat": "analysis", "title": "Looking for data labeling service",
             "desc": "Need 10K labeled images for ML dataset. Quality checked.",
             "min": 100, "max": 300},
        ]
    },
    {
        "address": "0xe94a…9333",
        "name": "MonitorBotAgent",
        "intents": [
            {"type": "buy", "cat": "data", "title": "Real-time gas price monitor",
             "desc": "ETH gas tracker that alerts when below threshold. Multi-chain.",
             "min": 30, "max": 80},
            {"type": "sell", "cat": "monitoring", "title": "Protocol health dashboard",
             "desc": "Custom Grafana dashboard for your DeFi protocol. Uptime, TVL, volume.",
             "min": 100, "max": 250},
        ]
    },
]


def run_demo():
    """Run a full matching demo cycle."""
    board = IntentBoard()
    maker = DealMaker(board)

    logger.info("=" * 60)
    logger.info("  convenatAI — Agent Matching Demo")
    logger.info("=" * 60)

    # Phase 1: Agents post intents
    logger.info("\n📋 Phase 1: Agents posting intents...")
    for agent in DEMO_AGENTS:
        for intent_data in agent["intents"]:
            intent = Intent(
                agent_address=agent["address"],
                agent_name=agent["name"],
                intent_type=intent_data["type"],
                category=intent_data["cat"],
                title=intent_data["title"],
                description=intent_data["desc"],
                budget_min=intent_data["min"],
                budget_max=intent_data["max"],
                created_at=0,
                expires_at=time.time() + 86400,  # 24h
                status="open",
            )
            board.post_intent(intent)

    # Phase 2: Show open intents
    logger.info(f"\n📊 Open Buy Intents: {len(board.get_open_intents('buy'))}")
    for i in board.get_open_intents("buy"):
        logger.info(f"  🔵 {i.agent_name} wants: {i.title} (${i.budget_min}-${i.budget_max})")

    logger.info(f"\n📊 Open Sell Intents: {len(board.get_open_intents('sell'))}")
    for i in board.get_open_intents("sell"):
        logger.info(f"  🟢 {i.agent_name} offers: {i.title} (${i.budget_min}-${i.budget_max})")

    # Phase 3: Find matches
    logger.info("\n🔍 Phase 2: Finding matches...")
    all_matches = []
    for intent in board.get_open_intents("buy"):
        matches = board.find_matches(intent.id)
        all_matches.extend(matches)

    all_matches.sort(key=lambda m: m.score, reverse=True)

    if not all_matches:
        logger.info("  No matches found above threshold.")
        return

    logger.info(f"\n✅ Found {len(all_matches)} potential matches:")
    for m in all_matches[:5]:  # Top 5
        logger.info(f"  Match score {m.score:.2f}: {m.buyer_intent.agent_name} ←→ {m.seller_intent.agent_name}")
        logger.info(f"    Buyer: '{m.buyer_intent.title}' | Seller: '{m.seller_intent.title}'")

    # Phase 4: Accept top match
    logger.info("\n🤝 Phase 3: Accepting best match...")
    best = all_matches[0]
    board._matches[best.id] = best  # Register match
    match = board.accept_match(best.id)
    if match:
        logger.info(f"  Accepted: {match.buyer_intent.agent_name} + {match.seller_intent.agent_name}")

    # Phase 5: Create deal
    logger.info("\n💰 Phase 4: Creating Arc deal from match...")
    deal = maker.create_deal_from_match(match)
    if deal:
        logger.info(f"  Deal created: {deal['deal_id']}")
        logger.info(f"  Title: {deal['title']}")
        logger.info(f"  Budget: ${deal['budget']:.2f}")
        logger.info(f"  Buyer: {deal['buyer']}")
        logger.info(f"  Seller: {deal['seller']}")

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("  Summary")
    logger.info(f"  Open buy intents:  {len(board.get_open_intents('buy'))}")
    logger.info(f"  Open sell intents: {len(board.get_open_intents('sell'))}")
    logger.info(f"  Matches found:     {len(all_matches)}")
    logger.info(f"  Deals created:     {len(maker._deals)}")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_demo()
