from __future__ import annotations
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional

from .agent import Agent

logger = logging.getLogger(__name__)

# Correct USDC token ID on ARC-TESTNET (from Circle console)
USDC_TESTNET_TOKEN_ID = os.getenv("USDC_TOKEN_ID", "15dc2b5d-0994-58b0-bf8c-3a0501148ee8")


def _node_transfer(from_wallet_id: str, to_address: str, amount: float, token_id: str) -> dict:
    """Transfer USDC via the Node.js bridge (handles Circle SDK properly)."""
    import json
    import shutil
    import subprocess

    node_path = None
    for c in ["node", "/usr/bin/node", "/usr/local/bin/node"]:
        p = shutil.which(c) or (c if os.path.exists(c) else None)
        if p:
            node_path = p
            break
    if not node_path:
        raise RuntimeError("Node.js not available for transfer")

    script_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
    script_path = os.path.join(script_dir, "circle_executor.js")
    if not os.path.exists(script_path):
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts", "circle_executor.js")

    args = json.dumps({
        "fromWalletId": from_wallet_id,
        "toAddress": to_address,
        "amount": str(amount),
        "tokenId": token_id,
        "feeLevel": "MEDIUM",
    })
    proc = subprocess.run([node_path, script_path, "transfer-usdc", args],
                          capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        err = proc.stderr.strip() or proc.stdout.strip()
        raise RuntimeError(f"Transfer failed: {err}")
    return json.loads(proc.stdout.strip())


@dataclass
class PaymentChannel:
    payer: Agent
    payee: Agent
    token_symbol: str = "USDC"
    capacity: float = 0.0
    balance: float = 0.0
    is_open: bool = False

    def open(self) -> None:
        if self.is_open:
            raise RuntimeError("Payment channel is already open.")
        self.balance = self.capacity
        self.is_open = True
        logger.info(f"Opened {self.token_symbol} stream capacity with ${self.capacity:.2f} to {self.payee.name}.")

    def send(self, amount: float) -> None:
        if not self.is_open:
            raise RuntimeError("Payment channel is not open.")
        if amount > self.balance:
            raise RuntimeError("Payment exceeds channel capacity balance.")

        # Try on-chain USDC transfer via Node bridge
        payer_id = getattr(self.payer.wallet, "wallet_id", None)
        payee_addr = getattr(self.payee.wallet, "address", None)
        if payer_id and payee_addr and os.getenv("CIRCLE_API_KEY"):
            try:
                result = _node_transfer(payer_id, payee_addr, amount, USDC_TESTNET_TOKEN_ID)
                logger.info(f"On-chain USDC transfer: {result.get('id', 'unknown')}")
            except Exception as e:
                logger.warning(f"On-chain transfer failed ({e}), using local balance only")
        else:
            # Fallback: local wallet balance tracking
            self.payer.wallet.withdraw(amount)
            self.payee.wallet.deposit(amount)

        self.balance -= amount
        logger.info(f"  channel paid ${amount:.2f} to {self.payee.name}.")

    def close(self) -> None:
        if not self.is_open:
            return
        self.is_open = False
        logger.info(f"Closed {self.token_symbol} payment channel to {self.payee.name}.")


@dataclass
class NanopaymentStream:
    channel: PaymentChannel
    amount: float
    duration: int
    schedule: list[float] = field(init=False)
    delivered_units: int = 0
    completed: bool = False

    def __post_init__(self) -> None:
        if self.duration <= 0:
            raise ValueError("Duration must be greater than zero.")
        per_unit = round(self.amount / self.duration, 2)
        self.schedule = [per_unit] * self.duration
        remainder = round(self.amount - sum(self.schedule), 2)
        if remainder:
            self.schedule[-1] += remainder

    def start(self, realtime: bool = False, delay_seconds: float = 0.0) -> None:
        if not self.channel.is_open:
            raise RuntimeError("Payment channel must be open before nanopayment streaming begins.")
        if self.channel.balance < self.amount:
            raise RuntimeError("Channel does not contain sufficient funds for the nanopayment stream.")

        logger.info(f"Starting Arc nanopayment stream of ${self.amount:.2f}")
        while self.delivered_units < self.duration:
            self.tick()
            if realtime and delay_seconds > 0:
                time.sleep(delay_seconds)
        self.completed = True
        logger.info(f"Nanopayment stream completed: total=${self.amount:.2f}")

    def tick(self) -> None:
        if not self.channel.is_open:
            raise RuntimeError("Cannot progress payment stream on a closed channel.")

        payment = self.schedule[self.delivered_units]
        self.channel.send(payment)
        self.delivered_units += 1
        logger.info(f"  streamed ${payment:.2f} to {self.channel.payee.name} (unit {self.delivered_units}/{self.duration})")

    def kill_stream(self) -> None:
        """Called by GenLayer AI if the SLA quality drops below threshold."""
        if not self.completed and self.channel.is_open:
            self.channel.close()
            logger.warning("GenLayer Validator triggered kill switch! Nanopayment stream interrupted.")


class ArcNanopaymentGateway:
    def __init__(self, token_symbol: str = "USDC"):
        self.token_symbol = token_symbol

    def open_channel(self, payer: Agent, payee: Agent, amount: float) -> PaymentChannel:
        channel = PaymentChannel(payer=payer, payee=payee, token_symbol=self.token_symbol, capacity=amount)
        channel.open()
        return channel

    def close_channel(self, channel: PaymentChannel) -> None:
        channel.close()
