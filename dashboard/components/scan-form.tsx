"use client";

import { useState } from "react";
import { Search, Loader2, AlertCircle } from "lucide-react";
import type { ChainId, Job } from "@/lib/types";
import { scanJobs } from "@/lib/rpc";

interface ScanFormProps {
  onResults: (jobs: Job[]) => void;
}

export function ScanForm({ onResults }: ScanFormProps) {
  const [chain, setChain] = useState<ChainId>("arc");
  const [fromBlock, setFromBlock] = useState("");
  const [toBlock, setToBlock] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleScan = async () => {
    setLoading(true);
    setError(null);
    try {
      const results = await scanJobs(
        chain,
        Number(fromBlock) || 0,
        Number(toBlock) || 9_999_999
      );
      onResults(results);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Scan failed. Check your RPC connection."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card p-5">
      <h2 className="mb-4" style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text-primary)" }}>
        Scan Chain
      </h2>

      <div className="flex gap-3 items-end flex-wrap">
        {/* Chain selector */}
        <div className="flex flex-col gap-1.5">
          <label style={{ fontSize: "0.65rem", fontWeight: 600, color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Chain
          </label>
          <select
            className="input"
            style={{ width: 150 }}
            value={chain}
            onChange={(e) => setChain(e.target.value as ChainId)}
          >
            <option value="arc">Arc Testnet</option>
            <option value="genlayer">GenLayer</option>
          </select>
        </div>

        {/* From block */}
        <div className="flex flex-col gap-1.5">
          <label style={{ fontSize: "0.65rem", fontWeight: 600, color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            From Block
          </label>
          <input
            type="number"
            placeholder="0"
            className="input"
            style={{ width: 140, fontFamily: "var(--font-mono)" }}
            value={fromBlock}
            onChange={(e) => setFromBlock(e.target.value)}
          />
        </div>

        {/* To block */}
        <div className="flex flex-col gap-1.5">
          <label style={{ fontSize: "0.65rem", fontWeight: 600, color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            To Block
          </label>
          <input
            type="number"
            placeholder="latest"
            className="input"
            style={{ width: 140, fontFamily: "var(--font-mono)" }}
            value={toBlock}
            onChange={(e) => setToBlock(e.target.value)}
          />
        </div>

        {/* Scan button */}
        <button
          className="btn-primary"
          onClick={handleScan}
          disabled={loading}
          style={{ height: 38 }}
        >
          {loading ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
          {loading ? "Scanning…" : "Scan Jobs"}
        </button>
      </div>

      {/* Error message */}
      {error && (
        <div
          className="flex items-center gap-2 mt-4 px-3 py-2 rounded-lg"
          style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)" }}
        >
          <AlertCircle size={13} style={{ color: "var(--danger)", flexShrink: 0 }} />
          <p style={{ fontSize: "0.78rem", color: "var(--danger)", fontFamily: "var(--font-mono)" }}>
            {error}
          </p>
        </div>
      )}
    </div>
  );
}
