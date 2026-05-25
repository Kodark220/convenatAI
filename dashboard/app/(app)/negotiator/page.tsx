"use client";

import useSWR from "swr";
import { motion } from "framer-motion";
import { Zap, Bot, ShieldCheck, Clock, ExternalLink, DollarSign, CheckCircle, XCircle, Loader2 } from "lucide-react";
import { TopBar } from "@/components/top-bar";
import { endpoints } from "@/lib/rpc";
import { formatUSDC, formatNumber } from "@/lib/utils";

interface NegotiatorStatus {
  agent_name: string;
  status: string;
  active_deals: {
    id: string;
    description: string;
    price: number;
    buyer: string;
    provider: string;
    elapsed_display: string;
    elapsed_seconds: number;
    status: string;
    verdict_in: number;
  }[];
  recent_settlements: {
    id: string;
    description: string;
    price: number;
    outcome: string;
  }[];
  arc_jobs_scanned: number;
  genlayer_jobs_scanned: number;
  wallet_balance: string;
}

const STATUS_BADGE: Record<string, { label: string; color: string; bg: string }> = {
  escrow_locked: { label: "Escrow Locked", color: "#fbbf24", bg: "rgba(245,158,11,0.12)" },
  pending: { label: "Pending", color: "#60a5fa", bg: "rgba(59,130,246,0.12)" },
  released: { label: "Released ✅", color: "#34d399", bg: "rgba(16,185,129,0.12)" },
  refunded: { label: "Refunded", color: "#f87171", bg: "rgba(239,68,68,0.12)" },
};

