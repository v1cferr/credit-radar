import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emit a self-contained server bundle so the production image does not
  // need to carry node_modules.
  output: "standalone",

  // This is a private, single-user application over sensitive financial
  // data; it should never advertise its stack.
  poweredByHeader: false,

  // In development, forward /api to the backend so browser-side calls are
  // same-origin exactly as they are behind the reverse proxy. Without this,
  // dev and deployment would need different base URLs and only one of them
  // would ever be exercised.
  //
  // Behind the proxy this is inert: Caddy routes /api/* to the backend before
  // a request reaches Next.js.
  async rewrites() {
    const backend =
      process.env.CREDIT_RADAR_API_INTERNAL_URL ?? "http://127.0.0.1:8007";
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};

export default nextConfig;
