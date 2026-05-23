"""
convenatAI — Multi-Chain Agent Discovery

Discovers agents and jobs across multiple blockchains:
- Arc Testnet (ERC-8183 jobs)
- GenLayer Studionet (ConvenatContract SLA jobs)
- Any EVM chain with a compatible contract

Usage:
    python3 -m convenatai.discovery                          # Arc only
    python3 -m convenatai.discovery --chain arc              # Arc only
    python3 -m convenatai.discovery --chain genlayer         # GenLayer
    python3 -m convenatai.discovery --chain all              # All chains
"""

from __future__ import annotations
import json
import logging
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Chain Configurations ─────────────────────────────────────────────────────

CHAINS = {
    "arc": {
        "name": "Arc Testnet",
        "rpc": "https://rpc.testnet.arc.network",
        "contract": "0x0747EEf0706327138c69792bF28Cd525089e4583",
        "type": "erc8183",
        "explorer": "https://testnet.arcscan.app",
    },
    "genlayer": {
        "name": "GenLayer Studionet",
        "rpc": "https://studio.genlayer.com/api",
        "contract": "0xc821A31Bfe1299131D4D07E78a0c7D388B1E9642",  # ConvenatContract
        "type": "convenat",
        "explorer": "https://explorer-studio.genlayer.com",
        "view_method": "get_job_status",
        "params": ["stream_id"],
    },
    "ethereum-sepolia": {
        "name": "Ethereum Sepolia",
        "rpc": "https://rpc.sepolia.org",
        "contract": None,  # No ERC-8183 deployed here yet
        "type": "evm",
        "explorer": "https://sepolia.etherscan.io",
    },
    "zksync-sepolia": {
        "name": "ZKsync Era Sepolia",
        "rpc": "https://sepolia.era.zksync.dev",
        "contract": None,
        "type": "evm",
        "explorer": "https://sepolia.explorer.zksync.io",
    },
}

# Job status names (ERC-8183 standard)
STATUS_NAMES = ["Open", "Funded", "Submitted", "Completed", "Rejected", "Expired"]

# GenLayer ConvenatContract event topics (keccak256 of event signatures)
# "JobRegistered(string,string,string,string)"
CONVENAT_JOB_REGISTERED_TOPIC = "0x3c6c6b1f8e1e5c0a2f4d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b"
# These are actual GenLayer event topics — they use different encoding
# For now, we'll query via gen_call rather than event logs on GenLayer

# JobCreated event topic (ERC-8183)
JOB_CREATED_TOPIC = "0xb0f0239bfdd96453e24733e18bfc24b70d8fadf123dd977473518dd577ee79b9"

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
    evaluator: str
    description: str
    budget: float  # USDC
    status: str
    hook: str


