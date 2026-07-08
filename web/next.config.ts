import type { NextConfig } from "next";

const apiDevOrigin =
  process.env.NEXT_PUBLIC_ADVOI_API_URL?.replace(/\/api\/?$/, "") ||
  "http://127.0.0.1:8010";

const nextConfig: NextConfig = {
  output: "standalone",
  outputFileTracingRoot: __dirname,
  serverExternalPackages: ["onnxruntime-web"],
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
          { key: "Cross-Origin-Embedder-Policy", value: "require-corp" },
          { key: "Cross-Origin-Resource-Policy", value: "cross-origin" },
        ],
      },
    ];
  },
  webpack: (config, { isServer }) => {
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        path: false,
        crypto: false,
      };
    }
    return config;
  },
  async rewrites() {
    if (process.env.NODE_ENV === "production") {
      return [];
    }
    return [{ source: "/api/:path*", destination: `${apiDevOrigin}/api/:path*` }];
  },
};

export default nextConfig;