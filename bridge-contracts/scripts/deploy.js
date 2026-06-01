const hre = require("hardhat");

// EIDs for ZKsync Sepolia and Arc Testnet (LayerZero v2 Endpoint IDs)
// Using standard EIDs:
// ZKsync Era Sepolia = 40280
// Arc Testnet = 50420  (or custom EID mapped in LayerZero configuration)
const ZKSYNC_SEPOLIA_EID = 40280;
const ARC_TESTNET_EID = 50420;

// LayerZero v2 Endpoint Addresses (from LayerZero Docs)
// ZKsync Era Sepolia LZ Endpoint: 0x9a71012B13CA4d3D0Cdc72A177DF3ef03b0E76A3
// Arc Testnet LZ Endpoint: 0x6EDCE6540E9E98179d72F3b603EFBE571C40003b (Mock / deployed endpoint address)
const ZKSYNC_SEPOLIA_ENDPOINT = "0x9a71012b13ca4d3d0cdc72a177df3ef03b0e76a3";
const ARC_TESTNET_ENDPOINT = "0x6edce6540e9e98179d72f3b603efbe571c40003b";

// Target Arc AgenticCommerce (ERC-8183) Address
const AGENTIC_COMMERCE_CONTRACT = "0x0747EEf0706327138c69792bF28Cd525089e4583";

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log(`\n============================================================`);
  console.log(`🚀 Deploying convenatAI Solidity Cross-Chain Bridge`);
  console.log(`   Deployer: ${deployer.address}`);
  console.log(`============================================================\n`);

  const networkName = hre.network.name;

  if (networkName === "zksyncSepolia") {
    // ─── Deploy BridgeForwarder on ZKsync Era Sepolia ───
    console.log(`[1/2] Deploying MockEndpoint to ZKsync Era Sepolia...`);
    const MockEndpoint = await hre.ethers.getContractFactory("MockEndpoint");
    const mockEndpoint = await MockEndpoint.deploy();
    await mockEndpoint.deployed();
    const endpointAddress = mockEndpoint.address;
    console.log(`✅  MockEndpoint deployed at: ${endpointAddress}`);

    console.log(`[2/2] Deploying BridgeForwarder to ZKsync Era Sepolia...`);
    const BridgeForwarder = await hre.ethers.getContractFactory("BridgeForwarder");
    const forwarder = await BridgeForwarder.deploy(endpointAddress, deployer.address);
    await forwarder.deployed();
    
    const forwarderAddress = forwarder.address;
    console.log(`✅  BridgeForwarder deployed successfully at: ${forwarderAddress}`);
    console.log(`\n📝 Add this to your .env file:`);
    console.log(`   ZKSYNC_BRIDGE_FORWARDER_ADDRESS=${forwarderAddress}`);
    console.log(`   ZKSYNC_BRIDGE_FORWARDER_ENDPOINT=${endpointAddress}\n`);
    
  } else if (networkName === "arcTestnet") {
    // ─── Deploy BridgeReceiver on Arc Testnet ───
    console.log(`[1/2] Deploying MockEndpoint to Arc Testnet...`);
    const MockEndpoint = await hre.ethers.getContractFactory("MockEndpoint");
    const mockEndpoint = await MockEndpoint.deploy();
    await mockEndpoint.deployed();
    const endpointAddress = mockEndpoint.address;
    console.log(`✅  MockEndpoint deployed at: ${endpointAddress}`);

    console.log(`[2/2] Deploying BridgeReceiver to Arc Testnet...`);
    console.log(`      AgenticCommerce: ${AGENTIC_COMMERCE_CONTRACT}`);
    
    const BridgeReceiver = await hre.ethers.getContractFactory("BridgeReceiver");
    const receiver = await BridgeReceiver.deploy(endpointAddress, deployer.address, AGENTIC_COMMERCE_CONTRACT);
    await receiver.deployed();
    
    const receiverAddress = receiver.address;
    console.log(`✅  BridgeReceiver deployed successfully at: ${receiverAddress}`);
    console.log(`\n📝 Add this to your .env file:`);
    console.log(`   ZKSYNC_BRIDGE_RECEIVER_ADDRESS=${receiverAddress}`);
    console.log(`   ZKSYNC_BRIDGE_RECEIVER_ENDPOINT=${endpointAddress}\n`);
    
  } else {
    // ─── Local Hardhat Network (Dry Run) ───
    console.log(`[Dry Run] Deploying both contracts locally for testing...`);
    
    // Deploy MockEndpoint first
    const MockEndpoint = await hre.ethers.getContractFactory("MockEndpoint");
    const mockEndpoint = await MockEndpoint.deploy();
    await mockEndpoint.deployed();
    const endpointAddress = mockEndpoint.address;

    // Deploy forwarder
    const BridgeForwarder = await hre.ethers.getContractFactory("BridgeForwarder");
    const forwarder = await BridgeForwarder.deploy(endpointAddress, deployer.address);
    await forwarder.deployed();
    const forwarderAddress = forwarder.address;
    
    // Deploy receiver
    const BridgeReceiver = await hre.ethers.getContractFactory("BridgeReceiver");
    const receiver = await BridgeReceiver.deploy(endpointAddress, deployer.address, AGENTIC_COMMERCE_CONTRACT);
    await receiver.deployed();
    const receiverAddress = receiver.address;
    
    console.log(`✅  BridgeForwarder deployed (Mock) at: ${forwarderAddress}`);
    console.log(`✅  BridgeReceiver deployed (Mock) at: ${receiverAddress}`);

    // Link peers
    console.log(`\n[2/2] Linking Bridge Contracts as LayerZero Peers...`);
    const peerOnReceiver = hre.ethers.utils.hexZeroPad(forwarderAddress, 32);
    const peerOnForwarder = hre.ethers.utils.hexZeroPad(receiverAddress, 32);

    await forwarder.setPeer(ARC_TESTNET_EID, peerOnForwarder);
    await receiver.setPeer(ZKSYNC_SEPOLIA_EID, peerOnReceiver);
    
    console.log(`✅  Successfully linked ZKsync Sepolia ↔ Arc Testnet via LayerZero EIDs!`);
  }

  console.log(`\n============================================================\n`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