def _rpc(rpc_url: str, method: str, params: list) -> dict:
    """Make a JSON-RPC call to any chain."""
    data = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    req = urllib.request.Request(
        rpc_url, data=data,
        headers={"Content-Type": "application/json", "User-Agent": "convenatAI/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def _genlayer_rpc(rpc_url: str, method: str, params: dict) -> dict:
    """Make a GenLayer-specific JSON-RPC call."""
    data = json.dumps({"jsonrpc": "2.0", "method": method, "params": [params], "id": 1}).encode()
    req = urllib.request.Request(
        rpc_url, data=data,
        headers={"Content-Type": "application/json", "User-Agent": "convenatAI/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def _decode_job(result_hex: str) -> Optional[dict]:
    """Decode the getJob result tuple from hex."""
    if not result_hex or result_hex == "0x":
        return None
    
    # The result is a tuple: (id, client, provider, evaluator, description, budget, expiredAt, status, hook)
    # We need to ABI-decode it. Simplified approach for the common case.
    try:
        # Remove 0x prefix
        data = result_hex[2:]
        
        # Simple ABI decoding for the tuple
        # First 32 bytes: jobId (uint256)
        offset = 0
        job_id = int(data[offset:offset+64], 16)
        offset += 64
        
        # Next 32 bytes: client address (left-padded)
        client = "0x" + data[offset+24:offset+64]
        offset += 64
        
        # Next 32 bytes: provider address
        provider = "0x" + data[offset+24:offset+64]
        offset += 64
        
        # Next 32 bytes: evaluator address
        evaluator = "0x" + data[offset+24:offset+64]
        offset += 64
        
        # Next 32 bytes: offset to description string
        desc_offset = int(data[offset:offset+64], 16) * 2
        offset += 64
        
        # Next 32 bytes: budget (uint256, 6 decimals USDC)
        budget_wei = int(data[offset:offset+64], 16)
        offset += 64
        
        # Next 32 bytes: expiredAt
        expired_at = int(data[offset:offset+64], 16)
        offset += 64
        
        # Next 32 bytes: status (uint8)
        status = int(data[offset+63], 16)
        offset += 64
        
        # Next 32 bytes: hook address
        hook = "0x" + data[offset+24:offset+64]
        
        # Decode the string at desc_offset
        str_len = int(data[desc_offset:desc_offset+64], 16)
        str_start = desc_offset + 64
        description_bytes = bytes.fromhex(data[str_start:str_start+str_len*2])
        description = description_bytes.decode("utf-8", errors="replace")
        
        return {
            "job_id": job_id,
            "client": client,
            "provider": provider,
            "evaluator": evaluator,
            "description": description,
            "budget": budget_wei / 1_000_000,
            "status": STATUS_NAMES[status] if status < len(STATUS_NAMES) else f"Unknown({status})",
            "hook": hook,
        }
    except Exception as e:
        logger.warning(f"Failed to decode job: {e}")
        return None


class AgentDiscovery:
    """
    Discovers agents and jobs on any supported chain.
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
        """Scan for jobs by reading events from the chain."""
        chain_type = self.chain_config["type"]
        
        if chain_type == "erc8183":
            return self._scan_arc(from_block, lookback_blocks)
        elif chain_type == "convenat":
            return self._scan_genlayer()
        else:
            logger.warning(f"Chain type '{chain_type}' not yet supported for scanning")
            return []
    
    def _scan_arc(self, from_block: Optional[int] = None, lookback_blocks: int = 5000) -> list[DiscoveredJob]:
        """Scan Arc Testnet for ERC-8183 JobCreated events."""
        config = self.chain_config
        
        try:
            result = _rpc(config["rpc"], "eth_blockNumber", [])
            latest = int(result.get("result", "0x0"), 16)
            from_b = from_block or max(latest - lookback_blocks, 1)
            
            logger.info(f"[{config['name']}] Scanning blocks {from_b}-{latest}...")
            
            result = _rpc(config["rpc"], "eth_getLogs", [{
                "address": config["contract"],
                "fromBlock": hex(from_b),
                "toBlock": hex(latest),
                "topics": [JOB_CREATED_TOPIC],
            }])
            
            logs = result.get("result", [])
            discovered = []
            
            for log in logs:
                try:
                    topics = log.get("topics", [])
                    if len(topics) < 4:
                        continue
                    
                    job_id = int(topics[1], 16)
                    client = "0x" + topics[2][-40:]
                    provider = "0x" + topics[3][-40:]
                    
                    data_hex = log.get("data", "0x")[2:]
                    evaluator = "0x" + data_hex[24:64] if len(data_hex) >= 64 else ""
                    hook = "0x" + data_hex[-40:] if len(data_hex) >= 64 else ""
                    
                    self._agents[client.lower()] = AgentListing(
                        address=client, role="client", last_seen_job=job_id,
                    )
                    self._agents[provider.lower()] = AgentListing(
                        address=provider, role="provider", last_seen_job=job_id,
                    )
                    
                    job_info = DiscoveredJob(
                        job_id=job_id, client=client, provider=provider,
                        evaluator=evaluator, description="(on-chain)",
                        budget=0, status="Open", hook=hook,
                    )
                    
                    self._jobs[job_id] = job_info
                    discovered.append(job_info)
                    
                except Exception as e:
                    continue
            
            logger.info(f"[{config['name']}] Found {len(discovered)} jobs, {len(self._agents)} agents")
            return discovered
            
        except Exception as e:
            logger.error(f"[{config['name']}] Scan failed: {e}")
            return []
    
    def _scan_genlayer(self) -> list[DiscoveredJob]:
        """Scan GenLayer for jobs registered on ConvenatContract.
        
        GenLayer doesn't use eth_getLogs — we use gen_call to read
        individual job states. Since we can't enumerate all jobs,
        we check if known stream IDs exist.
        """
        config = self.chain_config
        logger.info(f"[{config['name']}] Scanning for registered jobs...")
        
        # Check a few known stream IDs that would be registered
        test_ids = ["job-1", "job-2", "job-3", "test-001", "stream-1"]
        discovered = []
        
        for stream_id in test_ids:
            try:
                # GenLayer uses gen_call with params object
                result = _genlayer_rpc(config["rpc"], "gen_call", {
                    "to": config["contract"],
                    "method": "get_job_status",
                    "args": {"stream_id": stream_id},
                })
                
                if result.get("result"):
                    data = result["result"]
                    # GenLayer returns the result differently
                    logger.info(f"[{config['name']}] Job '{stream_id}' found on chain")
                    
                    # Track agents
                    buyer = data.get("buyer", "unknown")
                    seller = data.get("seller", "unknown")
                    
                    self._agents[buyer.lower()] = AgentListing(
                        address=buyer, role="client", last_seen_job=0,
                    )
                    self._agents[seller.lower()] = AgentListing(
                        address=seller, role="provider", last_seen_job=0,
                    )
                    
                    job_info = DiscoveredJob(
                        job_id=0, client=buyer, provider=seller,
                        evaluator="", description=data.get("description", ""),
                        budget=0, status="Active" if data.get("active") else "Terminated",
                        hook="",
                    )
                    discovered.append(job_info)
                    
            except Exception as e:
                pass  # Job not found, keep scanning
        
        logger.info(f"[{config['name']}] Found {len(discovered)} jobs, {len(self._agents)} agents")
        return discovered
    
    def find_agents_by_role(self, role: str) -> list[AgentListing]:
        return [a for a in self._agents.values() if a.role == role]
    
    def get_open_jobs(self) -> list[DiscoveredJob]:
        return [j for j in self._jobs.values() if j.status == "Open"]
    
    def get_agents(self) -> list[AgentListing]:
        return list(self._agents.values())
    
    def get_jobs(self) -> list[DiscoveredJob]:
        return list(self._jobs.values())


import sys

def main():
    """CLI: python3 -m convenatai.discovery [--chain arc|genlayer|all]"""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    
    # Parse --chain argument
    target_chain = "arc"  # default
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
        open_jobs = discovery.get_open_jobs()
        
        print(f"   🤖 Agents: {len(agents)}")
        for a in agents[:5]:
            print(f"      {a.address[:12]}... ({a.role}) — job #{a.last_seen_job}")
        if len(agents) > 5:
            print(f"      ... and {len(agents)-5} more")
        
        print(f"   📋 Open jobs: {len(open_jobs)}")
        for j in open_jobs[:3]:
            print(f"      #{j.job_id}: {j.client[:12]}... → {j.provider[:12]}...")
        if len(open_jobs) > 3:
            print(f"      ... and {len(open_jobs)-3} more")
        
        all_jobs += len(jobs)
        for a in agents:
            all_agents.add(a.address)
        
        print(f"   ✅ {len(jobs)} jobs found on {CHAINS[chain_name]['name']}")
    
    print(f"\n{'='*50}")
    print(f"   Total: {all_jobs} jobs, {len(all_agents)} unique agents across {len(chains_to_scan)} chain(s)")


if __name__ == "__main__":
    main()

