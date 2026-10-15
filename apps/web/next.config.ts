import type { NextConfig } from "next";

// The pitch videos are uploaded from the browser to Supabase Storage and played
// from it through signed links, so the Supabase address is allowed for both.
// The address is read when the app is built.
const supabase = (() => {
  try {
    return process.env.NEXT_PUBLIC_SUPABASE_URL ? new URL(process.env.NEXT_PUBLIC_SUPABASE_URL).origin : "";
  } catch {
    return "";
  }
})();

// SRD SEC-W2: security headers on every response.
const csp = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  // The fonts are served from this site by next/font, so no font host is allowed.
  "style-src 'self' 'unsafe-inline'",
  "font-src 'self'",
  "img-src 'self' data:",
  // blob: lets a founder watch the video they chose before it uploads.
  `media-src 'self' blob: ${supabase}`.trim(),
  `connect-src 'self' ${supabase}`.trim(),
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
].join("; ");

const securityHeaders = [
  { key: "Content-Security-Policy", value: csp },
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];

const config: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  transpilePackages: ["@ikonetu/ui-tokens", "@ikonetu/score-engine"],
  // A piece of evidence carries up to three files of 10 MB each through a server action.
  experimental: { serverActions: { bodySizeLimit: "32mb" } },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
  // The investor interest form was retired on 15 October 2026, when investor
  // accounts opened. Its old address goes to For investors.
  async redirects() {
    return [{ source: "/investor-interest", destination: "/for-investors", permanent: true }];
  },
};

export default config;
