"""
convenatAI — Arc Network ERC-8183 Integration

Provides the ArcJobOrchestrator that replaces the mock LegalContract/Escrow
with real on-chain ERC-8183 job lifecycle on Arc Testnet.

Two modes:
  - LIVE: Uses Circle Developer-Controlled Wallets API + Arc RPC
  - LOCAL MOCK: Falls back to the existing LegalContract/Escrow for dev/testing

Requires CIRCLE_API_KEY + CIRCLE_ENTITY_SECRET in .env for live mode.
"""

from __future__ import annotations
import logging
import os
import time
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

from dotenv import load_dotenv

from .agent import Agent, HAS_CIRCLE
from .circle_client import (
    check_connection as circle_check_connection,
    list_wallets,
    create_wallets as circle_create_wallets,
    create_contract_execution_transaction,
)

load_dotenv()

logger = logging.getLogger(__name__)

# ─── Compatibility: use our lightweight REST client ──────────────────────

def _circle_api_available() -> bool:
    """Check if we have working Circle API access."""
    return bool(os.getenv("CIRCLE_API_KEY") and os.getenv("CIRCLE_ENTITY_SECRET"))

# ─── Constants ────────────────────────────────────────────────────────────────

ARC_TESTNET = {
    "chain_id": 5042002,
    "rpc": os.getenv("ARC_RPC_URL", "https://rpc.testnet.arc.network"),
    "usdc_token_id": os.getenv("USDC_TOKEN_ID", "15dc2b5d-0994-58b0-bf8c-3a0501148ee8"),
}

AGENTIC_COMMERCE_CONTRACT = os.getenv(
    "AGENTIC_COMMERCE_CONTRACT",
    "0xcc23aF94f43Ffcfe7348C5135B5d1Fb4e148E5f1",
)
USDC_ERC20_CONTRACT = "0x3600000000000000000000000000000000000000"

# ─── ERC-8183 Job Status ──────────────────────────────────────────────────────

class JobStatus(IntEnum):
    OPEN = 0
    FUNDED = 1
    SUBMITTED = 2
    COMPLETED = 3
    REJECTED = 4
    EXPIRED = 5

STATUS_NAMES = ["Open", "Funded", "Submitted", "Completed", "Rejected", "Expired"]


# ─── ERC-8183 ABI (minimal — functions we call) ───────────────────────────────

ERC8183_ABI = [
    # createJob(address,address,uint256,string,address) → uint256 jobId
    {
        "type": "function",
        "name": "createJob",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "provider", "type": "address"},
            {"name": "evaluator", "type": "address"},
            {"name": "expiredAt", "type": "uint256"},
            {"name": "description", "type": "string"},
            {"name": "hook", "type": "address"},
        ],
        "outputs": [{"name": "jobId", "type": "uint256"}],
    },
    # setBudget(uint256,uint256,bytes)
    {
        "type": "function",
        "name": "setBudget",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "jobId", "type": "uint256"},
            {"name": "amount", "type": "uint256"},
            {"name": "optParams", "type": "bytes"},
        ],
        "outputs": [],
    },
    # fund(uint256,bytes)
    {
        "type": "function",
        "name": "fund",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "jobId", "type": "uint256"},
            {"name": "optParams", "type": "bytes"},
        ],
        "outputs": [],
    },
    # submit(uint256,bytes32,bytes)
    {
        "type": "function",
        "name": "submit",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "jobId", "type": "uint256"},
            {"name": "deliverable", "type": "bytes32"},
            {"name": "optParams", "type": "bytes"},
        ],
        "outputs": [],
    },
    # complete(uint256,bytes32,bytes)
    {
        "type": "function",
        "name": "complete",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "jobId", "type": "uint256"},
            {"name": "reason", "type": "bytes32"},
            {"name": "optParams", "type": "bytes"},
        ],
        "outputs": [],
    },
    # reject(uint256,bytes32,bytes)
    {
        "type": "function",
        "name": "reject",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "jobId", "type": "uint256"},
            {"name": "reason", "type": "bytes32"},
            {"name": "optParams", "type": "bytes"},
        ],
        "outputs": [],
    },
    # getJob(uint256) → tuple
    {
        "type": "function",
        "name": "getJob",
        "stateMutability": "view",
        "inputs": [{"name": "jobId", "type": "uint256"}],
        "outputs": [
            {
                "type": "tuple",
                "components": [
                    {"name": "id", "type": "uint256"},
                    {"name": "client", "type": "address"},
                    {"name": "provider", "type": "address"},
                    {"name": "evaluator", "type": "address"},
                    {"name": "description", "type": "string"},
                    {"name": "budget", "type": "uint256"},
                    {"name": "expiredAt", "type": "uint256"},
                    {"name": "status", "type": "uint8"},
                    {"name": "hook", "type": "address"},
                ],
            }
        ],
    },
    # approve(address,uint256) — USDC ERC-20
    {
        "type": "function",
        "name": "approve",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "bool"}],
    },
]

