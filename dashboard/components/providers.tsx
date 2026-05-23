"use client";

import { SWRConfig } from "swr";
import { fetcher } from "@/lib/rpc";
import { WagmiProvider } from "wagmi";
import { RainbowKitProvider, darkTheme } from "@rainbow-me/rainbowkit";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { wagmiConfig } from "@/lib/wagmi";
import "@rainbow-me/rainbowkit/styles.css";
import { useState } from "react";

export function Providers({ children }: { children: React.ReactNode }) {
  // QueryClient must be created inside component to avoid sharing state between requests
  const [queryClient] = useState(() => new QueryClient());

  return (
    <WagmiProvider config={wagmiConfig}>
      <QueryClientProvider client={queryClient}>
        <RainbowKitProvider
          theme={darkTheme({
            accentColor: "#7170ff",
            accentColorForeground: "white",
            borderRadius: "medium",
            fontStack: "system",
            overlayBlur: "small",
          })}
          modalSize="compact"
        >
          <SWRConfig
            value={{
              fetcher,
              refreshInterval: 15000,
              revalidateOnFocus: false,
              dedupingInterval: 5000,
            }}
          >
            {children}
          </SWRConfig>
        </RainbowKitProvider>
      </QueryClientProvider>
    </WagmiProvider>
  );
}
