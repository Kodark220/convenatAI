"""
convenatAI — ERC-8004 Identity Registries Integration

Integrates with three deployed registries on Arc Testnet:
  IdentityRegistry:    0x8004A818BFB912233c491871b3d84c89A494BD9e
  ReputationRegistry:  0x8004B663056A597Dffe9eCcC1965A193B7388713
  ValidationRegistry:  0x8004Cb1BF31DAf7788923b405b754f57acEB4272

Two modes:
  - LIVE: Uses Circle Developer-Controlled Wallets API + Arc RPC
  - LOCAL MOCK: Falls back to in-memory identity store for dev/testing

Usage:
    from .arc_identity import ArcIdentityManager

    mgr = ArcIdentityManager()
    mgr.register_agent_identity(agent, "ipfs://QmExample...")
    info = mgr.get_agent_identity("0x...")
    balance = mgr.get_agent_reputation("0x...")
    is_valid = mgr.validate_agent("0x...")
"""

from __future__ import annotations
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

from .agent import Agent, HAS_CIRCLE
from .circle_client import create_contract_execution_transaction, list_wallets, get_wallet_balance

load_dotenv()

# CIRCLE_READY: True when both Circle API key and entity secret are set
CIRCLE_READY = bool(os.getenv("CIRCLE_API_KEY") and os.getenv("CIRCLE_ENTITY_SECRET"))

logger = logging.getLogger(__name__)

# ─── ERC-8004 Registry Addresses (Arc Testnet) ──────────────────────────────

IDENTITY_REGISTRY = "0x8004A818BFB912233c491871b3d84c89A494BD9e"
REPUTATION_REGISTRY = "0x8004B663056A597Dffe9eCcC1965A193B7388713"
VALIDATION_REGISTRY = "0x8004Cb1BF31DAf7788923b405b754f57acEB4272"

ARC_TESTNET_CHAIN = "ARC-TESTNET"

# ─── ERC-8004 ABI (minimal — functions we call) ────────────────────────────

IDENTITY_ABI = [
    # register(string) — register identity with metadata URI
    {
        "type": "function",
        "name": "register",
        "stateMutability": "nonpayable",
        "inputs": [{"name": "metadataUri", "type": "string"}],
        "outputs": [],
    },
    # register(identity, metadataUri) — register identity with address + URI
    {
        "type": "function",
        "name": "register",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "identity", "type": "address"},
            {"name": "metadataUri", "type": "string"},
        ],
        "outputs": [],
    },
    # getIdentity(address) → tuple(address identity, string metadataUri, uint256 registeredAt)
    {
        "type": "function",
        "name": "getIdentity",
        "stateMutability": "view",
        "inputs": [{"name": "agent", "type": "address"}],
        "outputs": [
            {"name": "identity", "type": "address"},
            {"name": "metadataUri", "type": "string"},
            {"name": "registeredAt", "type": "uint256"},
        ],
    },
    # isRegistered(address) → bool
    {
        "type": "function",
        "name": "isRegistered",
        "stateMutability": "view",
        "inputs": [{"name": "agent", "type": "address"}],
        "outputs": [{"name": "", "type": "bool"}],
    },
]

REPUTATION_ABI = [
    # getReputation(address) → uint256 (reputation score)
    {
        "type": "function",
        "name": "getReputation",
        "stateMutability": "view",
        "inputs": [{"name": "agent", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    # updateReputation(address, uint256) — only callable by authorized
    {
        "type": "function",
        "name": "updateReputation",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "agent", "type": "address"},
            {"name": "score", "type": "uint256"},
        ],
        "outputs": [],
    },
]

VALIDATION_ABI = [
    # validate(address) → bool
    {
        "type": "function",
        "name": "validate",
        "stateMutability": "view",
        "inputs": [{"name": "agent", "type": "address"}],
        "outputs": [{"name": "", "type": "bool"}],
    },
    # setValid(address, bool) — only callable by authorized
    {
        "type": "function",
        "name": "setValid",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "agent", "type": "address"},
            {"name": "valid", "type": "bool"},
        ],
        "outputs": [],
    },
]


