"""
convenatAI — Circle REST API Client (lightweight, no SDK required)

Replaces the `circle-developer-controlled-wallets` pip package with
direct HTTP calls to the Circle Developer-Controlled Wallets API.

API Docs: https://developers.circle.com/wallets/api-reference
"""

from __future__ import annotations
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

CIRCLE_API_BASE = "https://api.circle.com/v1/w3s"
CIRCLE_DEV_BASE = "https://api.circle.com/v1/w3s/developer"

# ─── Configuration ────────────────────────────────────────────────────────────

HAS_CIRCLE = bool(os.getenv("CIRCLE_API_KEY") and os.getenv("CIRCLE_ENTITY_SECRET"))

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _api_key() -> str:
    return os.environ.get("CIRCLE_API_KEY", "")

def _headers() -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_api_key()}",
        "User-Agent": "convenatAI/1.0",
        "Accept": "application/json",
    }

def _api_post(path: str, body: dict, use_dev_base: bool = False) -> dict:
    """Make a POST request to the Circle API."""
    base = CIRCLE_DEV_BASE if use_dev_base else CIRCLE_API_BASE
    url = f"{base}{path}"
    data = json.dumps(body).encode()
    req = Request(url, data=data, headers=_headers(), method="POST")
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        err_body = e.read().decode() if e.fp else ""
        logger.error(f"Circle API error {e.code}: {err_body}")
        raise RuntimeError(f"Circle API error {e.code}: {err_body}")
    except URLError as e:
        logger.error(f"Circle network error: {e.reason}")
        raise RuntimeError(f"Circle network error: {e.reason}")


def _api_get(path: str) -> dict:
    """Make a GET request to the Circle API."""
    url = f"{CIRCLE_API_BASE}{path}"
    req = Request(url, headers=_headers(), method="GET")
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        err_body = e.read().decode() if e.fp else ""
        raise RuntimeError(f"Circle API error {e.code}: {err_body}")
    except URLError as e:
        raise RuntimeError(f"Circle network error: {e.reason}")


# ─── Wallet Management ───────────────────────────────────────────────────────

@dataclass
class CircleWallet:
    wallet_id: str
    address: str
    blockchain: str
    account_type: str


def create_wallet_set(name: str = "convenatAI Agent Wallets") -> str:
    """Create a wallet set and return its ID."""
    result = _api_post("/wallets/sets", {
        "entitySecret": os.environ["CIRCLE_ENTITY_SECRET"],
        "name": name,
    })
    wallet_set_id = result["data"]["walletSet"]["id"]
    logger.info(f"WalletSet created: {wallet_set_id}")
    return wallet_set_id


def create_wallets(
    count: int = 2,
    blockchain: str = "ARC-TESTNET",
    wallet_set_id: Optional[str] = None,
) -> list[CircleWallet]:
    """Create developer-controlled wallets on Arc Testnet."""
    if not wallet_set_id:
        wallet_set_id = create_wallet_set()

    result = _api_post("/wallets", {
        "entitySecret": os.environ["CIRCLE_ENTITY_SECRET"],
        "blockchains": [blockchain],
        "count": count,
        "walletSetId": wallet_set_id,
        "accountType": "SCA",
    })

    wallets_data = result["data"]["wallets"]
    wallets = []
    for w in wallets_data:
        wallet = CircleWallet(
            wallet_id=w["id"],
            address=w["address"],
            blockchain=w["blockchain"],
            account_type=w.get("accountType", "SCA"),
        )
        wallets.append(wallet)
        logger.info(f"Wallet created: {wallet.address} ({wallet.wallet_id})")
    return wallets


def get_wallet_balance(wallet_id: str) -> float:
    """Get USDC balance for a wallet (returns in USDC dollars)."""
    try:
        result = _api_get(f"/wallets/{wallet_id}/balances")
        for balance in result["data"].get("tokenBalances", []):
            if balance.get("token", {}).get("symbol") == "USDC":
                # Amount is in atomic units (6 decimals for USDC)
                atomic = int(balance["amount"])
                return atomic / 1_000_000
        return 0.0
    except Exception as e:
        logger.warning(f"Could not fetch balance for {wallet_id}: {e}")
        return 0.0


def list_wallets() -> list[CircleWallet]:
    """List all wallets in this account."""
    result = _api_get("/wallets")
    wallets = []
    for w in result["data"].get("wallets", []):
        wallets.append(CircleWallet(
            wallet_id=w["id"],
            address=w["address"],
            blockchain=w["blockchain"],
            account_type=w.get("accountType", "SCA"),
        ))
    return wallets


