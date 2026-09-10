/**
 * Prepares the end-to-end environment before any browser starts.
 *
 * Two steps, both here rather than in `webServer`, because both must finish
 * before anything serves a request and `webServer` entries start in
 * parallel:
 *
 * 1. Seed the E2E database. The Python script owns this, since it is the
 *    side that has the migrations and the models; it also refuses to run
 *    against a database whose name does not mark it as disposable.
 * 2. Build the frontend once. Two `next start` processes then share that
 *    build read-only, which is what lets a second instance run against a
 *    deliberately unreachable backend without two dev servers fighting over
 *    the same `.next` directory.
 */

import { execFileSync } from "node:child_process";
import path from "node:path";

import { E2E_DATABASE_URL } from "./helpers/environment";

const BACKEND_DIR = path.resolve(__dirname, "..", "..", "backend");
const FRONTEND_DIR = path.resolve(__dirname, "..");

// Typed as a plain record rather than NodeJS.ProcessEnv: Next.js augments
// that interface to require NODE_ENV, which an override map should not have
// to restate.
function run(
  command: string,
  args: string[],
  cwd: string,
  env: Record<string, string>,
): void {
  execFileSync(command, args, {
    cwd,
    stdio: "inherit",
    env: { ...process.env, ...env },
  });
}

export default function globalSetup(): void {
  run("uv", ["run", "python", "scripts/seed_e2e.py"], BACKEND_DIR, {
    CREDIT_RADAR_DATABASE_URL: E2E_DATABASE_URL,
  });

  run("pnpm", ["exec", "next", "build"], FRONTEND_DIR, {
    NEXT_TELEMETRY_DISABLED: "1",
  });
}
