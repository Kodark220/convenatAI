"""
convenatAI — Agent Intent Matching Engine
==========================================
Agents post what they want to buy (intents) or what they offer (capabilities).
The engine matches them by description similarity, budget range, and availability.
"""

from __future__ import annotations

import json
import logging
import os
import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


# ─── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class Intent:
    """What an agent wants."""
    agent_address: str
    agent_name: str
    intent_type: str  # "buy" or "sell"
    category: str     # e.g. "data", "compute", "content", "analysis", "audit"
    title: str
    description: str
    budget_min: float  # USDC
    budget_max: float
    created_at: float
    expires_at: float
    status: str        # "open", "matched", "expired", "cancelled"
    id: str = ""

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def is_active(self) -> bool:
        return self.status == "open" and not self.is_expired()


@dataclass
class Match:
    """A match between a buyer intent and a seller capability."""
    buyer_intent: Intent
    seller_intent: Intent
    score: float          # 0.0 to 1.0 match confidence
    matched_at: float
    status: str           # "pending", "accepted", "negotiating", "deal_made", "rejected"
    deal_id: str = ""
    id: str = ""


# ─── Simple keyword-based matching ───────────────────────────────────────────

# Category keywords for matching
CATEGORY_KEYWORDS = {
    "data": ["data", "dataset", "feed", "sentiment", "price", "market", "stream", "api"],
    "compute": ["compute", "gpu", "cpu", "processing", "calculation", "render", "train"],
    "content": ["content", "article", "post", "writing", "copy", "blog", "social"],
    "analysis": ["analysis", "analytics", "report", "insight", "research", "audit", "review"],
    "audit": ["audit", "security", "contract", "review", "verify", "inspect"],
    "trading": ["trade", "swap", "exchange", "arbitrage", "market making"],
    "monitoring": ["monitor", "watch", "alert", "track", "observe", "scrape"],
}


def _compute_match_score(buyer: Intent, seller: Intent) -> float:
    """Score how well a buyer intent matches a seller intent (0.0 - 1.0)."""
    score = 0.0

    # Same category = big boost
    if buyer.category == seller.category:
        score += 0.3

    # Budget overlap
    if seller.budget_min <= buyer.budget_max and seller.budget_max >= buyer.budget_min:
        # How much overlap
        overlap_min = max(buyer.budget_min, seller.budget_min)
        overlap_max = min(buyer.budget_max, seller.budget_max)
        if overlap_max > overlap_min:
            buyer_range = max(buyer.budget_max - buyer.budget_min, 1)
            overlap_pct = (overlap_max - overlap_min) / buyer_range
            score += 0.2 * min(overlap_pct, 1.0)

    # Keyword overlap in title + description
    buyer_words = set((buyer.title + " " + buyer.description).lower().split())
    seller_words = set((seller.title + " " + seller.description).lower().split())
    common = buyer_words & seller_words
    if common:
        score += 0.15 * min(len(common) / 5, 1.0)

    # Category keyword overlap
    cat_words = CATEGORY_KEYWORDS.get(buyer.category, [])
    if cat_words:
        seller_cat_matches = sum(1 for w in cat_words if w in seller.description.lower())
        score += 0.1 * min(seller_cat_matches / 3, 1.0)

    # Both active
    if buyer.is_active() and seller.is_active():
        score += 0.1

    return min(score, 1.0)


# ─── Intent Board ────────────────────────────────────────────────────────────

