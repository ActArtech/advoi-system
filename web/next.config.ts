import type { NextConfig } from "next";

const apiDevOrigin =
  process.env.NEXT_PUBLIC_ADVOI_API_URL?.replace(/\/api\/?$/, "") ||
  "http://127.0.0.1:8010";

const nextConfig: NextConfig = {
  output: "standalone",
  outputFileTracingRoot: __dirname,
  async rewrites() {
    if (process.env.NODE_ENV === "production") {
      return [];
    }
    return [{ source: "/api/:path*", destination: `${apiDevOrigin}/api/:path*` }];
  },
};

export default nextConfig;