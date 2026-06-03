"""
convenatAI — Multi-Chain Agent Discovery

Discovers agents and jobs across supported blockchains.
Only counts jobs from our own contract address and wallet pool.
No mock/fake data — every reported job is a real on-chain event.
"""

from __future__ import annotations
import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Our Known Wallet Addresses (Circle-managed on ARC-TESTNET) ────────────────

OUR_WALLETS = {
    "0x92e9aac1ed7044487bc8d8128465c7e588d9e1b6",  # Treasury
    "0x366c3352daee2b4b0117e6bdd1ff291beafcc8ad",  # Buyer
    "0xe94a73aeb28c452fb62677184960bb831b759333",  # Seller
    "0x6c578db2034617039116f27521f748aad00f0a45",  # Extra 1
    "0x1505102c7247b0e3323e689cb5bc6a142dff4408",  # Extra 2
}

OUR_DEPLOYER = "0xF9346827f713Eb953a2e22465b9Ee91901726BDC"

# ─── Chain Configurations ─────────────────────────────────────────────────────

OUR_ARC_CONTRACT = "0xcc23aF94f43Ffcfe7348C5135B5d1Fb4e148E5f1"

CHAINS = {
    "arc": {
        "name": "Arc Testnet",
        "rpc": os.getenv("ARC_RPC_URL", "https://rpc.testnet.arc.network"),
        "contract": OUR_ARC_CONTRACT,
        "type": "erc8183",
        "explorer": "https://testnet.arcscan.app",
    },
    "genlayer": {
        "name": "GenLayer Bradbury Testnet",
        "rpc": "https://rpc-bradbury.genlayer.com",
        "contract": "0xa420275FBC13949Fd42f879A31d7B9187BD06A08",
        "type": "convenat",
        "explorer": "https://explorer-bradbury.genlayer.com",
    },
}

# Job status names (ERC-8183 standard)
STATUS_NAMES = ["Open", "Funded", "Submitted", "Completed", "Rejected", "Expired"]

# JobCreated event topic (ERC-8183)
JOB_CREATED_TOPIC = "0xb0f0239bfdd96453e24733e18bfc24b70d8fadf123dd977473518dd577ee79b9"

# IntentRegistry
INTENT_REGISTRY_CONTRACT = os.getenv("INTENT_REGISTRY_CONTRACT", "0xa46fB1a257C91F14871daf7d2011B36a210b0747")
INTENT_POSTED_TOPIC = "0x12f5796be572154adc5b6a34211aaa71985ac4e45ef29e9e671b1700d44bcc20"

# Function selectors
FUNCTIONS = {
    "createJob": "0x72c14f2f",
    "setBudget": "0x6b3e5f5a",
    "fund": "0xdb2bd708",
    "submit": "0xd4382083",
    "complete": "0xa410712d",
    "getJob": "0x1459823e",
}


@dataclass
class AgentListing:
    """An agent discovered on the network."""
    address: str
    role: str  # client or provider
    last_seen_job: int
    description: str = ""


@dataclass
class DiscoveredJob:
    """A job discovered on-chain."""
    job_id: int
    client: str
    provider: str
    description: str
    budget: float  # USDC
    status: str
    tx_hash: str = ""
    block_number: int = 0


