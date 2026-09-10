/**
 * The shape a chart needs, which is much smaller than an observation.
 *
 * An `Observation` carries a provenance block -- source, upstream
 * reference, collector version, collection time -- and that is deliberate:
 * every collected value must be traceable. But a chart plots a date and a
 * value, and passing whole observations into a client component serializes
 * the provenance of every point into the page. On the market page that is
 * 1025 provenance blocks and 397 KB, roughly ten times what the plotted
 * data weighs.
 *
 * Provenance is not lost, it is shown where it belongs: once per indicator,
 * on the card, from the latest observation. Repeating it 990 times made the
 * page slower without telling the reader anything new.
 */

import type { IndicatorKind, ObservationSeries } from "@/lib/api/types";

/** One plotted point. Short keys because there are hundreds of these. */
export interface SeriesPoint {
  /** Reference date, ISO. */
  d: string;
  /** The value exactly as the source published it, still a string. */
  v: string;
}

export function toSeriesPoints(series: ObservationSeries): SeriesPoint[] {
  return series.observations.map((observation) => ({
    d: observation.reference_date,
    v: observation.value,
  }));
}

/**
 * How to join two consecutive points, which depends on what the series is.
 *
 * A policy rate is a step function. The Selic target set by the Copom holds
 * at exactly one value until the next decision changes it, so the honest
 * line between two decisions is flat and then vertical. Sloping between
 * them would draw the rate passing through values it never had.
 *
 * Everything else here is measured over a period rather than decided, and
 * is drawn straight between measurements. Not as a spline: a monotone curve
 * through monthly averages bulges past the points it connects, which puts a
 * rate on the screen that was never published -- the one thing this
 * interface must never do.
 */
export function lineTypeFor(kind: IndicatorKind): "stepAfter" | "linear" {
  return kind === "policy_rate" ? "stepAfter" : "linear";
}
