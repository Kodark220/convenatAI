"""
convenatAI — GenLayer Client Helper

Wraps calls to the ConvenatContract deployed on GenLayer Studionet.
Handles the RPC format differences for gen_call vs eth JSON-RPC.

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
import subprocess
import sys
import urllib.request
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ─── Configuration ───────────────────────────────────────────────────────────

CONVENAT_CONTRACT = os.getenv(
    "CONVENAT_CONTRACT_ADDRESS",
    "0xc821A31Bfe1299131D4D07E78a0c7D388B1E9642",
)
GENLAYER_RPC = os.getenv(
    "GENLAYER_RPC_URL",
    "https://studio.genlayer.com/api",
)

# Prefixed address format (GenLayer CLI converts bare 0x... to Address type;
# using 'addr-' prefix forces string storage in the contract)
ADDR_PREFIX = "addr-"


def _has_cli() -> bool:
    """Check if genlayer CLI is available (runs on Windows via PowerShell)."""
    try:
        result = subprocess.run(
            ["powershell.exe", "-Command", "genlayer --version"],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def _cli_call(method: str, args: list[str]) -> dict:
    """Call a view method via genlayer CLI (handles auth)."""
    quoted = [f"'{a}'" for a in args]
    cmd = (
        f"genlayer call {CONVENAT_CONTRACT} {method} "
        f"--args {' '.join(quoted)}"
    )
    try:
        result = subprocess.run(
            ["powershell.exe", "-Command", cmd],
            capture_output=True, text=True, timeout=60,
        )
        stdout = result.stdout
        # Parse JSON from output (CLI prints extra text)
        # Find the Result: line and parse below it
        lines = stdout.split("\n")
        # Find everything between "Result:" line and empty line or "√"
        in_result = False
        json_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped == "Result:":
                in_result = True
                continue
            if in_result:
                if not stripped or stripped.startswith("√"):
                    break
                json_lines.append(stripped)
        json_str = " ".join(json_lines)
        if json_str:
            import ast
            try:
                py_str = json_str.replace(': true,', ': True,').replace(': true}', ': True}')
                py_str = py_str.replace(': false,', ': False,').replace(': false}', ': False}')
                py_str = py_str.replace(': null,', ': None,').replace(': null}', ': None}')
                parsed = ast.literal_eval(py_str)
                return {"result": parsed}
            except Exception as e:
                # Manual conversion: NodeJS-style {key: val} -> Python dict
                import re
                # Find all key: value pairs
                quoted = json_str
                # Remove outer braces
                quoted = quoted.strip()
                if quoted.startswith("{") and quoted.endswith("}"):
                    quoted = quoted[1:-1].strip()
                result = {}
                # Split by comma, but not inside strings
                import re as _re
                pairs = _re.split(r",\s*(?=(?:[^']*'[^']*')*[^']*$)", quoted)
                for pair in pairs:
                    if ":" not in pair:
                        continue
                    key, _, val = pair.partition(":")
                    key = key.strip().strip("'").strip('"')
                    val = val.strip().strip("'").strip('"')
                    if val == "true":
                        val = True
                    elif val == "false":
                        val = False
                    elif val == "null":
                        val = None
                    result[key] = val
                return {"result": result}
        return {"error": "No JSON result found", "raw": stdout[:500]}
    except Exception as e:
        return {"error": str(e)}


def _cli_write(method: str, args: list[str]) -> dict:
    """Call a write method via genlayer CLI (handles auth)."""
    quoted = [f"'{a}'" for a in args]
    cmd = (
        f"genlayer write {CONVENAT_CONTRACT} {method} "
        f"--args {' '.join(quoted)}"
    )
    try:
        result = subprocess.run(
            ["powershell.exe", "-Command", cmd],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            return {"status": "executed", "method": method}
        return {"status": "error", "error": result.stderr[:500] or result.stdout[:500]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _rpc(method: str, params: dict) -> dict:
    """Make a GenLayer JSON-RPC call (direct HTTP, may 403 for gen_call)."""
    data = json.dumps({
        "jsonrpc": "2.0",
        "method": method,
        "params": [params],
        "id": 1,
    }).encode()
    req = urllib.request.Request(
        GENLAYER_RPC,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "convenatAI/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        logger.warning(f"GenLayer RPC call failed: {e}")
        return {"error": str(e)}


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
        """
        Register a job on the ConvenatContract (SLA monitor).

        Uses genlayer CLI via PowerShell for authenticated writes.
        Falls back to direct HTTP if CLI unavailable.
        """
        logger.info(
            f"Registering job on GenLayer: {stream_id} "
            f"(buyer={buyer_id[:12]}..., seller={seller_id[:12]}...)"
        )

        buyer = _format_addr(buyer_id)
        seller = _format_addr(seller_id)

        if _has_cli():
            return _cli_write("register_job", [
                stream_id, buyer, seller,
                description, quality_criteria, deliverable_uri,
            ])

        # Fallback: direct RPC
        logger.warning("GenLayer CLI not available, trying direct RPC")
        result = _rpc("gen_call", {
            "to": CONVENAT_CONTRACT,
            "method": "register_job",
            "args": {
                "stream_id": stream_id,
                "buyer_id": buyer,
                "seller_id": seller,
                "description": description,
                "quality_criteria": quality_criteria,
                "deliverable_uri": deliverable_uri,
            },
        })

        if result.get("error"):
            return {"status": "rpc_error", "error": result["error"]}

        return {"status": "notified", "stream_id": stream_id}

    @staticmethod
    def monitor_stream(
        stream_id: str,
        deliverable_uri: str,
    ) -> dict:
        """
        Trigger AI quality evaluation on GenLayer for a stream.

        Uses genlayer CLI via PowerShell for authenticated writes.
        Falls back to direct RPC if CLI unavailable.
        """
        logger.info(f"Monitoring GenLayer stream: {stream_id} @ {deliverable_uri}")

        if _has_cli():
            return _cli_write("monitor_stream", [
                stream_id, deliverable_uri,
            ])

        # Fallback: direct RPC
        logger.warning("GenLayer CLI not available, trying direct RPC")
        result = _rpc("gen_call", {
            "to": CONVENAT_CONTRACT,
            "method": "monitor_stream",
            "args": {
                "stream_id": stream_id,
                "deliverable_uri": deliverable_uri,
            },
        })

        if result.get("error"):
            return {"status": "rpc_error", "error": result["error"]}

        return {"status": "evaluated", "stream_id": stream_id}

    @staticmethod
    def get_job_status(stream_id: str) -> dict:
        """Check job status on GenLayer."""
        if _has_cli():
            return _cli_call("get_job_status", [stream_id])

        # Fallback: direct RPC
        result = _rpc("gen_call", {
            "to": CONVENAT_CONTRACT,
            "method": "get_job_status",
            "args": {"stream_id": stream_id},
        })

        if result.get("error"):
            return {"status": "error", "error": result["error"]}

        return result.get("result", {})