class IntentBoard:
    """Central registry where agents post intents and get matched."""

    def __init__(self):
        self._intents: dict[str, Intent] = {}
        self._matches: dict[str, Match] = {}

    def post_intent(self, intent: Intent) -> str:
        """Post a new buy/sell intent. Returns the intent ID."""
        intent.id = f"intent-{int(time.time() * 1000)}-{random.randint(1000, 9999)}"
        intent.created_at = time.time()
        intent.status = "open"
        self._intents[intent.id] = intent
        logger.info(f"Intent posted: {intent.agent_name} wants to {intent.intent_type} "
                     f"'{intent.title}' ({intent.category}, ${intent.budget_min}-${intent.budget_max})")
        return intent.id

    def find_matches(self, intent_id: str) -> list[Match]:
        """Find all potential matches for a given intent."""
        intent = self._intents.get(intent_id)
        if not intent:
            return []

        matches = []
        target_type = "sell" if intent.intent_type == "buy" else "buy"

        for other in self._intents.values():
            if other.id == intent_id:
                continue
            if other.intent_type != target_type:
                continue
            if not other.is_active():
                continue

            score = _compute_match_score(intent, other)
            if score >= 0.35:  # Minimum threshold
                match = Match(
                    buyer_intent=intent if intent.intent_type == "buy" else other,
                    seller_intent=other if intent.intent_type == "buy" else intent,
                    score=score,
                    matched_at=time.time(),
                    status="pending",
                    id=f"match-{int(time.time() * 1000)}-{random.randint(1000, 9999)}",
                )
                matches.append(match)

        matches.sort(key=lambda m: m.score, reverse=True)
        return matches

    def accept_match(self, match_id: str) -> Optional[Match]:
        """Buyer and seller accept the match. Moves to negotiation."""
        match = self._matches.get(match_id)
        if not match:
            return None
        match.status = "accepted"
        match.buyer_intent.status = "matched"
        match.seller_intent.status = "matched"
        logger.info(f"Match accepted: {match.buyer_intent.agent_name} <-> "
                     f"{match.seller_intent.agent_name} (score: {match.score:.2f})")
        return match

    def get_open_intents(self, intent_type: Optional[str] = None) -> list[Intent]:
        """Get all open (unmatched, unexpired) intents."""
        return [
            i for i in self._intents.values()
            if i.is_active() and (intent_type is None or i.intent_type == intent_type)
        ]

    def get_agent_intents(self, agent_address: str) -> list[Intent]:
        """Get all intents for a specific agent."""
        return [i for i in self._intents.values() if i.agent_address == agent_address]

    def cleanup_expired(self):
        """Mark expired intents."""
        now = time.time()
        for intent in self._intents.values():
            if intent.status == "open" and now > intent.expires_at:
                intent.status = "expired"

    def to_dict(self) -> dict:
        return {
            "open_buys": [vars(i) for i in self.get_open_intents("buy")],
            "open_sells": [vars(i) for i in self.get_open_intents("sell")],
            "matches": [vars(m) for m in self._matches.values() if m.status in ("pending", "accepted")],
        }

    def auto_match_all(self) -> list[Match]:
        """Auto-match all open buy intents with open sell intents.
        Skips intents already matched. Returns newly created matches above threshold.
        Cleans up old pending matches for intents no longer open."""
        new_matches = []

        # First: remove stale pending matches for intents that are now matched/expired
        matched_intent_ids = {
            i.id for i in self._intents.values()
            if i.status in ("matched", "expired", "cancelled")
        }
        stale_ids = [
            mid for mid, m in self._matches.items()
            if m.status == "pending" and (
                m.buyer_intent.id in matched_intent_ids or
                m.seller_intent.id in matched_intent_ids
            )
        ]
        for sid in stale_ids:
            del self._matches[sid]
        if stale_ids:
            logger.info(f"🧹 Cleaned {len(stale_ids)} stale pending matches")

        # Only match intents that are still open and haven't been matched before
        buys = self.get_open_intents("buy")
        sells = self.get_open_intents("sell")

        # Track which intent IDs already have pending matches to avoid duplicates
        already_matched = set()
        for m in self._matches.values():
            if m.status in ("pending", "accepted"):
                already_matched.add((m.buyer_intent.id, m.seller_intent.id))

        for buyer in buys:
            matches = self.find_matches(buyer.id)
            for m in matches:
                pair = (m.buyer_intent.id, m.seller_intent.id)
                if pair in already_matched:
                    continue
                self._matches[m.id] = m
                already_matched.add(pair)
                new_matches.append(m)

        return new_matches

    def auto_accept_best(self, min_score: float = 0.45) -> Optional[Match]:
        """Auto-accept the best pending match above threshold.
        Only accepts one match per intent pair — prevents duplicate deals.
        No human needed — fully autonomous."""
        pending = sorted(
            [m for m in self._matches.values() if m.status == "pending"],
            key=lambda m: m.score, reverse=True,
        )
        if pending and pending[0].score >= min_score:
            match = pending[0]
            match.status = "accepted"
            match.buyer_intent.status = "matched"
            match.seller_intent.status = "matched"
            logger.info(f"🤖 Auto-accepted match: {match.buyer_intent.agent_name} <-> "
                        f"{match.seller_intent.agent_name} (score: {match.score:.2f})")
            return match
        return None


# ─── Deal Maker (turns matched intents into Arc deals) ──────────────────────

class DealMaker:
    """Takes accepted matches and creates real Arc ERC-8183 deals."""

    def __init__(self, board: IntentBoard):
        self.board = board
        self._deals: dict = {}

    def create_deal_from_match(self, match: Match) -> Optional[dict]:
        """Create an Arc deal from a match. Returns deal info or None."""
        if match.status != "accepted":
            logger.warning(f"Cannot create deal from match {match.id}: status is {match.status}")
            return None

        deal = {
            "match_id": match.id,
            "buyer": match.buyer_intent.agent_address,
            "seller": match.seller_intent.agent_address,
            "title": match.buyer_intent.title,
            "description": match.buyer_intent.description,
            "budget": min((match.buyer_intent.budget_min + match.seller_intent.budget_max) / 2, 4.50),
            "category": match.buyer_intent.category,
            "status": "deal_pending",
            "created_at": time.time(),
        }

        deal_id = f"deal-{int(time.time() * 1000)}"
        self._deals[deal_id] = deal
        match.status = "deal_made"
        match.deal_id = deal_id

        logger.info(f"Deal created from match: {deal_id} — {deal['title']} (${deal['budget']:.2f})")
        return {"deal_id": deal_id, **deal}
