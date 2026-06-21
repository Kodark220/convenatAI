"""
convenatAI — GenLayer Client (SDK + RPC Hybrid)

Strategy (tiered):
1. GenLayer SDK (genlayer-py) — handles proper tx encoding + signing via
   eth_sendRawTransaction → consensus contract addTransaction
   (Works on Fly.io where genlayer-py is installed in Docker)
2. Python direct HTTP gen_call RPC — for reads only (get_job_status)
3. Node.js bridge fallback (genlayer_bridge.js)
4. Mock fallback — when all else fails

Key insight:
- Reads: gen_call RPC method with type='read', data=hex_encoded_method
- Writes: MUST go through eth_sendRawTransaction → consensus contract
          (Can't use gen_call type='write' — that's not how GenLayer works)
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import urllib.error
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

GENLAYER_PRIVATE_KEY = os.getenv("GENLAYER_PRIVATE_KEY", "")

# Path to Node.js bridge script
_SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts")
_BRIDGE_SCRIPT = os.path.join(_SCRIPTS_DIR, "genlayer_bridge.js")

# GenLayer RPC endpoints (tried in order for reads)
_GENLAYER_RPCS = [
    os.getenv("GENLAYER_RPC_URL", "https://studio.genlayer.com/api"),
    "https://rpc-bradbury.genlayer.com",
]

# ─── SDK Integration (for writes on Fly.io) ────────────────────────────

def _try_sdk_write(method: str, args: dict) -> dict | None:
    """Try using the genlayer-py SDK for a proper write transaction."""
    try:
        from genlayer_py import create_client
        from eth_account import Account
        from eth_account.signers.local import LocalAccount

        pk = GENLAYER_PRIVATE_KEY.replace("0x", "")
        if not pk or len(pk) != 64:
            logger.warning("SDK write: no valid private key")
            return None

        # Use Bradbury for writes (Studionet may not have GEN balance for gas)
        # Contract on Bradbury: 0xa420275FBC13949Fd42f879A31d7B9187BD06A08
        from genlayer_py.chains import testnet_bradbury as bradbury_chain
        
        account: LocalAccount = Account.from_key(pk)
        
        client = create_client(
            chain=bradbury_chain,
            account=account,
        )

        # Send write tx via SDK — use ordered args list to match contract param order
        bradbury_contract = "0xa420275FBC13949Fd42f879A31d7B9187BD06A08"
        logger.info(f"SDK write: {method}({args.get('stream_id', '?')}) to {bradbury_contract} on Bradbury")

        # Map method name to ordered param list (GenLayer kwargs sort alphabetically,
        # but contract expects specific order)
        if method == "register_job":
            ordered_args = [
                args.get("stream_id", ""),
                args.get("buyer_id", ""),
                args.get("seller_id", ""),
                args.get("description", ""),
                args.get("quality_criteria", ""),
                args.get("deliverable_uri", ""),
            ]
        elif method == "monitor_stream":
            ordered_args = [
                args.get("stream_id", ""),
                args.get("deliverable_uri", ""),
            ]
        else:
            ordered_args = list(args.values())

        tx_hash = client.write_contract(
            address=bradbury_contract,
            function_name=method,
            args=ordered_args,  # ordered list in contract param order
            account=account,
        )

        if tx_hash:
            logger.info(f"SDK write success: tx={tx_hash}")
            return {"status": "success", "tx_hash": tx_hash, "method": "sdk"}

        logger.warning("SDK write returned no tx hash")
        return None

    except ImportError as e:
        logger.debug(f"genlayer-py SDK not available: {e}")
        return None
    except Exception as e:
        logger.warning(f"SDK write failed: {e}")
        # Log more detail for debugging
        import traceback
        logger.warning(f"SDK traceback: {traceback.format_exc()[:300]}")
        return None


# ─── SDK Read (same genlayer-py SDK, works from cloud) ─────────────────

def _try_sdk_read(method: str, args: dict) -> dict | None:
    """Try reading GenLayer contract state via SDK's read_contract.
    Uses the genlayer-py SDK's gen_call through the provider (not raw HTTP),
    which works from Fly.io."""
    try:
        from genlayer_py import create_client
        from eth_account import Account
        from eth_account.signers.local import LocalAccount

        pk = GENLAYER_PRIVATE_KEY.replace("0x", "")
        if not pk or len(pk) != 64:
            logger.debug("SDK read: no valid private key")
            return None

        from genlayer_py.chains import testnet_bradbury as bradbury_chain

        account: LocalAccount = Account.from_key(pk)
        client = create_client(
            chain=bradbury_chain,
            account=account,
        )

        bradbury_contract = "0xa420275FBC13949Fd42f879A31d7B9187BD06A08"
        stream_id = args.get("stream_id", "")
        logger.info(f"SDK read: {method}(stream_id={stream_id})")

        # Use SDK's read_contract with raw_return to get the hex result
        result = client.read_contract(
            address=bradbury_contract,
            function_name=method,
            args=[stream_id],
            account=account,
            raw_return=True,
        )

        if result and result != "0x":
            logger.info(f"SDK read success via read_contract: {result[:80]}...")
            # Parse the hex-encoded return
            try:
                import eth_utils
                from eth_abi import decode as abi_decode
                raw = eth_utils.hexadecimal.decode_hex(result)
                decoded = abi_decode(
                    ["string", "string", "bool", "string", "string", "string"],
                    raw,
                )
                return {
                    "result": {
                        "buyer": decoded[0],
                        "seller": decoded[1],
                        "active": decoded[2],
                        "description": decoded[3],
                        "expected_quality_criteria": decoded[4],
                        "deliverable_uri": decoded[5],
                    }
                }
            except Exception as de:
                logger.debug(f"SDK read decode error: {de}")
                return {"result": {"raw": result}}
        else:
            logger.info("SDK read: no data (job may not exist)")
            return {"result": {"active": False, "buyer": "", "seller": "", "stream_id": stream_id}}

    except ImportError as e:
        logger.debug(f"genlayer-py SDK not available for read: {e}")
        return None
    except Exception as e:
        # Check if it's a revert (job not found)
        err_str = str(e)
        if "reverted" in err_str.lower() or "not found" in err_str.lower():
            logger.info(f"SDK read: job not found: {stream_id}")
            return {"result": {"active": False, "buyer": "", "seller": "", "stream_id": stream_id}}
        logger.warning(f"SDK read failed: {err_str[:200]}")
        return None


# ─── Raw JSON-RPC call against GenLayer (for reads) ────────────────────

def _genlayer_rpc_call(rpc_url: str, params: list) -> dict:
    """Make a GenLayer JSON-RPC call with proper error handling and retries."""
    import time
    data = json.dumps({
        "jsonrpc": "2.0",
        "method": "gen_call",
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
    last_err = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
                return result
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else ""
            logger.debug(f"GenLayer HTTP {e.code} on {rpc_url}: {body[:200]}")
            return {"error": {"code": e.code, "message": f"HTTP {e.code}: {body[:200]}"}}
        except Exception as e:
            last_err = e
            time.sleep(1 + attempt)
            
    logger.debug(f"GenLayer RPC error on {rpc_url} after 3 attempts: {last_err}")
    return {"error": {"code": -1, "message": str(last_err)}}


def _get_hex_encoded_method(method: str) -> str:
    """GenLayer gen_call needs method name hex-encoded as the 'data' field."""
    return "0x" + method.encode("utf-8").hex()


def _genlayer_read(method: str, args: dict) -> dict:
    """
    Read GenLayer contract state.
    Tier 1: SDK read (works from cloud — same SDK that writes use)
    Tier 2: gen_call HTTP RPC (blocked from Fly.io but works locally)
    """
    # Tier 1: SDK read (avoid Cloudflare-blocked gen_call)
    sdk_result = _try_sdk_read(method, args)
    if sdk_result is not None:
        logger.info(f"GenLayer read via SDK: {method} = {str(sdk_result['result'])[:200]}")
        # Wrap SDK result in gen_call-like format so _decode_genlayer_job works
        result_data = sdk_result["result"]
        if isinstance(result_data, dict):
            return {"result": result_data}
        # If result is already a dict-like object, return as-is
        return {"result": result_data}

    logger.debug("SDK read unavailable, falling back to gen_call HTTP RPC")

    # Tier 2: gen_call RPC (tried in order)
    method_hex = _get_hex_encoded_method(method)
    params = [{
        "type": "read",
        "from": "0x0000000000000000000000000000000000000000",
        "to": GENLAYER_CONTRACT,
        "data": method_hex,
    }]

    rpcs_to_try = list(dict.fromkeys(
        [os.getenv("GENLAYER_RPC_URL", "")] + _GENLAYER_RPCS
    ))
    rpcs_to_try = [r for r in rpcs_to_try if r]

    for rpc_url in rpcs_to_try:
        try:
            result = _genlayer_rpc_call(rpc_url, params)
            if result.get("error"):
                err_msg = str(result["error"])
                logger.debug(f"GenLayer read {rpc_url}: {err_msg[:100]}")
                continue
            return result
        except Exception as e:
            logger.debug(f"GenLayer read {rpc_url} failed: {e}")
            continue

    return {"status": "error", "error": "All GenLayer RPC endpoints unreachable", "mock": True}


# ─── Node.js Bridge Helper (Fallback for writes) ───────────────────────

def _node_bridge_exec(contract: str, method: str, args: dict, timeout: int = 120) -> dict:
    """Call the GenLayer Node.js bridge (fallback)."""
    cmd = ["node", _BRIDGE_SCRIPT, "read", contract, method, json.dumps(args)]
    env = os.environ.copy()
    logger.info(f"Bridge: node bridge.js ... {method}({args.get('stream_id', '?')})")

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=timeout,
            env=env,
        )
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        if stdout:
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                pass
            return {"status": "success", "output": stdout[:500]}
        logger.warning(f"Bridge failed (exit {proc.returncode}): {stderr[:200]}")
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


# ─── Response Decoding ────────────────────────────────────────────────

def _decode_genlayer_job(raw: dict) -> dict:
    """Parse a raw GenLayer response into a usable job status dict."""
    result = raw.get("result", {})
    if isinstance(result, dict):
        return {
            "active": result.get("active"),
            "stream_id": result.get("stream_id"),
            "buyer_id": result.get("buyer", result.get("buyer_id")),
            "seller_id": result.get("seller", result.get("seller_id")),
            "description": result.get("description"),
            "status": "Active" if result.get("active") else "Inactive",
            "criteria": result.get("criteria", result.get("expected_quality_criteria")),
            "deliverable_uri": result.get("deliverable_uri"),
            "raw": result,
        }
    if isinstance(result, str) and result.startswith("0x"):
        return {"raw_hex": result[:100], "raw": result}
    return {"raw": result}


# ─── SLA Client ───────────────────────────────────────────────────────

class NotifyGenLayer:
    """GenLayer SLA client.

    Uses genlayer-py SDK for writes (proper eth_sendRawTransaction).
    Falls back to gen_call RPC for reads.
    Falls back to Node.js bridge, then mock for writes.
    """

    @staticmethod
    def write(method: str, args: dict, label: str = "") -> dict:
        """Generic write: SDK → Node.js bridge → mock."""
        logger.info(f"GenLayer write: {method}({label or args.get('stream_id', '?')})")

        # 1. SDK (genlayer-py installed on Fly.io)
        sdk_result = _try_sdk_write(method, args)
        if sdk_result:
            return {"status": "registered", "live": True, "method": "sdk", **sdk_result}

        # 2. Node.js bridge fallback
        logger.info(f"SDK write failed, trying Node.js bridge...")
        bridge_result = _node_bridge_exec(GENLAYER_CONTRACT, method, args)
        if bridge_result.get("status") == "success" or bridge_result.get("tx_hash"):
            return {"status": "registered", "live": True, "method": "node_bridge", **bridge_result}

        # 3. Final fallback — log and return mock success so the deal flow continues
        logger.warning(f"All GenLayer write methods failed for {method}. Using mock fallback.")
        return {"status": "registered", "live": False, "method": "mock", "note": "GenLayer write fell back to mock"}

    @staticmethod
    def register_job(
        stream_id: str,
        buyer_id: str,
        seller_id: str,
        description: str,
        quality_criteria: str = "Standard SLA terms",
        deliverable_uri: str = "",
    ) -> dict:
        """Register a job on GenLayer."""
        kwargs = {
            "stream_id": stream_id,
            "buyer_id": buyer_id,
            "seller_id": seller_id,
            "description": description,
            "quality_criteria": quality_criteria,
            "deliverable_uri": deliverable_uri,
        }
        return NotifyGenLayer.write("register_job", kwargs, label=stream_id)

    @staticmethod
    def monitor_stream(
        stream_id: str,
        deliverable_uri: str,
    ) -> dict:
        """Trigger AI quality evaluation on GenLayer."""
        kwargs = {"stream_id": stream_id, "deliverable_uri": deliverable_uri}
        return NotifyGenLayer.write("monitor_stream", kwargs, label=stream_id)

    @staticmethod
    def get_job_status(stream_id: str) -> dict:
        """Check job status on GenLayer via gen_call read RPC."""
        logger.debug(f"Checking GenLayer job status via RPC: {stream_id}")

        raw_result = _genlayer_read("get_job_status", {"stream_id": stream_id})

        if raw_result.get("mock"):
            logger.warning(f"GenLayer RPC read failed: {raw_result.get('error')}")
            return {"error": raw_result.get("error")}

        if raw_result.get("error"):
            logger.warning(f"GenLayer RPC read error: {raw_result.get('error')}")
            return {"error": str(raw_result.get("error"))}

        decoded = _decode_genlayer_job(raw_result)
        if decoded.get("active") is not None:
            logger.info(f"GenLayer job {stream_id}: active={decoded['active']}")
            return {"result": decoded, "source": "rpc"}

        if decoded.get("raw"):
            return {"result": decoded, "source": "rpc_raw"}

        return {"error": f"No data for stream {stream_id} on GenLayer"}
