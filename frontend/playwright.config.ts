import { defineConfig, devices } from "@playwright/test";

import {
  BACKEND_PORT,
  BACKEND_URL,
  E2E_DATABASE_URL,
  FRONTEND_PORT,
  FRONTEND_URL,
  OFFLINE_FRONTEND_PORT,
  OFFLINE_FRONTEND_URL,
  UNREACHABLE_BACKEND_URL,
} from "./e2e/helpers/environment";

const isCI = !!process.env.CI;

/**
 * Chromium comes from the Nix development shell, not from Playwright's own
 * download.
 *
 * The binaries Playwright fetches are dynamically linked against paths that
 * do not exist on NixOS and fail to launch. Pointing at the nixpkgs build
 * also decouples the suite from Playwright's browser-revision pinning, which
 * otherwise breaks on every version bump on either side.
 */
const chromiumPath = process.env.CREDIT_RADAR_CHROMIUM;

/**
 * End-to-end configuration.
 *
 * These are full-stack tests: browser to Next.js to FastAPI to PostgreSQL.
 * They are owned by the frontend toolchain because pnpm already manages that
 * ecosystem, not because they only test the frontend.
 *
 * Chromium only, on purpose. This is a personal application used from one
 * browser; running three engines would triple the runtime to defend against
 * a compatibility problem nobody has. Cross-browser coverage is cheap to add
 * the day there is a reason for it.
 */
export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/global-setup.ts",

  fullyParallel: true,
  forbidOnly: isCI,
  // Retries only in CI. Locally a retry hides a flake instead of showing it,
  // and a flaky financial dashboard test is a bug worth seeing.
  retries: isCI ? 2 : 0,
  workers: isCI ? 1 : undefined,
  reporter: isCI ? [["github"], ["html", { open: "never" }]] : [["list"]],

  use: {
    baseURL: FRONTEND_URL,
    // Kept for the first retry only: a trace for every passing test is a lot
    // of disk for nothing.
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "off",
  },

  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        launchOptions: chromiumPath ? { executablePath: chromiumPath } : {},
      },
      testIgnore: /offline\.spec\.ts/,
    },
    {
      // A separate project because it needs a different base URL: the
      // instance whose backend is unreachable.
      name: "offline-backend",
      testMatch: /offline\.spec\.ts/,
      use: {
        ...devices["Desktop Chrome"],
        baseURL: OFFLINE_FRONTEND_URL,
        launchOptions: chromiumPath ? { executablePath: chromiumPath } : {},
      },
    },
  ],

  // Servers are never reused, not even locally. Global setup rebuilds the
  // frontend and the backend reads its code at import, so a reused process
  // would serve an artefact that was replaced underneath it. That produced a
  // run where thirteen unrelated tests failed once and then passed twice,
  // which is the worst kind of failure: it looks like flakiness and is
  // actually a stale build. A few seconds of startup is the price of every
  // run testing the code that is on disk.
  webServer: [
    {
      command: `uv run uvicorn credit_radar.api.app:app --host 127.0.0.1 --port ${BACKEND_PORT}`,
      cwd: "../backend",
      // Waits on the health endpoint, which also reports the database, so a
      // green start means the whole backend path works and not just that a
      // port opened.
      url: `${BACKEND_URL}/health`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        CREDIT_RADAR_DATABASE_URL: E2E_DATABASE_URL,
        CREDIT_RADAR_CORS_ORIGINS: FRONTEND_URL,
        CREDIT_RADAR_LOG_LEVEL: "WARNING",
      },
    },
    {
      command: `pnpm exec next start --port ${FRONTEND_PORT}`,
      url: FRONTEND_URL,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        CREDIT_RADAR_API_INTERNAL_URL: BACKEND_URL,
        NEXT_TELEMETRY_DISABLED: "1",
      },
    },
    {
      command: `pnpm exec next start --port ${OFFLINE_FRONTEND_PORT}`,
      url: OFFLINE_FRONTEND_URL,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        CREDIT_RADAR_API_INTERNAL_URL: UNREACHABLE_BACKEND_URL,
        NEXT_TELEMETRY_DISABLED: "1",
      },
    },
  ],
});