# ─── Contract Execution ──────────────────────────────────────────────────────

# Entity secret ciphertext cache (fetch public key once, cache encryption)
_entity_secret_ciphertext: str | None = None


def _entity_secret_pubkey() -> str:
    """Fetch the Circle entity public key for RSA-OAEP encryption."""
    try:
        result = _api_get("/config/entity/publicKey")
        key_data = result.get("data", {})
        pubkey_str = key_data.get("publicKey")
        if pubkey_str:
            return pubkey_str
        raise RuntimeError(f"No publicKey in response: {result}")
    except Exception as e:
        raise RuntimeError(f"Failed to fetch Circle public key: {e}")


def _encrypt_entity_secret(entity_secret: str, pubkey_pem: str) -> str:
    """
    Encrypt the entity secret with RSA-OAEP SHA-256 as required by Circle API.
    Returns base64-encoded ciphertext.
    """
    import base64
    try:
        from cryptography.hazmat.primitives.asymmetric import padding, rsa
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.backends import default_backend
    except ImportError:
        raise RuntimeError(
            "cryptography package required for on-chain operations. "
            "Install: pip install cryptography"
        )

    pubkey = serialization.load_pem_public_key(pubkey_pem.encode(), backend=default_backend())
    ciphertext = pubkey.encrypt(
        entity_secret.encode(),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return base64.b64encode(ciphertext).decode()


def _get_entity_secret_ciphertext() -> str:
    """Get (and cache) the encrypted entity secret."""
    global _entity_secret_ciphertext
    if _entity_secret_ciphertext:
        return _entity_secret_ciphertext
    entity_secret = os.environ.get("CIRCLE_ENTITY_SECRET", "")
    if not entity_secret:
        raise RuntimeError("CIRCLE_ENTITY_SECRET not set")
    pubkey_pem = _entity_secret_pubkey()
    _entity_secret_ciphertext = _encrypt_entity_secret(entity_secret, pubkey_pem)
    return _entity_secret_ciphertext


def _node_bridge(action: str, args: dict = None) -> dict:
    """Call the Node.js bridge script for Circle operations that need the SDK."""
    import json
    import os
    import shutil
    import subprocess

    # Find node executable in common locations
    node_path = None
    for candidate in ["node", "/usr/bin/node", "/usr/local/bin/node"]:
        p = shutil.which(candidate) or (candidate if os.path.exists(candidate) else None)
        if p:
            node_path = p
            break
    if not node_path:
        raise RuntimeError("Node.js not available")

    # Find circle_executor.js
    script_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
    script_path = os.path.join(script_dir, "circle_executor.js")
    if not os.path.exists(script_path):
        script_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts", "circle_executor.js"
        )

    cmd = [node_path, script_path, action, json.dumps(args or {})]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            err = proc.stderr.strip() or proc.stdout.strip()
            raise RuntimeError(f"Node bridge error: {err}")
        return json.loads(proc.stdout.strip())
    except json.JSONDecodeError:
        raise RuntimeError(f"Node bridge invalid JSON: {proc.stdout[:500]}")
    except FileNotFoundError:
        raise RuntimeError("Node.js not found")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Node bridge timed out")


def create_contract_execution_transaction(
    wallet_address: str,
    contract_address: str,
    abi_function_signature: str,
    abi_parameters: list[str],
    fee_level: str = "MEDIUM",
) -> dict:
    """
    Execute a contract function via Circle Developer-Controlled Wallets API.
    Uses RSA-OAEP encrypted entity secret for authentication.
    Returns dict with 'id' (transaction ID) and 'state'.

    Falls back to Node.js bridge if cryptography package is not available.
    """
    import uuid
    idempotency_key = str(uuid.uuid4())

    # Try pure Python REST first (no Node.js dependency)
    try:
        ciphertext = _get_entity_secret_ciphertext()
        result = _api_post("/transactions/contractExecution", {
            "idempotencyKey": idempotency_key,
            "entitySecretCiphertext": ciphertext,
            "walletAddress": wallet_address,
            "blockchain": "ARC-TESTNET",
            "contractAddress": contract_address,
            "abiFunctionSignature": abi_function_signature,
            "abiParameters": abi_parameters,
            "fee": {
                "type": "level",
                "config": {"feeLevel": fee_level},
            },
        })
        tx_id = result["data"]["id"]
        logger.info(f"Transaction submitted (REST): {tx_id}")
        return {"id": tx_id, "state": "pending"}
    except ImportError:
        logger.warning("cryptography not installed, trying Node.js bridge...")
    except Exception as e:
        logger.warning(f"REST approach failed ({e}), trying Node.js bridge...")

    # Fallback: Node.js bridge
    try:
        result = _node_bridge("contract-execution", {
            "walletAddress": wallet_address,
            "contractAddress": contract_address,
            "abiFunctionSignature": abi_function_signature,
            "abiParameters": abi_parameters,
            "feeLevel": fee_level,
            "idempotencyKey": idempotency_key,
        })
        tx_id = result.get("id", "unknown")
        logger.info(f"Transaction submitted (Node): {tx_id}")
        return {"id": tx_id, "state": "pending"}
    except Exception as e:
        raise RuntimeError(f"Arc contract execution failed (both REST and Node bridge): {e}")


