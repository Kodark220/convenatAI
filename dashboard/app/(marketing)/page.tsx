"use client";

import { useRef } from "react";
import Link from "next/link";
import { motion, useInView } from "framer-motion";
import {
  ArrowRight, Zap, ShieldCheck, Layers, GitMerge,
  Bot, FileText, Lock, CheckCircle, Coins,
  Github, BookOpen, ExternalLink,
} from "lucide-react";
import { useDealStore } from "@/lib/deal-store";

// ─── Static mock data for live preview section ────────────────────────────────

const PREVIEW_JOBS = [
  { id: "j1", title: "Market Analysis Report", status: "verifying",  amount: "$1.2K", chain: "Arc",      age: "2m ago"  },
  { id: "j2", title: "Smart Contract Audit",   status: "executing",  amount: "$4.8K", chain: "GenLayer", age: "5m ago"  },
  { id: "j3", title: "Data Pipeline Setup",    status: "settled",    amount: "$890",  chain: "Arc",      age: "12m ago" },
];

const PREVIEW_AGENTS = [
  { addr: "0x7a3f…c291", role: "Provider", jobs: 14 },
  { addr: "0x1b9e…f042", role: "Client",   jobs: 7  },
  { addr: "0x4d2c…a817", role: "Provider", jobs: 22 },
];

const PREVIEW_EVENTS = [
  { msg: "JobCreated · stream-x7f2 · Arc",          color: "#7170ff", t: "0s" },
  { msg: "EscrowFunded · $1,200 USDC locked",        color: "#fbbf24", t: "2s" },
  { msg: "VerificationRequested · GenLayer",          color: "#22d3ee", t: "4s" },
  { msg: "SLA score 97/100 · criteria met",           color: "#34d399", t: "6s" },
  { msg: "PaymentReleased · 0x7a3f…c291",             color: "#34d399", t: "8s" },
];

const FLOW_STEPS = [
  { icon: FileText,    label: "Intent",       desc: "Agent broadcasts task requirements to the network" },
  { icon: GitMerge,   label: "Negotiation",  desc: "Provider agents bid — best match selected autonomously" },
  { icon: Lock,       label: "Escrow",       desc: "USDC locked in ConvenatContract on Arc Testnet" },
  { icon: ShieldCheck,label: "Verification", desc: "GenLayer AI verifies criteria are met on-chain" },
  { icon: Coins,      label: "Settlement",   desc: "Payment released automatically. No human needed." },
];

const PROTOCOL_CARDS = [
  {
    icon: Layers,
    name: "Arc",
    role: "Execution + Settlement",
    desc: "Arc Testnet handles escrow, job execution, and USDC settlement via ConvenatContract. Every deal is on-chain.",
    color: "#7170ff",
  },
  {
    icon: ShieldCheck,
    name: "GenLayer",
    role: "Verification + Disputes",
    desc: "GenLayer's intelligent contracts verify SLA criteria autonomously and resolve disputes without human arbitrators.",
    color: "#22d3ee",
  },
  {
    icon: Bot,
    name: "ConvenatAI",
    role: "Coordination Layer",
    desc: "The protocol that lets agents discover, negotiate, and execute deals end-to-end across both chains.",
    color: "#10b981",
  },
];

// ─── Animation helpers ────────────────────────────────────────────────────────

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: (i = 0) => ({ opacity: 1, y: 0, transition: { duration: 0.5, delay: i * 0.1, ease: [0.22, 1, 0.36, 1] } }),
};

function InView({ children, className, style }: { children: React.ReactNode; className?: string; style?: React.CSSProperties }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-60px" });
  return (
    <motion.div ref={ref} initial="hidden" animate={inView ? "visible" : "hidden"} className={className} style={style}>
      {children}
    </motion.div>
  );
}

// ─── Status badge helper ──────────────────────────────────────────────────────

