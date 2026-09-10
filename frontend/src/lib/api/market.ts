/** Market resource calls. */

import { apiFetch, type ApiResult } from "@/lib/api/client";
import type {
  Health,
  IndicatorCode,
  MarketSummary,
  ObservationSeries,
} from "@/lib/api/types";

const API_V1 = "/api/v1";

export function getMarketSummary(): Promise<ApiResult<MarketSummary>> {
  return apiFetch<MarketSummary>(`${API_V1}/market/summary`);
}

export function getIndicatorHistory(
  code: IndicatorCode,
  options: { from?: string; to?: string; limit?: number } = {},
): Promise<ApiResult<ObservationSeries>> {
  const params = new URLSearchParams();
  if (options.from) params.set("from", options.from);
  if (options.to) params.set("to", options.to);
  if (options.limit) params.set("limit", String(options.limit));

  const query = params.toString();
  return apiFetch<ObservationSeries>(
    `${API_V1}/market/indicators/${code}/observations${query ? `?${query}` : ""}`,
  );
}

export function getHealth(): Promise<ApiResult<Health>> {
  return apiFetch<Health>("/health");
}
