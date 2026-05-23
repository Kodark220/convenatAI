"""
convenatAI — Circle Transaction Executor (Node.js Bridge)

Uses the Node.js Circle SDK to execute transactions since the Python SDK
has dependency issues and the raw API requires entity secret encryption.

This module shells out to Node.js when needed.
"""

from __future__ import annotations
import json
import logging
import os
import subprocess
import sys
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ─── Configuration ───────────────────────────────────────────────────────────

HAS_CIRCLE = bool(os.getenv("CIRCLE_API_KEY") and os.getenv("CIRCLE_ENTITY_SECRET"))

_SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts")
_EXECUTOR_SCRIPT = os.path.join(_SCRIPTS_DIR, "circle_executor.js")


# ─── Node.js Bridge ─────────────────────────────────────────────────────────

def _ensure_executor_script():
    """Create the Node.js executor script if it doesn't exist."""
    if os.path.exists(_EXECUTOR_SCRIPT):
        return
    
    os.makedirs(os.path.dirname(_EXECUTOR_SCRIPT), exist_ok=True)
    
    script_content = r'''const { initiateDeveloperControlledWalletsClient } = require('@circle-fin/developer-controlled-wallets');

const API_KEY = process.env.CIRCLE_API_KEY;
const ENTITY_SECRET = process.env.CIRCLE_ENTITY_SECRET;

if (!API_KEY || !ENTITY_SECRET) {
  console.error(JSON.stringify({ error: 'Missing CIRCLE_API_KEY or CIRCLE_ENTITY_SECRET' }));
  process.exit(1);
}

const client = initiateDeveloperControlledWalletsClient({
  apiKey: API_KEY,
  entitySecret: ENTITY_SECRET,
});

async function main() {
  const action = process.argv[2];
  const args = JSON.parse(process.argv[3] || '{}');

  try {
    let result;

    switch (action) {
      case 'list-wallets': {
        const wallets = await client.listWallets({});
        result = wallets.data?.wallets ?? [];
        break;
      }

      case 'create-wallet-set': {
        const ws = await client.createWalletSet({
          name: args.name || 'convenatAI Agent Wallets',
        });
        result = { id: ws.data?.walletSet?.id };
        break;
      }

      case 'create-wallets': {
        const count = args.count || 1;
        const wsId = args.walletSetId;
        
        if (!wsId) {
          const ws = await client.createWalletSet({
            name: args.name || 'convenatAI Agent Wallets',
          });
          args.walletSetId = ws.data?.walletSet?.id;
        }

        const wallets = await client.createWallets({
          blockchains: ['ARC-TESTNET'],
          count: count,
          walletSetId: args.walletSetId,
          accountType: 'SCA',
        });
        result = wallets.data?.wallets?.map(w => ({
          id: w.id,
          address: w.address,
          blockchain: w.blockchain,
          accountType: w.accountType,
        })) ?? [];
        break;
      }

      case 'contract-execution': {
        const tx = await client.createContractExecutionTransaction({
          walletAddress: args.walletAddress,
          blockchain: 'ARC-TESTNET',
          contractAddress: args.contractAddress,
          abiFunctionSignature: args.abiFunctionSignature,
          abiParameters: args.abiParameters,
          fee: { type: 'level', config: { feeLevel: args.feeLevel || 'MEDIUM' } },
        });
        result = { id: tx.data?.id, state: tx.data?.state };
        break;
      }

      case 'get-balance': {
        const walletId = args.walletId;
        const balances = await client.getWalletTokenBalance({
          id: walletId,
        });
        result = balances.data?.tokenBalances ?? [];
        break;
      }

      case 'check-connection': {
        const wallets = await client.listWallets({});
        result = { connected: true, walletCount: wallets.data?.wallets?.length ?? 0 };
        break;
      }

      default:
        console.error(JSON.stringify({ error: 'Unknown action: ' + action }));
        process.exit(1);
    }

    console.log(JSON.stringify(result));
  } catch (e) {
    console.error(JSON.stringify({
      error: e.message,
      details: e.response?.data || e.response || {},
    }));
    process.exit(1);
  }
}

main();
'''
    
    with open(_EXECUTOR_SCRIPT, 'w') as f:
        f.write(script_content)
    
    logger.debug(f"Created executor script: {_EXECUTOR_SCRIPT}")


def _node_exec(action: str, args: Optional[dict] = None) -> dict:
    """Execute a Node.js command via the bridge script."""
    _ensure_executor_script()
    
    cmd = [
        "node",
        _EXECUTOR_SCRIPT,
        action,
        json.dumps(args or {}),
    ]
    
    env = os.environ.copy()
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=_SCRIPTS_DIR,
            env=env,
        )
        
        if result.returncode != 0:
            stderr = result.stderr.strip()
            try:
                err_data = json.loads(stderr)
                raise RuntimeError(err_data.get("error", stderr))
            except json.JSONDecodeError:
                raise RuntimeError(stderr or f"Node process exited with code {result.returncode}")
        
        # stdout is the JSON result
        stdout = result.stdout.strip()
        # stderr may contain warnings — ignore them
        if result.stderr.strip():
            logger.debug(f"Node stderr: {result.stderr.strip()[:200]}")
        
        if not stdout:
            return {}
        
        return json.loads(stdout)
        
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Node.js {action} timed out")
    except FileNotFoundError:
        raise RuntimeError("Node.js not found in PATH. Is Node.js installed?")


# ─── Public API ──────────────────────────────────────────────────────────────

def check_connection() -> dict:
    """Test connection to Circle API."""
    return _node_exec("check-connection")


def transfer_usdc(from_wallet_id: str, to_address: str, amount: str) -> dict:
    """Transfer USDC between wallets via Circle API.
    
    Args:
        from_wallet_id: Source Circle wallet ID.
        to_address: Destination wallet address.
        amount: Amount in USDC as string (e.g. "5" = 5 USDC).
    Returns:
        {"id": "tx-...", "state": "pending"} 
    """
    return _node_exec("transfer-usdc", {
        "fromWalletId": from_wallet_id,
        "toAddress": to_address,
        "amount": amount,
    })


def list_wallets() -> list[dict]:
    """List all Arc Testnet wallets."""
    return _node_exec("list-wallets")


def create_wallets(count: int = 2, name: str = "convenatAI Agent Wallets") -> list[dict]:
    """Create new Arc Testnet wallets."""
    return _node_exec("create-wallets", {"count": count, "name": name})


def create_contract_execution_transaction(
    wallet_address: str,
    contract_address: str,
    abi_function_signature: str,
    abi_parameters: list[str],
    fee_level: str = "MEDIUM",
) -> dict:
    """Execute a contract function via Circle Developer-Controlled Wallets."""
    return _node_exec("contract-execution", {
        "walletAddress": wallet_address,
        "contractAddress": contract_address,
        "abiFunctionSignature": abi_function_signature,
        "abiParameters": abi_parameters,
        "feeLevel": fee_level,
    })
