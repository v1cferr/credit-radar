import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emit a self-contained server bundle so the production image does not
  // need to carry node_modules.
  output: "standalone",

  // This is a private, single-user application over sensitive financial
  // data; it should never advertise its stack.
  poweredByHeader: false,
};

export default nextConfig;
