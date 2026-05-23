// ─── Core Domain Types ────────────────────────────────────────────────────────

export type ChainId = "arc" | "genlayer";

export type JobStatus = "open" | "active" | "completed" | "failed" | "disputed";

export type AgentRole = "client" | "provider" | "arbitrator";

// ─── Job ──────────────────────────────────────────────────────────────────────

export interface Job {
  id: string;
  streamId: string;
  buyer: string;
  seller: string;
  usdcAmount: number;
  status: JobStatus;
  chain: ChainId;
  createdAt: number; // unix timestamp
  updatedAt: number;
  criteria?: string;
  txHash?: string;
}

// ─── Agent ────────────────────────────────────────────────────────────────────

export interface Agent {
  address: string;
  role: AgentRole;
  jobCount: number;
  totalUSDC: number;
  activeJobs: number;
  registeredAt: number;
  chain: ChainId;
}

// ─── Event ────────────────────────────────────────────────────────────────────

export interface ChainEvent {
  id: string;
  blockNumber: number;
  txHash: string;
  eventName: string;
  args: Record<string, string>;
  chain: ChainId;
  timestamp: number;
}

// ─── Stats ────────────────────────────────────────────────────────────────────

export interface DashboardStats {
  totalJobs: number;
  activeAgents: number;
  dealsDone: number;
  usdcStreamed: number;
}

// ─── Chain Info ───────────────────────────────────────────────────────────────

export interface ChainInfo {
  id: ChainId | "circle"; // "circle" used for Circle Wallets card on dashboard
  name: string;
  rpc: string;
  contract: string;
  explorerUrl: string;
  status: "live" | "idle" | "error";
  blockNumber?: number;
}

// ─── Charts ───────────────────────────────────────────────────────────────────

export interface DailyDataPoint {
  date: string;
  jobs: number;
  usdc: number;
  agents: number;
}

// ─── GenLayer ─────────────────────────────────────────────────────────────────

export interface RegisterJobPayload {
  streamId: string;
  buyer: string;
  seller: string;
  criteria: string;
}
