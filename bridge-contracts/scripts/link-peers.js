const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log(`============================================================`);
  console.log(`🔗 Linking LayerZero Peers`);
  console.log(`   Deployer: ${deployer.address}`);
  console.log(`============================================================\n`);

  const forwarderAddress = process.env.ZKSYNC_BRIDGE_FORWARDER_ADDRESS;
  const receiverAddress = process.env.ZKSYNC_BRIDGE_RECEIVER_ADDRESS;

  if (!forwarderAddress || !receiverAddress) {
    console.error("❌ Error: Both ZKSYNC_BRIDGE_FORWARDER_ADDRESS and ZKSYNC_BRIDGE_RECEIVER_ADDRESS must be set in your .env!");
    process.exit(1);
  }

  console.log(`Forwarder address (ZKsync Sepolia): ${forwarderAddress}`);
  console.log(`Receiver address (Arc Testnet): ${receiverAddress}`);

  const ZKSYNC_SEPOLIA_EID = 40280;
  const ARC_TESTNET_EID = 50420;

  const peerOnReceiver = hre.ethers.utils.hexZeroPad(forwarderAddress, 32);
  const peerOnForwarder = hre.ethers.utils.hexZeroPad(receiverAddress, 32);

  const networkName = hre.network.name;

  if (networkName === "zksyncSepolia") {
    console.log(`Connecting to BridgeForwarder on ZKsync Sepolia...`);
    const BridgeForwarder = await hre.ethers.getContractAt("BridgeForwarder", forwarderAddress);
    
    console.log(`Setting peer for EID ${ARC_TESTNET_EID} to ${peerOnForwarder}...`);
    const tx = await BridgeForwarder.setPeer(ARC_TESTNET_EID, peerOnForwarder);
    console.log(`Transaction submitted: ${tx.hash}`);
    await tx.wait();
    console.log(`✅ BridgeForwarder setPeer complete!`);
  } else if (networkName === "arcTestnet") {
    console.log(`Connecting to BridgeReceiver on Arc Testnet...`);
    const BridgeReceiver = await hre.ethers.getContractAt("BridgeReceiver", receiverAddress);
    
    console.log(`Setting peer for EID ${ZKSYNC_SEPOLIA_EID} to ${peerOnReceiver}...`);
    const tx = await BridgeReceiver.setPeer(ZKSYNC_SEPOLIA_EID, peerOnReceiver);
    console.log(`Transaction submitted: ${tx.hash}`);
    await tx.wait();
    console.log(`✅ BridgeReceiver setPeer complete!`);
  } else {
    console.log("❌ Unknown network! Please run on zksyncSepolia or arcTestnet.");
  }
  console.log(`\n============================================================\n`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