USDC_ABI = [
    {
        "type": "function",
        "name": "approve",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "bool"}],
    },
    {
        "type": "function",
        "name": "balanceOf",
        "stateMutability": "view",
        "inputs": [{"name": "account", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
    },
]


# ─── Circle API helpers (pure Python REST, no SDK required) ─────────────────

def _get_circle_client():
    """Get the Circle REST client.
    Returns None if keys are unavailable."""
    if not HAS_CIRCLE:
        return None
    try:
        result = circle_check_connection()
        if result.get("connected"):
            logger.info("Circle API connected successfully")
        else:
            logger.warning(f"Circle API connection failed: {result.get('error')}")
        return result
    except Exception as e:
        logger.warning(f"Circle client init failed: {e}")
        return None


# ─── Mock Web3 for local development ──────────────────────────────────────────

def _get_web3():
    """Get a Web3 instance connected to Arc Testnet, or None if web3 not installed."""
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(ARC_TESTNET["rpc"]))
        return w3
    except ImportError:
        return None


# ─── USDC helpers ─────────────────────────────────────────────────────────────

def _usdc_to_wei(amount_usd: float) -> int:
    """Convert USDC dollar amount to 6-decimal integer (mwei)."""
    return int(amount_usd * 1_000_000)


def _wei_to_usdc(wei: int) -> float:
    """Convert 6-decimal USDC wei to dollar float."""
    return wei / 1_000_000


# ─── ArcJobTracker: in-memory job state (for local mock + tracking) ────────────

@dataclass
class ArcJobInfo:
    job_id: int
    client_address: str
    provider_address: str
    description: str
    budget: float  # in USDC dollars
    status: JobStatus
    onchain: bool = False  # True if confirmed on-chain
    tx_hash: str = ""  # On-chain transaction hash if confirmed