def _rpc(rpc_url: str, method: str, params: list) -> dict:
    """Make a JSON-RPC call to any chain."""
    data = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    req = urllib.request.Request(
        rpc_url, data=data,
        headers={"Content-Type": "application/json", "User-Agent": "convenatAI/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        logger.debug(f"RPC call to {rpc_url[:50]} failed: {e}")
        return {"error": str(e)}


class AgentDiscovery:
    """
    Discovers agents and jobs on any supported chain.
    Only counts activity from our own contract address.
    """

    def __init__(self, chain: str = "arc"):
        if chain not in CHAINS:
            raise ValueError(f"Unknown chain: {chain}. Options: {list(CHAINS.keys())}")
        self.chain_config = CHAINS[chain]
        self._agents: dict[str, AgentListing] = {}
        self._jobs: dict[int, DiscoveredJob] = {}
        self._chain = chain

    @property
    def chain_name(self) -> str:
        return self.chain_config["name"]

    def scan_recent_jobs(self, from_block: Optional[int] = None, lookback_blocks: int = 5000) -> list[DiscoveredJob]:
        """Scan for jobs by reading events from OUR contract on the chain."""
        chain_type = self.chain_config["type"]

        if chain_type == "erc8183":
            jobs = self._scan_arc(from_block, lookback_blocks)
            # Also scan the IntentRegistry for posted intents
            self._scan_intent_registry(from_block, lookback_blocks)
            return jobs
        elif chain_type == "convenat":
            return self._scan_genlayer()
        else:
            logger.warning(f"Chain type '{chain_type}' not yet supported for scanning")
            return []

    def _scan_arc(self, from_block: Optional[int] = None, lookback_blocks: int = 5000) -> list[DiscoveredJob]:
        """Scan Arc Testnet for ERC-8183 JobCreated events on OUR contract.
        Falls back to checking known transaction receipts if eth_getLogs is pruned."""
        config = self.chain_config
        our_contract = config["contract"].lower()

        try:
            # Get latest block
            result = _rpc(config["rpc"], "eth_blockNumber", [])
            if "error" in result:
                logger.warning(f"[{config['name']}] RPC error: {result['error']}")
                return []
            latest = int(result.get("result", "0x0"), 16)

            # Scan in chunks of 10,000 blocks (Arc RPC limit)
            from_b = from_block or max(latest - lookback_blocks, 1)
            chunk_size = 10000
            all_logs = []

            chunk_start = from_b
            while chunk_start < latest:
                chunk_end = min(chunk_start + chunk_size, latest)
                logger.info(f"[{config['name']}] Scanning blocks {chunk_start}-{chunk_end} for contract {our_contract[:12]}...")
                result = _rpc(config["rpc"], "eth_getLogs", [{
                    "address": our_contract,
                    "fromBlock": hex(chunk_start),
                    "toBlock": hex(chunk_end),
                    "topics": [JOB_CREATED_TOPIC],
                }])
                if "error" not in result:
                    logs = result.get("result", [])
                    all_logs.extend(logs)
                else:
                    logger.warning(f"  getLogs chunk failed ({result['error']}), trying receipt fallback...")
                chunk_start = chunk_end + 1

            discovered = []
            seen_addresses = set()

            for log in all_logs:
                try:
                    topics = log.get("topics", [])
                    if len(topics) < 4:
                        continue

                    job_id = int(topics[1], 16)
                    client = "0x" + topics[2][-40:].lower()
                    provider = "0x" + topics[3][-40:].lower()
                    block_number = int(log.get("blockNumber", "0x0"), 16)
                    tx_hash = log.get("transactionHash", "")

                    # Only count this job if it involves one of OUR wallets
                    # or the deployer — ignore random testnet activity
                    if client not in OUR_WALLETS and provider not in OUR_WALLETS and client != OUR_DEPLOYER:
                        continue

                    data_hex = log.get("data", "0x")[2:]
                    description = "(on-chain job)"
                    budget = 0
                    if len(data_hex) >= 64:
                        try:
                            desc_offset = int(data_hex[:64], 16) * 2
                            desc_len = int(data_hex[desc_offset:desc_offset+64], 16) * 2
                            desc_bytes = bytes.fromhex(data_hex[desc_offset+64:desc_offset+64+desc_len])
                            description = desc_bytes.decode('utf-8', errors='replace')
                            budget_offset = desc_offset + 64 + ((desc_len + 63) // 64) * 64
                            if budget_offset + 64 <= len(data_hex):
                                budget = int(data_hex[budget_offset:budget_offset+64], 16) / 1_000_000
                        except (ValueError, IndexError):
                            pass

                    # Only add unique addresses from our own activity
                    if client not in seen_addresses:
                        self._agents[client] = AgentListing(
                            address=client, role="client", last_seen_job=job_id,
                        )
                        seen_addresses.add(client)
                    if provider not in seen_addresses and provider != "0x0000000000000000000000000000000000000000":
                        self._agents[provider] = AgentListing(
                            address=provider, role="provider", last_seen_job=job_id,
                        )
                        seen_addresses.add(provider)

                    job_info = DiscoveredJob(
                        job_id=job_id, client=client, provider=provider,
                        description=description, budget=budget,
                        status="Open", tx_hash=tx_hash, block_number=block_number,
                    )
                    self._jobs[job_id] = job_info
                    discovered.append(job_info)

                except Exception:
                    continue

            # If we found 0 jobs from logs but we know deals exist, try checking
            # the transaction receipt directly for known tx hashes
            if len(discovered) == 0 and len(all_logs) == 0:
                # Check known test transactions from Circle API
                known_txs = [
                    "0x70fb10c4aa0c3bcf32d26716d95bf27001794d7c3249a677ea80f0067aca798e",
                ]
                for tx_hash in known_txs:
                    try:
                        receipt = _rpc(config["rpc"], "eth_getTransactionReceipt", [tx_hash])
                        if "error" in receipt:
                            continue
                        r = receipt.get("result", {})
                        if not r:
                            continue
                        for log in r.get("logs", []):
                            if log.get("address", "").lower() != our_contract:
                                continue
                            topics = log.get("topics", [])
                            if len(topics) < 4:
                                continue
                            job_id = int(topics[1], 16)
                            client = "0x" + topics[2][-40:].lower()
                            provider = "0x" + topics[3][-40:].lower()
                            block_number = int(r.get("blockNumber", "0x0"), 16)
                            logger.info(f"  Found job #{job_id} from receipt: {client[:12]} → {provider[:12]} (tx: {tx_hash[:18]}...)")
                            
                            self._agents[client] = AgentListing(address=client, role="client", last_seen_job=job_id)
                            if provider != "0x0000000000000000000000000000000000000000":
                                self._agents[provider] = AgentListing(address=provider, role="provider", last_seen_job=job_id)
                            
                            job_info = DiscoveredJob(
                                job_id=job_id, client=client, provider=provider,
                                description="(on-chain deal)", budget=0,
                                status="Open", tx_hash=tx_hash, block_number=block_number,
                            )
                            self._jobs[job_id] = job_info
                            discovered.append(job_info)
                    except Exception:
                        continue

            logger.info(f"[{config['name']}] Found {len(discovered)} jobs from our contract, "
                        f"{len(self._agents)} unique agents")
            return discovered

        except Exception as e:
            logger.error(f"[{config['name']}] Scan failed: {e}")
            return []

    def _scan_intent_registry(self, from_block: Optional[int] = None, lookback_blocks: int = 5000) -> list[dict]:
        """Scan our IntentRegistry contract for IntentPosted events.
        Converts on-chain intents into the local IntentBoard format so the
        matching engine can find buyers and sellers automatically."""
        config = self.chain_config
        registry = INTENT_REGISTRY_CONTRACT

        try:
            result = _rpc(config["rpc"], "eth_blockNumber", [])
            if "error" in result:
                return []
            latest = int(result.get("result", "0x0"), 16)
            from_b = from_block or max(latest - lookback_blocks, 1)

            # Scan in chunks
            chunk_size = 10000
            all_logs = []
            chunk_start = from_b
            while chunk_start < latest:
                chunk_end = min(chunk_start + chunk_size, latest)
                result = _rpc(config["rpc"], "eth_getLogs", [{
                    "address": registry,
                    "fromBlock": hex(chunk_start),
                    "toBlock": hex(chunk_end),
                    "topics": [INTENT_POSTED_TOPIC],
                }])
                if "error" not in result:
                    all_logs.extend(result.get("result", []))
                chunk_start = chunk_end + 1

            discovered = []
            for log in all_logs:
                try:
                    topics = log.get("topics", [])
                    if len(topics) < 2:
                        continue
                    intent_id = int(topics[1], 16)
                    agent = "0x" + topics[2][-40:].lower()
                    data_hex = log.get("data", "0x")[2:]

                    # Decode: intentType (uint8), category(string), title(string),
                    # description(string), budgetMin(uint256), budgetMax(uint256)
                    # This is complex from raw hex — just log the discovery
                    # The IntentBoard stores the key info
                    intent_type = "buy" if int(data_hex[:2], 16) == 0 else "sell"

                    # Add to agents list
                    if agent not in self._agents:
                        self._agents[agent] = AgentListing(
                            address=agent,
                            role="client" if intent_type == "buy" else "provider",
                            last_seen_job=intent_id,
                            description=f"IntentRegistry intent #{intent_id}",
                        )

                    discovered.append({
                        "intent_id": intent_id,
                        "agent": agent,
                        "type": intent_type,
                        "tx_hash": log.get("transactionHash", ""),
                    })
                    logger.info(f"  📋 Intent #{intent_id}: {agent[:12]}... wants to {intent_type}")

                except Exception:
                    continue

            if discovered:
                logger.info(f"[IntentRegistry] Found {len(discovered)} intents from {registry[:12]}...")
            return discovered

        except Exception as e:
            logger.debug(f"[IntentRegistry] scan failed: {e}")
            return []

    def _scan_genlayer(self) -> list[DiscoveredJob]:
        """Scan GenLayer for jobs registered on our ConvenatContract.
        
        Uses gen_call with get_job_status for known stream IDs from our deals.
        """
        config = self.chain_config
        logger.info(f"[{config['name']}] Scanning for registered jobs...")
        
        # Check known stream IDs that would be registered from our deal pipeline
        # These stream IDs come from the auto-matching system
        discovered = []
        
        # We check a few common patterns — real stream IDs are created 
        # dynamically when deals are registered via register_job()
        # The backend passes them, we just discover what's on-chain
        test_ids = [f"stream-{i}" for i in range(1, 20)]
        test_ids += [f"deal-{h}" for h in ["c362fe5501b5", "c07148c92974", "e7d5b43a0952"]]
        
        for stream_id in test_ids:
            try:
                # GenLayer uses gen_call for view methods
                payload = json.dumps({
                    "jsonrpc": "2.0",
                    "method": "gen_call",
                    "params": [{
                        "to": config["contract"],
                        "method": "get_job_status",
                        "args": {"stream_id": stream_id},
                    }],
                    "id": 1,
                }).encode()
                req = urllib.request.Request(
                    config["rpc"], data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    raw = json.loads(resp.read().decode())
                    
                if raw.get("result"):
                    data = raw["result"]
                    logger.info(f"[{config['name']}] Job '{stream_id}' found on chain")
                    
                    buyer = data.get("buyer", "unknown")
                    seller = data.get("seller", "unknown")
                    
                    # Track agents
                    if buyer not in self._agents:
                        self._agents[buyer] = AgentListing(address=buyer, role="client", last_seen_job=0)
                    if seller not in self._agents:
                        self._agents[seller] = AgentListing(address=seller, role="provider", last_seen_job=0)
                    
                    job_info = DiscoveredJob(
                        job_id=0, client=buyer, provider=seller,
                        description=data.get("description", ""),
                        budget=0, status="Active" if data.get("active") else "Terminated",
                        tx_hash="genlayer",
                    )
                    discovered.append(job_info)
                    
            except Exception:
                pass  # Job not found, keep scanning
        
        logger.info(f"[{config['name']}] Found {len(discovered)} jobs, {len(self._agents)} agents")
        return discovered

    def get_agents(self) -> list[AgentListing]:
        return list(self._agents.values())

    def get_jobs(self) -> list[DiscoveredJob]:
        return list(self._jobs.values())


import sys

def main():
    """CLI: python3 -m convenatai.discovery [--chain arc|genlayer|all]"""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    
    target_chain = "arc"
    if "--chain" in sys.argv:
        idx = sys.argv.index("--chain")
        if idx + 1 < len(sys.argv):
            target_chain = sys.argv[idx + 1]
    
    chains_to_scan = list(CHAINS.keys()) if target_chain == "all" else [target_chain]
    
    all_jobs = 0
    all_agents = set()
    
    for chain_name in chains_to_scan:
        if chain_name not in CHAINS:
            print(f"❌ Unknown chain: {chain_name}")
            continue
        
        print(f"\n🔍 [{CHAINS[chain_name]['name']}] Scanning...\n")
        
        discovery = AgentDiscovery(chain=chain_name)
        jobs = discovery.scan_recent_jobs(lookback_blocks=5000)
        agents = discovery.get_agents()
        
        print(f"   🤖 Agents: {len(agents)}")
        for a in agents[:5]:
            print(f"      {a.address[:12]}... ({a.role}) — job #{a.last_seen_job}")
        if len(agents) > 5:
            print(f"      ... and {len(agents)-5} more")
        
        print(f"   📋 Jobs found: {len(jobs)}")
        for j in jobs[:3]:
            print(f"      #{j.job_id}: {j.client[:12]}... → {j.provider[:12]}... (${j.budget})")
        if len(jobs) > 3:
            print(f"      ... and {len(jobs)-3} more")
        
        all_jobs += len(jobs)
        for a in agents:
            all_agents.add(a.address)
        
        print(f"   ✅ {len(jobs)} jobs found on {CHAINS[chain_name]['name']}")
    
    print(f"\n{'='*50}")
    print(f"   Total: {all_jobs} jobs, {len(all_agents)} unique agents across {len(chains_to_scan)} chain(s)")


if __name__ == "__main__":
    main()
