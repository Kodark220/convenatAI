"""
convenatAI — GenLayer-to-Arc Bridge Relay Service
=================================================
Autonomous background service that bridges the GenLayer SLA Monitoring contract 
to the Arc Testnet ERC-8183 Job Settlement contract.

Workflow:
1. Scans Arc Testnet for jobs in 'Funded' or 'Submitted' state.
2. For each active job on Arc, checks its SLA status on the GenLayer ConvenatContract
   using the stream ID (format: 'stream-arc-{job_id}').
3. If the GenLayer contract reports 'active: false' (meaning SLA criteria breached):
   - Triggers the on-chain Kill-Switch by calling `reject(job_id)` on the Arc contract.
   - Refounds the client, cancelling future nanopayment settlements.
"""

import argparse
import asyncio
import logging
import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("convenatAI.bridge")

from convenatai.agent import Agent, Wallet
from convenatai.arc_integration import ArcJobManager, JobStatus, STATUS_NAMES
from convenatai.discovery import AgentDiscovery
from convenatai.genlayer_client import NotifyGenLayer
from convenatai.circle_client import list_wallets

class BridgeRelay:
    def __init__(self, use_live: bool = None, interval: int = 15):
        """
        Args:
            use_live: True for real Arc/GenLayer testnets, False for Mock.
            interval: Polling frequency in seconds.
        """
        if use_live is None:
            use_live = bool(os.getenv("CIRCLE_API_KEY") and os.getenv("CIRCLE_ENTITY_SECRET"))
            
        self.use_live = use_live
        self.interval = interval
        self.arc_manager = ArcJobManager(use_live=use_live)
        self.discovery = AgentDiscovery(chain="arc" if use_live else "genlayer")
        
        # Initialize default evaluator agent (with wallet configured for signing)
        self.evaluator = Agent("BridgeEvaluator", role="evaluator", wallet=Wallet())
        
        if self.use_live:
            # Map existing wallet details from Circle so we can sign
            try:
                wallets = list_wallets()
                if wallets:
                    # By default, use the buyer/client wallet (TradingAgent) as evaluator
                    # Wallet index 1 (0x92e9aac...) is TradingAgent in worker.py
                    if len(wallets) >= 2:
                        self.evaluator.wallet.address = wallets[1].address
                        self.evaluator.wallet.wallet_id = wallets[1].wallet_id
                    else:
                        self.evaluator.wallet.address = wallets[0].address
                        self.evaluator.wallet.wallet_id = wallets[0].wallet_id
                    logger.info(f"Bridge Evaluator initialized with wallet: {self.evaluator.wallet.address}")
            except Exception as e:
                logger.error(f"Failed to load Circle wallets: {e}")
        else:
            logger.info("Bridge initialized in LOCAL MOCK mode.")

    async def run(self):
        logger.info("=" * 60)
        logger.info("  convenatAI — GenLayer-to-Arc Bridge Relay Service")
        logger.info(f"  Mode: {'🔴 LIVE (Arc/GenLayer Testnets)' if self.use_live else '🟡 LOCAL MOCK'}")
        logger.info(f"  Interval: {self.interval}s")
        logger.info("=" * 60)

        while True:
            try:
                await self.process_jobs()
            except Exception as e:
                logger.error(f"Error during bridge processing cycle: {e}", exc_info=True)
            
            await asyncio.sleep(self.interval)

    async def process_jobs(self):
        logger.info(f"--- Scanning bridge jobs at {datetime.now().strftime('%H:%M:%S')} ---")
        
        if not self.use_live:
            # Mock mode: check mock jobs in arc_manager
            jobs = list(self.arc_manager._mock_jobs.values())
            active_jobs = [j for j in jobs if j.status in (JobStatus.FUNDED, JobStatus.SUBMITTED)]
            
            logger.info(f"Found {len(active_jobs)} active mock jobs to monitor.")
            for job in active_jobs:
                # Mock stream ID convention
                stream_id = f"stream-arc-{job.job_id}"
                
                # Check GenLayer mock/real contract
                job_status = NotifyGenLayer.get_job_status(stream_id)
                if job_status.get("error"):
                    logger.warning(f"  Job #{job.job_id} | GenLayer RPC offline: {job_status['error']}")
                    continue
                
                is_active = job_status.get("active", job_status.get("result", {}).get("active", None))
                if is_active is False:
                    logger.info(f"  🚨 Job #{job.job_id} | SLA breach detected on GenLayer! Triggering Arc Rejection.")
                    self.arc_manager.complete_job(
                        evaluator=self.evaluator,
                        job_id=job.job_id,
                        approved=False,
                        reason="sla-breach"
                    )
            return

        # Live mode: Scan Arc testnet for active jobs
        try:
            discovered_jobs = self.discovery.scan_recent_jobs(lookback_blocks=2000)
            
            # Filter jobs on-chain that are Funded or Submitted (which are candidates for rejection)
            active_candidate_jobs = []
            for d_job in discovered_jobs:
                # Query real job status on Arc
                try:
                    job_info = self.arc_manager.get_job_status(d_job.job_id)
                    # Funded = 1, Submitted = 2
                    if job_info.status in (JobStatus.FUNDED, JobStatus.SUBMITTED):
                        active_candidate_jobs.append(job_info)
                except Exception as e:
                    logger.debug(f"Could not fetch full job info for job #{d_job.job_id}: {e}")
            
            logger.info(f"Found {len(active_candidate_jobs)} active on-chain jobs on Arc.")
            
            for job in active_candidate_jobs:
                stream_id = f"stream-arc-{job.job_id}"
                logger.info(f"  Job #{job.job_id} | Polling GenLayer SLA: {stream_id}")
                
                job_status = NotifyGenLayer.get_job_status(stream_id)
                if job_status.get("error"):
                    logger.warning(f"  Job #{job.job_id} | GenLayer status fetch failed: {job_status['error']}")
                    continue
                
                is_active = job_status.get("active", job_status.get("result", {}).get("active", None))
                if is_active is None:
                    logger.debug(f"  Job #{job.job_id} | No active SLA registered on GenLayer for stream: {stream_id}")
                    continue
                
                if is_active is False:
                    logger.info(f"  🚨 Job #{job.job_id} | SLA breached on GenLayer! Triggering on-chain reject.")
                    try:
                        self.arc_manager.complete_job(
                            evaluator=self.evaluator,
                            job_id=job.job_id,
                            approved=False,
                            reason="sla-breach-killswitch"
                        )
                        logger.info(f"  ✅ Job #{job.job_id} successfully rejected and refunded on Arc!")
                    except Exception as e:
                        logger.error(f"  ❌ Failed to reject Job #{job.job_id} on Arc: {e}")
                else:
                    logger.info(f"  Job #{job.job_id} | SLA is healthy.")
                    
        except Exception as e:
            logger.error(f"Failed to scan Arc jobs: {e}")

def main():
    parser = argparse.ArgumentParser(description="convenatAI — GenLayer-to-Arc Bridge Relay Service")
    parser.add_argument("--interval", type=int, default=15, help="Polling interval in seconds")
    parser.add_argument("--live", action="store_true", help="Force Live Network mode")
    parser.add_argument("--mock", action="store_true", help="Force Local Mock mode")
    args = parser.parse_args()

    use_live = None
    if args.live:
        use_live = True
    elif args.mock:
        use_live = False

    relay = BridgeRelay(use_live=use_live, interval=args.interval)
    
    try:
        asyncio.run(relay.run())
    except KeyboardInterrupt:
        logger.info("Shutdown request received. Stopping Bridge Relay.")

if __name__ == "__main__":
    main()
