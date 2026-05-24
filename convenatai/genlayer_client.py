"""
convenatAI — GenLayer Client Helper

Wraps calls to the ConvenatContract deployed on GenLayer Bradbury/Studionet.
Uses Bradbury RPC as primary, falls back to Studionet.

Usage:
    from .genlayer_client import NotifyGenLayer, call_genlayer_contract

    # Register a job on GenLayer after arbitration
    tx = NotifyGenLayer.register_job(
        stream_id="stream-001",
        buyer_id="0x...",
        seller_id="0x...",
        description="SLA monitor for AI deal",
        quality_criteria="95% uptime required",
        deliverable_uri="https://api.example.com/delivery/1",
    )

    # Monitor a stream (AI quality evaluation)
    result = NotifyGenLayer.monitor_stream(
        stream_id="stream-001",
        deliverable_uri="https://api.example.com/delivery/1",
    )
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ─── Configuration (Bradbury primary, Studionet fallback) ──────────────────

GENLAYER_RPCS = [
    os.getenv("GENLAYER_RPC_URL", "https://rpc-bradbury.genlayer.com"),  # Bradbury (env override)
    "https://studio.genlayer.com:8443/api",                               # Studionet (fallback)
    "https://studio.genlayer.com/api",                                    # Studionet alt (fallback)
]

GENLAYER_CONTRACTS = [
    os.getenv("CONVENAT_CONTRACT_BRADBURY", "0xa420275FBC13949Fd42f879A31d7B9187BD06A08"),  # Bradbury
    os.getenv("CONVENAT_CONTRACT_ADDRESS", "0xc821A31Bfe1299131D4D07E78a0c7D388B1E9642"),   # Studionet
]

ADDR_PREFIX = "addr-"


def _try_rpcs(method: str, params: list | dict, timeout: int = 8) -> dict:
    """Try each GenLayer RPC in order until one works."""
    errors = []
    # Normalize to list of param objects
    param_list = params if isinstance(params, list) else [params]
    for i, rpc_url in enumerate(GENLAYER_RPCS):
        contract = GENLAYER_CONTRACTS[min(i, len(GENLAYER_CONTRACTS) - 1)]
        # Set contract address in each param object
        for p in param_list:
            p["to"] = contract
        data = json.dumps({
            "jsonrpc": "2.0",
            "method": method,
            "params": param_list,
            "id": 1,
        }).encode()
        req = urllib.request.Request(
            rpc_url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "convenatAI/1.0"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read().decode())
                if "error" not in result:
                    return result
                errors.append(f"{rpc_url}: {result['error']}")
        except Exception as e:
            errors.append(f"{rpc_url}: {e}")
            continue
    return {"error": "; ".join(errors)}


def _format_addr(raw: str) -> str:
    """Format address for GenLayer contract storage (bypass Address type)."""
    if raw.startswith("0x"):
        return ADDR_PREFIX + raw[2:]
    if not raw.startswith(ADDR_PREFIX):
        return ADDR_PREFIX + raw
    return raw


class NotifyGenLayer:
    """Helper to call ConvenatContract methods on GenLayer."""

    @staticmethod
    def register_job(
        stream_id: str,
        buyer_id: str,
        seller_id: str,
        description: str,
        quality_criteria: str = "Standard SLA terms",
        deliverable_uri: str = "",
    ) -> dict:
        """Register a job on the ConvenatContract (SLA monitor)."""
        buyer = _format_addr(buyer_id)
        seller = _format_addr(seller_id)

        logger.info(
            f"Registering job on GenLayer: {stream_id} "
            f"(buyer={buyer_id[:12]}..., seller={seller_id[:12]}...)"
        )

        result = _try_rpcs("gen_call", [{
            "to": GENLAYER_CONTRACTS[0],
            "method": "register_job",
            "args": {
                "stream_id": stream_id,
                "buyer_id": buyer,
                "seller_id": seller,
                "description": description,
                "quality_criteria": quality_criteria,
                "deliverable_uri": deliverable_uri,
            },
            "type": "write",
        }])

        if result.get("error"):
            return {"status": "rpc_error", "error": result["error"]}

        return {"status": "notified", "stream_id": stream_id}

    @staticmethod
    def monitor_stream(
        stream_id: str,
        deliverable_uri: str,
    ) -> dict:
        """Trigger AI quality evaluation on GenLayer for a stream."""
        logger.info(f"Monitoring GenLayer stream: {stream_id} @ {deliverable_uri}")

        result = _try_rpcs("gen_call", [{
            "to": GENLAYER_CONTRACTS[0],
            "method": "monitor_stream",
            "args": {
                "stream_id": stream_id,
                "deliverable_uri": deliverable_uri,
            },
            "type": "write",
        }])

        if result.get("error"):
            return {"status": "rpc_error", "error": result["error"]}

        return {"status": "evaluated", "stream_id": stream_id}

    @staticmethod
    def get_job_status(stream_id: str) -> dict:
        """Check job status on GenLayer (tries Bradbury, falls back to Studionet)."""
        result = _try_rpcs("gen_call", [{
            "to": GENLAYER_CONTRACTS[0],
            "method": "get_job_status",
            "args": {"stream_id": stream_id},
            "type": "read",
        }])

        if result.get("error"):
            return {"status": "error", "error": result["error"]}

        return result.get("result", {})
