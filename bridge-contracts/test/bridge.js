const { expect } = require("chai");
const { ethers } = require("hardhat");

// Robust version-agnostic helper for Ethers v5 / v6 compatibility
const zeroPad = (val, length) => {
  if (ethers.zeroPadValue) return ethers.zeroPadValue(val, length);
  if (ethers.hexZeroPad) return ethers.hexZeroPad(val, length);
  if (ethers.utils && ethers.utils.hexZeroPad) return ethers.utils.hexZeroPad(val, length);
  const raw = val.replace("0x", "");
  return "0x" + raw.padStart(length * 2, "0");
};

const encodePayload = (types, values) => {
  if (ethers.AbiCoder) return ethers.AbiCoder.defaultAbiCoder().encode(types, values);
  if (ethers.utils && ethers.utils.defaultAbiCoder) return ethers.utils.defaultAbiCoder.encode(types, values);
  throw new Error("Unable to locate ABI coder in ethers");
};

const getAddress = (contract) => {
  if (!contract) return "0x0000000000000000000000000000000000000000";
  if (typeof contract === "string") return contract;
  return contract.address || contract.target || (contract.getAddress ? contract.getAddress() : contract.address);
};

const AddressZero = ethers.ZeroAddress || (ethers.constants && ethers.constants.AddressZero) || "0x0000000000000000000000000000000000000000";

const waitForDeployment = async (contract) => {
  if (contract.waitForDeployment) await contract.waitForDeployment();
  else if (contract.deployed) await contract.deployed();
};

const getSolidityPackedKeccak256 = (types, values) => {
  if (ethers.solidityPackedKeccak256) return ethers.solidityPackedKeccak256(types, values);
  if (ethers.utils && ethers.utils.solidityKeccak256) return ethers.utils.solidityKeccak256(types, values);
  throw new Error("Unable to locate solidity keccak256 in ethers");
};

describe("convenatAI — LayerZero Solidity Bridge Unit Tests", function () {
  let deployer;
  let client;
  let provider;
  let mockCommerce;
  let receiver;
  let mockEndpoint;

  // Fake LayerZero details
  const ZKSYNC_SEPOLIA_EID = 40280;
  let FAKE_GUID;

  beforeEach(async function () {
    [deployer, client, provider] = await ethers.getSigners();
    FAKE_GUID = zeroPad("0x1234", 32);

    // 1. Deploy MockEndpoint
    const MockEndpoint = await ethers.getContractFactory("MockEndpoint");
    mockEndpoint = await MockEndpoint.deploy();
    await waitForDeployment(mockEndpoint);

    // 2. Deploy MockAgenticCommerce
    const MockAgenticCommerce = await ethers.getContractFactory("MockAgenticCommerce");
    mockCommerce = await MockAgenticCommerce.deploy();
    await waitForDeployment(mockCommerce);

    // 3. Deploy BridgeReceiver (using mockEndpoint address as LZ Endpoint so it can call setDelegate)
    const BridgeReceiver = await ethers.getContractFactory("BridgeReceiver");
    receiver = await BridgeReceiver.deploy(
      getAddress(mockEndpoint), // mock LZ endpoint
      deployer.address, // delegate
      getAddress(mockCommerce)
    );
    await waitForDeployment(receiver);

    // 4. Set the deployer as a trusted LayerZero peer on the receiver
    // This allows lzReceive to accept messages from our EID
    const peerBytes32 = zeroPad(deployer.address, 32);
    await receiver.setPeer(ZKSYNC_SEPOLIA_EID, peerBytes32);
  });

  it("should deploy mock commerce and register jobs correctly", async function () {
    const tx = await mockCommerce.connect(client).createJob(provider.address);
    await tx.wait();

    expect(await mockCommerce.getJobStatus(1)).to.equal(1); // 1 = Funded
  });

  it("should receive LayerZero message and reject Arc job on SLA breach", async function () {
    // 1. Create a job on-chain
    await mockCommerce.connect(client).createJob(provider.address);
    expect(await mockCommerce.getJobStatus(1)).to.equal(1); // Funded

    // 2. Encode the LZ payload (jobId, reason)
    const jobId = 1;
    const reason = "Quality criteria not met: Tweet count less than 100";
    const payload = encodePayload(
      ["uint256", "string"],
      [jobId, reason]
    );

    // 3. Prepare LayerZero Origin metadata
    const origin = {
      srcEid: ZKSYNC_SEPOLIA_EID,
      sender: zeroPad(deployer.address, 32),
      nonce: 1
    };

    // 4. Simulate LZ message receipt (calling simulateReceive from our mock endpoint contract)
    const tx = await mockEndpoint.simulateReceive(
      getAddress(receiver),
      origin,
      FAKE_GUID,
      payload,
      AddressZero,
      "0x"
    );
    await tx.wait();

    // 5. Verify the job has been REJECTED on-chain
    expect(await mockCommerce.getJobStatus(1)).to.equal(4); // 4 = Rejected

    // 6. Verify correct reason hash is stored on mock commerce
    const jobInfo = await mockCommerce.jobs(1);
    const expectedReasonHash = getSolidityPackedKeccak256(["string"], [reason]);
    expect(jobInfo.reason).to.equal(expectedReasonHash);
  });

  it("should allow owner to update AgenticCommerce contract address", async function () {
    const newAddr = ethers.Wallet.createRandom().address;
    await receiver.setAgenticCommerce(newAddr);
    expect(await receiver.agenticCommerce()).to.equal(newAddr);
  });
});
