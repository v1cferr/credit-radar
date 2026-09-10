import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emit a self-contained server bundle so the production image does not
  // need to carry node_modules.
  output: "standalone",

  // This is a private, single-user application over sensitive financial
  // data; it should never advertise its stack.
  poweredByHeader: false,

  // A DEVELOPMENT-ONLY rewrite, so browser-side calls are same-origin in dev
  // exactly as they are behind the reverse proxy. Without it, dev and
  // deployment would need different base URLs and only one would ever be
  // exercised.
  //
  // Emitted only in development on purpose. Next.js resolves rewrites at
  // BUILD time into the routes manifest, so a destination read from the
  // environment here would bake the builder's value into the image: a
  // production container would forward /api to 127.0.0.1:8007 inside itself
  // and answer 500. In production the proxy routes /api/* to the backend
  // before a request ever reaches Next.js, so no rewrite is wanted, and the
  // frontend port on its own now 404s that path instead of failing.
  async rewrites() {
    if (process.env.NODE_ENV !== "development") return [];
    const backend =
      process.env.CREDIT_RADAR_API_INTERNAL_URL ?? "http://127.0.0.1:8007";
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};

export default nextConfig;
