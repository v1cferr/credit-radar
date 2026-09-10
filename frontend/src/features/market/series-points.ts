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

import type {
  IndicatorCode,
  IndicatorKind,
  ObservationSeries,
} from "@/lib/api/types";

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


/** One series ready to plot, with what is needed to draw and label it. */
export interface PlottedSeries {
  code: IndicatorCode;
  kind: IndicatorKind;
  points: SeriesPoint[];
}

/**
 * A row of the merged dataset: one reference date across every series.
 *
 * Each series contributes two entries: its code holding the plotted number,
 * and an entry in `published` holding the string the source published. The
 * chart plots the number -- Recharts compares and scales what it is given,
 * and handed a string it computes a domain from text -- while the tooltip
 * reads the published string, so the figure on screen is never a float
 * re-rendered as decimal.
 */
export type MergedRow = Record<string, unknown> & {
  d: string;
  published: Record<string, string>;
};

/**
 * Merge several series into rows keyed by reference date.
 *
 * A date where one series has no observation is left absent rather than
 * carried over from the previous date or interpolated. The chart then draws
 * a gap, which is what a gap is: the source published nothing. Filling it
 * would invent a rate.
 */
export function mergeSeries(series: PlottedSeries[]): MergedRow[] {
  const rows = new Map<string, MergedRow>();

  for (const entry of series) {
    for (const point of entry.points) {
      const row = rows.get(point.d) ?? { d: point.d, published: {} };
      row[entry.code] = Number(point.v);
      row.published[entry.code] = point.v;
      rows.set(point.d, row);
    }
  }

  return [...rows.values()].sort((a, b) => a.d.localeCompare(b.d));
}
