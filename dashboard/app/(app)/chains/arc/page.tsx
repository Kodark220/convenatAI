"use client";

import useSWR from "swr";
import { ExternalLink } from "lucide-react";
import { TopBar } from "@/components/top-bar";
import { JobsBarChart, USDCAreaChart, AgentsLineChart } from "@/components/charts";
import { endpoints } from "@/lib/rpc";
import type { ChainEvent, ChainInfo, DailyDataPoint } from "@/lib/types";
import { shortHash, formatTimestamp } from "@/lib/utils";

export default function ArcChainPage() {
  const { data: info } = useSWR<ChainInfo>(endpoints.chainInfo("arc"));
  const { data: events = [] } = useSWR<ChainEvent[]>(endpoints.events("arc"), { refreshInterval: 10000 });
  const { data: chartData = [] } = useSWR<DailyDataPoint[]>(endpoints.chartData("arc"));

  return (
    <>
      <TopBar title="Arc Testnet" subtitle="Chain deep-dive & live events" />

      <div className="p-6 space-y-6">
        {/* Chain info card */}
        {info && (
          <div className="card p-5">
            <div className="flex items-start justify-between mb-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className="live-dot"
                    style={{ display: "inline-block" }}
                  />
                  <h2 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)" }}>
                    {info.name}
                  </h2>
                  <span className="badge" style={{ background: "var(--success-glow)", color: "var(--success)", border: "1px solid rgba(16,185,129,0.2)" }}>
                    Live
                  </span>
                </div>
                {info.blockNumber && (
                  <p style={{ fontSize: "0.72rem", color: "var(--text-faint)", fontFamily: "var(--font-mono)" }}>
                    Block #{info.blockNumber.toLocaleString()}
                  </p>
                )}
              </div>
              <a href={info.explorerUrl} target="_blank" rel="noopener noreferrer" className="btn-ghost" style={{ fontSize: "0.75rem" }}>
                <ExternalLink size={12} />
                Explorer
              </a>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <InfoItem label="Contract" value={info.contract} mono truncate />
              <InfoItem label="RPC Endpoint" value={info.rpc} mono truncate />
              <InfoItem label="Network" value="Arc Testnet" />
            </div>
          </div>
        )}

        {/* Charts */}
        <div>
          <p style={{ fontSize: "0.7rem", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--text-faint)", marginBottom: 12 }}>
            Analytics (14d)
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <ChartCard title="Jobs / Day">
              <JobsBarChart data={chartData} />
            </ChartCard>
            <ChartCard title="USDC / Day">
              <USDCAreaChart data={chartData} />
            </ChartCard>
            <ChartCard title="Active Agents">
              <AgentsLineChart data={chartData} />
            </ChartCard>
          </div>
        </div>

        {/* Live events table */}
        <div className="card">
          <div className="px-5 py-4" style={{ borderBottom: "1px solid var(--border)" }}>
            <div className="flex items-center gap-2">
              <span className="live-dot" style={{ display: "inline-block" }} />
              <h2 style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text-primary)" }}>
                Live Events
              </h2>
              <span style={{ fontSize: "0.65rem", color: "var(--text-faint)", fontFamily: "var(--font-mono)" }}>
                auto-refresh 10s
              </span>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Block</th>
                  <th>Event</th>
                  <th>Args</th>
                  <th>Tx Hash</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {events.map((evt) => (
                  <tr key={evt.id}>
                    <td>
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--text-muted)" }}>
                        #{evt.blockNumber.toLocaleString()}
                      </span>
                    </td>
                    <td>
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--accent-bright)" }}>
                        {evt.eventName}
                      </span>
                    </td>
                    <td>
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", color: "var(--text-faint)" }}>
                        {Object.entries(evt.args).map(([k, v]) => `${k}: ${v}`).join(", ")}
                      </span>
                    </td>
                    <td>
                      <span className="text-address">{shortHash(evt.txHash)}</span>
                    </td>
                    <td>
                      <span style={{ fontSize: "0.72rem", color: "var(--text-faint)", fontFamily: "var(--font-mono)" }}>
                        {formatTimestamp(evt.timestamp)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card p-5">
      <p style={{ fontSize: "0.72rem", fontWeight: 600, color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 14 }}>
        {title}
      </p>
      {children}
    </div>
  );
}

function InfoItem({ label, value, mono, truncate }: { label: string; value: string; mono?: boolean; truncate?: boolean }) {
  return (
    <div>
      <p style={{ fontSize: "0.65rem", fontWeight: 600, color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }}>
        {label}
      </p>
      <p style={{
        fontSize: "0.75rem",
        color: "var(--text-muted)",
        fontFamily: mono ? "var(--font-mono)" : undefined,
        overflow: truncate ? "hidden" : undefined,
        textOverflow: truncate ? "ellipsis" : undefined,
        whiteSpace: truncate ? "nowrap" : undefined,
      }}>
        {value}
      </p>
    </div>
  );
}
