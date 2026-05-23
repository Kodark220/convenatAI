"use client";

import { motion } from "framer-motion";
import { ShieldCheck, Lock, CheckCircle, XCircle, Clock } from "lucide-react";
import type { Deal } from "@/lib/deal-store";
import { formatUSDC, shortHash } from "@/lib/utils";

// ─── Escrow Card ─────────────────────────────────────────────────────────────

export function EscrowCard({ deal }: { deal: Deal }) {
  const funded = ["escrow_funded", "executing", "verifying", "settled", "disputed", "arbitrating", "resolved"].includes(deal.status);
  const settled = deal.status === "settled" || deal.status === "resolved";

  return (
    <div className="card p-5">
      <div className="flex items-center gap-2 mb-4">
        <div style={{ width: 28, height: 28, borderRadius: 7, background: funded ? "rgba(245,158,11,0.12)" : "var(--surface-3)", border: `1px solid ${funded ? "rgba(245,158,11,0.25)" : "var(--border)"}`, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Lock size={13} style={{ color: funded ? "#fbbf24" : "var(--text-faint)" }} />
        </div>
        <p style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--text-primary)" }}>Escrow</p>
        <span className="badge" style={{ marginLeft: "auto", ...(funded ? { background: "rgba(245,158,11,0.1)", color: "#fbbf24", border: "1px solid rgba(245,158,11,0.2)" } : { background: "var(--surface-3)", color: "var(--text-faint)", border: "1px solid var(--border)" }) }}>
          {settled ? "Released" : funded ? "Locked" : "Pending"}
        </span>
      </div>

      <div className="space-y-3">
        <EscrowRow label="Amount">
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "1.1rem", fontWeight: 700, color: funded ? "#fbbf24" : "var(--text-faint)" }}>
            {formatUSDC(deal.budget)}
          </span>
        </EscrowRow>
        <EscrowRow label="Chain">
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.78rem", color: "var(--text-muted)" }}>
            {deal.chain === "arc" ? "Arc Testnet" : "GenLayer"}
          </span>
        </EscrowRow>
        <EscrowRow label="Tx Hash">
          {deal.escrowTx ? (
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--accent-bright)" }}>
              {shortHash(deal.escrowTx)}
            </span>
          ) : (
            <span style={{ fontSize: "0.72rem", color: "var(--text-faint)" }}>Awaiting funding…</span>
          )}
        </EscrowRow>
        {deal.settlementTx && (
          <EscrowRow label="Settlement Tx">
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "#34d399" }}>
              {shortHash(deal.settlementTx)}
            </span>
          </EscrowRow>
        )}
      </div>

      {funded && !settled && (
        <motion.div
          className="mt-4 flex items-center gap-2"
          animate={{ opacity: [0.6, 1, 0.6] }}
          transition={{ duration: 2, repeat: Infinity }}
          style={{ padding: "8px 10px", borderRadius: 8, background: "rgba(245,158,11,0.06)", border: "1px solid rgba(245,158,11,0.12)" }}
        >
          <motion.div style={{ width: 6, height: 6, borderRadius: "50%", background: "#fbbf24" }} animate={{ opacity: [1, 0.3, 1] }} transition={{ duration: 1.5, repeat: Infinity }} />
          <span style={{ fontSize: "0.7rem", color: "#fbbf24", fontFamily: "var(--font-mono)" }}>USDC locked in ConvenatContract</span>
        </motion.div>
      )}
    </div>
  );
}

function EscrowRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <span style={{ fontSize: "0.68rem", color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.07em", fontWeight: 600 }}>{label}</span>
      {children}
    </div>
  );
}

// ─── Verification Card ────────────────────────────────────────────────────────

export function VerificationCard({ deal }: { deal: Deal }) {
  const verifying = deal.status === "verifying";
  const verified = deal.status === "settled" || deal.status === "resolved";
  const score = deal.verificationScore;

  return (
    <div className="card p-5">
      <div className="flex items-center gap-2 mb-4">
        <div style={{ width: 28, height: 28, borderRadius: 7, background: verified ? "rgba(16,185,129,0.12)" : "var(--surface-3)", border: `1px solid ${verified ? "rgba(16,185,129,0.25)" : "var(--border)"}`, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <ShieldCheck size={13} style={{ color: verified ? "#34d399" : "var(--text-faint)" }} />
        </div>
        <p style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--text-primary)" }}>GenLayer Verification</p>
        <span className="badge" style={{ marginLeft: "auto", ...(verified ? { background: "rgba(16,185,129,0.1)", color: "#34d399", border: "1px solid rgba(16,185,129,0.2)" } : verifying ? { background: "rgba(6,182,212,0.1)", color: "#22d3ee", border: "1px solid rgba(6,182,212,0.2)" } : { background: "var(--surface-3)", color: "var(--text-faint)", border: "1px solid var(--border)" }) }}>
          {verified ? "Approved" : verifying ? "Checking…" : "Pending"}
        </span>
      </div>

      <div className="space-y-3">
        <div>
          <p style={{ fontSize: "0.65rem", color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.07em", fontWeight: 600, marginBottom: 6 }}>Criteria</p>
          <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", lineHeight: 1.5 }}>{deal.criteria || "—"}</p>
        </div>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: "0.68rem", color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.07em", fontWeight: 600 }}>SLA Score</span>
          {score !== undefined ? (
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <div style={{ width: 60, height: 4, borderRadius: 2, background: "var(--surface-3)", overflow: "hidden" }}>
                <motion.div
                  style={{ height: "100%", background: score >= 90 ? "#34d399" : score >= 70 ? "#fbbf24" : "#f87171", borderRadius: 2 }}
                  initial={{ width: 0 }}
                  animate={{ width: `${score}%` }}
                  transition={{ duration: 0.8 }}
                />
              </div>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.78rem", fontWeight: 600, color: score >= 90 ? "#34d399" : "#fbbf24" }}>{score}/100</span>
            </div>
          ) : (
            <span style={{ fontSize: "0.72rem", color: "var(--text-faint)" }}>
              {verifying ? "Evaluating…" : "Not started"}
            </span>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: "0.68rem", color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.07em", fontWeight: 600 }}>Result</span>
          {verified ? (
            <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
              <CheckCircle size={13} style={{ color: "#34d399" }} />
              <span style={{ fontSize: "0.75rem", color: "#34d399", fontFamily: "var(--font-mono)" }}>Approved</span>
            </div>
          ) : verifying ? (
            <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
              <Clock size={12} style={{ color: "#22d3ee" }} />
              <span style={{ fontSize: "0.75rem", color: "#22d3ee", fontFamily: "var(--font-mono)" }}>In progress</span>
            </div>
          ) : (
            <span style={{ fontSize: "0.72rem", color: "var(--text-faint)" }}>—</span>
          )}
        </div>
      </div>
    </div>
  );
}
