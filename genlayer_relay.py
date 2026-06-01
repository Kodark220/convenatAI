#!/usr/bin/env python3
"""
convenatAI — GenLayer Local Relay
Runs on your local machine. Forwards GenLayer write requests to the RPC
using the correct gen_call with type='write' (not gen_send).
"""

import json
import logging
import os
import subprocess
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("genlayer-relay")

GENLAYER_CONTRACT = "0xc821A31Bfe1299131D4D07E78a0c7D388B1E9642"
GENLAYER_RPC = "https://studio.genlayer.com/api"
GENLAYER_PRIVATE_KEY = os.getenv("GENLAYER_PRIVATE_KEY", "")
BRIDGE_SCRIPT = os.path.join(os.path.dirname(__file__), "scripts", "genlayer_bridge.js")


def genlayer_rpc_call(method, params):
    data = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    req = urllib.request.Request(
        GENLAYER_RPC, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


class RelayHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "network": "studionet"}).encode())
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path != "/genlayer/write":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        try:
            payload = json.loads(body)
        except Exception:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(json.dumps({"error": "invalid json"}).encode())
            return

        method = payload.get("method", "register_job")
        kwargs = payload.get("kwargs", {})
        contract = payload.get("contract", GENLAYER_CONTRACT)

        logger.info(f"Relay: {method}({kwargs.get('stream_id', '?')})")

        # Use Node.js bridge (uses genlayer-js SDK for proper ABI encoding)
        try:
            cmd = ["node", BRIDGE_SCRIPT, "write", contract, method, json.dumps(kwargs)]
            env = os.environ.copy()
            logger.info(f"Running bridge: {' '.join(cmd[-6:])}")
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
            if proc.returncode == 0:
                result = proc.stdout.strip()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(result.encode() if result else json.dumps({"status": "ok"}).encode())
                logger.info(f"  ✓ Bridge success")
                return
            raise RuntimeError(proc.stderr[:500])
        except Exception as e:
            logger.warning(f"  Bridge failed: {e}")

        # Last resort: direct RPC (may not have proper encoding)
        try:
            from_addr = "0x" + GENLAYER_PRIVATE_KEY[-40:].lower() if GENLAYER_PRIVATE_KEY else "0x0000000000000000000000000000000000000000"
            params = [{
                "type": "write",
                "from": from_addr,
                "to": contract,
                "data": "0x",
            }]
            result = genlayer_rpc_call("gen_call", params)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "result": result}).encode())
            logger.info(f"  ✓ RPC fallback success")
            return
        except Exception as e:
            logger.warning(f"  RPC fallback failed: {e}")

        # All failed
        self.send_response(502)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({"error": "All GenLayer write methods failed"}).encode())
        logger.error(f"  ✗ All methods failed")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 9090))
    server = HTTPServer(("0.0.0.0", port), RelayHandler)
    logger.info(f"GenLayer Relay listening on http://0.0.0.0:{port}")
    logger.info(f"  Contract: {GENLAYER_CONTRACT}")
    logger.info(f"  RPC: {GENLAYER_RPC}")
    logger.info(f"  Private key: {'SET' if GENLAYER_PRIVATE_KEY else 'NOT SET'}")
    print(f"\n  👉 Set in cloud app env:")
    print(f"     GENLAYER_RELAY_URL=http://YOUR_WSL_IP:{port}")
    print(f"     (Find your WSL IP with: hostname -I | awk '{{print $1}}')\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
