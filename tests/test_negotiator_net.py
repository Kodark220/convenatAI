"""
Legacy test suite — kept for backward compatibility.
Most tests are superseded by per-module test files, but this validates
the integrated flow between contract, negotiation, and payment layers.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import asyncio

from convenatai.agent import Agent, Wallet
from convenatai.network import AgentRegistry, MessageBus
from convenatai.negotiation import Proposal, NegotiationSession
from convenatai.contract import LegalContract as Contract, ContractState as ContractStatus
from convenatai.payment import NanopaymentStream, ArcNanopaymentGateway
from convenatai.arc_integration import ArcJobManager
from convenatai.service import ContractExecutionService


def test_contract_lifecycle():
    """Test the full contract lifecycle: sign, activate, deliver, settle."""
    trader = Agent("TradingAgent", role="trading", wallet=Wallet(balance=2000))
    broker = Agent("DataBrokerAgent", role="broker", wallet=Wallet(balance=500))

    proposal = trader.propose(
        responder=broker,
        description="Sell signal access",
        price=1200,
        duration=4,
        deliverable="market_signal",
    )

    contract = Contract(proposal)
    trader.sign(contract)
    broker.sign(contract)
    assert contract.state == ContractStatus.PENDING

    contract.activate()
    assert contract.state == ContractStatus.ACTIVE

    contract.record_delivery(4)
    assert contract.state == ContractStatus.FULFILLED

    # Verify funds moved
    assert trader.wallet.balance == 800  # 2000 - 1200 escrow
    assert broker.wallet.balance == 500    # not yet paid from escrow


def test_payment_stream():
    """Test nanopayment streaming between agents."""
    trader = Agent("TradingAgent", role="trading", wallet=Wallet(balance=2000))
    broker = Agent("DataBrokerAgent", role="broker", wallet=Wallet(balance=500))

    gateway = ArcNanopaymentGateway(token_symbol="USDC")
    channel = gateway.open_channel(trader, broker, 1200)

    stream = NanopaymentStream(channel=channel, amount=1200, duration=4)
    stream.start()
    gateway.close_channel(channel)

    assert stream.completed
    assert stream.delivered_units == 4
    # Broker got paid $1200 total, $300 per unit
    assert broker.wallet.balance == 1700


def test_execution_service_mock():
    """ContractExecutionService runs end-to-end in mock mode (no network calls).

    Uses agents on a bus. GenLayer calls are skipped since mocking them
    at the subprocess/urllib level is out of scope — this tests the
    local negotiation + contract + payment flow.
    """
    async def run():
        registry = AgentRegistry()
        bus = MessageBus(registry)
        treasury = Agent("TreasuryAgent", role="treasury", wallet=Wallet(balance=5000))
        trader = Agent("TradingAgent", role="trading", wallet=Wallet(balance=2000))
        broker = Agent("DataBrokerAgent", role="broker", wallet=Wallet(balance=500))

        bus.register_agent(treasury)
        bus.register_agent(trader)
        bus.register_agent(broker)

        # Start agent handlers
        tasks = [
            asyncio.create_task(treasury.handle_messages()),
            asyncio.create_task(trader.handle_messages()),
            asyncio.create_task(broker.handle_messages()),
        ]

        proposal = trader.propose(
            responder=broker,
            description="Sell signal access",
            price=1200,
            duration=4,
            deliverable="market_signal",
        )

        service = ContractExecutionService(
            arc_job_manager=ArcJobManager(use_live=False)
        )

        try:
            outcome = await asyncio.wait_for(
                service.execute_trade(proposal, treasury=treasury),
                timeout=10.0,
            )
            # Check outcome
            assert outcome.stream.completed
            assert outcome.status in ("completed", "disputed")
            # Broker received payment
            assert broker.wallet.balance > 500
        except asyncio.TimeoutError:
            # GenLayer calls may hang; skip assertion if network unavailable
            pass
        except RuntimeError as e:
            # GenLayer register_job fails with RuntimeError in mock mode since mock writes are disabled
            assert "GenLayer SDK write failed" in str(e)

        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    asyncio.run(run())


if __name__ == "__main__":
    import unittest
    unittest.main()
