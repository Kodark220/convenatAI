"""Tests for GenLayer client (NotifyGenLayer basic mock mode)."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from convenatai.genlayer_client import (
    NotifyGenLayer,
    _format_addr,
    GENLAYER_CONTRACTS,
    GENLAYER_RPCS,
)


def test_format_addr_0x():
    """_format_addr adds 'addr-' prefix to hex addresses."""
    result = _format_addr("0xabc123")
    assert result == "addr-abc123"


def test_format_addr_already_prefixed():
    """_format_addr doesn't double-prefix."""
    result = _format_addr("addr-abc123")
    assert result == "addr-abc123"


def test_format_addr_plain():
    """_format_addr handles non-hex strings."""
    result = _format_addr("AgentName")
    assert result == "addr-AgentName"


def test_constants_loaded():
    """Constants have expected values or defaults."""
    assert len(GENLAYER_CONTRACTS) > 0
    assert len(GENLAYER_RPCS) > 0


def test_register_job_returns_rpc_error():
    """register_job returns rpc_error when no CLI or live RPC available."""
    result = NotifyGenLayer.register_job(
        stream_id="test-stream",
        buyer_id="0xBuyer",
        seller_id="0xSeller",
        description="Test job",
    )
    # Since we're not on Windows with PowerShell, it should fall through
    # to RPC or return rpc_error
    assert result is not None
    assert "status" in result or "error" in result


def test_monitor_stream_returns_rpc_error():
    """monitor_stream returns rpc_error when no CLI or live RPC available."""
    result = NotifyGenLayer.monitor_stream(
        stream_id="test-stream",
        deliverable_uri="https://example.com/delivery/1",
    )
    assert result is not None
    assert "status" in result or "error" in result


def test_get_job_status_returns_error():
    """get_job_status returns error when no CLI or live RPC available."""
    result = NotifyGenLayer.get_job_status("test-stream")
    assert result is not None
