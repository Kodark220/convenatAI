#!/usr/bin/env python3
"""
convenatAI — GenLayer RPC Test Script
Tests read and write operations against GenLayer contracts.

Usage:
  python3 test_genlayer.py                          # Test Bradbury default
  python3 test_genlayer.py --network testnet-bradbury
  python3 test_genlayer.py --network studionet
  python3 test_genlayer.py --register               # Actually register a test job
"""

import json
import logging
import os
import sys
import urllib.request
import urllib.error

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test-genlayer")

# Load .env
from dotenv import load_dotenv
load_dotenv()

NETWORKS = {
    "testnet-bradbury": {
        "rpc": "https://rpc-bradbury.genlayer.com",
        "contract": "0xa420275FBC13949Fd42f879A31d7B9187BD06A08",
    },
    "studionet": {
        "rpc": "https://studio.genlayer.com/api",
        "contract": "0xc821A31Bfe1299131D4D07E78a0c7D388B1E9642",
    },
    "studionet-8443": {
        "rpc": "https://studio.genlayer.com:8443/api",
        "contract": "0xc821A31Bfe1299131D4D07E78a0c7D388B1E9642",
    },
}

PRIVATE_KEY = os.getenv("GENLAYER_PRIVATE_KEY", "")


def get_from_address(pk: str) -> str:
    pk = pk.replace("0x", "")
    if pk:
        return "0x" + pk[-40:].lower()
    return "0x0000000000000000000000000000000000000000"


def genlayer_rpc_call(rpc_url: str, params: list) -> dict:
    """Make a GenLayer JSON-RPC gen_call."""
    data = json.dumps({
        "jsonrpc": "2.0",
        "method": "gen_call",
        "params": params,
        "id": 1,
    }).encode()
    req = urllib.request.Request(
        rpc_url, data=data,
        headers={"Content-Type": "application/json", "User-Agent": "convenatAI-test/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": {"code": e.code, "message": e.read().decode()[:300]}}
    except Exception as e:
        return {"error": {"code": -1, "message": str(e)}}


def test_read(network_name: str, config: dict):
    """Test gen_call with type='read' and method/args format."""
    print(f"\n{'='*60}")
    print(f"TEST: Read (type='read') — {network_name}")
    print(f"RPC:  {config['rpc']}")
    print(f"Contract: {config['contract']}")
    print(f"{'='*60}")

    # Test with method/args format (CORRECT for GenLayer)
    print(f"\n[1] gen_call type='read' with method/args:")
    result = genlayer_rpc_call(config["rpc"], [{
        "type": "read",
        "to": config["contract"],
        "method": "get_job_status",
        "args": {"stream_id": "test-001"},
    }])
    print(f"    Result: {json.dumps(result, indent=2)[:500]}")

    if result.get("error"):
        print(f"    ❌ FAILED: {result['error']}")
    elif result.get("result") is not None:
        print(f"    ✅ SUCCESS: result={result['result']}")
    else:
        print(f"    ⚠️ Unexpected response")


def test_write(network_name: str, config: dict):
    """Test gen_call with type='write' and method/args format."""
    print(f"\n{'='*60}")
    print(f"TEST: Write (type='write') — {network_name}")
    print(f"RPC:  {config['rpc']}")
    print(f"Contract: {config['contract']}")
    print(f"{'='*60}")

    from_addr = get_from_address(PRIVATE_KEY)
    print(f"From: {from_addr}")
    print(f"PK set: {'YES' if PRIVATE_KEY else 'NO'}")

    args = {
        "stream_id": "test-001",
        "buyer_id": "0xBuyer12345678901234567890123456789012345",
        "seller_id": "0xSeller1234567890123456789012345678901234",
        "description": "Test job for GenLayer RPC fix verification",
        "quality_criteria": "Must pass automated verification test",
        "deliverable_uri": "https://example.com/test-deliverable",
    }

    print(f"\n[1] gen_call type='write' with method/args:")
    result = genlayer_rpc_call(config["rpc"], [{
        "type": "write",
        "from": from_addr,
        "to": config["contract"],
        "method": "register_job",
        "args": args,
    }])
    print(f"    Result: {json.dumps(result, indent=2)[:600]}")

    if result.get("error"):
        print(f"    ❌ FAILED: {result['error']}")
    elif result.get("result") is not None:
        print(f"    ✅ SUCCESS: result={result['result']}")
    else:
        print(f"    ⚠️ Check result above")

    # Now verify the job was registered by reading it back
    print(f"\n[2] Verify — read back the job status:")
    verify = genlayer_rpc_call(config["rpc"], [{
        "type": "read",
        "to": config["contract"],
        "method": "get_job_status",
        "args": {"stream_id": "test-001"},
    }])
    print(f"    Result: {json.dumps(verify, indent=2)[:500]}")
    if verify.get("result") and isinstance(verify["result"], dict):
        print(f"    ✅ Job found: active={verify['result'].get('active')}")
    else:
        print(f"    ⚠️ Job not found or unexpected format")


def test_bridge(network_name: str, config: dict):
    """Test the Node.js bridge script (for comparison)."""
    print(f"\n{'='*60}")
    print(f"TEST: Node.js Bridge — {network_name}")
    print(f"{'='*60}")

    import subprocess
    import os

    bridge = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "scripts", "genlayer_bridge.js"
    )

    if not os.path.exists(bridge):
        print(f"Bridge script not found: {bridge}")
        return

    print(f"\n[1] Bridge — read get_job_status:")
    try:
        env = os.environ.copy()
        env["GENLAYER_NETWORK"] = network_name
        proc = subprocess.run(
            ["node", bridge, "read", config["contract"], "get_job_status", json.dumps({"stream_id": "test-001"})],
            capture_output=True, text=True, timeout=30, env=env,
        )
        if proc.returncode == 0:
            print(f"    stdout: {proc.stdout[:500]}")
        if proc.stderr:
            print(f"    stderr: {proc.stderr[:200]}")
        if proc.returncode == 0:
            print(f"    ✅ Bridge read succeeded")
        else:
            print(f"    ❌ Bridge read failed (exit {proc.returncode})")
    except Exception as e:
        print(f"    ❌ Bridge error: {e}")


