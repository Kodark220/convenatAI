import { readFileSync } from "fs";
import path from "path";
import { GenLayerClient } from "genlayer-js";
import { testnetBradbury } from "genlayer-js/chains";
import { createWalletClient } from "genlayer-js/clients";

/**
 * Deploy ConvenatContract.py to GenLayer Bradbury Testnet.
 *
 * Usage:
 *   GENLAYER_PRIVATE_KEY=your_key_here npx tsx deploy/deploy_convenat.ts
 *
 * The private key should be WITHOUT the 0x prefix.
 */
async function main() {
  const privateKey = process.env.GENLAYER_PRIVATE_KEY;
  if (!privateKey) {
    console.error("❌ GENLAYER_PRIVATE_KEY not set in environment");
    console.error("   Usage: GENLAYER_PRIVATE_KEY=your_key npx tsx deploy/deploy_convenat.ts");
    process.exit(1);
  }

  console.log("🚀 Deploying ConvenatContract to Bradbury Testnet...");
  console.log("   Network: https://rpc-bradbury.genlayer.com");
  console.log("   Chain ID: 4221");
  console.log("");

  // Create the GenLayer client connected to Bradbury
  const walletClient = createWalletClient({
    privateKey: privateKey,
    chain: testnetBradbury,
  });

  const client = new GenLayerClient({
    client: walletClient,
    chain: testnetBradbury,
  });

  // Read the contract file
  const filePath = path.resolve(process.cwd(), "contracts/ConvenatContract.py");
  const contractCode = new Uint8Array(readFileSync(filePath));

  console.log(`📄 Contract source: ${filePath}`);
  console.log(`   Size: ${contractCode.length} bytes`);
  console.log("");

  // Initialize consensus
  console.log("🔄 Initializing consensus...");
  await client.initializeConsensusSmartContract();

  // Deploy the contract
  console.log("📦 Deploying contract...");
  const deployTransaction = await client.deployContract({
    code: contractCode,
    args: [],
  });

  console.log(`⏳ Transaction submitted: ${deployTransaction}`);
  console.log("   Waiting for confirmation (this may take a minute)...");

  // Wait for deployment confirmation
  const receipt = await client.waitForTransactionReceipt({
    hash: deployTransaction as `0x${string}`,
    retries: 200,
  });

  // Check deployment success
  const statusName = receipt.statusName;
  if (statusName !== "ACCEPTED" && statusName !== "FINALIZED") {
    throw new Error(`Deployment failed. Status: ${statusName}. Receipt: ${JSON.stringify(receipt)}`);
  }

  // Get contract address
  const deployedContractAddress = receipt.data?.contract_address ||
    (receipt.txDataDecoded as any)?.contractAddress;

  if (!deployedContractAddress) {
    console.warn("⚠️  Could not extract contract address from receipt.");
    console.log("Raw receipt:", JSON.stringify(receipt, null, 2));
    process.exit(1);
  }

  console.log("");
  console.log("✅  Contract deployed successfully!");
  console.log(`   Transaction Hash: ${deployTransaction}`);
  console.log(`   Contract Address: ${deployedContractAddress}`);
  console.log("");
  console.log("📝  Add this to your .env file:");
  console.log(`   CONVENAT_CONTRACT_ADDRESS=${deployedContractAddress}`);
  console.log("");
  console.log("🔗  View on explorer: https://explorer-bradbury.genlayer.com/address/${deployedContractAddress}");
}

main().catch((err) => {
  console.error("❌ Deployment failed:", err);
  process.exit(1);
});
