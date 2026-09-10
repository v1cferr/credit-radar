/**
 * How current a source's data is, as one vocabulary.
 *
 * The dashboard had three ways of saying this: the indicator card compared
 * a timestamp against a threshold of its own, the data-sources table showed
 * the raw outcome of the last attempt, and the overview said nothing. So a
 * source last collected nine days ago appeared as "Sincronizado há 9 dias"
 * with a warning on its card and as "Saudável" in the table, which is two
 * answers to one question.
 *
 * Freshness combines both facts, because either alone misleads. A
 * successful collection from last week is not current data, and a failed
 * attempt this morning does not mean the value on screen is wrong -- only
 * that nobody has been able to confirm it.
 */

import type { CollectionRun } from "@/lib/api/types";

export type Freshness = "fresh" | "stale" | "failed" | "no_data" | "never";

/**
 * How old a successful collection may be before it is called stale.
 *
 * Thirty-six hours. The most frequent series here is published on business
 * days, so a daily collection that has run once since yesterday is current;
 * missing two runs in a row is not a weekend, it is a problem.
 */
export const STALE_AFTER_MS = 36 * 60 * 60 * 1000;

export function freshnessOf(
  lastRun: CollectionRun | null,
  now: number,
): Freshness {
  if (lastRun === null) return "never";
  if (lastRun.status === "failed") return "failed";
  if (lastRun.status === "no_data") return "no_data";
  return now - new Date(lastRun.finished_at).getTime() > STALE_AFTER_MS
    ? "stale"
    : "fresh";
}

/**
 * The label as it reads after a count, in both numbers.
 *
 * Portuguese agrees in number, so "7 atualizada" is wrong where English
 * would get away with one form. Kept beside the badge labels rather than
 * derived by appending an "s", which would produce "7 falhous".
 */
export const FRESHNESS_COUNT_LABELS: Record<
  Freshness,
  { one: string; many: string }
> = {
  fresh: { one: "atualizada", many: "atualizadas" },
  stale: { one: "desatualizada", many: "desatualizadas" },
  failed: { one: "falhou", many: "falharam" },
  no_data: { one: "sem dados", many: "sem dados" },
  never: { one: "nunca coletada", many: "nunca coletadas" },
};

export const FRESHNESS_LABELS: Record<Freshness, string> = {
  fresh: "Atualizada",
  stale: "Desatualizada",
  failed: "Falhou",
  no_data: "Sem dados",
  never: "Nunca coletada",
};

/**
 * What each state means, in the words a reader needs to decide whether to
 * trust the number next to it.
 */
export const FRESHNESS_DESCRIPTIONS: Record<Freshness, string> = {
  fresh: "A última coleta funcionou e é recente.",
  stale:
    "A última coleta funcionou, mas há tempo suficiente para o valor já ter mudado na fonte.",
  failed:
    "A última tentativa falhou. O valor exibido pode não ser mais o atual.",
  no_data: "A fonte respondeu sem nenhuma observação para o período.",
  never: "Nenhuma coleta foi tentada para esta fonte ainda.",
};

/** Which semantic token a state reads in. Never a colour name. */
export type Tone = "positive" | "warning" | "negative" | "neutral";

export const FRESHNESS_TONE: Record<Freshness, Tone> = {
  fresh: "positive",
  stale: "warning",
  failed: "negative",
  no_data: "neutral",
  never: "neutral",
};
