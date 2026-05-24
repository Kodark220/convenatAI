import { defineChain } from "viem";
import { http, createConfig } from "wagmi";
import { mainnet } from "wagmi/chains";
import { getDefaultConfig } from "@rainbow-me/rainbowkit";

// ─── Arc Testnet ──────────────────────────────────────────────────────────────
// TODO: replace with actual Arc testnet chain ID + RPC from your backend team
export const arcTestnet = defineChain({
  id: 5_042_002, // Arc Testnet (0x4cef52)
  name: "Arc Testnet",
  nativeCurrency: { name: "ARC", symbol: "ARC", decimals: 18 },
  rpcUrls: {
    default: {
      http: [process.env.NEXT_PUBLIC_ARC_RPC ?? "https://rpc.arc-testnet.io"],
    },
  },
  blockExplorers: {
    default: {
      name: "Arc Explorer",
      url: "https://explorer.arc-testnet.io",
    },
  },
  testnet: true,
});

// ─── GenLayer Testnet ─────────────────────────────────────────────────────────
// TODO: replace with actual GenLayer testnet chain ID + RPC
export const genLayerTestnet = defineChain({
  id: 42_069, // placeholder — update with real GenLayer testnet chain ID
  name: "GenLayer Testnet",
  nativeCurrency: { name: "GEN", symbol: "GEN", decimals: 18 },
  rpcUrls: {
    default: {
      http: [process.env.NEXT_PUBLIC_GENLAYER_RPC ?? "https://rpc.genlayer-testnet.io"],
    },
  },
  blockExplorers: {
    default: {
      name: "GenLayer Explorer",
      url: "https://explorer.genlayer.io",
    },
  },
  testnet: true,
});

// ─── Wagmi config ─────────────────────────────────────────────────────────────
export const wagmiConfig = getDefaultConfig({
  appName: "convenatAI",
  // TODO: get a free project ID from https://cloud.walletconnect.com
  projectId: process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID ?? "YOUR_WALLETCONNECT_PROJECT_ID",
  chains: [arcTestnet, genLayerTestnet],
  transports: {
    [arcTestnet.id]: http(),
    [genLayerTestnet.id]: http(),
  },
  ssr: true,
});
