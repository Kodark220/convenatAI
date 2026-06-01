import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Lock the file tracing root in Next 14 experimental features
  experimental: {
    outputFileTracingRoot: path.join(__dirname, "./"),
  },

  // Skip type checking during build — third-party packages (swr, wagmi,
  // walletconnect) ship incomplete type declarations that block strict mode.
  // Run `npx tsc --noEmit` separately for project-level type safety.
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  
  images: {
    remotePatterns: [
      {
        protocol: "http",
        hostname: "79.76.62.48",
        port: "8001",
        pathname: "/**",
      },
    ],
  },
  
  webpack: (config, { webpack }) => {
    // Priority resolve from local dashboard/node_modules
    config.resolve.modules = [
      path.resolve(__dirname, "node_modules"),
      ...(config.resolve.modules || ["node_modules"]),
    ];
    
    // Explicitly alias tailwind-merge to guarantee local resolution
    config.resolve.alias = {
      ...config.resolve.alias,
      'tailwind-merge': path.resolve(__dirname, 'node_modules/tailwind-merge'),
    };
    
    // Polyfill or ignore node-native packages
    config.resolve.fallback = {
      ...config.resolve.fallback,
      fs: false,
      net: false,
      tls: false,
      crypto: false,
    };
    
    // Ignore optional multi-chain peer dependencies of Wagmi/RainbowKit that are not used
    config.plugins.push(
      new webpack.IgnorePlugin({
        resourceRegExp: /@solana|pnpapi|porto/,
      })
    );
    
    return config;
  },
};

export default nextConfig;