def get_transaction_status(tx_id: str) -> dict:
    """Poll transaction status."""
    result = _api_get(f"/transactions/{tx_id}")
    return result["data"]


# ─── ERC-8183 Convenience Methods ────────────────────────────────────────────

AGENTIC_COMMERCE_CONTRACT = "0x0747EEf0706327138c69792bF28Cd525089e4583"
USDC_ERC20_CONTRACT = "0x3600000000000000000000000000000000000000"


def erc8183_create_job(
    wallet_address: str,
    provider: str,
    evaluator: str,
    description: str,
    hook: str = "0x0000000000000000000000000000000000000000",
    expired_at: Optional[int] = None,
) -> str:
    """Create an ERC-8183 job on Arc Testnet. Returns tx ID."""
    if expired_at is None:
        expired_at = int(time.time()) + 7 * 24 * 3600  # 7 days
    return create_contract_execution_transaction(
        wallet_address=wallet_address,
        contract_address=AGENTIC_COMMERCE_CONTRACT,
        abi_function_signature="createJob(address,address,uint256,string,address)",
        abi_parameters=[provider, evaluator, str(expired_at), description, hook],
    )


def erc8183_set_budget(wallet_address: str, job_id: int, amount_usdc: float) -> str:
    """Set budget for an ERC-8183 job. Returns tx ID."""
    amount_wei = int(amount_usdc * 1_000_000)  # 6 decimals
    return create_contract_execution_transaction(
        wallet_address=wallet_address,
        contract_address=AGENTIC_COMMERCE_CONTRACT,
        abi_function_signature="setBudget(uint256,uint256,bytes)",
        abi_parameters=[str(job_id), str(amount_wei), "0x"],
    )


def erc8183_approve_usdc(wallet_address: str, amount_usdc: float) -> str:
    """Approve USDC spending by the ERC-8183 contract. Returns tx ID."""
    amount_wei = int(amount_usdc * 1_000_000)
    return create_contract_execution_transaction(
        wallet_address=wallet_address,
        contract_address=USDC_ERC20_CONTRACT,
        abi_function_signature="approve(address,uint256)",
        abi_parameters=[AGENTIC_COMMERCE_CONTRACT, str(amount_wei)],
    )


def erc8183_fund_job(wallet_address: str, job_id: int) -> str:
    """Fund escrow for an ERC-8183 job. Returns tx ID."""
    return create_contract_execution_transaction(
        wallet_address=wallet_address,
        contract_address=AGENTIC_COMMERCE_CONTRACT,
        abi_function_signature="fund(uint256,bytes)",
        abi_parameters=[str(job_id), "0x"],
    )


def erc8183_submit_deliverable(
    wallet_address: str,
    job_id: int,
    deliverable_hash: str,
) -> str:
    """Submit a deliverable hash for an ERC-8183 job. Returns tx ID."""
    return create_contract_execution_transaction(
        wallet_address=wallet_address,
        contract_address=AGENTIC_COMMERCE_CONTRACT,
        abi_function_signature="submit(uint256,bytes32,bytes)",
        abi_parameters=[str(job_id), deliverable_hash, "0x"],
    )


def erc8183_complete_job(
    wallet_address: str,
    job_id: int,
    reason_hash: str,
) -> str:
    """Complete an ERC-8183 job. Returns tx ID."""
    return create_contract_execution_transaction(
        wallet_address=wallet_address,
        contract_address=AGENTIC_COMMERCE_CONTRACT,
        abi_function_signature="complete(uint256,bytes32,bytes)",
        abi_parameters=[str(job_id), reason_hash, "0x"],
    )


# ─── Self-test ───────────────────────────────────────────────────────────────

def check_connection() -> dict:
    """Test connection to Circle API. Returns account info if successful."""
    try:
        result = _api_get("/wallets")
        return {"connected": True, "wallet_count": len(result["data"].get("wallets", []))}
    except Exception as e:
        return {"connected": False, "error": str(e)}
