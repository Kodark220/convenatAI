from __future__ import annotations
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional

from .agent import Agent, HAS_CIRCLE
if HAS_CIRCLE:
    from circle.web3 import developer_controlled_wallets
    from .agent import transactions_api

logger = logging.getLogger(__name__)

# Standard USDC token ID on Arc Testnet (example UUID format for Circle APIs)
# In production, fetch this from the Circle Tokens API for ARC-TESTNET.
USDC_TESTNET_TOKEN_ID = os.getenv("USDC_TOKEN_ID", "7b2e8a15-0610-4c7b-83c0-394e24eb5181")

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
        
        # Execute real on-chain transaction if Circle SDK is active
        if HAS_CIRCLE and self.payer.wallet.address and self.payee.wallet.address:
            logger.info(f"Executing Arc Testnet transfer: ${amount:.2f} USDC to {self.payee.wallet.address}")
            try:
                request = developer_controlled_wallets.CreateDeveloperTransactionTransferRequest.from_dict({
                    "idempotencyKey": os.urandom(16).hex(),
                    "walletId": self.payer.wallet.wallet_id,
                    "destinationAddress": self.payee.wallet.address,
                    "amounts": [str(amount)],
                    "feeLevel": "MEDIUM",
                    "tokenId": USDC_TESTNET_TOKEN_ID
                })
                response = transactions_api.create_developer_transaction_transfer(request)
                tx_id = response.data.id
                logger.info(f"Transfer initiated. Tx ID: {tx_id}")
            except Exception as e:
                logger.error(f"Arc transfer failed: {e}")
                raise RuntimeError(f"Onchain payment failed: {e}")
        else:
            # Fallback to local float math if running locally without keys
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

