"use client";

import { motion } from "framer-motion";
import { type LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string;
  change?: string;
  changePositive?: boolean;
  icon: LucideIcon;
  index?: number;
}

export function StatCard({ label, value, change, changePositive, icon: Icon, index = 0 }: StatCardProps) {
  return (
    <motion.div
      className="card p-5 flex flex-col gap-4"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.08, ease: [0.22, 1, 0.36, 1] }}
    >
      {/* Top row */}
      <div className="flex items-start justify-between">
        <p style={{ fontSize: "0.72rem", fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-faint)" }}>
          {label}
        </p>
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ background: "var(--accent-glow)", border: "1px solid rgba(113,112,255,0.15)" }}
        >
          <Icon size={14} style={{ color: "var(--accent-bright)" }} strokeWidth={1.8} />
        </div>
      </div>

      {/* Value */}
      <div>
        <p style={{ fontSize: "1.6rem", fontWeight: 700, color: "var(--text-primary)", letterSpacing: "-0.02em", fontFamily: "var(--font-display)", lineHeight: 1 }}>
          {value}
        </p>
        {change && (
          <p className="mt-1" style={{ fontSize: "0.72rem", color: changePositive ? "var(--success)" : "var(--danger)" }}>
            {changePositive ? "↑" : "↓"} {change} this week
          </p>
        )}
      </div>

      {/* Accent bar */}
      <div className="stat-accent" />
    </motion.div>
  );
}
