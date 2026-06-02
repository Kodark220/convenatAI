"use client";

import useSWR from "swr";
import { endpoints } from "@/lib/rpc";

export interface LivePreviewStats {
  dealsDone: number;
  activeAgents: number;
  usdcStreamed: number;
  totalJobs: number;
}

export interface LivePreviewJob {
  id: string;
  title?: string;
  status: string;
  amount: string;
  chain: string;
  age: string;
}

export interface LivePreviewAgent {
  address: string;
  role: string;
  jobs: number;
}

export interface LivePreviewEvent {
  message: string;
  color: string;
  t: string;
}

export function useLandingData() {
  const { data: stats, error: statsErr } = useSWR(endpoints.stats, {
    refreshInterval: 30000,
    fallbackData: null,
    onError: () => {},
  });

  const { data: jobs = [], error: jobsErr } = useSWR(endpoints.jobs, {
    refreshInterval: 30000,
    fallbackData: [],
    onError: () => {},
  });

  const { data: agents = [], error: agentsErr } = useSWR(endpoints.agents, {
    refreshInterval: 30000,
    fallbackData: [],
    onError: () => {},
  });

  const { data: negStatus, error: negErr } = useSWR(endpoints.negotiatorStatus, {
    refreshInterval: 30000,
    fallbackData: null,
    onError: () => {},
  });

  const hasError = !!(statsErr || jobsErr || agentsErr || negErr);

  // ── Stats ──
  const liveStats: LivePreviewStats = stats
    ? {
        dealsDone: stats.dealsDone ?? 0,
        activeAgents: stats.activeAgents ?? 0,
        usdcStreamed: stats.usdcStreamed ?? 0,
        totalJobs: stats.totalJobs ?? 0,
      }
    : {
        dealsDone: 0,
        activeAgents: 0,
        usdcStreamed: 0,
        totalJobs: 0,
      };

  // ── Jobs (top 3 recent) ──
  const liveJobs: LivePreviewJob[] = jobs.length > 0
    ? jobs.slice(0, 3).map((j: any) => {
        const ageSec = j.createdAt
          ? Math.floor((Date.now() - j.createdAt * 1000) / 1000)
          : 0;
        const age =
          ageSec < 60
            ? `${ageSec}s ago`
            : ageSec < 3600
              ? `${Math.floor(ageSec / 60)}m ago`
              : `${Math.floor(ageSec / 3600)}h ago`;
        return {
          id: j.id,
          title: j.description || j.title || `Job #${j.id.slice(0, 6)}`,
          status: j.status ?? "open",
          amount: j.usdcAmount ? `$${(j.usdcAmount / 1_000).toFixed(1)}K` : "—",
          chain: j.chain ?? "Arc",
          age,
        };
      })
    : [];

  // ── Agents (top 3) ──
  const liveAgents: LivePreviewAgent[] = agents.length > 0
    ? agents.slice(0, 3).map((a: any) => ({
        address: a.address ?? "0x0000…0000",
        role: a.role ?? "provider",
        jobs: a.jobCount ?? 0,
      }))
    : [];

  // ── Events from negotiator status ──
  const liveEvents: LivePreviewEvent[] = [];
  if (negStatus?.recent_settlements) {
    (negStatus.recent_settlements as any[]).slice(0, 5).forEach((s: any, i: number) => {
      liveEvents.push({
        message: `Settlement · ${s.deal_id ?? s.job_id ?? "unknown"} · $${(s.amount ?? 0).toLocaleString()}`,
        color: "#34d399",
        t: `${i * 2}s`,
      });
    });
  }
  if (negStatus?.active_deals) {
    (negStatus.active_deals as any[]).slice(0, 3).forEach((d: any, i: number) => {
      liveEvents.push({
        message: `ActiveDeal · ${d.job_id ?? d.id ?? "unknown"} · ${d.stage ?? "negotiating"}`,
        color: "#7170ff",
        t: `${i * 3 + 1}s`,
      });
    });
  }
  if (liveEvents.length === 0) {
    // Fallback: derive from recent jobs
    jobs.slice(0, 5).forEach((j: any, i: number) => {
      const chain = j.chain ?? "Arc";
      liveEvents.push({
        message: `Job${j.status === "completed" ? "Completed" : "Created"} · ${j.id?.slice(0, 8) ?? "unknown"} · ${chain}`,
        color: j.status === "completed" ? "#34d399" : "#22d3ee",
        t: `${i * 2}s`,
      });
    });
  }

  return {
    stats: liveStats,
    jobs: liveJobs,
    agents: liveAgents,
    events: liveEvents,
    isLoading: !stats && !hasError,
    hasError,
  };
}
