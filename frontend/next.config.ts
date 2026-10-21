import type { NextConfig } from "next";

// API origin for CSP connect-src (REST + WebSocket). Defaults to local dev.
const apiOrigin = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const wsOrigin = apiOrigin.replace(/^http/, "ws");

const nextConfig: NextConfig = {
    images: {
        // Member photos and horoscope charts are served straight from the API
        // (/uploads/...). Next 16's optimizer refuses upstreams that resolve to a
        // private IP (localhost in dev), and member photos should not be copied
        // into the optimizer cache, so every <Image> is served as-is.
        unoptimized: true,
        // Keeps the API host allowed if optimization is ever re-enabled.
        remotePatterns: [new URL(`${apiOrigin}/uploads/**`)],
    },
    async headers() {
        return [
            {
                source: "/(.*)",
                headers: [
                    {
                        key: "X-Content-Type-Options",
                        value: "nosniff",
                    },
                    {
                        key: "X-Frame-Options",
                        value: "DENY",
                    },
                    {
                        key: "Referrer-Policy",
                        value: "strict-origin-when-cross-origin",
                    },
                    {
                        key: "Content-Security-Policy",
                        // Default strict policy - adjust if you need inline scripts or specific external assets
                        value: `default-src 'self'; img-src 'self' data: blob: ${apiOrigin}; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; connect-src 'self' ${apiOrigin} ${wsOrigin};`,
                    },
                ],
            },
        ];
    },
};

export default nextConfig;
