"use client";

import { RefreshCw } from "lucide-react";
import { useState } from "react";
import { useSWRConfig } from "swr";
import { WalletButton } from "@/components/wallet-button";

interface TopBarProps {
  title: string;
  subtitle?: string;
}

export function TopBar({ title, subtitle }: TopBarProps) {
  const { mutate } = useSWRConfig();
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    await mutate(
      (key) => typeof key === "string" && key.startsWith("/api"),
      undefined,
      { revalidate: true }
    );
    setTimeout(() => setRefreshing(false), 600);
  };

  return (
    <div
      className="flex items-center justify-between px-6 py-3 sticky top-0 z-20"
      style={{
        background: "rgba(8,9,10,0.85)",
        backdropFilter: "blur(12px)",
        borderBottom: "1px solid var(--border)",
        height: "var(--topbar-height)",
      }}
    >
      <div>
        <h1 style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-display)" }}>
          {title}
        </h1>
        {subtitle && (
          <p style={{ fontSize: "0.7rem", color: "var(--text-faint)", fontFamily: "var(--font-mono)" }}>
            {subtitle}
          </p>
        )}
      </div>

      <div className="flex items-center gap-3">
        {/* Chain indicators */}
        <div className="flex items-center gap-4 mr-2">
          <ChainIndicator label="Arc" status="live" />
          <ChainIndicator label="GenLayer" status="idle" />
          <ChainIndicator label="Circle" status="live" />
        </div>

        {/* Refresh */}
        <button
          className="btn-ghost"
          onClick={handleRefresh}
          style={{ padding: "6px 10px", fontSize: "0.75rem" }}
        >
          <RefreshCw size={12} className={refreshing ? "animate-spin" : ""} />
          Refresh
        </button>

        {/* Wallet */}
        <WalletButton />
      </div>
    </div>
  );
}

function ChainIndicator({ label, status }: { label: string; status: "live" | "idle" | "error" }) {
  const color = status === "live" ? "var(--success)" : status === "error" ? "var(--danger)" : "var(--text-faint)";
  return (
    <div className="flex items-center gap-1.5">
      <span style={{
        width: 6, height: 6, borderRadius: "50%", background: color,
        boxShadow: status === "live" ? `0 0 0 2px rgba(16,185,129,0.15)` : "none",
        display: "inline-block",
      }} />
      <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
        {label}
      </span>
    </div>
  );
}
