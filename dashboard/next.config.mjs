/** @type {import('next').NextConfig} */
const nextConfig = {
  // Allow the OCI backend as a valid image/API source
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
};
export default nextConfig;
