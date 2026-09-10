/**
 * Which series the market page charts, and how far back each one goes.
 *
 * Feature configuration rather than routing, so it lives with the feature.
 * The window differs by publication frequency: the Selic target is daily and
 * a shorter window keeps the chart readable, while the credit rates are
 * monthly and need years before a trend is visible at all.
 */

import type { IndicatorCode } from "@/lib/api/types";

export interface ChartedSeries {
  code: IndicatorCode;
  /** Inclusive start of the charted window, as an ISO date. */
  from: string;
}

export const CHARTED_SERIES: ChartedSeries[] = [
  { code: "SELIC_TARGET", from: "2024-01-01" },
  { code: "VEHICLE_FINANCING_RATE_PF", from: "2023-09-01" },
];
