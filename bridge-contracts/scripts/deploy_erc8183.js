const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying with:", deployer.address);

  const Factory = await hre.ethers.getContractFactory("MockAgenticCommerce");
  const contract = await Factory.deploy();
  await contract.deployed();
  
  const addr = contract.address;
  console.log("Contract deployed at:", addr);
  
  const code = await hre.ethers.provider.getCode(addr);
  console.log("Code length:", code.length);
  console.log("SUCCESS");
}

main().catch(console.error);
