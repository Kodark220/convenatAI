"use client";

import { motion } from "framer-motion";
import { ExternalLink } from "lucide-react";
import type { ChainInfo } from "@/lib/types";
import { shortAddress } from "@/lib/utils";

interface ChainCardProps {
  chain: ChainInfo;
  index?: number;
}

export function ChainCard({ chain, index = 0 }: ChainCardProps) {
  const isLive = chain.status === "live";

  return (
    <motion.div
      className="card p-5"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.2 + index * 0.07, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          {isLive ? (
            <motion.span
              className="live-dot"
              animate={{ opacity: [1, 0.3, 1] }}
              transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
            />
          ) : (
            <span className="idle-dot" />
          )}
          <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--text-primary)" }}>
            {chain.name}
          </span>
        </div>
        <span
          className="badge"
          style={{
            background: isLive ? "var(--success-glow)" : "rgba(255,255,255,0.04)",
            color: isLive ? "var(--success)" : "var(--text-faint)",
            border: `1px solid ${isLive ? "rgba(16,185,129,0.2)" : "var(--border)"}`,
          }}
        >
          {chain.status}
        </span>
      </div>

      <div className="space-y-2">
        <Row label="Contract" value={shortAddress(chain.contract)} mono />
        {chain.blockNumber && (
          <Row label="Block" value={`#${chain.blockNumber.toLocaleString()}`} mono />
        )}
        <Row label="RPC" value={chain.rpc.replace("https://", "")} mono />
      </div>

      {chain.explorerUrl && (
        <a
          href={chain.explorerUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-4 flex items-center gap-1.5 btn-ghost w-full justify-center"
          style={{ fontSize: "0.75rem" }}
        >
          <ExternalLink size={11} />
          Explorer
        </a>
      )}
    </motion.div>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span style={{ fontSize: "0.7rem", color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600 }}>
        {label}
      </span>
      <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", fontFamily: mono ? "var(--font-mono)" : undefined }}>
        {value}
      </span>
    </div>
  );
}
