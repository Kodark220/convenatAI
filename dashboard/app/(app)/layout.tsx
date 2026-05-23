"use client";

import { Sidebar } from "@/components/sidebar";
import { CreateDealModal } from "@/components/deals/create-deal-modal";
import { CreateDealButton } from "@/components/deals/create-deal-button";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar />
      <main
        style={{
          marginLeft: "var(--sidebar-width)",
          flex: 1,
          minHeight: "100vh",
          overflowX: "hidden",
        }}
      >
        {children}
      </main>
      <CreateDealModal />
      <CreateDealButton />
    </div>
  );
}
