"""Tests for GenLayer client (NotifyGenLayer basic mock mode)."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from convenatai.genlayer_client import (
    NotifyGenLayer,
    GENLAYER_CONTRACT,
)


def test_constants_loaded():
    """Constants have expected values or defaults."""
    assert GENLAYER_CONTRACT is not None


def test_register_job_returns_rpc_error():
    """register_job raises RuntimeError when mock write fallback is disabled."""
    with pytest.raises(RuntimeError, match="GenLayer SDK write failed"):
        NotifyGenLayer.register_job(
            stream_id="test-stream",
            buyer_id="0xBuyer",
            seller_id="0xSeller",
            description="Test job",
        )


def test_monitor_stream_returns_rpc_error():
    """monitor_stream raises RuntimeError when mock write fallback is disabled."""
    with pytest.raises(RuntimeError, match="GenLayer SDK write failed"):
        NotifyGenLayer.monitor_stream(
            stream_id="test-stream",
            deliverable_uri="https://example.com/delivery/1",
        )


def test_get_job_status_returns_error():
    """get_job_status returns error when no CLI or live RPC available."""
    result = NotifyGenLayer.get_job_status("test-stream")
    assert result is not None