export default function NegotiatorPage() {
  const { data, error, isLoading } = useSWR<NegotiatorStatus>(endpoints.negotiatorStatus, {
    refreshInterval: 5000,
  });

  return (
    <>
      <TopBar title="NegotiatorNet" subtitle="AI agent escrow + dispute resolution" />

      <div className="p-6 space-y-6">
        {/* ── Status Header ── */}
        <motion.div
          className="card"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          style={{ padding: 24, display: "flex", alignItems: "center", gap: 16, justifyContent: "space-between" }}
        >
          <div className="flex items-center gap-4">
            <div style={{ width: 48, height: 48, borderRadius: 12, background: "var(--accent-glow)", border: "1px solid rgba(113,112,255,0.2)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <ShieldCheck size={22} style={{ color: "var(--accent-bright)" }} />
            </div>
            <div>
              <p style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-display)" }}>
                {data?.agent_name ?? "NegotiatorNet"}
              </p>
              <p style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                Status: <span style={{ color: data?.status === "running" ? "#34d399" : "#f87171" }}>
                  {data?.status === "running" ? "● Running" : "○ Stopped"}
                </span>
                {" · "}Scanning {formatNumber(data?.arc_jobs_scanned ?? 0)} Arc jobs
              </p>
            </div>
          </div>
          <div style={{ textAlign: "right", fontSize: "0.78rem", fontFamily: "var(--font-mono)" }}>
            <p style={{ color: "var(--text-faint)" }}>Wallet Balance</p>
            <p style={{ color: "var(--text-primary)", fontWeight: 700, fontSize: "1rem" }}>
              ${data?.wallet_balance ?? "0.00"} USDC
            </p>
          </div>
        </motion.div>

        {/* ── Active Deals ── */}
        <div>
          <p style={{ fontSize: "0.7rem", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--text-faint)", marginBottom: 12 }}>
            Active Negotiations
          </p>
          {isLoading ? (
            <div className="card" style={{ padding: 40, textAlign: "center" }}>
              <Loader2 size={24} className="animate-spin" style={{ color: "var(--text-faint)", margin: "0 auto" }} />
            </div>
          ) : !data?.active_deals?.length ? (
            <div className="card" style={{ padding: 32, textAlign: "center" }}>
              <Bot size={32} style={{ color: "var(--text-faint)", margin: "0 auto 12px", opacity: 0.4 }} />
              <p style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>No active negotiations</p>
              <p style={{ fontSize: "0.72rem", color: "var(--text-faint)", marginTop: 4 }}>
                Waiting for agents to request a deal...
              </p>
            </div>
          ) : (
            <div className="grid gap-3">
              {data.active_deals.map((deal, i) => {
                const badge = STATUS_BADGE[deal.status] ?? STATUS_BADGE.pending;
                const progress = Math.min(100, (deal.elapsed_seconds / 360) * 100);
                return (
                  <motion.div
                    key={deal.id}
                    className="card"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    style={{ padding: 20 }}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <Zap size={16} style={{ color: "var(--accent-bright)" }} />
                        <p style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-primary)" }}>
                          {deal.description}
                        </p>
                      </div>
                      <span style={{ padding: "3px 10px", borderRadius: 6, fontSize: "0.68rem", fontWeight: 600, fontFamily: "var(--font-mono)", background: badge.bg, color: badge.color, border: `1px solid ${badge.color}33` }}>
                        {badge.label}
                      </span>
                    </div>

                    <div className="grid grid-cols-3 gap-4 mb-3" style={{ fontSize: "0.72rem" }}>
                      <div>
                        <p style={{ color: "var(--text-faint)", marginBottom: 2 }}>Buyer</p>
                        <p style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>{deal.buyer}</p>
                      </div>
                      <div>
                        <p style={{ color: "var(--text-faint)", marginBottom: 2 }}>Provider</p>
                        <p style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>{deal.provider}</p>
                      </div>
                      <div>
                        <p style={{ color: "var(--text-faint)", marginBottom: 2 }}>Amount</p>
                        <p style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono)", fontWeight: 700 }}>
                          ${deal.price.toFixed(2)} USDC
                        </p>
                      </div>
                    </div>

                    {/* Progress bar */}
                    <div style={{ height: 4, borderRadius: 2, background: "var(--border)", overflow: "hidden" }}>
                      <div style={{ width: `${progress}%`, height: "100%", borderRadius: 2, background: progress >= 100 ? "#34d399" : "var(--accent-bright)", transition: "width 2s ease" }} />
                    </div>
                    <div className="flex items-center justify-between mt-1.5">
                      <span style={{ fontSize: "0.65rem", color: "var(--text-faint)", fontFamily: "var(--font-mono)" }}>
                        <Clock size={10} style={{ display: "inline", marginRight: 3 }} />
                        {deal.elapsed_display}
                      </span>
                      {deal.verdict_in > 0 ? (
                        <span style={{ fontSize: "0.65rem", color: "var(--text-faint)", fontFamily: "var(--font-mono)" }}>
                          GenLayer verdict in ~{deal.verdict_in}s
                        </span>
                      ) : (
                        <span style={{ fontSize: "0.65rem", color: "#34d399", fontFamily: "var(--font-mono)" }}>
                          Awaiting settlement...
                        </span>
                      )}
                    </div>
                  </motion.div>
                );
              })}
            </div>
          )}
        </div>

        {/* ── Recent Settlements ── */}
        {data?.recent_settlements?.length > 0 && (
          <div>
            <p style={{ fontSize: "0.7rem", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--text-faint)", marginBottom: 12 }}>
              Recent Settlements
            </p>
            <div className="grid gap-2">
              {data.recent_settlements.map((s) => (
                <div key={s.id} className="card" style={{ padding: 14, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div className="flex items-center gap-3">
                    {s.outcome === "released" ? (
                      <CheckCircle size={16} style={{ color: "#34d399" }} />
                    ) : (
                      <XCircle size={16} style={{ color: "#f87171" }} />
                    )}
                    <div>
                      <p style={{ fontSize: "0.78rem", color: "var(--text-primary)", fontWeight: 500 }}>{s.description}</p>
                      <p style={{ fontSize: "0.68rem", color: "var(--text-faint)", fontFamily: "var(--font-mono)" }}>
                        {s.outcome === "released" ? "Released to provider" : "Refunded to buyer"}
                      </p>
                    </div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <p style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
                      ${s.price.toFixed(2)}
                    </p>
                    <span style={{ padding: "2px 8px", borderRadius: 4, fontSize: "0.6rem", fontWeight: 600, fontFamily: "var(--font-mono)", background: s.outcome === "released" ? "rgba(16,185,129,0.12)" : "rgba(239,68,68,0.12)", color: s.outcome === "released" ? "#34d399" : "#f87171" }}>
                      {s.outcome}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Stats Summary ── */}
        <div className="grid grid-cols-3 gap-4">
          <div className="card" style={{ padding: 20 }}>
            <p style={{ fontSize: "0.65rem", color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }}>Arc Jobs Scanned</p>
            <p style={{ fontSize: "1.3rem", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
              {formatNumber(data?.arc_jobs_scanned ?? 0)}
            </p>
          </div>
          <div className="card" style={{ padding: 20 }}>
            <p style={{ fontSize: "0.65rem", color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }}>Active Deals</p>
            <p style={{ fontSize: "1.3rem", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
              {data?.active_deals?.length ?? 0}
            </p>
          </div>
          <div className="card" style={{ padding: 20 }}>
            <p style={{ fontSize: "0.65rem", color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }}>Settlements</p>
            <p style={{ fontSize: "1.3rem", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
              {data?.recent_settlements?.length ?? 0}
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
