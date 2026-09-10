/**
 * What a movement means for someone who wants to borrow.
 *
 * Direction is arithmetic; whether it is good news is not. Every indicator
 * tracked today is a cost to a borrower -- the policy rate, the financing
 * rates derived from it, the inflation indices that contracts are corrected
 * by -- so for all of them a rise is unfavourable. That is a fact about
 * these indicators and this reader, not a rule about numbers: the same rise
 * is good news for a saver, and a bureau score, when one is collected, will
 * be favourable rising.
 *
 * It is a function of `IndicatorKind` for that reason. When the first
 * indicator arrives whose rise is welcome, this is the one place that has
 * to learn about it, and TypeScript will require it to.
 */

import type { IndicatorKind } from "@/lib/api/types";

export type Favourability = "positive" | "negative" | "neutral";

const HIGHER_IS_WORSE: Record<IndicatorKind, boolean> = {
  policy_rate: true,
  market_interest_rate: true,
  inflation_index: true,
};

export function favourabilityOf(
  kind: IndicatorKind,
  direction: "up" | "down" | "flat",
): Favourability {
  if (direction === "flat") return "neutral";
  const worse = HIGHER_IS_WORSE[kind] ? direction === "up" : direction === "down";
  return worse ? "negative" : "positive";
}

/** How a movement reads in words, for a reader who cannot see the colour. */
export function describeMovement(
  direction: "up" | "down" | "flat",
  favourability: Favourability,
): string {
  if (direction === "flat") return "sem variação";
  const movement = direction === "up" ? "alta" : "queda";
  if (favourability === "neutral") return movement;
  return favourability === "negative"
    ? `${movement}, desfavorável para quem toma crédito`
    : `${movement}, favorável para quem toma crédito`;
}
