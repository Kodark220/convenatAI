#!/usr/bin/env python3
"""
convenatAI — GenLayer Python Wrapper (wrapper around genlayer_client)

This module delegates to genlayer_client's NotifyGenLayer.
Kept for backward compatibility with code that imports ConvenatContract directly.

GenLayer RPC format for reads:
  gen_call(params=[{"type": "read", "from": addr, "to": addr, "data": hex_encoded_method}])

Writes go through genlayer-py SDK (eth_sendRawTransaction → consensus contract).
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import urllib.error
import urllib.request

from dotenv import load_dotenv

from convenatai.genlayer_client import NotifyGenLayer

load_dotenv()
logger = logging.getLogger("genlayer-wrapper")


# ─── Configuration ───────────────────────────────────────────────────────

NETWORKS = {
    "testnet-bradbury": {
        "rpc": "https://rpc-bradbury.genlayer.com",
        "contract": "0xa420275FBC13949Fd42f879A31d7B9187BD06A08",
        "chain_id": 10701,
    },
    "studionet": {
        "rpc": "https://studio.genlayer.com/api",
        "contract": "0xc821A31Bfe1299131D4D07E78a0c7D388B1E9642",
        "chain_id": 10700,
    },
}


# ─── ConvenatContract API (delegates to NotifyGenLayer) ─────────────────

class ConvenatContract:
    """Python wrapper for the GenLayer ConvenatContract.

    Delegates all calls to NotifyGenLayer from genlayer_client.
    Kept for backward compatibility.
    """

    def __init__(self, network: str = None, contract: str = None, private_key: str = None):
        net_name = network or os.getenv("GENLAYER_NETWORK", "studionet").lower()
        net = NETWORKS.get(net_name)

        self.rpc_url = os.getenv("GENLAYER_RPC_URL") or (net["rpc"] if net else NETWORKS["studionet"]["rpc"])
        self.contract = contract or os.getenv("CONVENAT_CONTRACT_ADDRESS") or (
            net["contract"] if net else NETWORKS["studionet"]["contract"]
        )
        self.private_key = private_key or os.getenv("GENLAYER_PRIVATE_KEY", "")
        self.network = net_name

    def register_job(self, stream_id, buyer_id, seller_id, description, quality_criteria="Standard SLA terms", deliverable_uri=""):
        return NotifyGenLayer.register_job(
            stream_id=stream_id,
            buyer_id=buyer_id,
            seller_id=seller_id,
            description=description,
            quality_criteria=quality_criteria,
            deliverable_uri=deliverable_uri,
        )

    def monitor_stream(self, stream_id, deliverable_uri):
        return NotifyGenLayer.monitor_stream(
            stream_id=stream_id,
            deliverable_uri=deliverable_uri,
        )

    def get_job_status(self, stream_id):
        return NotifyGenLayer.get_job_status(stream_id=stream_id)
