/**
 * How the collection behind this dashboard is doing, in one line.
 *
 * The overview's most important fact is not a rate: it is whether the rates
 * on it can be trusted right now. A source that failed this morning or has
 * not been read in a week changes how every figure below should be read, so
 * it is stated before them rather than discovered by opening each card.
 *
 * Counts only the states that occur. "0 falharam" is noise; one failure is
 * the whole message.
 */

import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  FRESHNESS_LABELS,
  FRESHNESS_TONE,
  freshnessOf,
  type Freshness,
  type Tone,
} from "@/features/data-sources/freshness";
import { formatRelativeTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { IndicatorSummary } from "@/lib/api/types";

/** Worst first: a failure has to be seen before a success is reassuring. */
const ORDER: Freshness[] = ["failed", "stale", "no_data", "never", "fresh"];

const DOT_CLASSES: Record<Tone, string> = {
  positive: "bg-positive",
  warning: "bg-warning",
  negative: "bg-negative",
  neutral: "bg-neutral",
};

export function CollectionHealth({
  indicators,
  now,
}: {
  indicators: IndicatorSummary[];
  now: number;
}) {
  const counts = new Map<Freshness, number>();
  let mostRecent: string | null = null;

  for (const entry of indicators) {
    const freshness = freshnessOf(entry.last_run, now);
    counts.set(freshness, (counts.get(freshness) ?? 0) + 1);

    // The last time anything was successfully read, which is what "up to
    // date" means for the dashboard as a whole.
    const run = entry.last_run;
    if (run && run.status === "success") {
      if (mostRecent === null || run.finished_at > mostRecent) {
        mostRecent = run.finished_at;
      }
    }
  }

  const present = ORDER.filter((freshness) => counts.has(freshness));

  return (
    <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3 rounded-lg border bg-card px-4 py-3">
      <div className="min-w-0 space-y-1.5">
        <p className="text-xs font-medium text-muted-foreground">
          Coleta das fontes
        </p>
        <ul className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
          {present.map((freshness) => (
            <li
              key={freshness}
              className="flex items-center gap-1.5 text-sm whitespace-nowrap"
            >
              {/* Paired with the word, never standing in for it. */}
              <span
                aria-hidden
                className={cn(
                  "size-1.5 shrink-0 rounded-full",
                  DOT_CLASSES[FRESHNESS_TONE[freshness]],
                )}
              />
              <span className="numeric font-semibold">
                {counts.get(freshness)}
              </span>
              <span className="text-muted-foreground">
                {FRESHNESS_LABELS[freshness].toLocaleLowerCase("pt-BR")}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <div className="flex items-center gap-3">
        {mostRecent ? (
          <p className="text-xs text-muted-foreground">
            Última coleta {formatRelativeTime(mostRecent, now)}
          </p>
        ) : null}
        <Button
          variant="outline"
          size="sm"
          render={<Link href="/data-sources" prefetch={false} />}
        >
          Fontes
          <ArrowRight className="size-3.5" aria-hidden />
        </Button>
      </div>
    </div>
  );
}
