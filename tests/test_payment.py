"""Tests for Payment layer (PaymentChannel, NanopaymentStream, ArcNanopaymentGateway)."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from convenatai.agent import Agent, Wallet
from convenatai.payment import PaymentChannel, NanopaymentStream, ArcNanopaymentGateway


def test_payment_channel_open():
    """PaymentChannel.open sets balance and marks open."""
    payer = Agent("Payer", "trader", wallet=Wallet(balance=1000))
    payee = Agent("Payee", "broker", wallet=Wallet(balance=500))
    ch = PaymentChannel(payer=payer, payee=payee, token_symbol="USDC", capacity=200)
    ch.open()
    assert ch.is_open is True
    assert ch.balance == 200.0


def test_payment_channel_double_open_raises():
    """Opening an already-open channel raises RuntimeError."""
    payer = Agent("Payer", "trader", wallet=Wallet(balance=1000))
    payee = Agent("Payee", "broker", wallet=Wallet(balance=500))
    ch = PaymentChannel(payer=payer, payee=payee, capacity=200)
    ch.open()
    try:
        ch.open()
        assert False, "Should have raised"
    except RuntimeError as e:
        assert "already open" in str(e)


def test_payment_channel_send_local():
    """PaymentChannel.send transfers funds locally in mock mode."""
    payer = Agent("Payer", "trader", wallet=Wallet(balance=1000))
    payee = Agent("Payee", "broker", wallet=Wallet(balance=500))
    ch = PaymentChannel(payer=payer, payee=payee, capacity=300)
    ch.open()

    ch.send(100)
    assert ch.balance == 200  # capacity - sent
    assert payer.wallet.balance == 900  # 1000 - 100
    assert payee.wallet.balance == 600  # 500 + 100


def test_payment_channel_send_exceeds_balance_raises():
    """Sending more than channel balance raises RuntimeError."""
    payer = Agent("Payer", "trader", wallet=Wallet(balance=1000))
    payee = Agent("Payee", "broker", wallet=Wallet(balance=500))
    ch = PaymentChannel(payer=payer, payee=payee, capacity=100)
    ch.open()
    try:
        ch.send(200)
        assert False, "Should have raised"
    except RuntimeError as e:
        assert "exceeds" in str(e)


def test_payment_channel_send_closed_raises():
    """Sending on a closed channel raises RuntimeError."""
    payer = Agent("Payer", "trader", wallet=Wallet(balance=1000))
    payee = Agent("Payee", "broker", wallet=Wallet(balance=500))
    ch = PaymentChannel(payer=payer, payee=payee, capacity=100)
    # Not opened
    try:
        ch.send(10)
        assert False, "Should have raised"
    except RuntimeError as e:
        assert "not open" in str(e)


def test_payment_channel_close():
    """Closing a channel marks it as not open."""
    payer = Agent("Payer", "trader", wallet=Wallet(balance=1000))
    payee = Agent("Payee", "broker", wallet=Wallet(balance=500))
    ch = PaymentChannel(payer=payer, payee=payee, capacity=100)
    ch.open()
    ch.close()
    assert ch.is_open is False


def test_nanopayment_stream_raises_on_zero_duration():
    """NanopaymentStream raises ValueError for zero duration."""
    payer = Agent("Payer", "trader", wallet=Wallet(balance=1000))
    payee = Agent("Payee", "broker", wallet=Wallet(balance=500))
    ch = PaymentChannel(payer=payer, payee=payee, capacity=100)
    ch.open()
    try:
        NanopaymentStream(channel=ch, amount=100, duration=0)
        assert False, "Should have raised"
    except ValueError as e:
        assert "greater than zero" in str(e)


def test_nanopayment_stream_start_no_channel_raises():
    """Starting stream on unopened channel raises RuntimeError."""
    payer = Agent("Payer", "trader", wallet=Wallet(balance=1000))
    payee = Agent("Payee", "broker", wallet=Wallet(balance=500))
    ch = PaymentChannel(payer=payer, payee=payee, capacity=100)
    stream = NanopaymentStream(channel=ch, amount=100, duration=4)
    try:
        stream.start()
        assert False, "Should have raised"
    except RuntimeError as e:
        assert "must be open" in str(e)


def test_nanopayment_stream_full_cycle():
    """NanopaymentStream completes full payment cycle."""
    payer = Agent("Payer", "trader", wallet=Wallet(balance=1000))
    payee = Agent("Payee", "broker", wallet=Wallet(balance=500))
    ch = PaymentChannel(payer=payer, payee=payee, capacity=120)
    ch.open()

    stream = NanopaymentStream(channel=ch, amount=120, duration=4)
    stream.start()
    assert stream.completed is True
    assert stream.delivered_units == 4
    # Payer: 1000 - 120 = 880
    assert payer.wallet.balance == 880.0
    # Payee: 500 + 120 = 620
    assert payee.wallet.balance == 620.0


def test_nanopayment_stream_kill():
    """Killing a stream closes the channel."""
    payer = Agent("Payer", "trader", wallet=Wallet(balance=1000))
    payee = Agent("Payee", "broker", wallet=Wallet(balance=500))
    ch = PaymentChannel(payer=payer, payee=payee, capacity=120)
    ch.open()
    stream = NanopaymentStream(channel=ch, amount=120, duration=4)

    # Kill before starting (channel open but stream not completed)
    stream.kill_stream()
    assert ch.is_open is False


def test_arc_gateway_open_close():
    """ArcNanopaymentGateway opens and closes channels."""
    payer = Agent("Payer", "trader", wallet=Wallet(balance=1000))
    payee = Agent("Payee", "broker", wallet=Wallet(balance=500))
    gateway = ArcNanopaymentGateway(token_symbol="USDC")
    ch = gateway.open_channel(payer, payee, 250)
    assert ch.is_open is True
    assert ch.capacity == 250.0

    gateway.close_channel(ch)
    assert ch.is_open is False


def test_nanopayment_stream_schedule():
    """NanopaymentStream payment schedule splits amount evenly."""
    payer = Agent("Payer", "trader", wallet=Wallet(balance=1000))
    payee = Agent("Payee", "broker", wallet=Wallet(balance=500))
    ch = PaymentChannel(payer=payer, payee=payee, capacity=10)
    stream = NanopaymentStream(channel=ch, amount=10, duration=3)
    # 10 / 3 = 3.33 recurring, so: 3.33, 3.33, 3.34
    assert len(stream.schedule) == 3
    assert sum(stream.schedule) == 10.0
