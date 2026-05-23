"use client";

import { use, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft, Play, AlertTriangle, Zap,
  StopCircle, FlaskConical, FlaskConicalOff,
} from "lucide-react";
import { useDealStore } from "@/lib/deal-store";
import { DEAL_STATUS_CONFIG } from "@/lib/deal-config";
import { DealTimeline } from "@/components/deals/deal-timeline";
import { DealEventLog } from "@/components/deals/deal-event-log";
import { EscrowCard, VerificationCard } from "@/components/deals/deal-cards";
import { formatUSDC, shortAddress } from "@/lib/utils";

export default function DealPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const { deals, runDemo, stopDemo, raiseDispute, isDemoRunning, isDemoMode, toggleDemoMode } = useDealStore();
  const deal = deals[id];

  useEffect(() => {
    if (!deal) router.replace("/dashboard");
  }, [deal, router]);

  if (!deal) return null;

  const statusConfig = DEAL_STATUS_CONFIG[deal.status];
  const isTerminal = ["settled", "resolved"].includes(deal.status);
  const isDisputing = ["disputed", "arbitrating"].includes(deal.status);

  // In demo mode: dispute always available unless already terminal or disputing
  // In normal mode: only available during active lifecycle stages
  const canDispute = isDemoMode
    ? !isTerminal && !isDisputing
    : ["escrow_funded", "executing", "verifying"].includes(deal.status);

  const isDemoable = deal.status === "open" || (isDemoMode && !isTerminal && !isDisputing && !isDemoRunning);

  const OUTCOME_LABELS = {
    buyer_refund:  { label: "Buyer Refunded", color: "#60a5fa" },
    seller_payout: { label: "Seller Paid Out", color: "#34d399" },
    split:         { label: "Split Settlement", color: "#fbbf24" },
  };

  return (
    <>
      {/* ── Topbar ── */}
      <div
        className="flex items-center justify-between px-6 py-3 sticky top-0 z-20"
        style={{ background: "rgba(8,9,10,0.9)", backdropFilter: "blur(12px)", borderBottom: "1px solid var(--border)", height: "var(--topbar-height)", gap: 12 }}
      >
        <div className="flex items-center gap-3" style={{ minWidth: 0 }}>
          <button onClick={() => router.back()} className="btn-ghost" style={{ padding: "5px 10px", fontSize: "0.75rem", flexShrink: 0 }}>
            <ArrowLeft size={13} /> Back
          </button>
          <div style={{ width: 1, height: 16, background: "var(--border)", flexShrink: 0 }} />
          <span style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--text-primary)", fontFamily: "var(--font-display)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {deal.title}
          </span>
          <span className="badge" style={{ ...statusConfig.style, flexShrink: 0 }}>{statusConfig.label}</span>
        </div>

        <div className="flex items-center gap-2" style={{ flexShrink: 0 }}>
          {/* Demo mode toggle */}
          <button
            onClick={toggleDemoMode}
            title={isDemoMode ? "Demo Mode ON — click to disable" : "Demo Mode OFF — click to enable"}
            style={{
              display: "flex", alignItems: "center", gap: 5,
              padding: "5px 10px", borderRadius: 7, fontSize: "0.7rem", fontWeight: 600,
              cursor: "pointer", border: "1px solid",
              background: isDemoMode ? "rgba(245,158,11,0.1)" : "transparent",
              borderColor: isDemoMode ? "rgba(245,158,11,0.3)" : "var(--border)",
              color: isDemoMode ? "#fbbf24" : "var(--text-faint)",
              transition: "all 0.15s ease",
            }}
          >
            {isDemoMode ? <FlaskConical size={12} /> : <FlaskConicalOff size={12} />}
            {isDemoMode ? "Demo Mode" : "Live Mode"}
          </button>

          {/* Dispute button — always in demo mode, conditional in live mode */}
          {canDispute && (
            <motion.button
              className="btn-ghost"
              style={{ fontSize: "0.75rem", color: "var(--danger)", borderColor: "rgba(239,68,68,0.3)" }}
              onClick={() => raiseDispute(deal.id, isDemoMode ? "Demo dispute triggered by tester" : "Execution criteria not met")}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.97 }}
            >
              <AlertTriangle size={12} />
              Raise Dispute
            </motion.button>
          )}

          {/* Demo run / stop */}
          {!isTerminal && !isDisputing && (
            <motion.button
              className="btn-primary"
              style={{
                fontSize: "0.78rem", padding: "7px 14px",
                background: isDemoRunning ? "rgba(94,106,210,0.5)" : undefined,
              }}
              onClick={() => isDemoRunning ? stopDemo() : runDemo(deal.id)}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.97 }}
            >
              {isDemoRunning ? <StopCircle size={13} /> : <Play size={13} />}
              {isDemoRunning ? "Stop" : "Run Demo"}
            </motion.button>
          )}
        </div>
      </div>

      <div className="p-6 space-y-5">

        {/* ── Demo mode banner ── */}
        <AnimatePresence>
          {isDemoMode && (
            <motion.div
              initial={{ opacity: 0, y: -8, height: 0 }}
              animate={{ opacity: 1, y: 0, height: "auto" }}
              exit={{ opacity: 0, y: -8, height: 0 }}
              className="flex items-center gap-3 px-4 py-3 rounded-lg"
              style={{ background: "rgba(245,158,11,0.06)", border: "1px solid rgba(245,158,11,0.2)", overflow: "hidden" }}
            >
              <FlaskConical size={13} style={{ color: "#fbbf24", flexShrink: 0 }} />
              <p style={{ fontSize: "0.75rem", color: "#fbbf24", fontFamily: "var(--font-mono)" }}>
                Demo mode enabled — dispute can be triggered at any lifecycle stage
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Running demo banner ── */}
        <AnimatePresence>
          {isDemoRunning && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="flex items-center gap-3 px-4 py-3 rounded-lg"
              style={{ background: "var(--accent-glow)", border: "1px solid rgba(113,112,255,0.25)" }}
            >
              <motion.div
                style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--accent-bright)", flexShrink: 0 }}
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ duration: 1, repeat: Infinity }}
              />
              <p style={{ fontSize: "0.78rem", color: "var(--accent-bright)", fontFamily: "var(--font-mono)" }}>
                Autonomous deal simulation running — you can raise a dispute at any time to test arbitration…
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Arbitration banner ── */}
        <AnimatePresence>
          {isDisputing && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="flex items-center gap-3 px-4 py-3 rounded-lg"
              style={{ background: "rgba(239,68,68,0.07)", border: "1px solid rgba(239,68,68,0.25)" }}
            >
              <motion.div
                style={{ width: 8, height: 8, borderRadius: "50%", background: "#ef4444", flexShrink: 0 }}
                animate={{ opacity: [1, 0.2, 1], scale: [1, 1.3, 1] }}
                transition={{ duration: 0.8, repeat: Infinity }}
              />
              <p style={{ fontSize: "0.78rem", color: "#f87171", fontFamily: "var(--font-mono)" }}>
                {deal.status === "arbitrating"
                  ? "GenLayer arbitration in progress — validator nodes evaluating dispute…"
                  : "Dispute raised — initialising GenLayer arbitration…"}
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Deal header ── */}
        <div className="card p-5">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
            <HeaderStat label="Budget" value={formatUSDC(deal.budget)} highlight />
            <HeaderStat label="Chain" value={deal.chain === "arc" ? "Arc Testnet" : "GenLayer"} mono />
            <HeaderStat label="Buyer Agent" value={shortAddress(deal.buyerAgent, 8)} mono />
            <HeaderStat
              label="Seller Agent"
              value={deal.sellerAgent === "—" ? "Matching…" : shortAddress(deal.sellerAgent, 8)}
              mono
              muted={deal.sellerAgent === "—"}
            />
          </div>
          {deal.description && (
            <p style={{ marginTop: 16, fontSize: "0.8rem", color: "var(--text-muted)", lineHeight: 1.6, paddingTop: 16, borderTop: "1px solid var(--border)" }}>
              {deal.description}
            </p>
          )}
        </div>

        {/* ── Timeline ── */}
        <DealTimeline currentStatus={deal.status} />

        {/* ── Arbitration outcome card ── */}
        <AnimatePresence>
          {deal.status === "resolved" && deal.arbitrationOutcome && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="card p-5"
              style={{ border: "1px solid rgba(239,68,68,0.2)", background: "rgba(239,68,68,0.03)" }}
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p style={{ fontSize: "0.65rem", fontWeight: 600, color: "var(--danger)", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 4 }}>
                    Arbitration Complete
                  </p>
                  <p style={{ fontSize: "0.9rem", fontWeight: 700, color: "var(--text-primary)" }}>
                    GenLayer Verdict
                  </p>
                </div>
                <span
                  className="badge"
                  style={{
                    background: `${OUTCOME_LABELS[deal.arbitrationOutcome].color}18`,
                    color: OUTCOME_LABELS[deal.arbitrationOutcome].color,
                    border: `1px solid ${OUTCOME_LABELS[deal.arbitrationOutcome].color}33`,
                  }}
                >
                  {OUTCOME_LABELS[deal.arbitrationOutcome].label}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-4" style={{ paddingTop: 12, borderTop: "1px solid var(--border)" }}>
                <OutcomeDetail label="Dispute Reason" value={deal.disputeReason ?? "Not specified"} />
                <OutcomeDetail label="Settlement Tx" value={deal.settlementTx ? `${deal.settlementTx.slice(0, 12)}…` : "—"} mono />
                <OutcomeDetail label="Resolved By" value="GenLayer Testnet" />
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Escrow + Verification ── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <EscrowCard deal={deal} />
          <VerificationCard deal={deal} />
        </div>

        {/* ── Event log ── */}
        <DealEventLog events={[...deal.events].reverse()} />

        {/* ── Settled CTA ── */}
        <AnimatePresence>
          {deal.status === "settled" && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="card p-6 text-center"
              style={{ border: "1px solid rgba(16,185,129,0.2)", background: "rgba(16,185,129,0.04)" }}
            >
              <p style={{ fontSize: "0.7rem", fontWeight: 600, color: "var(--success)", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>
                Deal Complete
              </p>
              <p style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: 4 }}>
                {formatUSDC(deal.budget)} settled autonomously
              </p>
              <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginBottom: 20 }}>
                No human intervention required. Verified by GenLayer, settled on Arc.
              </p>
              <button className="btn-primary" onClick={() => useDealStore.getState().openModal()}>
                <Zap size={13} />
                Create Another Deal
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </>
  );
}

function HeaderStat({ label, value, highlight, mono, muted }: {
  label: string; value: string; highlight?: boolean; mono?: boolean; muted?: boolean;
}) {
  return (
    <div>
      <p style={{ fontSize: "0.65rem", fontWeight: 600, color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 5 }}>{label}</p>
      <p style={{
        fontSize: highlight ? "1.1rem" : "0.82rem",
        fontWeight: highlight ? 700 : 500,
        color: highlight ? "var(--text-primary)" : muted ? "var(--text-faint)" : "var(--text-muted)",
        fontFamily: mono ? "var(--font-mono)" : "var(--font-display)",
      }}>
        {value}
      </p>
    </div>
  );
}

function OutcomeDetail({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <p style={{ fontSize: "0.62rem", fontWeight: 600, color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }}>{label}</p>
      <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontFamily: mono ? "var(--font-mono)" : undefined }}>{value}</p>
    </div>
  );
}
