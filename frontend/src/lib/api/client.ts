/**
 * The single place this application talks to the backend.
 *
 * Every piece of financial data reaches the UI through here. The frontend
 * never contacts Banco Central, a credit bureau, a Playwright worker or the
 * database directly, so all data has passed through the backend's domain
 * layer and carries its provenance.
 *
 * Requests are made server-side by default, which keeps the API address off
 * the client. Anything that does run in the browser goes to the same origin
 * and is routed to the backend by the proxy in front, so the deployment never
 * depends on a client knowing where the API lives.
 */

const SERVER_BASE_URL =
  process.env.CREDIT_RADAR_API_INTERNAL_URL ?? "http://127.0.0.1:8007";

/** Browser-side base URL: empty, meaning same-origin.
 *
 * Behind the reverse proxy, `/api/*` is routed to the backend before Next.js
 * sees it; in development, the rewrite in next.config.ts does the same. Either
 * way the backend's address never reaches the client and there is no
 * cross-origin request to authorize. */
const BROWSER_BASE_URL = "";

/** Milliseconds before a backend call is abandoned.
 *
 * Present for the same reason the backend sets one on outbound calls: a
 * provider that hangs must not hang the page. */
const REQUEST_TIMEOUT_MS = 15_000;

/**
 * Outcome of a backend call, carrying when the call happened.
 *
 * `fetchedAt` exists because staleness is a first-class concern here: the UI
 * has to say how old a value is. Reading the clock at fetch time rather than
 * during render keeps components pure and, more usefully, ties the timestamp
 * to the moment the data was actually observed.
 */
export type ApiResult<T> =
  | { ok: true; data: T; fetchedAt: number }
  | { ok: false; error: string; fetchedAt: number };

function baseUrl(): string {
  return typeof window === "undefined" ? SERVER_BASE_URL : BROWSER_BASE_URL;
}

/**
 * Fetch JSON from the backend, returning a result rather than throwing.
 *
 * Failures are values, not exceptions, because a provider being unreachable
 * is an expected state this application has to render honestly -- as a stale
 * or unavailable source -- rather than as a crashed page.
 */
export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<ApiResult<T>> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const fetchedAt = Date.now();

  try {
    const response = await fetch(`${baseUrl()}${path}`, {
      ...init,
      signal: controller.signal,
      headers: { Accept: "application/json", ...init?.headers },
      // Observations change only when a collection runs, but showing a
      // stale value as current is exactly what this project must not do.
      cache: "no-store",
    });

    if (!response.ok) {
      return {
        ok: false,
        error: `The backend returned ${response.status} for ${path}.`,
        fetchedAt,
      };
    }

    return { ok: true, data: (await response.json()) as T, fetchedAt };
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      return {
        ok: false,
        error: "The backend did not respond in time.",
        fetchedAt,
      };
    }
    return {
      ok: false,
      error:
        "The backend could not be reached. Is it running? " +
        "Start it with: cd backend && uv run uvicorn credit_radar.api.app:app --port 8007",
      fetchedAt,
    };
  } finally {
    clearTimeout(timeout);
  }
}