# ─── Web3 helper (optional) ────────────────────────────────────────────────

def _get_web3():
    """Get a Web3 instance connected to Arc Testnet, or None if web3 not installed."""
    try:
        from web3 import Web3
        rpc = os.getenv("ARC_RPC_URL", "https://rpc.testnet.arc.network")
        w3 = Web3(Web3.HTTPProvider(rpc))
        return w3
    except ImportError:
        return None


# ─── Data classes ──────────────────────────────────────────────────────────

@dataclass
class IdentityInfo:
    address: str
    metadata_uri: str
    registered_at: int  # unix timestamp
    registered: bool = False


@dataclass
class ReputationInfo:
    address: str
    score: int  # reputation score (0-100 or similar)
    onchain: bool = False


@dataclass
class ValidationInfo:
    address: str
    is_valid: bool
    onchain: bool = False


# ─── ArcIdentityManager ────────────────────────────────────────────────────

class ArcIdentityManager:
    """Manages ERC-8004 identity, reputation, and validation registries.

    In live mode, calls the real registries via Circle API or Web3.
    In mock mode, simulates registries in-memory.
    """

    def __init__(self, use_live: Optional[bool] = None):
        """
        Args:
            use_live: True for on-chain Arc, False for mock.
                      Default: auto-detect from CIRCLE_API_KEY + CIRCLE_ENTITY_SECRET.
        """
        if use_live is None:
            use_live = CIRCLE_READY

        self._live = use_live
        self._web3 = _get_web3()

        # Mock state
        self._mock_identities: dict[str, IdentityInfo] = {}
        self._mock_reputations: dict[str, ReputationInfo] = {}
        self._mock_validations: dict[str, ValidationInfo] = {}

        if self._live and not CIRCLE_READY:
            logger.warning("Live mode requested but Circle API not configured. Falling back to mock.")
            self._live = False

    @property
    def is_live(self) -> bool:
        return self._live

    # ─── Identity Registry ──────────────────────────────────────────────────

    def register_agent_identity(
        self,
        agent: Agent,
        metadata_uri: str = "",
    ) -> dict:
        """Register an agent's identity on the ERC-8004 IdentityRegistry.

        Args:
            agent: The agent to register (must have wallet.address).
            metadata_uri: URI pointing to agent metadata (e.g. IPFS, HTTPS).

        Returns:
            dict with registration result.
        """
        address = agent.wallet.address or agent.name
        if not metadata_uri:
            metadata_uri = f"did:convenatai:{agent.name}:{agent.role}"

        logger.info(
            f"Registering identity for {agent.name} ({address}) "
            f"with metadata: {metadata_uri}"
        )

        if self._live:
            return self._register_identity_onchain(agent, metadata_uri)
        else:
            return self._register_identity_mock(address, metadata_uri)

    def _register_identity_mock(self, address: str, metadata_uri: str) -> dict:
        """Mock registration — store in-memory."""
        self._mock_identities[address] = IdentityInfo(
            address=address,
            metadata_uri=metadata_uri,
            registered_at=int(time.time()),
            registered=True,
        )
        logger.info(f"[MOCK] Identity registered for {address}: {metadata_uri}")
        return {
            "status": "registered",
            "address": address,
            "metadata_uri": metadata_uri,
        }

    def _register_identity_onchain(self, agent: Agent, metadata_uri: str) -> dict:
        """Call register() on the real IdentityRegistry via Circle API."""
        logger.info(f"Registering identity on-chain for {agent.wallet.address}...")
        try:
            result = create_contract_execution_transaction(
                wallet_address=agent.wallet.address,
                contract_address=IDENTITY_REGISTRY,
                abi_function_signature="register(string)",
                abi_parameters=[metadata_uri],
            )
            tx_id = result.get("id", "unknown")
            logger.info(f"Identity registration tx submitted: {tx_id}")
            return {
                "status": "registered",
                "tx_id": tx_id,
                "address": agent.wallet.address,
                "metadata_uri": metadata_uri,
            }
        except Exception as e:
            logger.error(f"Identity registration on-chain failed: {e}")
            # Fallback to mock if on-chain fails
            logger.warning("Falling back to mock identity registration")
            return self._register_identity_mock(agent.wallet.address or agent.name, metadata_uri)

    def get_agent_identity(self, address: str) -> IdentityInfo:
        """Query identity info for an agent address from IdentityRegistry.

        Returns IdentityInfo with registration details.
        """
        if self._live and self._web3:
            return self._get_identity_onchain(address)
        else:
            return self._get_identity_mock(address)

    def _get_identity_mock(self, address: str) -> IdentityInfo:
        info = self._mock_identities.get(address)
        if info is None:
            return IdentityInfo(
                address=address,
                metadata_uri="",
                registered_at=0,
                registered=False,
            )
        return info

    def _get_identity_onchain(self, address: str) -> IdentityInfo:
        """Read identity from on-chain IdentityRegistry via Web3."""
        try:
            contract = self._web3.eth.contract(
                address=self._web3.to_checksum_address(IDENTITY_REGISTRY),
                abi=[a for a in IDENTITY_ABI if a["stateMutability"] == "view"],
            )
            result = contract.functions.getIdentity(address).call()
            return IdentityInfo(
                address=result[0],
                metadata_uri=result[1],
                registered_at=result[2],
                registered=True,
            )
        except Exception as e:
            logger.error(f"getIdentity on-chain failed: {e}")
            # Fallback to mock
            return self._get_identity_mock(address)

    def is_agent_registered(self, address: str) -> bool:
        """Check if an agent address is registered on the IdentityRegistry."""
        info = self.get_agent_identity(address)
        return info.registered

    # ─── Reputation Registry ────────────────────────────────────────────────

    def get_agent_reputation(self, address: str) -> ReputationInfo:
        """Query reputation score from ReputationRegistry."""
        if self._live and self._web3:
            return self._get_reputation_onchain(address)
        else:
            return self._get_reputation_mock(address)

    def _get_reputation_mock(self, address: str) -> ReputationInfo:
        info = self._mock_reputations.get(address)
        if info is None:
            return ReputationInfo(address=address, score=0, onchain=False)
        return info

    def _get_reputation_onchain(self, address: str) -> ReputationInfo:
        try:
            contract = self._web3.eth.contract(
                address=self._web3.to_checksum_address(REPUTATION_REGISTRY),
                abi=[a for a in REPUTATION_ABI if a["stateMutability"] == "view"],
            )
            score = contract.functions.getReputation(address).call()
            return ReputationInfo(address=address, score=score, onchain=True)
        except Exception as e:
            logger.error(f"getReputation on-chain failed: {e}")
            return self._get_reputation_mock(address)

    def update_agent_reputation(
        self,
        caller: Agent,
        target_address: str,
        score: int,
    ) -> dict:
        """Update reputation score for an agent (authorized caller only)."""
        if self._live:
            return self._update_reputation_onchain(caller, target_address, score)
        else:
            return self._update_reputation_mock(target_address, score)

    def _update_reputation_mock(self, target_address: str, score: int) -> dict:
        self._mock_reputations[target_address] = ReputationInfo(
            address=target_address,
            score=score,
            onchain=False,
        )
        logger.info(f"[MOCK] Reputation updated for {target_address}: {score}")
        return {"status": "updated", "address": target_address, "score": score}

    def _update_reputation_onchain(self, caller: Agent, target_address: str, score: int) -> dict:
        try:
            result = create_contract_execution_transaction(
                wallet_address=caller.wallet.address,
                contract_address=REPUTATION_REGISTRY,
                abi_function_signature="updateReputation(address,uint256)",
                abi_parameters=[target_address, str(score)],
            )
            tx_id = result.get("id", "unknown")
            logger.info(f"Reputation update tx submitted: {tx_id}")
            return {"status": "updated", "tx_id": tx_id, "address": target_address, "score": score}
        except Exception as e:
            logger.error(f"Reputation update on-chain failed: {e}")
            return self._update_reputation_mock(target_address, score)

    # ─── Validation Registry ────────────────────────────────────────────────

    def validate_agent(self, address: str) -> ValidationInfo:
        """Check if an agent is validated on the ValidationRegistry."""
        if self._live and self._web3:
            return self._validate_onchain(address)
        else:
            return self._validate_mock(address)

    def _validate_mock(self, address: str) -> ValidationInfo:
        info = self._mock_validations.get(address)
        if info is None:
            # In mock mode, all registered agents are considered valid
            is_valid = self.is_agent_registered(address)
            return ValidationInfo(address=address, is_valid=is_valid, onchain=False)
        return info

    def _validate_onchain(self, address: str) -> ValidationInfo:
        try:
            contract = self._web3.eth.contract(
                address=self._web3.to_checksum_address(VALIDATION_REGISTRY),
                abi=[a for a in VALIDATION_ABI if a["stateMutability"] == "view"],
            )
            is_valid = contract.functions.validate(address).call()
            return ValidationInfo(address=address, is_valid=is_valid, onchain=True)
        except Exception as e:
            logger.error(f"validate on-chain failed: {e}")
            return self._validate_mock(address)

    def set_agent_validation(
        self,
        caller: Agent,
        target_address: str,
        valid: bool,
    ) -> dict:
        """Set validation status for an agent (authorized caller only)."""
        if self._live:
            return self._set_validation_onchain(caller, target_address, valid)
        else:
            return self._set_validation_mock(target_address, valid)

    def _set_validation_mock(self, target_address: str, valid: bool) -> dict:
        self._mock_validations[target_address] = ValidationInfo(
            address=target_address,
            is_valid=valid,
            onchain=False,
        )
        logger.info(f"[MOCK] Validation set for {target_address}: valid={valid}")
        return {"status": "updated", "address": target_address, "valid": valid}

    def _set_validation_onchain(self, caller: Agent, target_address: str, valid: bool) -> dict:
        try:
            result = create_contract_execution_transaction(
                wallet_address=caller.wallet.address,
                contract_address=VALIDATION_REGISTRY,
                abi_function_signature="setValid(address,bool)",
                abi_parameters=[target_address, str(valid).lower()],
            )
            tx_id = result.get("id", "unknown")
            logger.info(f"Validation set tx submitted: {tx_id}")
            return {"status": "updated", "tx_id": tx_id, "address": target_address, "valid": valid}
        except Exception as e:
            logger.error(f"Validation set on-chain failed: {e}")
            return self._set_validation_mock(target_address, valid)

    # ─── Batch utilities ────────────────────────────────────────────────────

    def register_agents_auto(self, agents: list[Agent]) -> list[dict]:
        """Register multiple agents in batch.

        Only registers agents that aren't already registered.
        Returns list of registration results.
        """
        results = []
        for agent in agents:
            addr = agent.wallet.address or agent.name
            if self.is_agent_registered(addr):
                logger.info(f"{agent.name} ({addr}) already registered, skipping")
                results.append({
                    "status": "already_registered",
                    "address": addr,
                })
            else:
                metadata = f"did:convenatai:{agent.name}:{agent.role}"
                result = self.register_agent_identity(agent, metadata)
                results.append(result)
        return results

    def get_full_profile(self, address: str) -> dict:
        """Get full identity, reputation, and validation info for an address."""
        identity = self.get_agent_identity(address)
        reputation = self.get_agent_reputation(address)
        validation = self.validate_agent(address)

        return {
            "address": address,
            "identity": {
                "metadata_uri": identity.metadata_uri,
                "registered_at": identity.registered_at,
                "registered": identity.registered,
            },
            "reputation": {
                "score": reputation.score,
                "onchain": reputation.onchain,
            },
            "validation": {
                "is_valid": validation.is_valid,
                "onchain": validation.onchain,
            },
        }
