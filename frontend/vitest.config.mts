/**
 * Unit tests for pure modules: formatting, label maps, domain-free helpers.
 *
 * Deliberately narrow. Component and page behaviour is covered by the
 * Playwright suite against a real backend, which is where rendering,
 * navigation and empty states are actually observable. This runner exists
 * for the pure functions underneath, where a wrong string is a bug that no
 * amount of clicking would reveal.
 *
 * `.mts` because this package is CommonJS, as a Next.js project is, and
 * Vite's native config loader would otherwise read ESM syntax as CJS.
 */

import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";

export default defineConfig({
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  test: {
    include: ["src/**/*.test.ts"],
    environment: "node",
  },
});