def main():
    # Parse --network argument
    network_name = "testnet-bradbury"
    do_register = False
    for arg in sys.argv[1:]:
        if arg.startswith("--network="):
            network_name = arg.split("=", 1)[1]
        elif arg == "--network" and sys.argv.index(arg) + 1 < len(sys.argv):
            network_name = sys.argv[sys.argv.index(arg) + 1]
        elif arg == "--register":
            do_register = True

    config = NETWORKS.get(network_name)
    if not config:
        print(f"Unknown network: {network_name}")
        print(f"Available: {list(NETWORKS.keys())}")
        sys.exit(1)

    print(f"\n🔬 GenLayer RPC Test Suite")
    print(f"   Network: {network_name}")
    print(f"   RPC:     {config['rpc']}")
    print(f"   Contract: {config['contract']}")
    print(f"   PK set:  {'YES' if PRIVATE_KEY else 'NO'}")

    # Always test reads
    test_read(network_name, config)

    # Test writes if --register or if PK is available
    if do_register and PRIVATE_KEY:
        test_write(network_name, config)
    elif PRIVATE_KEY:
        print(f"\n(PK available — use --register to test writes)")
    else:
        print(f"\n(No PK — skipping write tests)")

    # Test bridge
    test_bridge(network_name, config)

    # Test all RPC endpoints
    print(f"\n{'='*60}")
    print(f"TEST: All RPC Endpoints — Read get_job_status('test-001')")
    print(f"{'='*60}")
    for name, cfg in NETWORKS.items():
        result = genlayer_rpc_call(cfg["rpc"], [{
            "type": "read",
            "to": cfg["contract"],
            "method": "get_job_status",
            "args": {"stream_id": "test-001"},
        }])
        status = "✅" if result.get("result") is not None else ("❌" if result.get("error") else "⚠️")
        err = result.get("error", {}).get("message", "")
        print(f"  {status} {name:20s} | result={str(result.get('result', ''))[:60]} | err={err[:60]}")


if __name__ == "__main__":
    main()
