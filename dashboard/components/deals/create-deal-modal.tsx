"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Loader2, Zap } from "lucide-react";
import { useDealStore } from "@/lib/deal-store";
import { useRouter } from "next/navigation";

export function CreateDealModal() {
  const { isModalOpen, closeModal, createDeal } = useDealStore();
  const router = useRouter();

  const [form, setForm] = useState({
    title: "",
    description: "",
    budget: "",
    deadline: "",
    criteria: "",
    chain: "arc" as "arc" | "genlayer",
  });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = () => {
    const e: Record<string, string> = {};
    if (!form.title.trim()) e.title = "Required";
    if (!form.budget || isNaN(Number(form.budget)) || Number(form.budget) <= 0) e.budget = "Enter a valid USDC amount";
    if (!form.deadline) e.deadline = "Required";
    if (!form.criteria.trim()) e.criteria = "Required";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) return;
    setLoading(true);
    await new Promise((r) => setTimeout(r, 600)); // feel deliberate
    const deal = createDeal({
      title: form.title.trim(),
      description: form.description.trim(),
      budget: Number(form.budget),
      deadline: form.deadline,
      criteria: form.criteria.trim(),
      chain: form.chain,
    });
    setLoading(false);
    router.push(`/deals/${deal.id}`);
  };

  const set = (k: string, v: string) => {
    setForm((f) => ({ ...f, [k]: v }));
    if (errors[k]) setErrors((e) => { const n = { ...e }; delete n[k]; return n; });
  };

  return (
    <AnimatePresence>
      {isModalOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 z-50"
            style={{ background: "rgba(0,0,0,0.75)", backdropFilter: "blur(4px)" }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={closeModal}
          />

          {/* Modal */}
          <motion.div
            className="fixed z-50 inset-0 flex items-center justify-center p-4"
            initial={{ opacity: 0, scale: 0.96, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 8 }}
            transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
          >
            <div
              className="w-full max-w-lg"
              style={{
                background: "var(--surface-1)",
                border: "1px solid var(--border-strong)",
                borderRadius: 16,
                boxShadow: "0 24px 80px rgba(0,0,0,0.6), 0 0 0 1px rgba(113,112,255,0.08)",
              }}
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-center justify-between px-6 py-5" style={{ borderBottom: "1px solid var(--border)" }}>
                <div className="flex items-center gap-3">
                  <div style={{ width: 32, height: 32, borderRadius: 8, background: "var(--accent-glow)", border: "1px solid rgba(113,112,255,0.2)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <Zap size={14} style={{ color: "var(--accent-bright)" }} />
                  </div>
                  <div>
                    <p style={{ fontSize: "0.9rem", fontWeight: 700, color: "var(--text-primary)" }}>Create Deal</p>
                    <p style={{ fontSize: "0.68rem", color: "var(--text-faint)", fontFamily: "var(--font-mono)" }}>autonomous agent commerce</p>
                  </div>
                </div>
                <button onClick={closeModal} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-faint)", padding: 4 }}>
                  <X size={16} />
                </button>
              </div>

              {/* Form */}
              <div className="px-6 py-5 space-y-4">
                <ModalField label="Task Title" error={errors.title} required>
                  <input className="input" placeholder="e.g. Market research report on DeFi protocols"
                    value={form.title} onChange={(e) => set("title", e.target.value)} />
                </ModalField>

                <ModalField label="Description">
                  <textarea className="input" placeholder="Describe the task in detail…"
                    value={form.description} onChange={(e) => set("description", e.target.value)}
                    style={{ minHeight: 72, resize: "vertical" }} />
                </ModalField>

                <div className="grid grid-cols-2 gap-4">
                  <ModalField label="Budget (USDC)" error={errors.budget} required>
                    <input className="input" type="number" placeholder="500"
                      value={form.budget} onChange={(e) => set("budget", e.target.value)}
                      style={{ fontFamily: "var(--font-mono)" }} />
                  </ModalField>
                  <ModalField label="Deadline" error={errors.deadline} required>
                    <input className="input" type="date"
                      value={form.deadline} onChange={(e) => set("deadline", e.target.value)}
                      style={{ fontFamily: "var(--font-mono)", colorScheme: "dark" }} />
                  </ModalField>
                </div>

                <ModalField label="Verification Criteria" error={errors.criteria} required>
                  <input className="input" placeholder="e.g. Report must include 5+ sources, >2000 words"
                    value={form.criteria} onChange={(e) => set("criteria", e.target.value)} />
                </ModalField>

                <ModalField label="Settlement Chain">
                  <div className="grid grid-cols-2 gap-2">
                    {(["arc", "genlayer"] as const).map((c) => (
                      <button
                        key={c}
                        onClick={() => set("chain", c)}
                        style={{
                          padding: "8px 12px", borderRadius: 8, fontSize: "0.78rem",
                          fontWeight: 500, cursor: "pointer", textAlign: "left",
                          border: form.chain === c ? "1px solid rgba(113,112,255,0.4)" : "1px solid var(--border)",
                          background: form.chain === c ? "var(--accent-glow)" : "var(--surface-2)",
                          color: form.chain === c ? "var(--accent-bright)" : "var(--text-muted)",
                          transition: "all 0.15s ease",
                          fontFamily: "var(--font-display)",
                        }}
                      >
                        {c === "arc" ? "⬡ Arc Testnet" : "◈ GenLayer"}
                      </button>
                    ))}
                  </div>
                </ModalField>
              </div>

              {/* Footer */}
              <div className="flex gap-3 px-6 py-4" style={{ borderTop: "1px solid var(--border)" }}>
                <button className="btn-primary flex-1" onClick={handleSubmit} disabled={loading}>
                  {loading ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
                  {loading ? "Creating…" : "Create Deal"}
                </button>
                <button className="btn-ghost" onClick={closeModal} style={{ flexShrink: 0 }}>Cancel</button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function ModalField({ label, error, required, children }: { label: string; error?: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label style={{ fontSize: "0.65rem", fontWeight: 600, color: error ? "var(--danger)" : "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
        {label}{required && <span style={{ color: "var(--danger)" }}> *</span>}
      </label>
      {children}
      {error && <p style={{ fontSize: "0.68rem", color: "var(--danger)", fontFamily: "var(--font-mono)" }}>{error}</p>}
    </div>
  );
}
