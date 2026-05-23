"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { ChainEvent } from "@/lib/types";
import { shortHash, timeAgo } from "@/lib/utils";

interface EventFeedProps {
  events: ChainEvent[];
  maxVisible?: number;
}

export function EventFeed({ events, maxVisible = 20 }: EventFeedProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(events.slice(0, maxVisible));

  useEffect(() => {
    setVisible(events.slice(0, maxVisible));
  }, [events, maxVisible]);

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [visible]);

  return (
    <div className="card flex flex-col" style={{ height: 340 }}>
      {/* Header */}
      <div className="px-5 py-4 flex items-center justify-between" style={{ borderBottom: "1px solid var(--border)" }}>
        <div className="flex items-center gap-2">
          <motion.span
            className="live-dot"
            animate={{ opacity: [1, 0.3, 1] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          />
          <h2 style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text-primary)" }}>
            Event Feed
          </h2>
        </div>
        <span style={{ fontSize: "0.65rem", color: "var(--text-faint)", fontFamily: "var(--font-mono)", letterSpacing: "0.06em" }}>
          LIVE
        </span>
      </div>

      {/* Feed */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-5 py-2"
        style={{ scrollBehavior: "smooth" }}
      >
        <AnimatePresence initial={false}>
          {visible.map((evt) => (
            <motion.div
              key={evt.id}
              className="event-line"
              style={{ display: "flex", alignItems: "baseline", gap: 4 }}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.25 }}
            >
              <span className="event-block" style={{ flexShrink: 0 }}>#{evt.blockNumber} ·</span>
              <span className="event-name" style={{ flexShrink: 0 }}>{evt.eventName}</span>
              <span style={{ color: "var(--text-faint)", flexShrink: 0 }}>·</span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.68rem", color: "var(--text-faint)", flexShrink: 0 }}>
                {shortHash(evt.txHash)}
              </span>
              <span style={{ color: "var(--text-faint)", flexShrink: 0 }}>·</span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.65rem", color: "var(--text-faint)", flexShrink: 0 }}>
                {evt.chain}
              </span>
              {/* Push timestamp to the right */}
              <span style={{ flex: 1 }} />
              <span style={{ fontSize: "0.65rem", color: "var(--text-faint)", flexShrink: 0 }}>
                {timeAgo(evt.timestamp)}
              </span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
