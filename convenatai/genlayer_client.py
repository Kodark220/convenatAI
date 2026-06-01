"""
convenatAI — GenLayer Client (CLI-first with Python RPC + Mock fallback)

Strategy (tiered):
1. Try `genlayer` CLI (Node.js) for writes — works if installed and has RAM
2. Try Python HTTP JSON-RPC for reads — always works
3. Mock fallback for writes — when CLI is unavailable

The CLI needs ~1.2GB VM during account import but settles to ~300MB after.
On 512MB+ machines the genlayer CLI works fine.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import urllib.request
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ─── Configuration ─────────────────────────────────────────────────────

GENLAYER_CONTRACT = os.getenv(
    "CONVENAT_CONTRACT_ADDRESS",
    "0xc821A31Bfe1299131D4D07E78a0c7D388B1E9642",  # Studionet
)

GENLAYER_NETWORK = os.getenv("GENLAYER_NETWORK", "studionet")
_GENLAYER_PASSWORD = os.getenv("GENLAYER_PASSWORD", "convenatAI123")

# GenLayer RPC endpoints (fallback chain)
_GENLAYER_RPCS = [
    os.getenv("GENLAYER_RPC_URL", "https://rpc-bradbury.genlayer.com"),
    "https://studio.genlayer.com/api",
]

# ─── CLI availability check ──────────────────────────────────────────

def _cli_available() -> bool:
    """Check if the genlayer CLI is installed and has an imported account."""
    try:
        # Check if CLI exists
        result = subprocess.run(
            ["genlayer", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return False
        # Check if account was already imported (from a previous deploy)
        acct = subprocess.run(
            ["genlayer", "account", "list"],
            capture_output=True, text=True, timeout=10,
            input=_GENLAYER_PASSWORD + "\n",
        )
        if "convenatAI" in (acct.stdout + acct.stderr):
            return True
        # CLI exists but no account — can't write (import spikes >512MB)
        logger.info("genlayer CLI installed but no account imported — writes will use mock")
        return False
    except FileNotFoundError:
        return False
    except Exception as e:
        logger.debug(f"genlayer CLI check: {e}")
        return False


# ─── CLI subprocess helper ────────────────────────────────────────────

def _cli_exec(*args: str, timeout: int = 60, input_text: str | None = None) -> dict:
    """Run a genlayer CLI command and return JSON/status."""
    cmd = ["genlayer", *args]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=timeout,
            input=input_text or (_GENLAYER_PASSWORD + "\n"),
        )
        output = (proc.stdout + proc.stderr).strip()
        if proc.returncode != 0:
            return {"status": "error", "error": output[:500]}
        return {"status": "success", "output": output[:500]}
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "CLI timed out"}
    except FileNotFoundError:
        return {"status": "error", "error": "CLI not found"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ─── Raw JSON-RPC call against GenLayer ──────────────────────────────

def _genlayer_rpc_call(rpc_url: str, method: str, params: list) -> dict:
    """Make a GenLayer JSON-RPC call."""
    data = json.dumps({
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1,
    }).encode()
    req = urllib.request.Request(
        rpc_url, data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "convenatAI/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def _genlayer_read(method: str, params: dict) -> dict:
    """Try to call a GenLayer view/read method via JSON-RPC.
    Tries multiple RPC endpoints in order.
    """
    for rpc_url in _GENLAYER_RPCS:
        try:
            result = _genlayer_rpc_call(rpc_url, method, [params])
            if "error" in result:
                logger.debug(f"GenLayer RPC {rpc_url} error: {result['error']}")
                continue
            return result
        except Exception as e:
            logger.debug(f"GenLayer RPC {rpc_url} failed: {e}")
            continue
    return {"status": "error", "error": "All GenLayer RPC endpoints unreachable"}


def _decode_genlayer_job(raw: dict) -> dict:
    """Parse a raw GenLayer response into a usable job status dict."""
    result = raw.get("result", {})
    if isinstance(result, dict):
        return {
            "active": result.get("active"),
            "stream_id": result.get("stream_id"),
            "buyer_id": result.get("buyer_id"),
            "seller_id": result.get("seller_id"),
            "description": result.get("description"),
            "status": result.get("status"),
            "raw": result,
        }
    return {"raw": result}


class NotifyGenLayer:
    """GenLayer SLA client with CLI-first, mock-fallback strategy."""

    @staticmethod
    def register_job(
        stream_id: str,
        buyer_id: str,
        seller_id: str,
        description: str,
        quality_criteria: str = "Standard SLA terms",
        deliverable_uri: str = "",
    ) -> dict:
        """Register a job on GenLayer. Tries CLI first, falls back to mock."""
        logger.info(
            f"Registering job on GenLayer ({GENLAYER_NETWORK}): {stream_id} "
            f"(buyer={buyer_id[:12]}..., seller={seller_id[:12]}...)"
        )

        # Try CLI first
        if _cli_available():
            logger.info("genlayer CLI available — attempting live write")
            result = _cli_exec(
                "write",
                GENLAYER_CONTRACT,
                "register_job",
                "--args", stream_id, buyer_id, seller_id, description,
                timeout=120,
            )
            if result.get("status") != "error":
                logger.info(f"GenLayer register_job live: {result.get('output', '')[:200]}")
                return {"status": "registered", "stream_id": stream_id, "live": True}
            logger.warning(f"GenLayer CLI write failed: {result.get('error')}")

        # Fallback to mock
        logger.info(f"GenLayer notification (mock): {stream_id}")
        return {"status": "notified", "stream_id": stream_id, "mode": "mock"}

    @staticmethod
    def monitor_stream(
        stream_id: str,
        deliverable_uri: str,
    ) -> dict:
        """Trigger AI quality evaluation on GenLayer."""
        if _cli_available():
            result = _cli_exec(
                "write",
                GENLAYER_CONTRACT,
                "monitor_stream",
                "--args", stream_id, deliverable_uri,
                timeout=60,
            )
            if result.get("status") != "error":
                return {"status": "evaluated", "stream_id": stream_id, "live": True}
        return {"status": "mock", "stream_id": stream_id}

    @staticmethod
    def get_job_status(stream_id: str) -> dict:
        """Check job status on GenLayer via Python HTTP RPC (works without CLI)."""
        logger.debug(f"Checking GenLayer job status via RPC: {stream_id}")

        raw_result = _genlayer_read("gen_call", {
            "contract": GENLAYER_CONTRACT,
            "method": "get_job_status",
            "args": {"stream_id": stream_id},
        })

        if raw_result.get("status") == "error":
            logger.warning(f"GenLayer RPC read failed: {raw_result.get('error')}")
            return {"error": raw_result.get("error")}

        decoded = _decode_genlayer_job(raw_result)
        if decoded.get("active") is not None:
            logger.info(f"GenLayer job {stream_id}: active={decoded['active']}")
            return {"result": decoded, "source": "rpc"}

        if decoded.get("raw"):
            return {"result": decoded, "source": "rpc_raw"}

        return {"error": f"No data for stream {stream_id} on GenLayer"}
