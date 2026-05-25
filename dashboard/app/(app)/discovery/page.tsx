"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { TopBar } from "@/components/top-bar";
import { ScanForm } from "@/components/scan-form";
import type { Job } from "@/lib/types";
import { endpoints } from "@/lib/rpc";
import { shortAddress, formatUSDC, timeAgo, statusConfig, chainConfig } from "@/lib/utils";
import { useDealStore } from "@/lib/deal-store";

type FilterTab = "all" | "open" | "my";

const FILTER_TABS: { id: FilterTab; label: string }[] = [
  { id: "all", label: "All Jobs" },
  { id: "open", label: "Open Only" },
  { id: "my", label: "My Deals" },
];

export default function DiscoveryPage() {
  const router = useRouter();
  const createDeal = useDealStore((s) => s.createDeal);
  const { data: initialJobs = [] } = useSWR<Job[]>(endpoints.jobs);
  const [scanResults, setScanResults] = useState<Job[] | null>(null);
  const [activeFilter, setActiveFilter] = useState<FilterTab>("all");
  const [acceptingId, setAcceptingId] = useState<string | null>(null);

  const handleAccept = (job: Job) => {
    setAcceptingId(job.id);
    const deal = createDeal({
      title: `Job: ${job.streamId}`,
      description: `Accepted from Discovery — buyer ${job.buyer}, seller ${job.seller}`,
      budget: job.usdcAmount ?? 0,
      deadline: new Date(Date.now() + 7 * 86400000).toISOString().split("T")[0],
      criteria: job.criteria ?? "Execution must meet agreed SLA",
      chain: job.chain,
    });
    router.push(`/deals/${deal.id}`);
  };

  const jobs = scanResults ?? initialJobs;

  const filtered = jobs.filter((j) => {
    if (activeFilter === "open") return j.status === "open";
    // "my" would filter by connected wallet — leave as all for now
    return true;
  });

  return (
    <>
      <TopBar title="Discovery" subtitle="Scan chains for available jobs" />

      <div className="p-6 space-y-5">
        {/* Scan form */}
        <ScanForm onResults={setScanResults} />

        {/* Results */}
        <div className="card">
          {/* Filter tabs */}
          <div className="px-5 pt-5 pb-0">
            <div className="flex items-center justify-between mb-3">
              <h2 style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text-primary)" }}>
                {scanResults ? "Scan Results" : "Recent Jobs"}
              </h2>
              {scanResults && (
                <button
                  className="btn-ghost"
                  style={{ fontSize: "0.72rem", padding: "4px 10px" }}
                  onClick={() => setScanResults(null)}
                >
                  Clear scan
                </button>
              )}
            </div>

            <div className="flex gap-1" style={{ borderBottom: "1px solid var(--border)" }}>
              {FILTER_TABS.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveFilter(tab.id)}
                  style={{
                    padding: "6px 14px",
                    fontSize: "0.78rem",
                    fontWeight: 500,
                    fontFamily: "var(--font-display)",
                    border: "none",
                    background: "transparent",
                    cursor: "pointer",
                    color: activeFilter === tab.id ? "var(--accent-bright)" : "var(--text-faint)",
                    borderBottom: activeFilter === tab.id ? "2px solid var(--accent-bright)" : "2px solid transparent",
                    marginBottom: -1,
                    transition: "all 0.15s ease",
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Job list */}
          <div className="p-5 space-y-2">
            <AnimatePresence mode="popLayout">
              {filtered.length === 0 ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="py-12 text-center"
                >
                  <p style={{ color: "var(--text-faint)", fontSize: "0.825rem" }}>
                    No jobs found. Run a scan to discover jobs on-chain.
                  </p>
                </motion.div>
              ) : (
                filtered.map((job, i) => {
                  const s = statusConfig[job.status];
                  const c = chainConfig[job.chain];
                  return (
                    <motion.div
                      key={job.id}
                      layout
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.97 }}
                      transition={{ duration: 0.25, delay: i * 0.03 }}
                      className="card-surface p-4 flex items-center gap-4 cursor-pointer"
                      style={{ transition: "border-color 0.15s ease" }}
                      onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--border-strong)")}
                      onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
                    >
                      {/* Status dot */}
                      <div
                        style={{
                          width: 8, height: 8, borderRadius: "50%", flexShrink: 0,
                          background: job.status === "open" ? "#5e6ad2" : job.status === "active" ? "var(--success)" : "var(--text-faint)",
                        }}
                      />

                      {/* Job info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--text-primary)" }}>
                            {job.streamId}
                          </span>
                          <span className="badge" style={c.style}>{c.label}</span>
                          <span className="badge" style={s.style}>{s.label}</span>
                        </div>
                        <p style={{ fontSize: "0.7rem", color: "var(--text-faint)", fontFamily: "var(--font-mono)" }}>
                          {shortAddress(job.buyer)} → {shortAddress(job.seller)}
                        </p>
                      </div>

                      {/* Amount + time */}
                      <div className="text-right shrink-0">
                        <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.82rem", fontWeight: 600, color: "var(--text-primary)" }}>
                          {formatUSDC(job.usdcAmount)}
                        </p>
                        <p style={{ fontSize: "0.65rem", color: "var(--text-faint)", fontFamily: "var(--font-mono)" }}>
                          {timeAgo(job.createdAt)}
                        </p>
                      </div>

                      {/* Action */}
                      {job.status === "open" && (
                        <button
                          className="btn-primary"
                          style={{ fontSize: "0.72rem", padding: "5px 12px", flexShrink: 0, opacity: acceptingId === job.id ? 0.6 : 1 }}
                          disabled={acceptingId === job.id}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleAccept(job);
                          }}
                        >
                          {acceptingId === job.id ? "Opening…" : "Accept"}
                        </button>
                      )}
                    </motion.div>
                  );
                })
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </>
  );
}

