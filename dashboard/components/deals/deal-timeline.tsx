"use client";

import { motion } from "framer-motion";
import { CheckCircle, Circle, Loader } from "lucide-react";
import { TIMELINE_STAGES, DEAL_STATUS_CONFIG } from "@/lib/deal-config";
import type { DealStatus } from "@/lib/deal-store";

interface TimelineProps {
  currentStatus: DealStatus;
}

export function DealTimeline({ currentStatus }: TimelineProps) {
  const currentOrder = DEAL_STATUS_CONFIG[currentStatus]?.order ?? 0;
  const isDisputed = currentStatus === "disputed" || currentStatus === "arbitrating" || currentStatus === "resolved";

  return (
    <div className="card p-6">
      <p style={{ fontSize: "0.7rem", fontWeight: 600, color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 24 }}>
        Deal Lifecycle
      </p>

      <div style={{ position: "relative" }}>
        {/* Connector line */}
        <div style={{
          position: "absolute",
          top: 16,
          left: 16,
          right: 16,
          height: 1,
          background: "var(--border)",
          zIndex: 0,
        }} />

        {/* Progress line */}
        <motion.div
          style={{
            position: "absolute",
            top: 16,
            left: 16,
            height: 1,
            background: isDisputed
              ? "linear-gradient(90deg, #f87171, #ef4444)"
              : "linear-gradient(90deg, var(--accent-bright), #10b981)",
            zIndex: 1,
            transformOrigin: "left",
          }}
          initial={{ width: "0%" }}
          animate={{
            width: isDisputed
              ? "100%"
              : `${Math.min((currentOrder / (TIMELINE_STAGES.length - 1)) * 100, 100)}%`,
          }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        />

        {/* Stages */}
        <div style={{ display: "flex", justifyContent: "space-between", position: "relative", zIndex: 2 }}>
          {TIMELINE_STAGES.map((stage, i) => {
            const config = DEAL_STATUS_CONFIG[stage];
            const isDone = currentOrder > i;
            const isActive = currentOrder === i && !isDisputed;
            const isPending = currentOrder < i && !isDisputed;

            return (
              <div key={stage} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10, flex: 1 }}>
                {/* Node */}
                <motion.div
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    border: "2px solid",
                    borderColor: isDone ? "#10b981" : isActive ? "var(--accent-bright)" : "var(--border)",
                    background: isDone ? "rgba(16,185,129,0.15)" : isActive ? "var(--accent-glow)" : "var(--surface-1)",
                    boxShadow: isActive ? "0 0 16px rgba(113,112,255,0.3)" : "none",
                  }}
                  animate={isActive ? { boxShadow: ["0 0 8px rgba(113,112,255,0.2)", "0 0 20px rgba(113,112,255,0.4)", "0 0 8px rgba(113,112,255,0.2)"] } : {}}
                  transition={{ duration: 2, repeat: Infinity }}
                >
                  {isDone ? (
                    <CheckCircle size={14} style={{ color: "#10b981" }} />
                  ) : isActive ? (
                    <motion.div animate={{ rotate: 360 }} transition={{ duration: 2, repeat: Infinity, ease: "linear" }}>
                      <Loader size={13} style={{ color: "var(--accent-bright)" }} />
                    </motion.div>
                  ) : (
                    <Circle size={12} style={{ color: "var(--text-faint)" }} />
                  )}
                </motion.div>

                {/* Label */}
                <p style={{
                  fontSize: "0.65rem",
                  fontWeight: 600,
                  textAlign: "center",
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  color: isDone ? "#10b981" : isActive ? "var(--accent-bright)" : "var(--text-faint)",
                  lineHeight: 1.3,
                }}>
                  {config.label}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Disputed / Arbitrating / Resolved overlay */}
      {isDisputed && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-5 flex items-center gap-3 px-4 py-3 rounded-lg"
          style={{
            background: currentStatus === "resolved"
              ? "rgba(16,185,129,0.06)"
              : "rgba(239,68,68,0.08)",
            border: `1px solid ${currentStatus === "resolved" ? "rgba(16,185,129,0.2)" : "rgba(239,68,68,0.2)"}`,
          }}
        >
          <motion.div
            style={{
              width: 7, height: 7, borderRadius: "50%", flexShrink: 0,
              background: currentStatus === "resolved" ? "#10b981" : "#ef4444",
            }}
            animate={currentStatus === "arbitrating"
              ? { opacity: [1, 0.2, 1], scale: [1, 1.4, 1] }
              : { opacity: 1 }
            }
            transition={{ duration: 0.8, repeat: Infinity }}
          />
          <p style={{ fontSize: "0.78rem", color: currentStatus === "resolved" ? "var(--success)" : "#f87171" }}>
            {currentStatus === "resolved"
              ? "Dispute resolved — GenLayer arbitration verdict executed on Arc"
              : currentStatus === "arbitrating"
              ? "GenLayer arbitration active — validator nodes evaluating…"
              : "Dispute raised — awaiting GenLayer arbitration"}
          </p>
        </motion.div>
      )}
    </div>
  );
}
