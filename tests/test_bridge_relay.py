"""Tests for the Bridge Relay Service (mock mode)."""

import sys
import os
import pytest
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from convenatai.agent import Agent, Wallet
from convenatai.arc_integration import JobStatus
from convenatai.bridge_relay import BridgeRelay
from convenatai.genlayer_client import NotifyGenLayer

def test_bridge_relay_init_mock():
    """BridgeRelay initializes correctly in mock mode."""
    relay = BridgeRelay(use_live=False, interval=5)
    assert relay.use_live is False
    assert relay.interval == 5
    assert relay.evaluator is not None
    assert relay.evaluator.name == "BridgeEvaluator"

def test_bridge_relay_process_jobs_mock_sla_healthy(monkeypatch):
    """BridgeRelay keeps job active if GenLayer SLA is active/healthy."""
    relay = BridgeRelay(use_live=False, interval=1)
    
    # Create mock job
    client = Agent("Client", "trading", wallet=Wallet(balance=500))
    provider = Agent("Provider", "broker", wallet=Wallet(balance=200))
    job = relay.arc_manager.create_job(client, provider, "Mock SLA job", 100)
    relay.arc_manager.approve_and_fund(client, job.job_id, 100)
    
    # We should have job in FUNDED state
    assert relay.arc_manager._mock_jobs[job.job_id].status == JobStatus.FUNDED
    
    # Mock NotifyGenLayer.get_job_status to return active = True
    def mock_get_job_status(stream_id):
        return {"active": True}
        
    monkeypatch.setattr(NotifyGenLayer, "get_job_status", mock_get_job_status)
    
    asyncio.run(relay.process_jobs())
    
    # Job should still be FUNDED
    assert relay.arc_manager._mock_jobs[job.job_id].status == JobStatus.FUNDED


def test_bridge_relay_process_jobs_mock_sla_breached(monkeypatch):
    """BridgeRelay rejects job if GenLayer SLA is breached."""
    relay = BridgeRelay(use_live=False, interval=1)
    
    # Create mock job
    client = Agent("Client", "trading", wallet=Wallet(balance=500))
    provider = Agent("Provider", "broker", wallet=Wallet(balance=200))
    job = relay.arc_manager.create_job(client, provider, "Mock SLA job", 100)
    relay.arc_manager.approve_and_fund(client, job.job_id, 100)
    
    # We should have job in FUNDED state
    assert relay.arc_manager._mock_jobs[job.job_id].status == JobStatus.FUNDED
    
    # Mock NotifyGenLayer.get_job_status to return active = False
    def mock_get_job_status(stream_id):
        return {"active": False}
        
    monkeypatch.setattr(NotifyGenLayer, "get_job_status", mock_get_job_status)
    
    asyncio.run(relay.process_jobs())
    
    # Job should be transitioned to REJECTED due to SLA breach
    assert relay.arc_manager._mock_jobs[job.job_id].status == JobStatus.REJECTED
