/**
 * Addresses and ports the end-to-end environment uses.
 *
 * Deliberately distinct from the development stack's 5434/8007/3007, so a
 * suite that truncates tables and restarts servers can never touch the
 * running personal instance.
 */

export const E2E_POSTGRES_PORT = 5434;

export const E2E_DATABASE_URL =
  process.env.CREDIT_RADAR_E2E_DATABASE_URL ??
  `postgresql+psycopg://credit_radar:credit_radar@localhost:${E2E_POSTGRES_PORT}/credit_radar_e2e`;

export const BACKEND_PORT = 8008;
export const FRONTEND_PORT = 3008;

/** A second frontend, pointed at a backend that is not there.
 *
 * The dashboard fetches server-side, so a request cannot be intercepted from
 * the browser to simulate an outage. Running one instance against an
 * unreachable address is the only way to exercise the real failure path. */
export const OFFLINE_FRONTEND_PORT = 3009;

/** Discard port: nothing listens, so a connection is refused immediately
 * rather than hanging until a timeout. That keeps the error-state tests fast
 * and deterministic. */
export const UNREACHABLE_BACKEND_URL = "http://127.0.0.1:9";

export const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;
export const FRONTEND_URL = `http://127.0.0.1:${FRONTEND_PORT}`;
export const OFFLINE_FRONTEND_URL = `http://127.0.0.1:${OFFLINE_FRONTEND_PORT}`;
