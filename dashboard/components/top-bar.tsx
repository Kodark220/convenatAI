"use client";

import { RefreshCw, Zap } from "lucide-react";
import { useEffect, useState } from "react";
import useSWR from "swr";
import { useSWRConfig } from "swr";
import { WalletButton } from "@/components/wallet-button";
import { endpoints } from "@/lib/rpc";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

interface TopBarProps {
  title: string;
  subtitle?: string;
  children?: React.ReactNode;
}

export function TopBar({ title, subtitle, children }: TopBarProps) {
  const { mutate } = useSWRConfig();
  const [refreshing, setRefreshing] = useState(false);
  const [mode, setMode] = useState<"live" | "demo">("live");
  const [loadingMode, setLoadingMode] = useState(true);

  useEffect(() => {
    if (!API_BASE) return;
    fetch(`${API_BASE}/api/negotiator/mode`)
      .then(r => r.json())
      .then(d => { setMode(d.mode); setLoadingMode(false); })
      .catch(() => setLoadingMode(false));
  }, []);

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
      <div className="flex items-center gap-3">
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            padding: "3px 10px",
            borderRadius: 6,
            fontSize: "0.65rem",
            fontWeight: 700,
            fontFamily: "var(--font-mono)",
            letterSpacing: "0.04em",
            textTransform: "uppercase",
            background: mode === "live"
              ? "rgba(239,68,68,0.12)"
              : "rgba(234,179,8,0.12)",
            border: "1px solid",
            borderColor: mode === "live"
              ? "rgba(239,68,68,0.3)"
              : "rgba(234,179,8,0.3)",
            color: mode === "live" ? "#ef4444" : "#eab308",
          }}
        >
          <span style={{
            width: 6, height: 6, borderRadius: "50%",
            background: mode === "live" ? "#ef4444" : "#eab308",
            display: "inline-block",
            boxShadow: mode === "live"
              ? "0 0 0 2px rgba(239,68,68,0.25)"
              : "0 0 0 2px rgba(234,179,8,0.25)",
          }} />
          {loadingMode ? "..." : mode === "live" ? "Live" : "Demo"}
        </div>
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
      </div>

      <div className="flex items-center gap-3">
        {children}

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
