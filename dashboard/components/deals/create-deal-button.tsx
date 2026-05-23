"use client";

import { motion } from "framer-motion";
import { Plus } from "lucide-react";
import { useDealStore } from "@/lib/deal-store";

export function CreateDealButton() {
  const openModal = useDealStore((s) => s.openModal);

  return (
    <motion.button
      onClick={openModal}
      className="btn-primary"
      style={{
        position: "fixed",
        bottom: 28,
        right: 28,
        zIndex: 30,
        padding: "10px 18px",
        fontSize: "0.82rem",
        fontWeight: 600,
        borderRadius: 10,
        boxShadow: "0 0 0 1px rgba(113,112,255,0.3), 0 8px 32px rgba(94,106,210,0.25)",
      }}
      whileHover={{ scale: 1.04, boxShadow: "0 0 0 2px rgba(113,112,255,0.4), 0 12px 40px rgba(94,106,210,0.35)" }}
      whileTap={{ scale: 0.97 }}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.3 }}
    >
      <Plus size={14} />
      Create Deal
    </motion.button>
  );
}
