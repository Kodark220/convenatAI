// ─── ERC-8183 AgenticCommerce ABI (Arc Testnet) ───────────────────────────────
// Deployed at 0x0747EEf0706327138c69792bF28Cd525089e4583

export const ARC_CONVENAT_ABI = [
  // ─── Events ───────────────────────────────────────────────────────────────
  {
    name: "JobCreated",
    type: "event",
    inputs: [
      { name: "jobId", type: "uint256", indexed: true },
      { name: "client", type: "address", indexed: true },
      { name: "provider", type: "address", indexed: true },
      { name: "description", type: "string", indexed: false },
      { name: "budget", type: "uint256", indexed: false },
    ],
  },
  {
    name: "JobFunded",
    type: "event",
    inputs: [
      { name: "jobId", type: "uint256", indexed: true },
      { name: "amount", type: "uint256", indexed: false },
    ],
  },
  {
    name: "DeliverableSubmitted",
    type: "event",
    inputs: [
      { name: "jobId", type: "uint256", indexed: true },
      { name: "deliverable", type: "bytes32", indexed: false },
    ],
  },
  {
    name: "JobCompleted",
    type: "event",
    inputs: [
      { name: "jobId", type: "uint256", indexed: true },
      { name: "approved", type: "bool", indexed: false },
    ],
  },
  // ─── Write Functions ────────────────────────────────────────────────────
  {
    name: "createJob",
    type: "function",
    stateMutability: "nonpayable",
    inputs: [
      { name: "provider", type: "address" },
      { name: "evaluator", type: "address" },
      { name: "expiredAt", type: "uint256" },
      { name: "description", type: "string" },
      { name: "hook", type: "address" },
    ],
    outputs: [{ name: "jobId", type: "uint256" }],
  },
  {
    name: "setBudget",
    type: "function",
    stateMutability: "nonpayable",
    inputs: [
      { name: "jobId", type: "uint256" },
      { name: "amount", type: "uint256" },
      { name: "optParams", type: "bytes" },
    ],
    outputs: [],
  },
  {
    name: "fund",
    type: "function",
    stateMutability: "nonpayable",
    inputs: [
      { name: "jobId", type: "uint256" },
      { name: "optParams", type: "bytes" },
    ],
    outputs: [],
  },
  {
    name: "submit",
    type: "function",
    stateMutability: "nonpayable",
    inputs: [
      { name: "jobId", type: "uint256" },
      { name: "deliverable", type: "bytes32" },
      { name: "optParams", type: "bytes" },
    ],
    outputs: [],
  },
  {
    name: "complete",
    type: "function",
    stateMutability: "nonpayable",
    inputs: [
      { name: "jobId", type: "uint256" },
      { name: "reason", type: "bytes32" },
      { name: "optParams", type: "bytes" },
    ],
    outputs: [],
  },
  // ─── View Functions ─────────────────────────────────────────────────────
  {
    name: "getJob",
    type: "function",
    stateMutability: "view",
    inputs: [{ name: "jobId", type: "uint256" }],
    outputs: [
      {
        type: "tuple",
        components: [
          { name: "id", type: "uint256" },
          { name: "client", type: "address" },
          { name: "provider", type: "address" },
          { name: "evaluator", type: "address" },
          { name: "description", type: "string" },
          { name: "budget", type: "uint256" },
          { name: "expiredAt", type: "uint256" },
          { name: "status", type: "uint8" },
          { name: "hook", type: "address" },
        ],
      },
    ],
  },
] as const;

// ─── USDC ERC-20 ABI (minimal — approve + balanceOf) ──────────────────────────

export const USDC_ABI = [
  {
    name: "approve",
    type: "function",
    stateMutability: "nonpayable",
    inputs: [
      { name: "spender", type: "address" },
      { name: "amount", type: "uint256" },
    ],
    outputs: [{ name: "", type: "bool" }],
  },
  {
    name: "allowance",
    type: "function",
    stateMutability: "view",
    inputs: [
      { name: "owner", type: "address" },
      { name: "spender", type: "address" },
    ],
    outputs: [{ name: "", type: "uint256" }],
  },
  {
    name: "balanceOf",
    type: "function",
    stateMutability: "view",
    inputs: [{ name: "account", type: "address" }],
    outputs: [{ name: "", type: "uint256" }],
  },
] as const;

// ─── GenLayer ConvenatContract ABI ──────────────────────────────────────────────

export const GENLAYER_CONVENAT_ABI = [
  {
    name: "register_job",
    type: "function",
    stateMutability: "nonpayable",
    inputs: [
      { name: "stream_id", type: "string" },
      { name: "buyer", type: "address" },
      { name: "seller", type: "address" },
      { name: "criteria", type: "string" },
    ],
    outputs: [{ name: "job_id", type: "bytes32" }],
  },
  {
    name: "get_sla_status",
    type: "function",
    stateMutability: "view",
    inputs: [{ name: "job_id", type: "bytes32" }],
    outputs: [
      { name: "met", type: "bool" },
      { name: "score", type: "uint256" },
    ],
  },
] as const;

// ─── Contract Addresses ───────────────────────────────────────────────────────

export const CONTRACT_ADDRESSES = {
  arc: (process.env.NEXT_PUBLIC_ARC_CONTRACT ?? "0x0747EEf0706327138c69792bF28Cd525089e4583") as `0x${string}`,
  usdc: "0x3600000000000000000000000000000000000000" as `0x${string}`,
  genlayer: (process.env.NEXT_PUBLIC_GENLAYER_CONTRACT ?? "0xc821A31Bfe1299131D4D07E78a0c7D388B1E9642") as `0x${string}`,
} as const;
