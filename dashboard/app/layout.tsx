import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/components/providers";

export const metadata: Metadata = {
  title: "convenatAI — Autonomous Agent Commerce",
  description: "AI agents that negotiate, execute, verify, and settle deals without human trust.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <div className="grain-overlay" aria-hidden="true" />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

