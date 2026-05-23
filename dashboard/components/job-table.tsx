"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { Job, ChainId } from "@/lib/types";
import { shortAddress, shortHash, formatUSDC, timeAgo, statusConfig, chainConfig } from "@/lib/utils";

interface JobTableProps {
  jobs: Job[];
}

type Tab = "all" | ChainId;

const TABS: { id: Tab; label: string }[] = [
  { id: "all", label: "All Jobs" },
  { id: "arc", label: "Arc" },
  { id: "genlayer", label: "GenLayer" },
];

export function JobTable({ jobs }: JobTableProps) {
  const [activeTab, setActiveTab] = useState<Tab>("all");

  const filtered = activeTab === "all" ? jobs : jobs.filter((j) => j.chain === activeTab);

  return (
    <div className="card">
      {/* Header */}
      <div className="px-5 pt-5 pb-0">
        <div className="flex items-center justify-between mb-4">
          <h2 style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text-primary)" }}>
            Recent Jobs
          </h2>
          <span style={{ fontSize: "0.72rem", color: "var(--text-faint)", fontFamily: "var(--font-mono)" }}>
            {filtered.length} jobs
          </span>
        </div>

        {/* Tabs */}
        <div className="flex gap-1" style={{ borderBottom: "1px solid var(--border)" }}>
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: "6px 14px",
                fontSize: "0.78rem",
                fontWeight: 500,
                fontFamily: "var(--font-display)",
                border: "none",
                background: "transparent",
                cursor: "pointer",
                color: activeTab === tab.id ? "var(--accent-bright)" : "var(--text-faint)",
                borderBottom: activeTab === tab.id ? "2px solid var(--accent-bright)" : "2px solid transparent",
                marginBottom: -1,
                transition: "all 0.15s ease",
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              <th>Job ID</th>
              <th>Buyer</th>
              <th>Seller</th>
              <th>Amount</th>
              <th>Chain</th>
              <th>Status</th>
              <th>Age</th>
              <th>Tx</th>
            </tr>
          </thead>
          <tbody>
            <AnimatePresence mode="popLayout" initial={false}>
              {filtered.map((job) => {
                const s = statusConfig[job.status];
                const c = chainConfig[job.chain];
                return (
                  <motion.tr
                    key={job.id}
                    layout
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 8 }}
                    transition={{ duration: 0.2 }}
                  >
                    <td>
                      <span className="text-address">{job.streamId}</span>
                    </td>
                    <td>
                      <span className="text-address">{shortAddress(job.buyer)}</span>
                    </td>
                    <td>
                      <span className="text-address">{shortAddress(job.seller)}</span>
                    </td>
                    <td>
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem", color: "var(--text-primary)", fontWeight: 500 }}>
                        {formatUSDC(job.usdcAmount)}
                      </span>
                    </td>
                    <td>
                      <span className="badge" style={c.style}>{c.label}</span>
                    </td>
                    <td>
                      <span className="badge" style={s.style}>{s.label}</span>
                    </td>
                    <td>
                      <span style={{ fontSize: "0.72rem", color: "var(--text-faint)", fontFamily: "var(--font-mono)" }}>
                        {timeAgo(job.createdAt)}
                      </span>
                    </td>
                    <td>
                      {job.txHash && (
                        <span className="text-address" title={job.txHash}>
                          {shortHash(job.txHash)}
                        </span>
                      )}
                    </td>
                  </motion.tr>
                );
              })}
            </AnimatePresence>
          </tbody>
        </table>
      </div>
    </div>
  );
}
