/**
 * convenatAI — Balance & Deployment Readiness Checker
 * Checks wallet balances across all required networks before deployment.
 *
 * Networks required:
 *  1. GenLayer Bradbury Testnet   — for ConvenatContract.py
 *  2. ZKsync Era Sepolia          — for LayerZero Bridge Hub (BridgeForwarder.sol)
 *  3. Arc Testnet (EVM)           — for BridgeSender.sol, BridgeReceiver.sol
 */

const { ethers } = require("ethers");

// ─── Config ─────────────────────────────────────────────────────────────────
const PRIVATE_KEY = process.env.GENLAYER_PRIVATE_KEY || "0x0000000000000000000000000000000000000000000000000000000000000000";

const NETWORKS = [
  {
    name: "GenLayer Bradbury Testnet",
    rpc: "https://studio.genlayer.com:8443/api",
    nativeCurrency: "GEN",
    minRequired: "0.01",
    purpose: "Deploy ConvenatContract.py",
    isGenLayer: true,
  },
  {
    name: "ZKsync Era Sepolia (Bridge Hub)",
    rpc: "https://sepolia.era.zksync.dev",
    chainId: 300,
    nativeCurrency: "ETH",
    minRequired: "0.01",
    purpose: "Deploy BridgeForwarder.sol + BridgeReceiver.sol",
    isGenLayer: false,
  },
  {
    name: "Arc Testnet",
    rpc: "https://testnet.rpc.arc.io",
    nativeCurrency: "ETH",
    minRequired: "0.01",
    purpose: "Deploy BridgeSender.sol + BridgeReceiver.sol",
    isGenLayer: false,
  },
];

// ─── Main ────────────────────────────────────────────────────────────────────
async function checkBalances() {
  const wallet = new ethers.Wallet(PRIVATE_KEY);
  console.log(`\n${"=".repeat(60)}`);
  console.log(`  convenatAI — Deployment Balance Check`);
  console.log(`  Address: ${wallet.address}`);
  console.log(`${"=".repeat(60)}\n`);

  let allGood = true;

  for (const net of NETWORKS) {
    process.stdout.write(`  Checking ${net.name}... `);
    try {
      let balance = null;

      if (net.isGenLayer) {
        // GenLayer uses JSON-RPC but standard eth_getBalance
        const res = await fetch(net.rpc, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            jsonrpc: "2.0",
            method: "eth_getBalance",
            params: [wallet.address, "latest"],
            id: 1,
          }),
        });
        const json = await res.json();
        if (json.result) {
          balance = ethers.formatEther(BigInt(json.result));
        } else {
          balance = "0.0";
        }
      } else {
        const provider = new ethers.JsonRpcProvider(net.rpc);
        const raw = await provider.getBalance(wallet.address);
        balance = ethers.formatEther(raw);
      }

      const sufficient = parseFloat(balance) >= parseFloat(net.minRequired);
      const status = sufficient ? "✅" : "❌ NEEDS FUNDS";
      console.log(`${status}`);
      console.log(`       Balance  : ${parseFloat(balance).toFixed(6)} ${net.nativeCurrency}`);
      console.log(`       Required : ${net.minRequired} ${net.nativeCurrency} (for: ${net.purpose})`);
      if (!sufficient) allGood = false;
    } catch (err) {
      console.log(`⚠️  RPC ERROR`);
      console.log(`       Error    : ${err.message}`);
    }
    console.log();
  }

  console.log(`${"=".repeat(60)}`);
  if (allGood) {
    console.log(`  ✅ All balances sufficient. Ready to deploy!`);
  } else {
    console.log(`  ❌ Some accounts need funding before deployment.`);
    console.log(`\n  Faucets:`);
    console.log(`  • GenLayer Bradbury : https://testnet-faucet.genlayer.foundation`);
    console.log(`  • ZKsync Era Sepolia: https://faucet.quicknode.com/zksync/sepolia`);
    console.log(`  • Arc Testnet       : https://faucet.arc.io`);
  }
  console.log(`${"=".repeat(60)}\n`);
}

checkBalances().catch(console.error);
