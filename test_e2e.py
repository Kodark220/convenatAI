#!/usr/bin/env python3
"""
convenatAI — End-to-End GenLayer ConvenatContract Test

Tests the full read/write lifecycle:
1. Test read (get_job_status) on all configured RPC endpoints
2. Test write (register_job) using gen_call type=write format (the fix)
3. Test Node.js bridge
4. Verify response parsing

Usage:
  python3 test_e2e.py                         # Read-only tests
  python3 test_e2e.py --write                 # Also test writes (requires PK)
  python3 test_e2e.py --write --stream test-001  # Write a specific stream
  python3 test_e2e.py --network studionet     # Test specific network

Exit codes:
  0  = all tests pass
  1  = some tests failed
  2  = no live connectivity (all mocks/errors)
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

# Try to load .env — use manual parser (dotenv may not be installed)
_env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_file):
    try:
        with open(_env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except Exception:
        pass

# ─── Configuration ──────────────────────────────────────────────────────

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

PASS = "✅"
FAIL = "❌"
SKIP = "⏭️"
WARN = "⚠️"

passed = 0
failed = 0
skipped = 0


def test(name: str, condition: bool, detail: str = ""):
    global passed, failed
    icon = PASS if condition else FAIL
    if condition:
        passed += 1
    else:
        failed += 1
    print(f"  {icon} {name}{' — ' + detail if detail else ''}")


def skip(name: str, reason: str = ""):
    global skipped
    skipped += 1
    print(f"  {SKIP} {name}{' — ' + reason if reason else ''}")


def rpc_call(rpc_url: str, params: list) -> dict:
    """Make a gen_call RPC."""
    body = json.dumps({
        "jsonrpc": "2.0",
        "method": "gen_call",
        "params": params,
        "id": 1,
    }).encode()
    req = urllib.request.Request(
        rpc_url, data=body,
        headers={"Content-Type": "application/json", "User-Agent": "convenatAI-test/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main():
    global passed, failed, skipped

    # Parse args
    do_write = "--write" in sys.argv
    stream_id = "test-001"
    for i, arg in enumerate(sys.argv):
        if arg == "--stream" and i + 1 < len(sys.argv):
            stream_id = sys.argv[i + 1]
    target_network = None
    for i, arg in enumerate(sys.argv):
        if arg == "--network" and i + 1 < len(sys.argv):
            target_network = sys.argv[i + 1]

    networks_to_test = {target_network: NETWORKS[target_network]} if target_network else NETWORKS

    pk = os.getenv("GENLAYER_PRIVATE_KEY", "")
    bridge_script = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "scripts", "genlayer_bridge.js"
    )

    # Global summary header
    print()
    print("=" * 65)
    print("  convenatAI — GenLayer ConvenatContract End-to-End Test")
    print("=" * 65)
    print(f"  Write tests:  {'ENABLED' if do_write else 'DISABLED (pass --write)'}")
    print(f"  Private key:  {'SET' if pk else 'NOT SET'}")
    print(f"  Stream ID:    {stream_id}")
    print(f"  Bridge:       {'FOUND' if os.path.exists(bridge_script) else 'MISSING'}")
    print()

    # ════════════════════════════════════════════════════════════════════
    # TEST 1: RPC Read on all endpoints
    # ════════════════════════════════════════════════════════════════════
    print("─" * 65)
    print("  TEST 1: gen_call type='read' with method/args format")
    print("─" * 65)

    alive_endpoints = 0

    for net_name, net_config in networks_to_test.items():
        print(f"\n  [{net_name}] {net_config['rpc']}")
        try:
            result = rpc_call(net_config["rpc"], [{
                "type": "read",
                "to": net_config["contract"],
                "method": "get_job_status",
                "args": {"stream_id": stream_id},
            }])

            if result.get("result") is not None:
                raw = result["result"]
                if isinstance(raw, dict):
                    test(f"Read '{stream_id}' returns dict", True,
                         f"keys={list(raw.keys())} active={raw.get('active')}")
                else:
                    test(f"Read '{stream_id}' returns {type(raw).__name__}", True,
                         f"value={str(raw)[:80]}")
                alive_endpoints += 1
            elif result.get("error"):
                err = result["error"]
                msg = err.get("message", str(err))
                # "not found" errors are acceptable — means no job registered yet
                if "not found" in msg.lower() or "key not found" in msg.lower():
                    test(f"Read '{stream_id}' (not found — expected)", True, msg[:80])
                    alive_endpoints += 1
                else:
                    test(f"Read '{stream_id}'", False, msg[:120])
            else:
                test(f"Read '{stream_id}'", False,
                     f"unexpected response: {json.dumps(result)[:100]}")
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:100] if e.fp else ""
            test(f"HTTP {e.code}", False, body)
        except Exception as e:
            test(f"Connection failed", False, str(e)[:80])

    print(f"\n  Live endpoints: {alive_endpoints}/{len(networks_to_test)}")
    if alive_endpoints == 0:
        print(f"  {WARN} No endpoints reachable — subsequent tests may use mocks")
    print()

    # ════════════════════════════════════════════════════════════════════
    # TEST 2: RPC Write (optional)
    # ════════════════════════════════════════════════════════════════════
    if do_write:
        print("─" * 65)
        print("  TEST 2: gen_call type='write' with method/args format")
        print("─" * 65)

        if not pk:
            skip("Write tests", "No GENLAYER_PRIVATE_KEY set")
        elif alive_endpoints == 0:
            skip("Write tests", "No live RPC endpoints")
        else:
            # Use first alive network
            write_net_name, write_net = list(networks_to_test.items())[0]
            from_addr = "0x" + pk.replace("0x", "")[-40:].lower()
            write_stream = f"{stream_id}-e2e-{int(time.time())}"

            print(f"\n  Network: {write_net_name}")
            print(f"  Contract: {write_net['contract']}")
            print(f"  From:     {from_addr}")
            print(f"  Stream:   {write_stream}")
            print()

            # 2a. Direct Python gen_call type=write
            print(f"  [2a] Direct Python RPC (gen_call type=write):")
            try:
                result = rpc_call(write_net["rpc"], [{
                    "type": "write",
                    "from": from_addr,
                    "to": write_net["contract"],
                    "method": "register_job",
                    "args": {
                        "stream_id": write_stream,
                        "buyer_id": "0xBuyerTest1234567890123456789012345678901",
                        "seller_id": "0xSellerTest1234567890123456789012345678",
                        "description": "E2E test of fixed GenLayer RPC write",
                        "quality_criteria": "Must pass automated verification",
                        "deliverable_uri": f"https://test.convenatai.ai/{write_stream}",
                    },
                }])

                if result.get("result") is not None:
                    test(f"register_job('{write_stream}')", True,
                         f"result={json.dumps(result['result'])[:80]}")
                elif result.get("error"):
                    err = result["error"]
                    msg = err.get("message", str(err))
                    test(f"register_job('{write_stream}')", False, msg[:120])
                else:
                    test(f"register_job('{write_stream}')", False,
                         f"unexpected: {json.dumps(result)[:100]}")
            except Exception as e:
                test(f"register_job('{write_stream}')", False, str(e)[:80])

            # 2b. Verify by reading back
            print(f"  [2b] Verify — read back the job status:")
            try:
                result = rpc_call(write_net["rpc"], [{
                    "type": "read",
                    "to": write_net["contract"],
                    "method": "get_job_status",
                    "args": {"stream_id": write_stream},
                }])

                if result.get("result") is not None:
                    raw = result["result"]
                    if isinstance(raw, dict):
                        test(f"Read back '{write_stream}'", True,
                             f"active={raw.get('active')} buyer={str(raw.get('buyer', ''))[:20]}")
                    else:
                        test(f"Read back '{write_stream}'", True,
                             f"type={type(raw).__name__} val={str(raw)[:60]}")
                else:
                    msg = str(result.get("error", {}).get("message", "unknown"))
                    test(f"Read back '{write_stream}'", False, msg)
            except Exception as e:
                test(f"Read back '{write_stream}'", False, str(e)[:80])

        print()

    # ════════════════════════════════════════════════════════════════════
    # TEST 3: Node.js Bridge (if available)
    # ════════════════════════════════════════════════════════════════════
    print("─" * 65)
    print("  TEST 3: Node.js Bridge (genlayer_bridge.js)")
    print("─" * 65)

    if not os.path.exists(bridge_script):
        skip("Bridge tests", "genlayer_bridge.js not found")
    else:
        for net_name, net_config in networks_to_test.items():
            print(f"\n  [{net_name}]")
            try:
                env = os.environ.copy()
                env["GENLAYER_NETWORK"] = net_name
                if pk:
                    env["GENLAYER_PRIVATE_KEY"] = pk

                proc = subprocess.run(
                    ["node", bridge_script, "read", net_config["contract"],
                     "get_job_status", json.dumps({"stream_id": stream_id})],
                    capture_output=True, text=True, timeout=30, env=env,
                )

                if proc.returncode == 0 and proc.stdout.strip():
                    try:
                        result = json.loads(proc.stdout.strip())
                        if result.get("result") is not None:
                            test(f"Bridge read '{stream_id}'", True,
                                 f"result={str(result['result'])[:60]}")
                        elif result.get("error"):
                            err_msg = str(result["error"]).lower()
                            if "not found" in err_msg:
                                test(f"Bridge read '{stream_id}' (not found)", True)
                            else:
                                test(f"Bridge read '{stream_id}'", False,
                                     str(result["error"])[:80])
                        else:
                            test(f"Bridge read '{stream_id}'", False,
                                 f"unexpected: {proc.stdout[:100]}")
                    except json.JSONDecodeError:
                        test(f"Bridge read '{stream_id}'", False,
                             f"invalid JSON: {proc.stdout[:100]}")
                else:
                    test(f"Bridge read '{stream_id}'", False,
                         f"exit={proc.returncode} stderr={proc.stderr[:100]}")
            except subprocess.TimeoutExpired:
                test(f"Bridge read '{stream_id}'", False, "timed out (30s)")
            except Exception as e:
                test(f"Bridge read '{stream_id}'", False, str(e)[:60])

        # Test bridge write (if requested)
        if do_write and pk:
            write_net_name, write_net = list(networks_to_test.items())[0]
            write_stream = f"{stream_id}-bridge-{int(time.time())}"
            print(f"\n  [Bridge Write] {write_net_name} stream={write_stream}")
            try:
                env = os.environ.copy()
                env["GENLAYER_NETWORK"] = write_net_name
                env["GENLAYER_PRIVATE_KEY"] = pk

                proc = subprocess.run(
                    ["node", bridge_script, "write", write_net["contract"],
                     "register_job", json.dumps({
                         "stream_id": write_stream,
                         "buyer_id": "0xBridgeBuyerTest1234567890123456789012345",
                         "seller_id": "0xBridgeSellerTest1234567890123456789012",
                         "description": "Bridge E2E test",
                         "quality_criteria": "Pass bridge test",
                         "deliverable_uri": f"https://bridge.convenatai.ai/{write_stream}",
                     })],
                    capture_output=True, text=True, timeout=60, env=env,
                )

                if proc.returncode == 0 and proc.stdout.strip():
                    try:
                        result = json.loads(proc.stdout.strip())
                        if result.get("result") is not None or not result.get("error"):
                            test(f"Bridge write '{write_stream}'", True,
                                 f"result={str(result.get('result', ''))[:60]}")
                        else:
                            test(f"Bridge write '{write_stream}'", False,
                                 str(result.get("error", ""))[:80])
                    except json.JSONDecodeError:
                        test(f"Bridge write '{write_stream}'", False,
                             f"JSON error: {proc.stdout[:100]}")
                else:
                    test(f"Bridge write '{write_stream}'", False,
                         f"exit={proc.returncode} err={proc.stderr[:100]}")
            except Exception as e:
                test(f"Bridge write '{write_stream}'", False, str(e)[:60])
        elif do_write and not pk:
            skip("Bridge write test", "No private key")
        else:
            skip("Bridge write test", "Pass --write to enable")

    print()

    # ════════════════════════════════════════════════════════════════════
    # SUMMARY
    # ════════════════════════════════════════════════════════════════════
    print("=" * 65)
    print(f"  RESULTS:  {PASS} {passed} passed  {FAIL} {failed} failed  {SKIP} {skipped} skipped")
    print("=" * 65)

    if alive_endpoints == 0:
        print(f"\n  {WARN} No live GenLayer RPC endpoints were reachable.")
        print(f"  {WARN} Check your network connectivity and firewall settings.")
        print(f"  {WARN} The RPC endpoints are:")
        for n, c in NETWORKS.items():
            print(f"    {n}: {c['rpc']}")
        print(f"\n  {WARN} If you're behind a corporate firewall or VPN, try:")
        print(f"    1. Connect to a different network")
        print(f"    2. Run the local relay: python3 genlayer_relay.py")
        print(f"    3. Set GENLAYER_RELAY_URL=http://YOUR_IP:9090 in .env")
        print()

    sys.exit(1 if failed > 0 else (2 if alive_endpoints == 0 else 0))


if __name__ == "__main__":
    main()
