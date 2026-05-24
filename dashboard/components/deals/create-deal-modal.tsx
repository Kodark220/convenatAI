"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Loader2, Zap, Wallet, CheckCircle, ExternalLink } from "lucide-react";
import { useAccount } from "wagmi";
import { useDealStore } from "@/lib/deal-store";
import { useCreateDeal } from "@/lib/use-create-deal";
import { useRouter } from "next/navigation";

const TX_STEPS = ["approve", "createJob", "fund"] as const;
type TxStep = (typeof TX_STEPS)[number];

const STEP_LABELS: Record<TxStep, string> = {
  approve: "Approving USDC spending…",
  createJob: "Creating job on Arc Testnet…",
  fund: "Funding escrow…",
};

export function CreateDealModal() {
  const { isModalOpen, closeModal, isConnected, address } = { isConnected: false, address: null };
  // Use the real hook
  const { isConnected: walletConnected, address: walletAddress } = useAccount();
  const { createOnChainDeal, isCreating, error } = useCreateDeal();
  const router = useRouter();

  const [form, setForm] = useState({
    provider: "",
    description: "",
    budget: "",
    deadline: "",
    criteria: "",
  });
  const [loading, setLoading] = useState(false);
  const [txStep, setTxStep] = useState<TxStep | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [result, setResult] = useState<{
    dealId: string;
    jobId: number;
    approveTx: string;
    createTx: string;
    fundTx: string;
  } | null>(null);

  const validate = () => {
    const e: Record<string, string> = {};
    if (!walletConnected) e.wallet = "Connect your wallet first";
    if (!form.provider.trim()) e.provider = "Required";
    if (!form.budget || isNaN(Number(form.budget)) || Number(form.budget) <= 0) e.budget = "Enter a valid USDC amount";
    if (!form.criteria.trim()) e.criteria = "Required";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate() || !walletAddress) return;

    setLoading(true);
    setTxStep("approve");

    try {
      const result = await createOnChainDeal({
        provider: form.provider.trim() as `0x${string}`,
        description: form.description.trim() || form.provider.trim(),
        budgetUsdc: Number(form.budget),
      });

      if (result) {
        setResult(result);
        setTxStep(null);
      } else {
        setLoading(false);
        setTxStep(null);
      }
    } catch {
      setLoading(false);
      setTxStep(null);
    }
  };

  const set = (k: string, v: string) => {
    setForm((f) => ({ ...f, [k]: v }));
    if (errors[k]) setErrors((e) => { const n = { ...e }; delete n[k]; return n; });
  };

  const close = () => {
    closeModal();
    setLoading(false);
    setTxStep(null);
    setResult(null);
    setErrors({});
  };

  return (
    <AnimatePresence>
      {isModalOpen && (
        <>
          <motion.div
            className="fixed inset-0 z-50"
            style={{ background: "rgba(0,0,0,0.75)", backdropFilter: "blur(4px)" }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={close}
          />

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
                <div>
                  <p style={{ fontSize: "0.9rem", fontWeight: 700, color: "var(--text-primary)" }}>Create On-Chain Deal</p>
                  <p style={{ fontSize: "0.68rem", color: "var(--text-faint)", fontFamily: "var(--font-mono)" }}>
                    {walletConnected ? `${walletAddress?.slice(0, 6)}...${walletAddress?.slice(-4)}` : "Connect wallet to start"}
                  </p>
                </div>
                <button onClick={close} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-faint)", padding: 4 }}>
                  <X size={16} />
                </button>
              </div>

              {result ? (
                /* ── Success State ── */
                <div className="px-6 py-8 text-center">
                  <div style={{ width: 48, height: 48, borderRadius: "50%", background: "rgba(16,185,129,0.15)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px" }}>
                    <CheckCircle size={24} style={{ color: "#34d399" }} />
                  </div>
                  <p style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: 4 }}>Deal Created!</p>
                  <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginBottom: 16 }}>Job #{result.jobId} — escrow locked on Arc Testnet</p>

                  <div className="flex flex-col gap-2" style={{ textAlign: "left", fontSize: "0.72rem", fontFamily: "var(--font-mono)" }}>
                    <TxLink label="Approve" hash={result.approveTx} />
                    <TxLink label="Create" hash={result.createTx} />
                    <TxLink label="Fund" hash={result.fundTx} />
                  </div>

                  <div className="flex gap-3 mt-6">
                    <button className="btn-primary flex-1" onClick={() => { router.push(`/deals/${result.dealId}`); close(); }}>
                      View Deal
                    </button>
                    <button className="btn-ghost" onClick={close}>Close</button>
                  </div>
                </div>
              ) : loading ? (
                /* ── Transaction Progress ── */
                <div className="px-6 py-8 text-center">
                  <Loader2 size={32} className="animate-spin" style={{ color: "var(--accent-bright)", margin: "0 auto 16px" }} />
                  <p style={{ fontSize: "0.9rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>
                    {txStep ? STEP_LABELS[txStep] : "Processing…"}
                  </p>
                  <p style={{ fontSize: "0.72rem", color: "var(--text-faint)", fontFamily: "var(--font-mono)" }}>
                    Confirm the transaction in MetaMask
                  </p>
                  <div className="flex gap-2 justify-center mt-6">
                    {TX_STEPS.map((step, i) => (
                      <div key={step} style={{
                        width: 8, height: 8, borderRadius: "50%",
                        background: txStep === step ? "var(--accent-bright)"
                          : TX_STEPS.indexOf(txStep ?? "fund") > i ? "#34d399"
                          : "var(--border-strong)",
                        transition: "all 0.3s ease",
                      }} />
                    ))}
                  </div>
                </div>
              ) : (
                /* ── Form ── */
                <>
                  <div className="px-6 py-5 space-y-4">
                    {!walletConnected && (
                      <div style={{ padding: 10, borderRadius: 8, background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.2)", display: "flex", gap: 8, alignItems: "center" }}>
                        <Wallet size={14} style={{ color: "#fbbf24", flexShrink: 0 }} />
                        <p style={{ fontSize: "0.72rem", color: "#fbbf24" }}>Connect your wallet to create deals on-chain</p>
                      </div>
                    )}

                    <ModalField label="Provider Address" error={errors.provider} required>
                      <input className="input" placeholder="0x… (recipient of USDC on completion)"
                        value={form.provider} onChange={(e) => set("provider", e.target.value)}
                        style={{ fontFamily: "var(--font-mono)" }} />
                    </ModalField>

                    <ModalField label="Description">
                      <textarea className="input" placeholder="Describe the task…"
                        value={form.description} onChange={(e) => set("description", e.target.value)}
                        style={{ minHeight: 60, resize: "vertical" }} />
                    </ModalField>

                    <ModalField label="Budget (USDC)" error={errors.budget} required>
                      <input className="input" type="number" placeholder="50"
                        value={form.budget} onChange={(e) => set("budget", e.target.value)}
                        style={{ fontFamily: "var(--font-mono)" }} />
                    </ModalField>

                    <ModalField label="Verification Criteria" error={errors.criteria} required>
                      <input className="input" placeholder="e.g. Report must include 5+ sources"
                        value={form.criteria} onChange={(e) => set("criteria", e.target.value)} />
                    </ModalField>

                    <div style={{ padding: 8, borderRadius: 8, background: "var(--surface-2)", fontSize: "0.68rem", color: "var(--text-faint)", fontFamily: "var(--font-mono)" }}>
                      Settlement on ⬡ Arc Testnet (Chain ID: 5042002)
                    </div>
                  </div>

                  <div className="flex gap-3 px-6 py-4" style={{ borderTop: "1px solid var(--border)" }}>
                    <button className="btn-primary flex-1" onClick={handleSubmit} disabled={loading}>
                      {loading ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
                      Create On-Chain Deal
                    </button>
                    <button className="btn-ghost" onClick={close} style={{ flexShrink: 0 }}>Cancel</button>
                  </div>
                </>
              )}

              {error && (
                <div style={{ padding: "8px 16px", background: "rgba(239,68,68,0.1)", borderTop: "1px solid rgba(239,68,68,0.2)", fontSize: "0.72rem", color: "#f87171", fontFamily: "var(--font-mono)" }}>
                  ✕ {error}
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function TxLink({ label, hash }: { label: string; hash: string }) {
  const url = `https://testnet.arcscan.app/tx/${hash}`;
  return (
    <a href={url} target="_blank" rel="noopener noreferrer"
      style={{ display: "flex", justifyContent: "space-between", padding: "6px 10px", borderRadius: 6, background: "var(--surface-2)", textDecoration: "none" }}>
      <span style={{ color: "var(--text-muted)" }}>{label}</span>
      <span style={{ display: "flex", alignItems: "center", gap: 4, color: "var(--accent-bright)" }}>
        {hash.slice(0, 10)}… <ExternalLink size={10} />
      </span>
    </a>
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
