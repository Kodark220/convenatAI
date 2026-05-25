// ─── RPC & API Layer ──────────────────────────────────────────────────────────
// Replace NEXT_PUBLIC_API_URL in .env.local to point to your backend.
// Each function maps 1-to-1 with a backend endpoint or on-chain call.

import type {
  Job,
  Agent,
  ChainEvent,
  DashboardStats,
  ChainInfo,
  DailyDataPoint,
  RegisterJobPayload,
  ChainId,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

// ─── Generic fetcher (used by SWR) ───────────────────────────────────────────

export async function fetcher<T>(url: string): Promise<T> {
  if (!API_BASE) {
    // Return mock data when no backend is connected
    return getMockData<T>(url);
  }
  const res = await fetch(`${API_BASE}${url}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// ─── Endpoint helpers (swap these for real eth_call / your API) ──────────────

export const endpoints = {
  stats: "/api/stats",
  jobs: "/api/jobs",
  agents: "/api/agents",
  events: (chain: ChainId) => `/api/chains/${chain}/events`,
  chainInfo: (chain: ChainId) => `/api/chains/${chain}`,
  chartData: (chain: ChainId) => `/api/chains/${chain}/chart`,
  registerJob: "/api/genlayer/register-job",
  scanJobs: (chain: ChainId, fromBlock: number, toBlock: number) =>
    `/api/chains/${chain}/scan?from=${fromBlock}&to=${toBlock}`,
  negotiatorStatus: "/api/negotiator/status",
};

// ─── Server Actions / Mutations ───────────────────────────────────────────────

export async function registerJob(payload: RegisterJobPayload): Promise<{ txHash: string }> {
  // TODO: replace with actual GenLayer contract call via your backend
  if (!API_BASE) {
    await new Promise((r) => setTimeout(r, 1200));
    return { txHash: `0x${Math.random().toString(16).slice(2)}` };
  }
  const res = await fetch(`${API_BASE}${endpoints.registerJob}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to register job");
  return res.json();
}

export async function scanJobs(
  chain: ChainId,
  fromBlock: number,
  toBlock: number
): Promise<Job[]> {
  // TODO: replace with eth_getLogs call via your backend
  if (!API_BASE) {
    await new Promise((r) => setTimeout(r, 800));
    return generateMockJobs(8, chain);
  }
  return fetcher<Job[]>(endpoints.scanJobs(chain, fromBlock, toBlock));
}

// ─── Mock Data (remove when backend is ready) ─────────────────────────────────

const STATUS_LIST = ["open", "active", "completed", "failed", "disputed"] as const;
const ROLES = ["client", "provider", "arbitrator"] as const;

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

function randomAddress() {
  return `0x${Array.from({ length: 40 }, () => Math.floor(Math.random() * 16).toString(16)).join("")}`;
}

function randomHash() {
  return `0x${Array.from({ length: 64 }, () => Math.floor(Math.random() * 16).toString(16)).join("")}`;
}

function generateMockJobs(count: number, chain?: ChainId): Job[] {
  return Array.from({ length: count }, () => ({
    // uid() ensures keys never collide between calls or between scan + feed
    id: `job-${uid()}`,
    streamId: `stream-${uid()}`,
    buyer: randomAddress(),
    seller: randomAddress(),
    usdcAmount: Math.floor(Math.random() * 10000) + 100,
    status: STATUS_LIST[Math.floor(Math.random() * STATUS_LIST.length)],
    chain: chain ?? (Math.random() > 0.5 ? "arc" : "genlayer"),
    createdAt: Date.now() - Math.random() * 86400000 * 7,
    updatedAt: Date.now() - Math.random() * 86400000,
    criteria: "SLA: 99.9% uptime, response < 200ms",
    txHash: randomHash(),
  }));
}

function generateMockAgents(count: number): Agent[] {
  return Array.from({ length: count }, (_, i) => ({
    address: randomAddress(),
    role: ROLES[i % ROLES.length],
    jobCount: Math.floor(Math.random() * 50) + 1,
    totalUSDC: Math.floor(Math.random() * 100000) + 1000,
    activeJobs: Math.floor(Math.random() * 5),
    registeredAt: Date.now() - Math.random() * 86400000 * 30,
    chain: Math.random() > 0.5 ? "arc" : "genlayer",
  }));
}

function generateMockEvents(count: number, chain: ChainId): ChainEvent[] {
  const eventNames = ["JobCreated", "JobAccepted", "JobCompleted", "PaymentReleased", "DisputeRaised"];
  return Array.from({ length: count }, () => ({
    // prefix with chain so Arc + GenLayer event IDs never collide
    id: `${chain}-evt-${uid()}`,
    blockNumber: 1_000_000 + Math.floor(Math.random() * 10_000),
    txHash: randomHash(),
    eventName: eventNames[Math.floor(Math.random() * eventNames.length)],
    args: { jobId: `job-${uid()}`, amount: `${Math.floor(Math.random() * 1000)}` },
    chain,
    timestamp: Date.now() - Math.random() * 3_600_000,
  }));
}

// Chart data is stable (date-keyed), so we generate it once per session —
// random values per day are fine, they just shouldn't jump on every poll.
function generateChartData(days = 14): DailyDataPoint[] {
  return Array.from({ length: days }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (days - i - 1));
    return {
      date: d.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
      jobs: Math.floor(Math.random() * 40) + 5,
      usdc: Math.floor(Math.random() * 50_000) + 1_000,
      agents: Math.floor(Math.random() * 20) + 10,
    };
  });
}

