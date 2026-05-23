"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Search,
  Bot,
  Layers,
  Settings,
  BookOpen,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  {
    group: "Overview",
    items: [
      { label: "Dashboard",  href: "/dashboard", icon: LayoutDashboard },
      { label: "Discovery",  href: "/discovery", icon: Search          },
      { label: "Agents",     href: "/agents",    icon: Bot             },
    ],
  },
  {
    group: "Chains",
    items: [
      { label: "Arc Testnet", href: "/chains/arc",      icon: Layers, dot: "live" },
      { label: "GenLayer",    href: "/chains/genlayer", icon: Layers, dot: "idle" },
    ],
  },
];

const FOOTER = [
  { label: "Settings", href: "#settings", icon: Settings },
  { label: "Docs", href: "#docs", icon: BookOpen },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sidebar">
      {/* ── Logo ── */}
      <div className="px-5 py-5 flex items-center gap-3">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-xs font-bold"
          style={{ background: "linear-gradient(135deg, #5e6ad2, #7170ff)" }}
        >
          C
        </div>
        <div>
          <p className="text-sm font-bold tracking-tight" style={{ color: "var(--text-primary)", fontFamily: "var(--font-display)" }}>
            convenat<span style={{ color: "var(--accent-bright)" }}>AI</span>
          </p>
          <p className="text-xs" style={{ color: "var(--text-faint)", fontFamily: "var(--font-mono)" }}>
            agent trading
          </p>
        </div>
      </div>

      <div className="separator mx-4" />

      {/* ── Nav ── */}
      <nav className="flex-1 px-3 py-2 overflow-y-auto space-y-4">
        {NAV.map((section) => (
          <div key={section.group}>
            <p
              className="px-3 mb-1"
              style={{
                fontSize: "0.65rem",
                fontWeight: 600,
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                color: "var(--text-faint)",
                fontFamily: "var(--font-display)",
              }}
            >
              {section.group}
            </p>
            <ul className="space-y-0.5">
              {section.items.map((item) => {
                const active = pathname === item.href;
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className={cn("nav-item", active && "active")}
                    >
                      <item.icon size={15} strokeWidth={1.8} />
                      <span className="flex-1">{item.label}</span>
                      {"dot" in item && item.dot === "live" && <span className="live-dot" />}
                      {"dot" in item && item.dot === "idle" && <span className="idle-dot" />}
                      {active && <ChevronRight size={12} style={{ color: "var(--accent-bright)" }} />}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* ── Network status ── */}
      <div className="px-4 py-3 mx-3 mb-2 rounded-10" style={{ background: "var(--surface-2)", border: "1px solid var(--border)", borderRadius: 10 }}>
        <p className="text-xs mb-2" style={{ color: "var(--text-faint)", fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase" }}>
          Network
        </p>
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-xs" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>Arc</span>
            <div className="flex items-center gap-1.5">
              <span className="live-dot" style={{ width: 6, height: 6 }} />
              <span className="text-xs" style={{ color: "var(--success)", fontFamily: "var(--font-mono)" }}>Live</span>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>GenLayer</span>
            <div className="flex items-center gap-1.5">
              <span className="idle-dot" style={{ width: 6, height: 6 }} />
              <span className="text-xs" style={{ color: "var(--text-faint)", fontFamily: "var(--font-mono)" }}>Idle</span>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>Circle</span>
            <div className="flex items-center gap-1.5">
              <span className="live-dot" style={{ width: 6, height: 6 }} />
              <span className="text-xs" style={{ color: "var(--success)", fontFamily: "var(--font-mono)" }}>Live</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Footer ── */}
      <div className="px-3 pb-4">
        <div className="separator" />
        {FOOTER.map((item) => (
          <Link key={item.href} href={item.href} className="nav-item">
            <item.icon size={14} strokeWidth={1.8} />
            <span>{item.label}</span>
          </Link>
        ))}
      </div>
    </aside>
  );
}
