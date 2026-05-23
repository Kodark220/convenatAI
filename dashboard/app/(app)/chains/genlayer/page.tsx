"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import useSWR from "swr";
import { CheckCircle, Loader2, PlusCircle, ExternalLink, Wallet } from "lucide-react";
import { TopBar } from "@/components/top-bar";
import { useWallet } from "@/components/wallet-button";
import { endpoints, registerJob } from "@/lib/rpc";
import type { ChainInfo, ChainEvent, RegisterJobPayload } from "@/lib/types";
import { shortHash, formatTimestamp } from "@/lib/utils";

export default function GenLayerPage() {
  const { data: info } = useSWR<ChainInfo>(endpoints.chainInfo("genlayer"));
  const { data: events = [] } = useSWR<ChainEvent[]>(endpoints.events("genlayer"), { refreshInterval: 15000 });

  const { address, isConnected, isOnGenLayer, switchToGenLayer } = useWallet();

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<RegisterJobPayload>({ streamId: "", buyer: "", seller: "", criteria: "" });
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Auto-fill buyer address when wallet connects
  useEffect(() => {
    if (address) {
      setForm((f) => ({ ...f, buyer: address }));
    }
  }, [address]);

  const handleRegister = async () => {
    if (!isConnected) {
      setError("Connect your wallet first.");
      return;
    }
    if (!isOnGenLayer) {
      setError("Switch to GenLayer Testnet to register a job.");
      return;
    }
    if (!form.streamId || !form.buyer || !form.seller) {
      setError("Stream ID, buyer, and seller are required.");
      return;
    }
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await registerJob(form);
      setSuccess(result.txHash);
      setForm((f) => ({ ...f, streamId: "", seller: "", criteria: "" })); // keep buyer (wallet)
    } catch {
      setError("Failed to register job. Check your backend connection.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <TopBar title="GenLayer" subtitle="ConvenatContract SLA monitor" />

      <div className="p-6 space-y-6">
        {/* Contract info card */}
        {info && (
          <div className="card p-5">
            <div className="flex items-start justify-between mb-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="idle-dot" style={{ display: "inline-block" }} />
                  <h2 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)" }}>
                    {info.name}
                  </h2>
                  <span className="badge" style={{ background: "rgba(255,255,255,0.04)", color: "var(--text-faint)", border: "1px solid var(--border)" }}>
                    Testnet
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

            <div className="grid grid-cols-2 gap-4">
              <div>
                <p style={{ fontSize: "0.65rem", fontWeight: 600, color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }}>Contract</p>
                <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--text-muted)" }}>{info.contract}</p>
              </div>
              <div>
                <p style={{ fontSize: "0.65rem", fontWeight: 600, color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }}>Wallet</p>
                {isConnected ? (
                  <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--success)" }}>{shortHash(address!)}</p>
                ) : (
                  <p style={{ fontSize: "0.72rem", color: "var(--text-faint)" }}>Not connected</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Register Job */}
        <div className="card">
          <div
            className="px-5 py-4 flex items-center justify-between cursor-pointer"
            style={{ borderBottom: showForm ? "1px solid var(--border)" : "none" }}
            onClick={() => setShowForm((v) => !v)}
          >
            <div className="flex items-center gap-2">
              <PlusCircle size={15} style={{ color: "var(--accent-bright)" }} />
              <h2 style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text-primary)" }}>
                Register Job
              </h2>
              <span style={{ fontSize: "0.7rem", color: "var(--text-faint)" }}>
                → calls <code style={{ fontFamily: "var(--font-mono)", color: "var(--accent-bright)" }}>register_job()</code>
              </span>
            </div>
            <span style={{ color: "var(--text-faint)", fontSize: "0.8rem" }}>{showForm ? "↑" : "↓"}</span>
          </div>

          <AnimatePresence>
            {showForm && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.25 }}
                style={{ overflow: "hidden" }}
              >
                <div className="p-5 space-y-4">
                  {/* Not connected warning */}
                  {!isConnected && (
                    <div className="flex items-center gap-3 p-3 rounded-lg" style={{ background: "rgba(94,106,210,0.08)", border: "1px solid rgba(94,106,210,0.2)" }}>
                      <Wallet size={14} style={{ color: "var(--accent-bright)", flexShrink: 0 }} />
                      <p style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
                        Connect your wallet to auto-fill your address and submit on-chain.
                      </p>
                    </div>
                  )}

                  {/* Wrong network warning */}
                  {isConnected && !isOnGenLayer && (
                    <div className="flex items-center justify-between p-3 rounded-lg" style={{ background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.2)" }}>
                      <p style={{ fontSize: "0.78rem", color: "var(--warning)" }}>
                        Switch to GenLayer Testnet to submit.
                      </p>
                      <button
                        className="btn-ghost"
                        style={{ fontSize: "0.72rem", padding: "4px 10px", color: "var(--warning)", borderColor: "rgba(245,158,11,0.3)" }}
                        onClick={switchToGenLayer}
                      >
                        Switch
                      </button>
                    </div>
                  )}

                  {/* Success */}
                  {success && (
                    <motion.div
                      initial={{ opacity: 0, y: -8 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="flex items-start gap-3 p-4"
                      style={{ background: "var(--success-glow)", border: "1px solid rgba(16,185,129,0.2)", borderRadius: 10 }}
                    >
                      <CheckCircle size={16} style={{ color: "var(--success)", flexShrink: 0, marginTop: 1 }} />
                      <div>
                        <p style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--success)" }}>Job registered!</p>
                        <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.68rem", color: "var(--text-muted)", marginTop: 2 }}>
                          Tx: {shortHash(success)}
                        </p>
                      </div>
                    </motion.div>
                  )}

                  {/* Error */}
                  {error && (
                    <div className="p-3 rounded-lg" style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)" }}>
                      <p style={{ fontSize: "0.78rem", color: "var(--danger)" }}>{error}</p>
                    </div>
                  )}

                  {/* Form fields */}
                  <div className="grid grid-cols-2 gap-4">
                    <Field label="Stream ID" required>
                      <input type="text" className="input" placeholder="stream-abc123"
                        value={form.streamId}
                        onChange={(e) => setForm((f) => ({ ...f, streamId: e.target.value }))}
                        style={{ fontFamily: "var(--font-mono)" }}
                      />
                    </Field>
                    <Field label="Criteria">
                      <input type="text" className="input" placeholder="SLA: 99.9% uptime"
                        value={form.criteria}
                        onChange={(e) => setForm((f) => ({ ...f, criteria: e.target.value }))}
                      />
                    </Field>
                    <Field label="Buyer Address (you)" required>
                      <input type="text" className="input"
                        placeholder={isConnected ? address : "Connect wallet or enter manually"}
                        value={form.buyer}
                        onChange={(e) => setForm((f) => ({ ...f, buyer: e.target.value }))}
                        style={{ fontFamily: "var(--font-mono)", opacity: isConnected ? 0.7 : 1 }}
                        readOnly={isConnected}
                      />
                    </Field>
                    <Field label="Seller Address" required>
                      <input type="text" className="input" placeholder="0x…"
                        value={form.seller}
                        onChange={(e) => setForm((f) => ({ ...f, seller: e.target.value }))}
                        style={{ fontFamily: "var(--font-mono)" }}
                      />
                    </Field>
                  </div>

                  <div className="flex gap-3 pt-1">
                    <button
                      className="btn-primary"
                      onClick={handleRegister}
                      disabled={loading || (isConnected && !isOnGenLayer)}
                    >
                      {loading ? <Loader2 size={14} className="animate-spin" /> : null}
                      {loading ? "Registering…" : "Register Job"}
                    </button>
                    <button className="btn-ghost"
                      onClick={() => {
                        setSuccess(null); setError(null);
                        setForm({ streamId: "", buyer: address ?? "", seller: "", criteria: "" });
                      }}
                    >
                      Reset
                    </button>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Events table */}
        <div className="card">
          <div className="px-5 py-4" style={{ borderBottom: "1px solid var(--border)" }}>
            <h2 style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text-primary)" }}>Contract Events</h2>
          </div>
          {events.length === 0 ? (
            <div className="py-12 text-center">
              <p style={{ color: "var(--text-faint)", fontSize: "0.825rem" }}>No events yet. Register a job to get started.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr><th>Block</th><th>Event</th><th>Args</th><th>Tx Hash</th><th>Time</th></tr>
                </thead>
                <tbody>
                  {events.map((evt) => (
                    <tr key={evt.id}>
                      <td><span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--text-muted)" }}>#{evt.blockNumber}</span></td>
                      <td><span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--accent-bright)" }}>{evt.eventName}</span></td>
                      <td><span style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", color: "var(--text-faint)" }}>{Object.entries(evt.args).map(([k, v]) => `${k}: ${v}`).join(", ")}</span></td>
                      <td><span className="text-address">{shortHash(evt.txHash)}</span></td>
                      <td><span style={{ fontSize: "0.72rem", color: "var(--text-faint)", fontFamily: "var(--font-mono)" }}>{formatTimestamp(evt.timestamp)}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function Field({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label style={{ fontSize: "0.65rem", fontWeight: 600, color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
        {label}{required && <span style={{ color: "var(--danger)" }}> *</span>}
      </label>
      {children}
    </div>
  );
}
