// ─── ConvenatAI Contract ABIs ─────────────────────────────────────────────────
// Replace with actual deployed contract ABIs from your backend team

export const ARC_CONVENAT_ABI = [
  {
    name: "JobCreated",
    type: "event",
    inputs: [
      { name: "jobId", type: "bytes32", indexed: true },
      { name: "buyer", type: "address", indexed: true },
      { name: "seller", type: "address", indexed: true },
      { name: "streamId", type: "string", indexed: false },
      { name: "amount", type: "uint256", indexed: false },
    ],
  },
  {
    name: "JobAccepted",
    type: "event",
    inputs: [
      { name: "jobId", type: "bytes32", indexed: true },
      { name: "seller", type: "address", indexed: true },
    ],
  },
  {
    name: "JobCompleted",
    type: "event",
    inputs: [
      { name: "jobId", type: "bytes32", indexed: true },
      { name: "amount", type: "uint256", indexed: false },
    ],
  },
  {
    name: "PaymentReleased",
    type: "event",
    inputs: [
      { name: "jobId", type: "bytes32", indexed: true },
      { name: "recipient", type: "address", indexed: true },
      { name: "amount", type: "uint256", indexed: false },
    ],
  },
] as const;

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
// TODO: update with deployed addresses from your backend

export const CONTRACT_ADDRESSES = {
  arc: process.env.NEXT_PUBLIC_ARC_CONTRACT ?? "0x0000000000000000000000000000000000000000",
  genlayer: process.env.NEXT_PUBLIC_GENLAYER_CONTRACT ?? "0x0000000000000000000000000000000000000000",
} as const;