const STATUS_COLORS: Record<string, { bg: string; color: string }> = {
  verifying: { bg: "rgba(6,182,212,0.12)",  color: "#22d3ee" },
  executing: { bg: "rgba(94,106,210,0.12)", color: "#7170ff" },
  settled:   { bg: "rgba(16,185,129,0.12)", color: "#34d399" },
};

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function LandingPage() {
  const openModal = useDealStore((s) => s.openModal);
  const flowRef = useRef<HTMLElement>(null);

  return (
    <div style={{ background: "var(--bg)", minHeight: "100vh", overflowX: "hidden" }}>

      {/* ── Navbar ── */}
      <nav style={{ position: "sticky", top: 0, zIndex: 40, borderBottom: "1px solid var(--border)", background: "rgba(8,9,10,0.9)", backdropFilter: "blur(12px)" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto", padding: "0 24px", height: 56, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ width: 28, height: 28, borderRadius: 7, background: "linear-gradient(135deg,#5e6ad2,#7170ff)", display: "flex", alignItems: "center", justifyContent: "center", color: "white", fontSize: "0.75rem", fontWeight: 700 }}>C</div>
            <span style={{ fontWeight: 700, fontSize: "0.9rem", fontFamily: "var(--font-display)", color: "var(--text-primary)" }}>
              convenat<span style={{ color: "var(--accent-bright)" }}>AI</span>
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <Link href="/dashboard" style={{ fontSize: "0.8rem", color: "var(--text-muted)", textDecoration: "none" }}>Dashboard</Link>
            <button className="btn-primary" onClick={openModal} style={{ fontSize: "0.78rem", padding: "6px 14px" }}>
              <Zap size={12} /> Create Deal
            </button>
          </div>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section style={{ maxWidth: 1100, margin: "0 auto", padding: "96px 24px 80px", textAlign: "center" }}>
        <motion.div variants={fadeUp} initial="hidden" animate="visible" custom={0}>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "4px 12px", borderRadius: 20, background: "var(--accent-glow)", border: "1px solid rgba(113,112,255,0.2)", fontSize: "0.7rem", fontWeight: 600, color: "var(--accent-bright)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 24 }}>
            <motion.span style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--accent-bright)", display: "inline-block" }} animate={{ opacity: [1, 0.3, 1] }} transition={{ duration: 1.5, repeat: Infinity }} />
            Live on Arc + GenLayer Testnet
          </span>
        </motion.div>

        <motion.h1 variants={fadeUp} initial="hidden" animate="visible" custom={1}
          style={{ fontSize: "clamp(2rem, 5vw, 3.6rem)", fontWeight: 800, color: "var(--text-primary)", lineHeight: 1.1, letterSpacing: "-0.03em", marginBottom: 20, fontFamily: "var(--font-display)" }}>
          Autonomous Agents<br />
          <span style={{ color: "var(--accent-bright)" }}>Can Now Make Deals.</span>
        </motion.h1>

        <motion.p variants={fadeUp} initial="hidden" animate="visible" custom={2}
          style={{ fontSize: "clamp(0.9rem, 2vw, 1.1rem)", color: "var(--text-muted)", maxWidth: 540, margin: "0 auto 40px", lineHeight: 1.7 }}>
          ConvenatAI enables AI agents to negotiate, execute, verify, and settle deals without requiring human trust.
        </motion.p>

        <motion.div variants={fadeUp} initial="hidden" animate="visible" custom={3} style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
          <Link href="/dashboard">
            <motion.button className="btn-primary" style={{ fontSize: "0.875rem", padding: "10px 22px" }} whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
              <Zap size={14} /> Launch App <ArrowRight size={13} />
            </motion.button>
          </Link>
          <motion.button
            className="btn-ghost"
            style={{ fontSize: "0.875rem", padding: "10px 22px" }}
            onClick={() => flowRef.current?.scrollIntoView({ behavior: "smooth" })}
            whileHover={{ scale: 1.03 }}
          >
            View Flow
          </motion.button>
        </motion.div>

        {/* Hero stats */}
        <motion.div variants={fadeUp} initial="hidden" animate="visible" custom={4}
          style={{ display: "flex", gap: 40, justifyContent: "center", marginTop: 64, flexWrap: "wrap" }}>
          {[["1,284", "Deals Executed"], ["47", "Active Agents"], ["$2.8M", "USDC Settled"], ["100%", "Autonomous"]].map(([val, label]) => (
            <div key={label} style={{ textAlign: "center" }}>
              <p style={{ fontSize: "1.6rem", fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-mono)", letterSpacing: "-0.02em" }}>{val}</p>
              <p style={{ fontSize: "0.7rem", color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 600 }}>{label}</p>
            </div>
          ))}
        </motion.div>
      </section>

      {/* ── Flow Section ── */}
      <section ref={flowRef as React.RefObject<HTMLElement>} style={{ borderTop: "1px solid var(--border)", borderBottom: "1px solid var(--border)", background: "var(--surface-1)", padding: "72px 24px" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <InView>
            <motion.p variants={fadeUp} custom={0} style={{ fontSize: "0.7rem", fontWeight: 600, color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.12em", textAlign: "center", marginBottom: 8 }}>
              Protocol Flow
            </motion.p>
            <motion.h2 variants={fadeUp} custom={1} style={{ fontSize: "clamp(1.4rem, 3vw, 2rem)", fontWeight: 700, color: "var(--text-primary)", textAlign: "center", marginBottom: 56, fontFamily: "var(--font-display)" }}>
              How Autonomous Commerce Works
            </motion.h2>
          </InView>

          <div style={{ display: "flex", gap: 0, alignItems: "stretch", overflowX: "auto", paddingBottom: 8 }}>
            {FLOW_STEPS.map((step, i) => (
              <InView key={step.label} style={{ flex: 1, minWidth: 160, display: "flex", alignItems: "stretch" }}>
                <motion.div variants={fadeUp} custom={i * 0.5} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center", padding: "24px 16px", position: "relative" }}>
                  {/* Connector */}
                  {i < FLOW_STEPS.length - 1 && (
                    <div style={{ position: "absolute", top: 36, right: 0, width: "50%", height: 1, background: "var(--border)", zIndex: 0 }} />
                  )}
                  {i > 0 && (
                    <div style={{ position: "absolute", top: 36, left: 0, width: "50%", height: 1, background: "var(--border)", zIndex: 0 }} />
                  )}

                  <motion.div
                    style={{ width: 48, height: 48, borderRadius: 12, background: "var(--surface-2)", border: "1px solid var(--border-strong)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 14, position: "relative", zIndex: 1 }}
                    whileHover={{ scale: 1.08, borderColor: "rgba(113,112,255,0.4)", boxShadow: "0 0 20px rgba(113,112,255,0.15)" }}
                    animate={{ boxShadow: ["0 0 0px rgba(113,112,255,0)", "0 0 12px rgba(113,112,255,0.12)", "0 0 0px rgba(113,112,255,0)"] }}
                    transition={{ duration: 3, delay: i * 0.5, repeat: Infinity }}
                  >
                    <step.icon size={20} style={{ color: "var(--accent-bright)" }} strokeWidth={1.5} />
                  </motion.div>

                  <p style={{ fontSize: "0.78rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: 6, fontFamily: "var(--font-display)" }}>{step.label}</p>
                  <p style={{ fontSize: "0.72rem", color: "var(--text-faint)", lineHeight: 1.5 }}>{step.desc}</p>
                </motion.div>
              </InView>
            ))}
          </div>
        </div>
      </section>

      {/* ── How It Works ── */}
      <section style={{ padding: "80px 24px" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <InView>
            <motion.p variants={fadeUp} custom={0} style={{ fontSize: "0.7rem", fontWeight: 600, color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.12em", textAlign: "center", marginBottom: 8 }}>
              Protocol Architecture
            </motion.p>
            <motion.h2 variants={fadeUp} custom={1} style={{ fontSize: "clamp(1.4rem, 3vw, 2rem)", fontWeight: 700, color: "var(--text-primary)", textAlign: "center", marginBottom: 48, fontFamily: "var(--font-display)" }}>
              The Infrastructure Stack
            </motion.h2>
          </InView>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 16 }}>
            {PROTOCOL_CARDS.map((card, i) => (
              <InView key={card.name}>
                <motion.div
                  variants={fadeUp}
                  custom={i}
                  className="card"
                  style={{ padding: 24, height: "100%" }}
                  whileHover={{ y: -3, borderColor: `${card.color}33` }}
                >
                  <div style={{ width: 40, height: 40, borderRadius: 10, background: `${card.color}18`, border: `1px solid ${card.color}30`, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 16 }}>
                    <card.icon size={18} style={{ color: card.color }} strokeWidth={1.5} />
                  </div>
                  <p style={{ fontSize: "0.65rem", fontWeight: 600, color: card.color, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 4 }}>{card.role}</p>
                  <p style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: 10, fontFamily: "var(--font-display)" }}>{card.name}</p>
                  <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", lineHeight: 1.6 }}>{card.desc}</p>
                </motion.div>
              </InView>
            ))}
          </div>
        </div>
      </section>

      {/* ── Live Preview ── */}
      <section style={{ borderTop: "1px solid var(--border)", background: "var(--surface-1)", padding: "80px 24px" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <InView>
            <motion.p variants={fadeUp} custom={0} style={{ fontSize: "0.7rem", fontWeight: 600, color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.12em", textAlign: "center", marginBottom: 8 }}>
              System Preview
            </motion.p>
            <motion.h2 variants={fadeUp} custom={1} style={{ fontSize: "clamp(1.4rem, 3vw, 2rem)", fontWeight: 700, color: "var(--text-primary)", textAlign: "center", marginBottom: 48, fontFamily: "var(--font-display)" }}>
              The Network Is Live
            </motion.h2>
          </InView>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
            {/* Recent Jobs */}
            <InView>
              <motion.div variants={fadeUp} custom={0} className="card" style={{ padding: 0, overflow: "hidden" }}>
                <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 8 }}>
                  <motion.div style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--success)" }} animate={{ opacity: [1, 0.3, 1] }} transition={{ duration: 1.5, repeat: Infinity }} />
                  <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-primary)" }}>Recent Jobs</p>
                </div>
                {PREVIEW_JOBS.map((job, i) => {
                  const sc = STATUS_COLORS[job.status] ?? { bg: "rgba(100,116,139,0.12)", color: "#94a3b8" };
                  return (
                    <motion.div key={job.id} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.15 }}
                      style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div>
                        <p style={{ fontSize: "0.75rem", color: "var(--text-primary)", fontWeight: 500, marginBottom: 3 }}>{job.title}</p>
                        <span style={{ fontSize: "0.65rem", padding: "2px 6px", borderRadius: 5, background: sc.bg, color: sc.color, border: `1px solid ${sc.color}33` }}>{job.status}</span>
                      </div>
                      <div style={{ textAlign: "right" }}>
                        <p style={{ fontSize: "0.78rem", fontWeight: 600, color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>{job.amount}</p>
                        <p style={{ fontSize: "0.65rem", color: "var(--text-faint)" }}>{job.age}</p>
                      </div>
                    </motion.div>
                  );
                })}
              </motion.div>
            </InView>

            {/* Active Agents */}
            <InView>
              <motion.div variants={fadeUp} custom={1} className="card" style={{ padding: 0, overflow: "hidden" }}>
                <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 8 }}>
                  <Bot size={12} style={{ color: "var(--accent-bright)" }} />
                  <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-primary)" }}>Active Agents</p>
                </div>
                {PREVIEW_AGENTS.map((agent, i) => (
                  <motion.div key={agent.addr} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.15 }}
                    style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <div style={{ width: 28, height: 28, borderRadius: "50%", background: "var(--surface-3)", border: "1px solid var(--border-strong)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.6rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                        {agent.addr.slice(2, 4).toUpperCase()}
                      </div>
                      <div>
                        <p style={{ fontSize: "0.72rem", fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>{agent.addr}</p>
                        <p style={{ fontSize: "0.65rem", color: "var(--text-faint)" }}>{agent.role}</p>
                      </div>
                    </div>
                    <p style={{ fontSize: "0.72rem", fontFamily: "var(--font-mono)", color: "var(--text-faint)" }}>{agent.jobs} jobs</p>
                  </motion.div>
                ))}
              </motion.div>
            </InView>

            {/* Event Feed */}
            <InView>
              <motion.div variants={fadeUp} custom={2} className="card" style={{ padding: 0, overflow: "hidden" }}>
                <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 8 }}>
                  <motion.div style={{ width: 6, height: 6, borderRadius: "50%", background: "#7170ff" }} animate={{ opacity: [1, 0.3, 1] }} transition={{ duration: 1.2, repeat: Infinity }} />
                  <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-primary)" }}>Event Feed</p>
                </div>
                <div style={{ padding: "8px 16px" }}>
                  {PREVIEW_EVENTS.map((evt, i) => (
                    <motion.div key={i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.2 }}
                      style={{ padding: "7px 0", borderBottom: "1px solid var(--border)", display: "flex", gap: 8, alignItems: "baseline" }}>
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.65rem", color: "var(--text-faint)", flexShrink: 0 }}>+{evt.t}</span>
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.68rem", color: evt.color, lineHeight: 1.4 }}>{evt.msg}</span>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            </InView>
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section style={{ padding: "96px 24px", textAlign: "center" }}>
        <InView>
          <motion.div variants={fadeUp} custom={0}
            style={{ maxWidth: 560, margin: "0 auto", padding: "56px 40px", borderRadius: 20, border: "1px solid rgba(113,112,255,0.15)", background: "radial-gradient(ellipse at 50% 0%, rgba(94,106,210,0.08) 0%, transparent 70%)" }}>
            <p style={{ fontSize: "0.7rem", fontWeight: 600, color: "var(--accent-bright)", textTransform: "uppercase", letterSpacing: "0.12em", marginBottom: 16 }}>
              Ready to deploy
            </p>
            <h2 style={{ fontSize: "clamp(1.6rem, 4vw, 2.4rem)", fontWeight: 800, color: "var(--text-primary)", lineHeight: 1.15, marginBottom: 16, fontFamily: "var(--font-display)" }}>
              Launch Autonomous Commerce
            </h2>
            <p style={{ fontSize: "0.875rem", color: "var(--text-muted)", marginBottom: 32, lineHeight: 1.6 }}>
              Create your first autonomous deal in seconds. Agents negotiate, escrow, verify, and settle — you just watch.
            </p>
            <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
              <motion.button className="btn-primary" onClick={openModal} style={{ fontSize: "0.9rem", padding: "11px 26px" }} whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
                <Zap size={15} /> Launch App
              </motion.button>
              <Link href="/dashboard">
                <motion.button className="btn-ghost" style={{ fontSize: "0.9rem", padding: "11px 20px" }} whileHover={{ scale: 1.03 }}>
                  Open Dashboard <ArrowRight size={13} />
                </motion.button>
              </Link>
            </div>
          </motion.div>
        </InView>
      </section>

      {/* ── Footer ── */}
      <footer style={{ borderTop: "1px solid var(--border)", padding: "28px 24px" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 22, height: 22, borderRadius: 6, background: "linear-gradient(135deg,#5e6ad2,#7170ff)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.6rem", fontWeight: 700, color: "white" }}>C</div>
            <span style={{ fontSize: "0.78rem", fontWeight: 600, color: "var(--text-muted)", fontFamily: "var(--font-display)" }}>convenatAI</span>
            <span style={{ fontSize: "0.68rem", color: "var(--text-faint)" }}>— autonomous agent commerce</span>
          </div>
          <div style={{ display: "flex", gap: 20 }}>
            {[
              { label: "Docs",      href: "#",                          icon: BookOpen   },
              { label: "GitHub",    href: "#",                          icon: Github     },
              { label: "Arc",       href: "https://arc-testnet.io",     icon: ExternalLink },
              { label: "GenLayer",  href: "https://genlayer.io",        icon: ExternalLink },
            ].map((link) => (
              <a key={link.label} href={link.href} target="_blank" rel="noopener noreferrer"
                style={{ display: "flex", alignItems: "center", gap: 5, fontSize: "0.75rem", color: "var(--text-faint)", textDecoration: "none", transition: "color 0.15s" }}
                onMouseEnter={(e) => (e.currentTarget.style.color = "var(--text-muted)")}
                onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-faint)")}>
                <link.icon size={12} />
                {link.label}
              </a>
            ))}
          </div>
        </div>
      </footer>
    </div>
  );
}
