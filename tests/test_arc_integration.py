"""Tests for Arc Integration (ArcJobManager in mock mode)."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from convenatai.agent import Agent, Wallet
from convenatai.arc_integration import ArcJobManager, JobStatus


def test_job_manager_mock_mode():
    """ArcJobManager starts in mock mode when use_live=False."""
    mgr = ArcJobManager(use_live=False)
    assert mgr.is_live is False
    assert mgr._mock_jobs == {}


def test_create_job_mock():
    """ArcJobManager.create_job creates a job in mock mode."""
    mgr = ArcJobManager(use_live=False)
    client = Agent("Client", "trading", wallet=Wallet(balance=1000))
    provider = Agent("Provider", "broker", wallet=Wallet(balance=500))

    job = mgr.create_job(client, provider, "Test job", 100.0)
    assert job.job_id == 1
    assert job.description == "Test job"
    assert job.budget == 100.0
    assert job.status == JobStatus.OPEN
    assert job.onchain is False


def test_create_job_increments_id():
    """Each create_job gets a new job ID."""
    mgr = ArcJobManager(use_live=False)
    client = Agent("C", "trader", wallet=Wallet(balance=1000))
    provider = Agent("P", "broker", wallet=Wallet(balance=500))

    j1 = mgr.create_job(client, provider, "Job 1", 50)
    j2 = mgr.create_job(client, provider, "Job 2", 75)
    assert j1.job_id == 1
    assert j2.job_id == 2


def test_set_budget_mock():
    """ArcJobManager.set_budget updates job budget in mock mode."""
    mgr = ArcJobManager(use_live=False)
    client = Agent("C", "trader", wallet=Wallet(balance=1000))
    provider = Agent("P", "broker", wallet=Wallet(balance=500))

    mgr.create_job(client, provider, "Job", 100)
    mgr.set_budget(provider, 1, 200)
    assert mgr._mock_jobs[1].budget == 200.0


def test_set_budget_missing_job_raises():
    """Setting budget for non-existent job raises RuntimeError."""
    mgr = ArcJobManager(use_live=False)
    provider = Agent("P", "broker", wallet=Wallet(balance=500))
    try:
        mgr.set_budget(provider, 999, 100)
        assert False, "Should have raised"
    except RuntimeError as e:
        assert "not found" in str(e)


def test_approve_and_fund_mock():
    """ArcJobManager.approve_and_fund escrows from client wallet."""
    mgr = ArcJobManager(use_live=False)
    client = Agent("C", "trader", wallet=Wallet(balance=500))
    provider = Agent("P", "broker", wallet=Wallet(balance=200))

    mgr.create_job(client, provider, "Job", 100)
    mgr.approve_and_fund(client, 1, 100)
    assert mgr._mock_jobs[1].status == JobStatus.FUNDED
    assert client.wallet.balance == 400  # 500 - 100


def test_submit_deliverable_mock():
    """ArcJobManager.submit_deliverable updates status to SUBMITTED."""
    mgr = ArcJobManager(use_live=False)
    client = Agent("C", "trader", wallet=Wallet(balance=500))
    provider = Agent("P", "broker", wallet=Wallet(balance=200))

    mgr.create_job(client, provider, "Job", 100)
    result = mgr.submit_deliverable(provider, 1, "deliverable-data")
    assert mgr._mock_jobs[1].status == JobStatus.SUBMITTED
    assert result == b"deliverable-data"


def test_complete_job_approved():
    """ArcJobManager.complete_job sets status to COMPLETED for approval."""
    mgr = ArcJobManager(use_live=False)
    client = Agent("C", "trader", wallet=Wallet(balance=500))
    provider = Agent("P", "broker", wallet=Wallet(balance=200))

    mgr.create_job(client, provider, "Job", 100)
    mgr.complete_job(client, 1, approved=True)
    assert mgr._mock_jobs[1].status == JobStatus.COMPLETED


def test_complete_job_rejected():
    """ArcJobManager.complete_job sets status to REJECTED."""
    mgr = ArcJobManager(use_live=False)
    client = Agent("C", "trader", wallet=Wallet(balance=500))
    provider = Agent("P", "broker", wallet=Wallet(balance=200))

    mgr.create_job(client, provider, "Job", 100)
    mgr.complete_job(client, 1, approved=False, reason="sla-failure")
    assert mgr._mock_jobs[1].status == JobStatus.REJECTED


def test_get_job_status_mock():
    """ArcJobManager.get_job_status returns job info."""
    mgr = ArcJobManager(use_live=False)
    client = Agent("C", "trader", wallet=Wallet(balance=500))
    provider = Agent("P", "broker", wallet=Wallet(balance=200))

    mgr.create_job(client, provider, "Job", 100)
    info = mgr.get_job_status(1)
    assert info.job_id == 1
    assert info.status == JobStatus.OPEN


def test_release_payment_mock():
    """ArcJobManager.release_payment deposits to provider in mock mode."""
    mgr = ArcJobManager(use_live=False)
    client = Agent("C", "trader", wallet=Wallet(balance=500))
    provider = Agent("P", "broker", wallet=Wallet(balance=200))

    mgr.create_job(client, provider, "Job", 100)
    mgr.release_payment(1, provider, 100)
    assert provider.wallet.balance == 300  # 200 + 100


def test_full_job_lifecycle_mock():
    """Full ERC-8183 job lifecycle works in mock mode."""
    mgr = ArcJobManager(use_live=False)
    client = Agent("Client", "trading", wallet=Wallet(balance=500))
    provider = Agent("Provider", "broker", wallet=Wallet(balance=200))

    # Step 1: Create
    job = mgr.create_job(client, provider, "Full cycle test", 150)
    assert job.status == JobStatus.OPEN

    # Step 2: Set budget
    mgr.set_budget(provider, job.job_id, 150)

    # Step 3: Approve and fund
    mgr.approve_and_fund(client, job.job_id, 150)
    assert mgr._mock_jobs[job.job_id].status == JobStatus.FUNDED

    # Step 4: Submit
    mgr.submit_deliverable(provider, job.job_id, "final-report")
    assert mgr._mock_jobs[job.job_id].status == JobStatus.SUBMITTED

    # Step 5: Complete
    mgr.complete_job(client, job.job_id, approved=True)
    assert mgr._mock_jobs[job.job_id].status == JobStatus.COMPLETED

    # Release
    mgr.release_payment(job.job_id, provider, 150)
    assert provider.wallet.balance == 350  # 200 + 150
