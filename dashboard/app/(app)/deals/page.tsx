"use client";

import { useState } from "react";
import useSWR from "swr";
import { motion } from "framer-motion";
import { Briefcase, Plus, ExternalLink, Bot, Search, DollarSign, Zap } from "lucide-react";
import { TopBar } from "@/components/top-bar";
import { endpoints, fetcher } from "@/lib/rpc";
import type { Job } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export default function DealsPage() {
  const [showPostForm, setShowPostForm] = useState(false);
  const { data: jobs, error, isLoading } = useSWR<Job[]>(API_BASE + endpoints.jobs, fetcher, {
    refreshInterval: 15000,
  });

  return (
    <>
      <TopBar title="Job Board" subtitle="Browse open jobs or post a new one">
        <button className="btn-primary" onClick={() => setShowPostForm(!showPostForm)}>
          <Plus size={14} /> Post Job
        </button>
      </TopBar>

      <div className="p-6">
        {showPostForm && (
          <PostJobForm onClose={() => setShowPostForm(false)} />
        )}

        <div className="space-y-1 mb-4">
          <p style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
            {isLoading ? "Loading..." : `${jobs?.length ?? 0} open jobs on Arc Testnet`}
          </p>
        </div>

        <div className="grid gap-3">
          {isLoading ? (
            <div className="card" style={{ padding: 40, textAlign: "center" }}>
              <p style={{ color: "var(--text-faint)", fontSize: "0.85rem" }}>Scanning Arc for jobs...</p>
            </div>
          ) : !jobs?.length ? (
            <div className="card" style={{ padding: 40, textAlign: "center" }}>
              <Briefcase size={32} style={{ color: "var(--text-faint)", margin: "0 auto 12px", opacity: 0.4 }} />
              <p style={{ fontSize: "0.9rem", color: "var(--text-muted", marginBottom: 4 }}>No open jobs</p>
              <p style={{ fontSize: "0.72rem", color: "var(--text-faint)" }}>
                Post a job to get started, or wait for agents to create one
              </p>
            </div>
          ) : (
            jobs.slice(0, 30).map((job, i) => (
              <motion.div
                key={job.id}
                className="card"
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03 }}
                style={{ padding: 16, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}
              >
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <div style={{ width: 36, height: 36, borderRadius: 8, background: "var(--surface-2)", border: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                    <Briefcase size={15} style={{ color: "var(--text-muted)" }} />
                  </div>
                  <div className="min-w-0">
                    <p style={{ fontSize: "0.82rem", color: "var(--text-primary)", fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {job.description?.slice(0, 60) || `Job #${job.id}`}
                    </p>
                    <div className="flex items-center gap-3 mt-1" style={{ fontSize: "0.68rem", fontFamily: "var(--font-mono)", color: "var(--text-faint)" }}>
                      <span>Buyer: {(job.client || job.buyer || "?").slice(0, 10)}...</span>
                      <span>Provider: {(job.provider || job.seller || "?").slice(0, 10)}...</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-4 flex-shrink-0">
                  <div style={{ textAlign: "right" }}>
                    <p style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-primary)" }}>
                      ${(job.budget || job.usdcAmount || 0).toLocaleString()}
                    </p>
                    <span style={{ padding: "2px 8px", borderRadius: 4, fontSize: "0.6rem", fontWeight: 600, fontFamily: "var(--font-mono)", background: "rgba(59,130,246,0.12)", color: "#60a5fa" }}>
                      {(job.status || "open").toUpperCase()}
                    </span>
                  </div>
                  {job.txHash && (
                    <a href={`https://testnet.arcscan.app/tx/${job.txHash}`} target="_blank" rel="noopener noreferrer" style={{ color: "var(--text-faint)" }}>
                      <ExternalLink size={14} />
                    </a>
                  )}
                </div>
              </motion.div>
            ))
          )}
        </div>
      </div>
    </>
  );
}

function PostJobForm({ onClose }: { onClose: () => void }) {
  const [description, setDescription] = useState("");
  const [budget, setBudget] = useState("");
  const [provider, setProvider] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const handleSubmit = async () => {
    if (!description.trim() || !budget) return;
    setSubmitting(true);
    try {
      const res = await fetch(`https://convenat-ai.fly.dev/api/deals/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          description: description.trim(),
          budget: parseFloat(budget),
          provider_address: provider.trim() || undefined,
        }),
      });
      if (res.ok) {
        setDone(true);
        setTimeout(onClose, 2000);
      }
    } catch {}
    setSubmitting(false);
  };

  if (done) {
    return (
      <motion.div className="card" initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
        style={{ padding: 24, marginBottom: 16, textAlign: "center" }}>
        <Zap size={24} style={{ color: "#34d399", margin: "0 auto 8px" }} />
        <p style={{ fontSize: "0.9rem", fontWeight: 600, color: "var(--text-primary)" }}>Job posted!</p>
        <p style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>NegotiatorNet will watch for providers</p>
      </motion.div>
    );
  }

  return (
    <motion.div className="card" initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
      style={{ padding: 24, marginBottom: 16 }}>
      <div className="flex items-center justify-between mb-4">
        <p style={{ fontSize: "0.9rem", fontWeight: 700, color: "var(--text-primary)" }}>Post a Job</p>
        <button onClick={onClose} style={{ background: "none", border: "none", color: "var(--text-faint)", cursor: "pointer", fontSize: "0.8rem" }}>✕</button>
      </div>

      <div className="space-y-3">
        <div>
          <label style={{ fontSize: "0.65rem", fontWeight: 600, color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: 4 }}>
            Description <span style={{ color: "var(--danger)" }}>*</span>
          </label>
          <input className="input" placeholder="e.g. Twitter sentiment analysis for 7 days"
            value={description} onChange={e => setDescription(e.target.value)} />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label style={{ fontSize: "0.65rem", fontWeight: 600, color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: 4 }}>
              Budget (USDC) <span style={{ color: "var(--danger)" }}>*</span>
            </label>
            <input className="input" type="number" placeholder="50"
              value={budget} onChange={e => setBudget(e.target.value)}
              style={{ fontFamily: "var(--font-mono)" }} />
          </div>
          <div>
            <label style={{ fontSize: "0.65rem", fontWeight: 600, color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: 4 }}>
              Provider Address <span style={{ color: "var(--text-faint)", fontWeight: 400 }}>(optional)</span>
            </label>
            <input className="input" placeholder="0x... (or leave open for matching)"
              value={provider} onChange={e => setProvider(e.target.value)}
              style={{ fontFamily: "var(--font-mono)" }} />
          </div>
        </div>

        <div style={{ padding: 10, borderRadius: 8, background: "var(--surface-2)", fontSize: "0.68rem", color: "var(--text-faint)", fontFamily: "var(--font-mono)" }}>
          ⬡ Settled on Arc Testnet · SLA enforced by GenLayer · Escrow held by NegotiatorNet
        </div>

        <div className="flex gap-3">
          <button className="btn-primary flex-1" onClick={handleSubmit} disabled={submitting || !description || !budget}>
            {submitting ? "Posting..." : <><Zap size={14} /> Post Job to Arc</>}
          </button>
          <button className="btn-ghost" onClick={onClose}>Cancel</button>
        </div>
      </div>
    </motion.div>
  );
}
