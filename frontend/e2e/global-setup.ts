/**
 * Prepares the end-to-end environment before any browser starts.
 *
 * Seeds the E2E database. The Python script owns this, since it is the side
 * that has the migrations and the models; it also refuses to run against a
 * database whose name does not mark it as disposable.
 *
 * The frontend build deliberately does NOT happen here. Playwright starts
 * `webServer` entries *before* global setup, so a build in this file
 * replaces `.next` underneath three already-running `next start`
 * processes. Each of them read their manifests at boot, so they go on
 * serving the previous build's chunk names -- which no longer exist. The
 * browser then gets a page whose stylesheet and scripts 404, and the
 * failures read as product bugs: a phone tab bar on a desktop screen, a
 * chart with no line, a drawer that will not open, a table overflowing its
 * card. Nothing reproduces alone, because running one spec rebuilds
 * nothing and the servers and the build agree again.
 *
 * The build is in the `test:e2e` script instead, where it finishes before
 * Playwright launches anything. It discards `.next` first, so a stale
 * Tailwind content scan cannot omit the utilities a new file is the first
 * to use.
 */

import { execFileSync } from "node:child_process";
import path from "node:path";

import { E2E_DATABASE_URL } from "./helpers/environment";

const BACKEND_DIR = path.resolve(__dirname, "..", "..", "backend");

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
}
