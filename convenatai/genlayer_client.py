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
    "0xa420275FBC13949Fd42f879A31d7B9187BD06A08",  # Bradbury Testnet
)

GENLAYER_NETWORK = os.getenv("GENLAYER_NETWORK", "testnet-bradbury")

# Path to Node.js bridge script
_SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts")
_BRIDGE_SCRIPT = os.path.join(_SCRIPTS_DIR, "genlayer_bridge.js")

# GenLayer RPC endpoints (fallback chain)
_GENLAYER_RPCS = [
    os.getenv("GENLAYER_RPC_URL", "https://rpc-bradbury.genlayer.com"),
    "https://studio.genlayer.com:8443/api",
]

# ─── Node.js Bridge Helper ────────────────────────────────────────────

def _node_bridge_exec(contract: str, method: str, kwargs: dict, timeout: int = 120) -> dict:
    """Call the GenLayer Node.js bridge for a write transaction.
    
    Uses the private key from GENLAYER_PRIVATE_KEY env var directly
    (no keystore, no password prompt).
    """
    cmd = ["node", _BRIDGE_SCRIPT, "write", contract, method, json.dumps(kwargs)]
    env = os.environ.copy()
    logger.info(f"Running: {' '.join(cmd)[:200]}...")

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=timeout,
            env=env,
        )
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        if stdout:
            logger.debug(f"Bridge stdout: {stdout[:300]}")
        if stderr:
            logger.warning(f"Bridge stderr: {stderr[:300]}")
        if proc.returncode == 0 and stdout:
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                pass
            return {"status": "success", "output": stdout[:500]}
        logger.warning(f"Bridge failed (exit {proc.returncode}): {stderr[:300]}")
        return {"status": "error", "error": stderr[:500] or f"exit {proc.returncode}"}
    except subprocess.TimeoutExpired:
        logger.warning("Node.js bridge timed out")
        return {"status": "error", "error": "Node.js bridge timed out"}
    except FileNotFoundError:
        logger.warning("Node.js not found")
        return {"status": "error", "error": "Node.js not found"}
    except Exception as e:
        logger.warning(f"Bridge error: {e}")
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
            # Bradbury uses type='read', Studio uses type='gen_call'
            is_studio = "studio" in rpc_url
            call_type = "gen_call" if is_studio else "read"
            call_params = {"type": call_type, **params}
            result = _genlayer_rpc_call(rpc_url, method, [call_params])
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
    """GenLayer SLA client.

    Uses Node.js bridge for writes. Falls back to mock on error.
    If GENLAYER_RELAY_URL is set, sends writes there instead (for local relay).
    """

    @staticmethod
    def _relay_write(method: str, kwargs: dict) -> dict | None:
        """Try sending write to local relay server (unblocked IP)."""
        relay_url = os.getenv("GENLAYER_RELAY_URL", "")
        if not relay_url:
            return None
        try:
            data = json.dumps({
                "method": method,
                "kwargs": kwargs,
                "contract": GENLAYER_CONTRACT,
            }).encode()
            req = urllib.request.Request(
                relay_url + "/genlayer/write",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
                if result.get("status") == "ok":
                    return result
                return None
        except Exception as e:
            logger.debug(f"Relay write failed: {e}")
            return None

    @staticmethod
    def register_job(
        stream_id: str,
        buyer_id: str,
        seller_id: str,
        description: str,
        quality_criteria: str = "Standard SLA terms",
        deliverable_uri: str = "",
    ) -> dict:
        """Register a job on GenLayer via direct RPC gen_send."""
        logger.info(
            f"Registering job on GenLayer ({GENLAYER_NETWORK}): {stream_id} "
            f"(buyer={buyer_id[:12]}..., seller={seller_id[:12]}...)"
        )

        # Try local relay first (unblocked home IP)
        kwargs_data = {
            "stream_id": stream_id,
            "buyer_id": buyer_id,
            "seller_id": seller_id,
            "description": description,
            "quality_criteria": quality_criteria,
            "deliverable_uri": deliverable_uri,
        }
        relay_result = NotifyGenLayer._relay_write("register_job", kwargs_data)
        if relay_result:
            logger.info(f"GenLayer register_job via relay: successful")
            return {"status": "registered", "stream_id": stream_id, "live": True}

        # Try Node.js bridge next (may fail with 522 from cloud)
        result = _node_bridge_exec(
            GENLAYER_CONTRACT, "register_job", kwargs_data, timeout=120
        )
        if result.get("status") != "error" or result.get("result"):
            logger.info(f"GenLayer register_job via bridge: {str(result)[:200]}")
            return {"status": "registered", "stream_id": stream_id, "live": True}

        # Fallback: mock
        logger.info(f"GenLayer notification (mock): {stream_id}")
        return {"status": "notified", "stream_id": stream_id, "mode": "mock"}

    @staticmethod
    def monitor_stream(
        stream_id: str,
        deliverable_uri: str,
    ) -> dict:
        """Trigger AI quality evaluation on GenLayer via Node.js bridge."""
        kwargs_data = {
            "stream_id": stream_id,
            "deliverable_uri": deliverable_uri,
        }
        result = _node_bridge_exec(
            GENLAYER_CONTRACT, "monitor_stream", kwargs_data, timeout=60
        )
        if result.get("status") != "error" or result.get("result"):
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
