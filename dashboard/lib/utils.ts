import type { CSSProperties } from "react";
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { JobStatus, AgentRole, ChainId } from "./types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function shortAddress(address: string, chars = 6): string {
  if (!address) return "";
  return `${address.slice(0, chars)}…${address.slice(-4)}`;
}

export function shortHash(hash: string): string {
  return shortAddress(hash, 10);
}

export function formatUSDC(amount: number): string {
  if (amount >= 1_000_000) return `$${(amount / 1_000_000).toFixed(2)}M`;
  if (amount >= 1_000) return `$${(amount / 1_000).toFixed(1)}K`;
  return `$${amount.toLocaleString()}`;
}

export function formatNumber(n: number): string {
  return n.toLocaleString();
}

export function timeAgo(timestamp: number): string {
  const seconds = Math.floor((Date.now() - timestamp) / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export function formatTimestamp(timestamp: number): string {
  return new Date(timestamp).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ─── Status colors — inline styles to guarantee no Tailwind purge ─────────────

export const statusConfig: Record<JobStatus, { label: string; style: CSSProperties }> = {
  open:      { label: "Open",      style: { background: "rgba(59,130,246,0.12)",  color: "#60a5fa", border: "1px solid rgba(59,130,246,0.2)"  } },
  active:    { label: "Active",    style: { background: "rgba(16,185,129,0.12)",  color: "#34d399", border: "1px solid rgba(16,185,129,0.2)"  } },
  completed: { label: "Completed", style: { background: "rgba(100,116,139,0.12)", color: "#94a3b8", border: "1px solid rgba(100,116,139,0.2)" } },
  failed:    { label: "Failed",    style: { background: "rgba(239,68,68,0.12)",   color: "#f87171", border: "1px solid rgba(239,68,68,0.2)"   } },
  disputed:  { label: "Disputed",  style: { background: "rgba(245,158,11,0.12)",  color: "#fbbf24", border: "1px solid rgba(245,158,11,0.2)"  } },
};

export const roleConfig: Record<AgentRole, { label: string; style: CSSProperties }> = {
  client:     { label: "Client",     style: { background: "rgba(139,92,246,0.12)",  color: "#a78bfa", border: "1px solid rgba(139,92,246,0.2)"  } },
  provider:   { label: "Provider",   style: { background: "rgba(6,182,212,0.12)",   color: "#22d3ee", border: "1px solid rgba(6,182,212,0.2)"   } },
  arbitrator: { label: "Arbitrator", style: { background: "rgba(245,158,11,0.12)",  color: "#fbbf24", border: "1px solid rgba(245,158,11,0.2)"  } },
};

export const chainConfig: Record<ChainId, { label: string; dot: string; style: CSSProperties }> = {
  arc: {
    label: "Arc",
    dot: "#10b981",
    style: { background: "rgba(94,106,210,0.12)", color: "#7170ff", border: "1px solid rgba(94,106,210,0.2)" },
  },
  genlayer: {
    label: "GenLayer",
    dot: "#8a8f98",
    style: { background: "rgba(100,116,139,0.12)", color: "#cbd5e1", border: "1px solid rgba(100,116,139,0.2)" },
  },
};

