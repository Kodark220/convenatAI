"use client";

import { useState, useMemo } from "react";
import { Search } from "lucide-react";
import useSWR from "swr";
import { TopBar } from "@/components/top-bar";
import { AgentCard } from "@/components/agent-card";
import type { Agent, AgentRole } from "@/lib/types";
import { endpoints } from "@/lib/rpc";

const ROLES: { id: AgentRole | "all"; label: string }[] = [
  { id: "all", label: "All Roles" },
  { id: "client", label: "Client" },
  { id: "provider", label: "Provider" },
  { id: "arbitrator", label: "Arbitrator" },
];

const PAGE_SIZE = 12;

export default function AgentsPage() {
  const { data: agents = [] } = useSWR<Agent[]>(endpoints.agents);
  const [search, setSearch] = useState("");
  const [role, setRole] = useState<AgentRole | "all">("all");
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    return agents.filter((a) => {
      const matchesRole = role === "all" || a.role === role;
      const matchesSearch =
        !search || a.address.toLowerCase().includes(search.toLowerCase());
      return matchesRole && matchesSearch;
    });
  }, [agents, role, search]);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paged = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <>
      <TopBar title="Agents" subtitle={`${agents.length} registered agents`} />

      <div className="p-6 space-y-5">
        {/* Filters */}
        <div className="flex items-center gap-3 flex-wrap">
          {/* Search */}
          <div className="relative">
            <Search
              size={13}
              style={{
                position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)",
                color: "var(--text-faint)", pointerEvents: "none",
              }}
            />
            <input
              type="text"
              placeholder="Search address…"
              className="input"
              style={{ paddingLeft: 30, width: 220, fontFamily: "var(--font-mono)", fontSize: "0.78rem" }}
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            />
          </div>

          {/* Role filter */}
          <div className="flex gap-1.5">
            {ROLES.map((r) => (
              <button
                key={r.id}
                onClick={() => { setRole(r.id); setPage(1); }}
                style={{
                  padding: "6px 12px",
                  borderRadius: 7,
                  fontSize: "0.75rem",
                  fontWeight: 500,
                  fontFamily: "var(--font-display)",
                  border: "1px solid",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                  background: role === r.id ? "var(--accent-glow)" : "transparent",
                  borderColor: role === r.id ? "rgba(113,112,255,0.3)" : "var(--border)",
                  color: role === r.id ? "var(--accent-bright)" : "var(--text-faint)",
                }}
              >
                {r.label}
              </button>
            ))}
          </div>

          <p style={{ marginLeft: "auto", fontSize: "0.72rem", color: "var(--text-faint)", fontFamily: "var(--font-mono)" }}>
            {filtered.length} agents
          </p>
        </div>

        {/* Agent grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
          {paged.map((agent, i) => (
            <AgentCard key={agent.address} agent={agent} index={i} />
          ))}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 pt-2">
            <button
              className="btn-ghost"
              style={{ padding: "5px 12px", fontSize: "0.75rem" }}
              disabled={page === 1}
              onClick={() => setPage((p) => p - 1)}
            >
              ← Prev
            </button>
            <span style={{ fontSize: "0.75rem", color: "var(--text-faint)", fontFamily: "var(--font-mono)" }}>
              {page} / {totalPages}
            </span>
            <button
              className="btn-ghost"
              style={{ padding: "5px 12px", fontSize: "0.75rem" }}
              disabled={page === totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next →
            </button>
          </div>
        )}
      </div>
    </>
  );
}
