require("@nomiclabs/hardhat-ethers");
require("dotenv").config({ path: "../.env" });

const PRIVATE_KEY = process.env.GENLAYER_PRIVATE_KEY || "0x0000000000000000000000000000000000000000000000000000000000000000";

// Ensure private key has 0x prefix for Hardhat
const formattedPrivateKey = PRIVATE_KEY.startsWith("0x") ? PRIVATE_KEY : `0x${PRIVATE_KEY}`;

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
    },
  },
  paths: {
    sources: "./contracts",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts"
  },
  networks: {
    hardhat: {},
    zksyncSepolia: {
      url: "https://sepolia.era.zksync.dev",
      accounts: [formattedPrivateKey],
    },
    arcTestnet: {
      url: process.env.ARC_RPC_URL || "https://rpc.testnet.arc.network",
      accounts: [formattedPrivateKey],
    }
  }
};
