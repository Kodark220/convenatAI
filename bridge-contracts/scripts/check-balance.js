const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  const networkName = hre.network.name;

  console.log(`============================================================`);
  console.log(`Checking balance on network: ${networkName}`);
  console.log(`Wallet address: ${deployer.address}`);

  const balance = await deployer.getBalance();
  console.log(`Balance: ${hre.ethers.utils.formatEther(balance)} ETH`);
  console.log(`============================================================\n`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
