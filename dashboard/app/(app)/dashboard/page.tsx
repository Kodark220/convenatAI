"use client";

import useSWR from "swr";
import { Briefcase, Bot, Handshake, DollarSign } from "lucide-react";
import { TopBar } from "@/components/top-bar";
import { StatCard } from "@/components/stat-card";
import { ChainCard } from "@/components/chain-card";
import { JobTable } from "@/components/job-table";
import { EventFeed } from "@/components/event-feed";
import { endpoints } from "@/lib/rpc";
import type { DashboardStats, Job, ChainEvent, ChainInfo } from "@/lib/types";
import { formatUSDC, formatNumber } from "@/lib/utils";

export default function DashboardPage() {
  const { data: stats } = useSWR<DashboardStats>(endpoints.stats);
  const { data: jobs = [] } = useSWR<Job[]>(endpoints.jobs);
  const { data: arcEvents = [] } = useSWR<ChainEvent[]>(endpoints.events("arc"));
  const { data: glEvents = [] } = useSWR<ChainEvent[]>(endpoints.events("genlayer"));
  const { data: arcInfo } = useSWR<ChainInfo>(endpoints.chainInfo("arc"));
  const { data: glInfo } = useSWR<ChainInfo>(endpoints.chainInfo("genlayer"));

  const allEvents = [...arcEvents, ...glEvents].sort((a, b) => b.timestamp - a.timestamp);

  const STAT_CARDS = [
    {
      label: "Total Jobs",
      value: stats ? formatNumber(stats.totalJobs) : "—",
      icon: Briefcase,
      change: "12.4%",
      changePositive: true,
    },
    {
      label: "Active Agents",
      value: stats ? formatNumber(stats.activeAgents) : "—",
      icon: Bot,
      change: "3.1%",
      changePositive: true,
    },
    {
      label: "Deals Done",
      value: stats ? formatNumber(stats.dealsDone) : "—",
      icon: Handshake,
      change: "8.7%",
      changePositive: true,
    },
    {
      label: "USDC Streamed",
      value: stats ? formatUSDC(stats.usdcStreamed) : "—",
      icon: DollarSign,
      change: "21.3%",
      changePositive: true,
    },
  ];

  const circleChain: ChainInfo = {
    id: "circle",
    name: "Circle Wallets",
    rpc: "https://api.circle.com/v1",
    contract: "USDC Programmable Wallets",
    explorerUrl: "https://developers.circle.com",
    status: "live",
  };

  return (
    <>
      <TopBar title="Dashboard" subtitle="convenatAI agent trading" />

      <div className="p-6 space-y-6">
        {/* ── Stat Cards ── */}
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
          {STAT_CARDS.map((card, i) => (
            <StatCard key={card.label} {...card} index={i} />
          ))}
        </div>

        {/* ── Chain Cards ── */}
        <div>
          <p style={{ fontSize: "0.7rem", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--text-faint)", marginBottom: 12 }}>
            Chain Status
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {arcInfo && <ChainCard chain={arcInfo} index={0} />}
            {glInfo && <ChainCard chain={glInfo} index={1} />}
            <ChainCard chain={circleChain} index={2} />
          </div>
        </div>

        {/* ── Jobs + Event Feed ── */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
          <div className="xl:col-span-2">
            <JobTable jobs={jobs} />
          </div>
          <div>
            <EventFeed events={allEvents} />
          </div>
        </div>
      </div>
    </>
  );
}
