"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Search, Bot, ShieldCheck, Briefcase, Layers, Settings, BookOpen, ChevronRight, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

function useChainStatus() {
  const [status, setStatus] = useState<{ arc: string }>({
    arc: "idle",
  });
  useEffect(() => {
    if (!API_BASE) {
      setStatus({ arc: "error" });
      return;
    }
    async function fetchChains() {
      try {
        const arcRes = await fetch(`${API_BASE}/api/chains/arc`);
        const arc = await arcRes.json();
        setStatus({
          arc: arc.status === "live" ? "live" : "error",
        });
      } catch {
        setStatus({ arc: "error" });
      }
    }
    fetchChains();
    const interval = setInterval(fetchChains, 30000);
    return () => clearInterval(interval);
  }, []);
  return status;
}

const NAV = [
  {
    group: "Overview",
    items: [
      { label: "Dashboard",   href: "/dashboard",  icon: LayoutDashboard },
      { label: "Deals",       href: "/deals",      icon: Briefcase      },
      { label: "convenatAI", href: "/negotiator", icon: ShieldCheck    },
      { label: "Discovery",   href: "/discovery",   icon: Search         },
      { label: "Agents",      href: "/agents",      icon: Bot            },
    ],
  },
  {
    group: "Chains",
    items: [
      { label: "Arc Testnet", href: "/chains/arc",      icon: Layers },
    ],
  },
];

const FOOTER = [
  { label: "Settings", href: "#settings", icon: Settings },
  { label: "Docs", href: "#docs", icon: BookOpen },
];

export function Sidebar() {
  const pathname = usePathname();
  const chainStatus = useChainStatus();
  const [mode, setMode] = useState<"live" | "demo">("live");
  const [toggling, setToggling] = useState(false);
  const [loadingMode, setLoadingMode] = useState(true);

  useEffect(() => {
    if (!API_BASE) return;
    fetch(`${API_BASE}/api/negotiator/mode`)
      .then(r => r.json())
      .then(d => { setMode(d.mode); setLoadingMode(false); })
      .catch(() => setLoadingMode(false));
  }, []);

  const handleToggleMode = async () => {
    setToggling(true);
    try {
      const res = await fetch(`${API_BASE}/api/negotiator/mode`, { method: "POST" });
      if (res.ok) {
        const d = await res.json();
        setMode(d.mode);
        setTimeout(() => window.location.reload(), 800);
      }
    } catch (e) {
      console.error(e);
    }
    setTimeout(() => setToggling(false), 2000);
  };

  return (
    <aside className="sidebar">
      {/* ── Logo ── */}
      <div className="px-5 py-5 flex items-center gap-3">
        <img
          src="/logo.png"
          alt="convenatAI Logo"
          className="w-8 h-8 rounded-lg object-cover"
          style={{ border: "1px solid rgba(113,112,255,0.2)" }}
        />
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

      {/* ── Mode Toggle Bar ── */}
      <div className="px-3 py-2">
        <button
          onClick={handleToggleMode}
          disabled={toggling || loadingMode}
          style={{
            width: "100%",
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "8px 12px",
            borderRadius: 8,
            border: "1px solid",
            cursor: "pointer",
            fontSize: "0.78rem",
            fontWeight: 600,
            fontFamily: "var(--font-display)",
            transition: "all 0.2s ease",
            background: mode === "live"
              ? "rgba(239,68,68,0.1)"
              : "rgba(234,179,8,0.1)",
            borderColor: mode === "live"
              ? "rgba(239,68,68,0.3)"
              : "rgba(234,179,8,0.3)",
            color: mode === "live" ? "#ef4444" : "#eab308",
          }}
        >
          <Zap size={14} />
          <span className="flex-1 text-left">
            {loadingMode ? "Loading..." : mode === "live" ? "🔴 Live Mode" : "🟡 Demo Mode"}
          </span>
          <span style={{ fontSize: "0.65rem", opacity: 0.6 }}>
            {toggling ? "..." : "switch"}
          </span>
        </button>
      </div>

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
                      {chainStatus.arc === "live" && <span className="live-dot" />}
                      {active && <ChevronRight size={12} style={{ color: "var(--accent-bright)" }} />}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

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