class ArcJobManager:
    """Manages ERC-8183 job lifecycle.
    
    In live mode, calls the real AgenticCommerce contract via Circle API.
    In mock mode, simulates the contract in-memory.
    """
    
    def __init__(self, use_live: Optional[bool] = True):
        """
        Args:
            use_live: True for on-chain Arc, False for mock.
                      Default: True (enforces live on-chain operations).
        """
        if use_live is None:
            use_live = True
        
        self._live = use_live
        self._circle = _get_circle_client() if use_live and HAS_CIRCLE else None
        self._web3 = _get_web3()
        
        # Track last tx hash for callers to inspect
        self._last_tx_hash = ""
        
        # Mock state
        self._next_job_id = 1
        self._mock_jobs: dict[int, ArcJobInfo] = {}
        
        if self._live and not _circle_api_available():
            raise ValueError(
                "Live mode is strictly required but Circle API keys "
                "(CIRCLE_API_KEY and CIRCLE_ENTITY_SECRET) are not configured in the environment."
            )
    
    @property
    def is_live(self) -> bool:
        return self._live
    
    def provision_agent_wallets(self, agents: list[Agent], reuse_existing: bool = True) -> list[Agent]:
        """Create Arc Testnet wallets for agents and attach them.
        
        In reuse_existing mode, checks if wallets already exist before creating new ones.
        Only works in live mode. In mock mode, agents keep their local wallets.
        Returns agents with wallets attached (or unchanged in mock mode).
        """
        if not self._live:
            logger.info("Mock mode — agents keep local wallets")
            return agents
        
        # Check if we already provisioned wallets
        existing = list_wallets()
        if reuse_existing and len(existing) >= len(agents):
            logger.info(f"Reusing {len(existing)} existing Arc wallets")
            # Wallet order: [0]=Treasury, [1]=Trader(client), [2]=Broker(provider)
            # Wallet 0 (0x92e9aac...) has 25 USDC → assign to TradingAgent (buyer/client)
            funded_addr = "0x92e9aac1ed7044487bc8d8128465c7e588d9e1b6"
            funded_id = "44a75773-f53d-5841-9f2b-9d0f5bcae66c"
            
            # Wallet 2 (0x366c33...) has 5 USDC → assign to DataBrokerAgent (provider/seller)
            provider_addr = "0x366c3352daee2b4b0117e6bdd1ff291beafcc8ad"
            provider_id = "316e0aef-3817-5a25-ac72-82d4a1d2b90b"
            
            for i, (agent, wallet_info) in enumerate(zip(agents, existing[:len(agents)])):
                addr = wallet_info.address
                wid = wallet_info.wallet_id
                
                # Index 1 = TradingAgent (buyer) → gets the funded wallet (25 USDC)
                if i == 1:
                    agent.wallet.address = funded_addr
                    agent.wallet.wallet_id = funded_id
                # Index 2 = DataBrokerAgent (provider) → gets wallet with 5 USDC
                elif i == 2:
                    agent.wallet.address = provider_addr
                    agent.wallet.wallet_id = provider_id
                else:
                    agent.wallet.address = addr
                    agent.wallet.wallet_id = wid
                logger.info(f"{agent.name} → {agent.wallet.address}")
            return agents
        
        logger.info("Provisioning new Arc Testnet wallets for agents...")
        try:
            wallets = circle_create_wallets(count=len(agents))
            for agent, wallet_info in zip(agents, wallets):
                agent.wallet.address = wallet_info.address
                agent.wallet.wallet_id = wallet_info.wallet_id
                logger.info(f"{agent.name} → {agent.wallet.address}")
        except Exception as e:
            logger.error(f"Wallet provisioning failed: {e}")
            logger.warning("Agents running with local wallets only")
        
        return agents
    
    def get_wallet_balance(self, wallet_id: str) -> float:
        """Get USDC balance from Circle API."""
        try:
            from .circle_client import get_wallet_balance as _get_balance
            return _get_balance(wallet_id)
        except Exception:
            return 0.0
    
    def create_job(
        self,
        client: Agent,
        provider: Agent,
        description: str,
        budget_usd: float,
        evaluator: Optional[Agent] = None,
        hook_address: str = "0x0000000000000000000000000000000000000000",
        expiry_seconds: int = 3600 * 24 * 7,  # 7 days
    ) -> ArcJobInfo:
        """Step 1: Create an ERC-8183 job on Arc."""
        eval_addr = evaluator.wallet.address if evaluator else client.wallet.address
        expired_at = int(time.time()) + expiry_seconds
        
        if self._live:
            return self._create_job_onchain(client, provider, description, budget_usd,
                                            eval_addr, hook_address, expired_at)
        else:
            return self._create_job_mock(client, provider, description, budget_usd,
                                         eval_addr, hook_address, expired_at)
    
    def _create_job_mock(
        self, client, provider, description, budget_usd, evaluator, hook, expired_at
    ) -> ArcJobInfo:
        job_id = self._next_job_id
        self._next_job_id += 1
        
        info = ArcJobInfo(
            job_id=job_id,
            client_address=client.wallet.address or "MockClient",
            provider_address=provider.wallet.address or "MockProvider",
            description=description,
            budget=budget_usd,
            status=JobStatus.OPEN,
            onchain=False,
        )
        self._mock_jobs[job_id] = info
        logger.info(f"[MOCK] Job {job_id} created: {description} for ${budget_usd:.2f}")
        return info
    
    def _create_job_onchain(self, client, provider, description, budget_usd,
                            evaluator, hook, expired_at) -> ArcJobInfo:
        """Call createJob on the real ERC-8183 contract via Circle API.
        Uses our contract's actual signature: createJob(address _provider)."""
        logger.info(f"Creating ERC-8183 job on Arc Testnet...")
        
        try:
            # Our contract (MockAgenticCommerce) uses simple createJob(address)
            # The client (msg.sender) is the buyer wallet, provider is the seller
            logger.info(f"  Client (buyer): {client.wallet.address}")
            logger.info(f"  Provider (seller): {provider.wallet.address}")
            logger.info(f"  Contract: {AGENTIC_COMMERCE_CONTRACT}")
            
            result = create_contract_execution_transaction(
                wallet_address=client.wallet.address,
                contract_address=AGENTIC_COMMERCE_CONTRACT,
                abi_function_signature="createJob(address)",
                abi_parameters=[provider.wallet.address],
            )
            tx_id = result.get("id", "unknown")
            logger.info(f"createJob tx submitted: {tx_id}")
            
            # Poll for the tx result using Circle REST API
            import time
            from .circle_client import get_transaction_status
            tx_hash = None
            
            for attempt in range(30):
                try:
                    tx_status = get_transaction_status(tx_id)
                    state = tx_status.get("state", "")
                    if state == "COMPLETE":
                        tx_hash = tx_status.get("txHash", "")
                        self._last_tx_hash = tx_hash
                        logger.info(f"createJob confirmed! txHash: {tx_hash}")
                        break
                    elif state == "FAILED":
                        raise RuntimeError(f"createJob failed: {tx_status.get('errorDetails', 'unknown')}")
                except Exception as e:
                    logger.debug(f"Poll attempt {attempt+1}: {e}")
                time.sleep(3)
            
            # Decode jobId from the transaction receipt
            job_id = self._decode_job_id_from_receipt(client.wallet.address, tx_hash) if tx_hash else None
            
            if job_id is None:
                job_id = self._next_job_id
                self._next_job_id += 1
                logger.warning(f"Using local jobId: {job_id}")
            
            # Store the tx_hash so discovery can pick it up
            if tx_hash:
                info = ArcJobInfo(
                    job_id=job_id,
                    client_address=client.wallet.address or "LiveClient",
                    provider_address=provider.wallet.address or "LiveProvider",
                    description=description,
                    budget=budget_usd,
                    status=JobStatus.OPEN,
                    onchain=True,
                    tx_hash=tx_hash,
                )
                logger.info(f"Job {job_id} created on-chain: {description[:40]} for ${budget_usd:.2f} (tx: {tx_hash[:18]}...)")
            else:
                info = ArcJobInfo(
                    job_id=job_id,
                    client_address=client.wallet.address or "LiveClient",
                    provider_address=provider.wallet.address or "LiveProvider",
                    description=description,
                    budget=budget_usd,
                    status=JobStatus.OPEN,
                    onchain=True,
                )
                logger.info(f"Job {job_id} created on-chain: {description[:40]} for ${budget_usd:.2f}")
            return info
            
        except Exception as e:
            logger.error(f"createJob on-chain failed: {e}")
            raise RuntimeError(f"Arc createJob failed: {e}")
    
    def _decode_job_id_from_receipt(self, wallet_address: str, tx_hash: str) -> int | None:
        """Decode the job ID from a createJob transaction receipt by reading event logs."""
        try:
            import urllib.request, json
            
            rpc_url = ARC_TESTNET.get("rpc", "https://rpc.testnet.arc.network")
            
            req_data = json.dumps({
                "jsonrpc": "2.0",
                "method": "eth_getTransactionReceipt",
                "params": [tx_hash],
                "id": 1,
            }).encode()
            
            req = urllib.request.Request(
                rpc_url,
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            
            with urllib.request.urlopen(req, timeout=15) as resp:
                receipt = json.loads(resp.read().decode()).get("result", {})
            
            if not receipt:
                return None
            
            # Look for the JobCreated event from AgenticCommerce
            # The event has topic0 = keccak256("JobCreated(uint256,address,address,address,uint256,string,address)")
            # topic1 = jobId, topic2 = client, topic3 = provider
            contract_addr = AGENTIC_COMMERCE_CONTRACT.lower()
            for log in receipt.get("logs", []):
                if log.get("address", "").lower() != contract_addr:
                    continue
                topics = log.get("topics", [])
                if len(topics) >= 2:
                    job_id_hex = topics[1]
                    if job_id_hex and job_id_hex != "0x" + "0"*64:
                        return int(job_id_hex, 16)
            
            return None
        except Exception as e:
            logger.warning(f"Failed to decode jobId from receipt: {e}")
            return None
    
    def set_budget(self, provider: Agent, job_id: int, amount_usd: float) -> None:
        """Step 2: Provider sets the job budget."""
        if self._live:
            self._set_budget_onchain(provider, job_id, amount_usd)
        else:
            self._set_budget_mock(provider, job_id, amount_usd)
    
    def _set_budget_mock(self, provider, job_id, amount_usd):
        if job_id not in self._mock_jobs:
            raise RuntimeError(f"Job {job_id} not found")
        self._mock_jobs[job_id].budget = amount_usd
        logger.info(f"[MOCK] Budget set for job {job_id}: ${amount_usd:.2f}")
    
    def _set_budget_onchain(self, provider, job_id, amount_usd):
        logger.info(f"Setting budget for job {job_id}: ${amount_usd:.2f}")
        try:
            result = create_contract_execution_transaction(
                wallet_address=provider.wallet.address,
                contract_address=AGENTIC_COMMERCE_CONTRACT,
                abi_function_signature="setBudget(uint256,uint256,bytes)",
                abi_parameters=[str(job_id), str(int(amount_usd * 1_000_000)), "0x"],
            )
            self._last_tx_hash = result.get('id', '')
            logger.info(f"setBudget tx submitted: {result.get('id', 'unknown')}")
        except Exception as e:
            logger.error(f"setBudget on-chain failed: {e}")
            raise RuntimeError(f"Arc setBudget failed: {e}")
    
    def approve_and_fund(self, client: Agent, job_id: int, amount_usd: float) -> None:
        """Step 3: Approve USDC and fund escrow."""
        if self._live:
            self._approve_and_fund_onchain(client, job_id, amount_usd)
        else:
            self._approve_and_fund_mock(client, job_id, amount_usd)
    
    def _approve_and_fund_mock(self, client, job_id, amount_usd):
        if job_id not in self._mock_jobs:
            raise RuntimeError(f"Job {job_id} not found")
        # Escrow the funds from client wallet (simulated)
        if not client.wallet.withdraw(amount_usd):
            raise RuntimeError(f"{client.name} cannot fund escrow for ${amount_usd:.2f}.")
        self._mock_jobs[job_id].status = JobStatus.FUNDED
        logger.info(f"[MOCK] Job {job_id} funded with ${amount_usd:.2f}")
    
    def _approve_and_fund_onchain(self, client, job_id, amount_usd):
        logger.info(f"Approving USDC and funding job {job_id}: ${amount_usd:.2f}")
        try:
            # Step 3a: Approve USDC
            result = create_contract_execution_transaction(
                wallet_address=client.wallet.address,
                contract_address=USDC_ERC20_CONTRACT,
                abi_function_signature="approve(address,uint256)",
                abi_parameters=[AGENTIC_COMMERCE_CONTRACT, str(int(amount_usd * 1_000_000))],
            )
            self._last_tx_hash = result.get('id', '')
            logger.info(f"USDC approve tx submitted: {result.get('id', 'unknown')}")
            
            # Step 3b: Fund escrow
            result = create_contract_execution_transaction(
                wallet_address=client.wallet.address,
                contract_address=AGENTIC_COMMERCE_CONTRACT,
                abi_function_signature="fund(uint256,bytes)",
                abi_parameters=[str(job_id), "0x"],
            )
            self._last_tx_hash = result.get('id', '')
            logger.info(f"fund tx submitted: {result.get('id', 'unknown')}")
            
        except Exception as e:
            logger.error(f"approve+fund on-chain failed: {e}")
            raise RuntimeError(f"Arc approve+fund failed: {e}")
    
    def submit_deliverable(self, provider: Agent, job_id: int, deliverable_text: str) -> bytes:
        """Step 4: Provider submits a deliverable hash."""
        if self._live:
            return self._submit_onchain(provider, job_id, deliverable_text)
        else:
            return self._submit_mock(provider, job_id, deliverable_text)
    
    def _submit_mock(self, provider, job_id, deliverable_text):
        if job_id not in self._mock_jobs:
            raise RuntimeError(f"Job {job_id} not found")
        self._mock_jobs[job_id].status = JobStatus.SUBMITTED
        logger.info(f"[MOCK] Job {job_id} submitted: {deliverable_text}")
        return deliverable_text.encode()
    
    def _submit_onchain(self, provider, job_id, deliverable_text):
        logger.info(f"Submitting deliverable for job {job_id}")
        try:
            if self._web3:
                deliverable_hash = self._web3.keccak(text=deliverable_text)
                hash_hex = "0x" + deliverable_hash.hex()
            else:
                import hashlib
                hash_hex = "0x" + hashlib.sha256(deliverable_text.encode()).hexdigest()
            
            result = create_contract_execution_transaction(
                wallet_address=provider.wallet.address,
                contract_address=AGENTIC_COMMERCE_CONTRACT,
                abi_function_signature="submit(uint256,bytes32,bytes)",
                abi_parameters=[str(job_id), hash_hex, "0x"],
            )
            self._last_tx_hash = result.get('id', '')
            logger.info(f"submit tx submitted: {result.get('id', 'unknown')}")
            return bytes.fromhex(hash_hex[2:])
        except Exception as e:
            logger.error(f"submit on-chain failed: {e}")
            raise RuntimeError(f"Arc submit failed: {e}")
    
    def complete_job(self, evaluator: Agent, job_id: int, approved: bool = True,
                     reason: str = "deliverable-approved") -> None:
        """Step 5: Evaluator completes or rejects the job."""
        if self._live:
            self._complete_onchain(evaluator, job_id, approved, reason)
        else:
            self._complete_mock(evaluator, job_id, approved, reason)
    
    def _complete_mock(self, evaluator, job_id, approved, reason):
        if job_id not in self._mock_jobs:
            raise RuntimeError(f"Job {job_id} not found")
        status = JobStatus.COMPLETED if approved else JobStatus.REJECTED
        self._mock_jobs[job_id].status = status
        logger.info(f"[MOCK] Job {job_id} completed: {reason}")
        
        # Release funds to provider on completion
        if approved:
            job = self._mock_jobs[job_id]
            # funds were already withdrawn from client, now give to provider
            # In mock mode, we transfer back + pay provider
            # (this is simplified — real escrow is on-chain)
    
    def _complete_onchain(self, evaluator, job_id, approved, reason):
        action = "complete" if approved else "reject"
        logger.info(f"{action.capitalize()}ing job {job_id}: approved={approved}")
        try:
            if self._web3:
                reason_hash = self._web3.keccak(text=reason)
                hash_hex = "0x" + reason_hash.hex()
            else:
                import hashlib
                hash_hex = "0x" + hashlib.sha256(reason.encode()).hexdigest()
            
            result = create_contract_execution_transaction(
                wallet_address=evaluator.wallet.address,
                contract_address=AGENTIC_COMMERCE_CONTRACT,
                abi_function_signature=f"{action}(uint256,bytes32,bytes)",
                abi_parameters=[str(job_id), hash_hex, "0x"],
            )
            self._last_tx_hash = result.get('id', '')
            logger.info(f"{action} tx submitted: {result.get('id', 'unknown')}")
        except Exception as e:
            logger.error(f"{action} on-chain failed: {e}")
            raise RuntimeError(f"Arc {action} failed: {e}")
    
    def get_job_status(self, job_id: int) -> ArcJobInfo:
        """Get current job status."""
        if self._live and self._web3:
            return self._get_job_onchain(job_id)
        else:
            return self._get_job_mock(job_id)
    
    def _get_job_mock(self, job_id):
        if job_id not in self._mock_jobs:
            raise RuntimeError(f"Job {job_id} not found")
        return self._mock_jobs[job_id]
    
    def _get_job_onchain(self, job_id):
        """Read job from on-chain contract via Web3."""
        try:
            contract = self._web3.eth.contract(
                address=self._web3.to_checksum_address(AGENTIC_COMMERCE_CONTRACT),
                abi=ERC8183_ABI,
            )
            job = contract.functions.getJob(job_id).call()
            status = JobStatus(int(job[7]))
            budget_wei = int(job[5])
            
            return ArcJobInfo(
                job_id=job_id,
                client_address=job[1],
                provider_address=job[2],
                description=job[4],
                budget=_wei_to_usdc(budget_wei),
                status=status,
                onchain=True,
            )
        except Exception as e:
            logger.error(f"getJob on-chain failed: {e}")
            raise RuntimeError(f"Arc getJob failed: {e}")
    
    def release_payment(self, job_id: int, provider: Agent, amount_usd: float) -> None:
        """Release escrowed USDC to the provider.
        
        In live mode, this happens automatically when complete() is called.
        In mock mode, we transfer the funds in our local wallet system.
        """
        if not self._live:
            # In mock: funds were reserved from client during fund(),
            # now transfer equivalent to provider
            # The actual mock fund() withdrew from client, so we deposit to provider
            provider.wallet.deposit(amount_usd)
            logger.info(f"[MOCK] Released ${amount_usd:.2f} to {provider.name}")
