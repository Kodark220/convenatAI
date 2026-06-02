// ─── RPC & API Layer ──────────────────────────────────────────────────────────
// All data flows through the FastAPI backend (serve.py).
// NEXT_PUBLIC_API_URL must be set in .env.local — no mock fallback.

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

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://convenat-ai.fly.dev";

// ─── Generic fetcher (used by SWR) ───────────────────────────────────────────

export async function fetcher<T>(url: string): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// ─── Endpoint helpers ────────────────────────────────────────────────────────

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
  negotiatorLogs: "/api/negotiator/logs",
  createDeal: "/api/deals/create",
  dealStatus: (dealId: string) => `/api/deals/${dealId}/status`,
};

// ─── Server Actions / Mutations ───────────────────────────────────────────────

export async function registerJob(payload: RegisterJobPayload): Promise<{ txHash: string }> {
  if (!API_BASE) throw new Error("Backend not configured");
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
  return fetcher<Job[]>(endpoints.scanJobs(chain, fromBlock, toBlock));
}

export async function createDealAPI(payload: {
  title: string;
  description: string;
  budget: number;
  deadline: string;
  criteria: string;
  chain: string;
}): Promise<{ deal_id: string }> {
  if (!API_BASE) throw new Error("Backend not configured");
  const res = await fetch(`${API_BASE}${endpoints.createDeal}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to create deal");
  return res.json();
}

export async function fetchDealStatus(dealId: string): Promise<{
  status: string;
  events: Array<{ message: string; type: string; timestamp: number }>;
  escrowTx?: string;
  verificationScore?: number;
  settlementTx?: string;
  sellerAgent?: string;
  buyerAgent?: string;
  arbitrationOutcome?: string;
}> {
  return fetcher(endpoints.dealStatus(dealId));
}
