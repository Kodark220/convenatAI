import type { CSSProperties } from "react";
import type { DealStatus } from "./deal-store";

export const DEAL_STATUS_CONFIG: Record<DealStatus, { label: string; style: CSSProperties; order: number }> = {
  open:          { label: "Open",          order: 0, style: { background: "rgba(59,130,246,0.12)",  color: "#60a5fa", border: "1px solid rgba(59,130,246,0.25)"  } },
  negotiating:   { label: "Negotiating",   order: 1, style: { background: "rgba(139,92,246,0.12)", color: "#a78bfa", border: "1px solid rgba(139,92,246,0.25)"  } },
  escrow_funded: { label: "Escrow Funded", order: 2, style: { background: "rgba(245,158,11,0.12)", color: "#fbbf24", border: "1px solid rgba(245,158,11,0.25)"  } },
  executing:     { label: "Executing",     order: 3, style: { background: "rgba(94,106,210,0.12)", color: "#7170ff", border: "1px solid rgba(94,106,210,0.25)"  } },
  verifying:     { label: "Verifying",     order: 4, style: { background: "rgba(6,182,212,0.12)",  color: "#22d3ee", border: "1px solid rgba(6,182,212,0.25)"   } },
  settled:       { label: "Settled",       order: 5, style: { background: "rgba(16,185,129,0.12)", color: "#34d399", border: "1px solid rgba(16,185,129,0.25)"  } },
  disputed:      { label: "Disputed",      order: 5, style: { background: "rgba(239,68,68,0.12)",  color: "#f87171", border: "1px solid rgba(239,68,68,0.25)"   } },
  arbitrating:   { label: "Arbitrating",   order: 5, style: { background: "rgba(239,68,68,0.08)",  color: "#fca5a5", border: "1px solid rgba(239,68,68,0.2)"    } },
  resolved:      { label: "Resolved",      order: 6, style: { background: "rgba(16,185,129,0.08)", color: "#6ee7b7", border: "1px solid rgba(16,185,129,0.15)"  } },
};

export const TIMELINE_STAGES: DealStatus[] = [
  "open", "negotiating", "escrow_funded", "executing", "verifying", "settled",
];

export const EVENT_TYPE_COLORS: Record<string, string> = {
  info:    "#8a8f98",
  success: "#34d399",
  warning: "#fbbf24",
  error:   "#f87171",
  chain:   "#7170ff",
};
