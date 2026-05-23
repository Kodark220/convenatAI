"use client";

import { ConnectButton } from "@rainbow-me/rainbowkit";
import { useAccount, useBalance, useSwitchChain } from "wagmi";
import { arcTestnet, genLayerTestnet } from "@/lib/wagmi";
import { shortAddress, formatUSDC } from "@/lib/utils";
import { ChevronDown, Wallet, AlertTriangle } from "lucide-react";
import { useState } from "react";

export function WalletButton() {
  return (
    <ConnectButton.Custom>
      {({
        account,
        chain,
        openAccountModal,
        openChainModal,
        openConnectModal,
        mounted,
      }) => {
        const ready = mounted;
        const connected = ready && account && chain;

        if (!ready) return null;

        if (!connected) {
          return (
            <button className="btn-primary" onClick={openConnectModal} style={{ fontSize: "0.78rem", padding: "7px 14px" }}>
              <Wallet size={13} />
              Connect Wallet
            </button>
          );
        }

        // Wrong network warning
        if (chain.unsupported) {
          return (
            <button
              onClick={openChainModal}
              style={{
                display: "flex", alignItems: "center", gap: 6,
                padding: "7px 12px", borderRadius: 8, fontSize: "0.78rem",
                fontWeight: 600, cursor: "pointer", border: "1px solid rgba(239,68,68,0.3)",
                background: "rgba(239,68,68,0.1)", color: "var(--danger)",
              }}
            >
              <AlertTriangle size={13} />
              Wrong Network
            </button>
          );
        }

        return (
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {/* Chain switcher */}
            <button
              onClick={openChainModal}
              style={{
                display: "flex", alignItems: "center", gap: 6,
                padding: "6px 10px", borderRadius: 8, fontSize: "0.72rem",
                fontWeight: 500, cursor: "pointer",
                border: "1px solid var(--border)", background: "var(--surface-2)",
                color: "var(--text-muted)",
              }}
            >
              {chain.hasIcon && chain.iconUrl && (
                <img src={chain.iconUrl} alt={chain.name} style={{ width: 14, height: 14, borderRadius: "50%" }} />
              )}
              {chain.name}
              <ChevronDown size={11} />
            </button>

            {/* Account button */}
            <button
              onClick={openAccountModal}
              style={{
                display: "flex", alignItems: "center", gap: 8,
                padding: "6px 12px", borderRadius: 8, fontSize: "0.78rem",
                fontWeight: 500, cursor: "pointer",
                border: "1px solid var(--border-strong)",
                background: "var(--surface-2)", color: "var(--text-primary)",
              }}
            >
              {/* Avatar dot */}
              <div style={{
                width: 20, height: 20, borderRadius: "50%",
                background: "linear-gradient(135deg, #5e6ad2, #10b981)",
                flexShrink: 0,
              }} />
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem" }}>
                {account.displayName}
              </span>
              {account.displayBalance && (
                <span style={{ color: "var(--text-faint)", fontSize: "0.68rem", fontFamily: "var(--font-mono)" }}>
                  {account.displayBalance}
                </span>
              )}
            </button>
          </div>
        );
      }}
    </ConnectButton.Custom>
  );
}

// ─── Hook: expose wallet state to the rest of the app ─────────────────────────
// Import this wherever you need the connected address (e.g. register_job form)

export function useWallet() {
  const { address, isConnected, chain } = useAccount();
  const { switchChain } = useSwitchChain();

  const switchToArc = () => switchChain({ chainId: arcTestnet.id });
  const switchToGenLayer = () => switchChain({ chainId: genLayerTestnet.id });

  const isOnArc = chain?.id === arcTestnet.id;
  const isOnGenLayer = chain?.id === genLayerTestnet.id;

  return {
    address,
    isConnected,
    chain,
    isOnArc,
    isOnGenLayer,
    switchToArc,
    switchToGenLayer,
  };
}
