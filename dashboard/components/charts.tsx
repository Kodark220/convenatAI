"use client";

import {
  BarChart, Bar, AreaChart, Area, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import type { DailyDataPoint } from "@/lib/types";

const GRID_STYLE = { stroke: "rgba(255,255,255,0.04)", strokeDasharray: "none" };
const AXIS_STYLE = { fill: "#4a4f58", fontSize: 10, fontFamily: "var(--font-mono)" };

interface ChartProps {
  data: DailyDataPoint[];
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "var(--surface-3)",
      border: "1px solid var(--border-strong)",
      borderRadius: 8,
      padding: "8px 12px",
    }}>
      <p style={{ fontSize: "0.7rem", color: "var(--text-faint)", marginBottom: 4, fontFamily: "var(--font-mono)" }}>{label}</p>
      {payload.map((p: any) => (
        <p key={p.dataKey} style={{ fontSize: "0.78rem", color: p.color, fontFamily: "var(--font-mono)" }}>
          {p.name}: {typeof p.value === "number" && p.name === "usdc" ? `$${p.value.toLocaleString()}` : p.value}
        </p>
      ))}
    </div>
  );
};

export function JobsBarChart({ data }: ChartProps) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
        <CartesianGrid vertical={false} {...GRID_STYLE} />
        <XAxis dataKey="date" tick={AXIS_STYLE} axisLine={false} tickLine={false} />
        <YAxis tick={AXIS_STYLE} axisLine={false} tickLine={false} />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
        <Bar dataKey="jobs" name="jobs" fill="#5e6ad2" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function USDCAreaChart({ data }: ChartProps) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
        <defs>
          <linearGradient id="usdcGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#10b981" stopOpacity={0.25} />
            <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid vertical={false} {...GRID_STYLE} />
        <XAxis dataKey="date" tick={AXIS_STYLE} axisLine={false} tickLine={false} />
        <YAxis tick={AXIS_STYLE} axisLine={false} tickLine={false} />
        <Tooltip content={<CustomTooltip />} />
        <Area dataKey="usdc" name="usdc" stroke="#10b981" strokeWidth={1.5} fill="url(#usdcGrad)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function AgentsLineChart({ data }: ChartProps) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
        <CartesianGrid vertical={false} {...GRID_STYLE} />
        <XAxis dataKey="date" tick={AXIS_STYLE} axisLine={false} tickLine={false} />
        <YAxis tick={AXIS_STYLE} axisLine={false} tickLine={false} />
        <Tooltip content={<CustomTooltip />} />
        <Line dataKey="agents" name="agents" stroke="#7170ff" strokeWidth={1.5} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
