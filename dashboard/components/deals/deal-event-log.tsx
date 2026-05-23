"use client";

import { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { DealEvent } from "@/lib/deal-store";
import { EVENT_TYPE_COLORS } from "@/lib/deal-config";

interface DealEventLogProps {
  events: DealEvent[];
}

const TYPE_PREFIX: Record<string, string> = {
  info:    "[INFO ]",
  success: "[OK   ]",
  warning: "[WARN ]",
  error:   "[ERROR]",
  chain:   "[CHAIN]",
};

export function DealEventLog({ events }: DealEventLogProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  return (
    <div className="card flex flex-col" style={{ height: 280 }}>
      <div className="px-5 py-4 flex items-center gap-2" style={{ borderBottom: "1px solid var(--border)", flexShrink: 0 }}>
        <motion.div
          style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--success)" }}
          animate={{ opacity: [1, 0.3, 1] }}
          transition={{ duration: 1.5, repeat: Infinity }}
        />
        <p style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--text-primary)" }}>Event Log</p>
        <span style={{ marginLeft: "auto", fontSize: "0.65rem", color: "var(--text-faint)", fontFamily: "var(--font-mono)" }}>
          {events.length} events
        </span>
      </div>

      <div ref={scrollRef} style={{ flex: 1, overflowY: "auto", padding: "12px 20px" }}>
        <AnimatePresence initial={false}>
          {events.map((evt) => (
            <motion.div
              key={evt.id}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2 }}
              style={{ display: "flex", gap: 10, paddingBottom: 8, marginBottom: 4, borderBottom: "1px solid var(--border)" }}
            >
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.67rem", color: "var(--text-faint)", flexShrink: 0, paddingTop: 1, minWidth: 52 }}>
                {new Date(evt.timestamp).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false })}
              </span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.67rem", color: EVENT_TYPE_COLORS[evt.type], flexShrink: 0, paddingTop: 1 }}>
                {TYPE_PREFIX[evt.type]}
              </span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
                {evt.message}
              </span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
