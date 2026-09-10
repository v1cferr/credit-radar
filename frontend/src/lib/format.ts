/**
 * Display formatting.
 *
 * The interface is pt-BR, so numbers, dates and rate notation all follow
 * Brazilian convention: "14,00% a.a." and "16/09/2026". Keeping the figures
 * in the notation their source publishes also makes them checkable against
 * that source without mental re-punctuation.
 *
 * The repository's code, comments and documentation stay en-US. Only what
 * reaches the screen is translated.
 */

import type { Unit } from "@/lib/api/types";

const LOCALE = "pt-BR";

/** Suffix for each unit, in the notation used by the Brazilian market. */
const UNIT_SUFFIX: Record<Unit, string> = {
  percent_per_year: "% a.a.",
  percent_per_month: "% a.m.",
  percent_per_day: "% a.d.",
  index_points: " pts",
};

/**
 * Format a decimal string for display, preserving the published scale.
 *
 * Formatting is driven by the number of decimals present in the source
 * string, so a rate published as "14.00" renders as "14,00" and not "14".
 * The trailing zero is information: it says the source published two
 * decimals of precision.
 */
export function formatDecimal(value: string): string {
  const decimals = value.includes(".") ? value.split(".")[1].length : 0;
  const parsed = Number(value);

  if (!Number.isFinite(parsed)) return value;

  return new Intl.NumberFormat(LOCALE, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(parsed);
}

/** Format a rate with its unit, e.g. "14,00% a.a.". */
export function formatRate(value: string, unit: Unit): string {
  return `${formatDecimal(value)}${UNIT_SUFFIX[unit]}`;
}

/** Format an ISO date (YYYY-MM-DD) as dd/MM/yyyy. */
export function formatDate(isoDate: string): string {
  const [year, month, day] = isoDate.split("-");
  if (!year || !month || !day) return isoDate;
  return `${day}/${month}/${year}`;
}

/** Format an ISO timestamp as a date and time in the user's timezone. */
export function formatDateTime(isoTimestamp: string): string {
  const date = new Date(isoTimestamp);
  if (Number.isNaN(date.getTime())) return isoTimestamp;

  return new Intl.DateTimeFormat(LOCALE, {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

/**
 * Describe how long ago a timestamp was, e.g. "há 2 horas".
 *
 * Used to make staleness visible: a source last synchronized nine days ago
 * must not look as current as one synchronized this morning.
 *
 * `now` is a parameter so callers rendering several timestamps can pass one
 * consistent reference instant instead of each call reading the clock.
 */
export function formatRelativeTime(
  isoTimestamp: string,
  now: number = Date.now(),
): string {
  const then = new Date(isoTimestamp).getTime();
  if (Number.isNaN(then)) return isoTimestamp;

  const seconds = Math.round((now - then) / 1000);

  if (seconds < 0) return "no futuro";
  if (seconds < 60) return "agora mesmo";

  const units: Array<[Intl.RelativeTimeFormatUnit, number]> = [
    ["minute", 60],
    ["hour", 3600],
    ["day", 86400],
    ["month", 2_592_000],
    ["year", 31_536_000],
  ];

  let chosen: [Intl.RelativeTimeFormatUnit, number] = units[0];
  for (const unit of units) {
    if (seconds >= unit[1]) chosen = unit;
  }

  const formatter = new Intl.RelativeTimeFormat(LOCALE, { numeric: "auto" });
  return formatter.format(-Math.floor(seconds / chosen[1]), chosen[0]);
}

/**
 * Difference between two decimal strings, formatted with a sign.
 *
 * Parsed to Number only because the result is a display delta, not a stored
 * value. Anything persisted or compared for money stays a string end to end.
 */
export function formatDelta(current: string, previous: string, unit: Unit): string {
  const difference = Number(current) - Number(previous);
  if (!Number.isFinite(difference)) return "";

  const decimals = current.includes(".") ? current.split(".")[1].length : 2;
  const formatted = new Intl.NumberFormat(LOCALE, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
    signDisplay: "exceptZero",
  }).format(difference);

  return `${formatted}${UNIT_SUFFIX[unit].replace("% ", " ")}`;
}
