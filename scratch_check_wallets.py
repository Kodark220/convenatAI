import os
import json
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

rpc_url = os.getenv("ARC_RPC_URL", "https://rpc.testnet.arc.network")
usdc_contract = "0x3600000000000000000000000000000000000000"

w3 = Web3(Web3.HTTPProvider(rpc_url))
print(f"Connected to Arc Testnet: {w3.is_connected()}")

# Core Agent Wallets
wallets = {
    "0x92e9aac1ed7044487bc8d8128465c7e588d9e1b6": "Treasury",
    "0x366c3352daee2b4b0117e6bdd1ff291beafcc8ad": "Buyer Agent",
    "0xe94a73aeb28c452fb62677184960bb831b759333": "Seller Agent",
    "0x6c578db2034617039116f27521f748aad00f0a45": "Extra Agent 1",
    "0x1505102c7247b0e3323e689cb5bc6a142dff4408": "Extra Agent 2",
}

# ERC-20 balanceOf ABI
usdc_abi = [{
    "type": "function",
    "name": "balanceOf",
    "stateMutability": "view",
    "inputs": [{"name": "account", "type": "address"}],
    "outputs": [{"name": "", "type": "uint256"}]
}]

usdc = w3.eth.contract(address=w3.to_checksum_address(usdc_contract), abi=usdc_abi)

print("\n" + "="*70)
print(f"{'Wallet Address':<45} | {'Role':<15} | {'Nonce':<6} | {'USDC Balance':<12}")
print("="*70)

for addr, role in wallets.items():
    checksum_addr = w3.to_checksum_address(addr)
    
    # 1. Nonce (Transaction Count)
    nonce = w3.eth.get_transaction_count(checksum_addr)
    
    # 2. USDC Balance
    try:
        bal_atomic = usdc.functions.balanceOf(checksum_addr).call()
        bal_usdc = bal_atomic / 1_000_000
    except Exception as e:
        bal_usdc = "Error"
        
    print(f"{addr:<45} | {role:<15} | {nonce:<6} | ${bal_usdc}")

print("="*70 + "\n")