const MOCK_CHAIN_INFO: Record<ChainId, ChainInfo> = {
  arc: {
    id: "arc",
    name: "Arc Testnet",
    rpc: "https://rpc.arc-testnet.io",
    contract: "0xConvenatArcContract000000000000000000000",
    explorerUrl: "https://explorer.arc-testnet.io",
    status: "live",
    blockNumber: 1_043_291,
  },
  genlayer: {
    id: "genlayer",
    name: "GenLayer Testnet",
    rpc: "https://rpc.genlayer-testnet.io",
    contract: "0xConvenatGenLayerContract00000000000000000",
    explorerUrl: "https://explorer.genlayer.io",
    status: "idle",
    blockNumber: 892_010,
  },
};

// Stable data frozen at module load (agents, chain info, charts don't change per poll)
const STABLE_AGENTS = generateMockAgents(24);
const STABLE_ARC_CHART = generateChartData(14);
const STABLE_GL_CHART = generateChartData(14);

// Factory: called fresh on every SWR revalidation so the event feed + job list
// appear to update, making mock mode feel like a live app.
function getMockData<T>(url: string): T {
  const key = url.split("?")[0];

  const MOCK_FACTORY: Record<string, () => unknown> = {
    "/api/stats": () => ({
      totalJobs: 1_284 + Math.floor(Math.random() * 10),
      activeAgents: 47,
      dealsDone: 938 + Math.floor(Math.random() * 5),
      usdcStreamed: 2_847_392 + Math.floor(Math.random() * 50_000),
    } satisfies DashboardStats),
    "/api/jobs":                      () => generateMockJobs(20),
    "/api/agents":                    () => STABLE_AGENTS,
    "/api/chains/arc/events":         () => generateMockEvents(15, "arc"),
    "/api/chains/genlayer/events":    () => generateMockEvents(10, "genlayer"),
    "/api/chains/arc":                () => MOCK_CHAIN_INFO.arc,
    "/api/chains/genlayer":           () => MOCK_CHAIN_INFO.genlayer,
    "/api/chains/arc/chart":          () => STABLE_ARC_CHART,
    "/api/chains/genlayer/chart":     () => STABLE_GL_CHART,
  };

  const factory = MOCK_FACTORY[key];
  if (!factory) return [] as T;
  return factory() as T;
}
