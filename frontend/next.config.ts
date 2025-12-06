import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  // Only use export mode in production builds
  ...(process.env.NODE_ENV === 'production' ? { output: 'export' } : {}),

  // In development, proxy API requests to backend
  async rewrites() {
    if (process.env.NODE_ENV === 'development') {
      return [
        {
          source: '/api/v1/:path*',
          destination: 'http://localhost:9527/api/v1/:path*',
        },
      ];
    }
    return [];
  },
};

export default nextConfig;
