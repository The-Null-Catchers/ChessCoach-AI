import type { NextConfig } from "next";

const internalApiUrl = process.env.INTERNAL_API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${internalApiUrl}/api/v1/:path*`,
      },
      {
        source: "/health",
        destination: `${internalApiUrl}/health`,
      },
      {
        source: "/health/ready",
        destination: `${internalApiUrl}/health/ready`,
      },
    ];
  },
};

export default nextConfig;
