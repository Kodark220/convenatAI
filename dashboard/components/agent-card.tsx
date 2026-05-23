"use client";

import { motion } from "framer-motion";
import type { Agent } from "@/lib/types";
import { shortAddress, formatUSDC, roleConfig, chainConfig } from "@/lib/utils";

interface AgentCardProps {
  agent: Agent;
  index?: number;
}

export function AgentCard({ agent, index = 0 }: AgentCardProps) {
  const role = roleConfig[agent.role];
  const chain = chainConfig[agent.chain];

  return (
    <motion.div
      className="card p-4 cursor-pointer"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: index * 0.04, ease: [0.22, 1, 0.36, 1] }}
      whileHover={{ scale: 1.02, y: -2 }}
    >
      {/* Top row */}
      <div className="flex items-start justify-between mb-3">
        {/* Avatar */}
        <div
          className="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold"
          style={{
            background: "var(--surface-3)",
            border: "1px solid var(--border-strong)",
            color: "var(--text-muted)",
            fontFamily: "var(--font-mono)",
          }}
        >
          {agent.address.slice(2, 4).toUpperCase()}
        </div>
        <div className="flex gap-1.5">
          <span className="badge" style={role.style}>{role.label}</span>
          <span className="badge" style={chain.style}>{chain.label}</span>
        </div>
      </div>

      {/* Address */}
      <p className="text-address mb-3" style={{ fontSize: "0.72rem" }}>
        {shortAddress(agent.address, 8)}
      </p>

      {/* Stats */}
      <div className="separator" />
      <div className="pt-3 grid grid-cols-3 gap-2">
        <Stat label="Jobs" value={agent.jobCount.toString()} />
        <Stat label="Active" value={agent.activeJobs.toString()} highlight={agent.activeJobs > 0} />
        <Stat label="Volume" value={formatUSDC(agent.totalUSDC)} />
      </div>
    </motion.div>
  );
}

function Stat({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="text-center">
      <p style={{
        fontSize: "0.82rem",
        fontWeight: 600,
        color: highlight ? "var(--success)" : "var(--text-primary)",
        fontFamily: "var(--font-mono)",
      }}>
        {value}
      </p>
      <p style={{ fontSize: "0.62rem", color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600 }}>
        {label}
      </p>
    </div>
  );
}
