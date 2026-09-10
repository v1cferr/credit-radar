/**
 * One market indicator: its current value, provenance and collection health.
 */

import { AlertTriangle, TrendingDown, TrendingUp, Minus } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ProvenancePopover } from "@/components/common/provenance-popover";
import { INDICATOR_LABELS } from "@/lib/labels";
import {
  formatDate,
  formatDelta,
  formatRate,
  formatRelativeTime,
} from "@/lib/format";
import type { IndicatorSummary, Observation } from "@/lib/api/types";

/** How stale a source may be before the card says so. */
const STALE_AFTER_MS = 36 * 60 * 60 * 1000;

function TrendIcon({ delta }: { delta: number }) {
  if (delta > 0) return <TrendingUp className="size-3.5" />;
  if (delta < 0) return <TrendingDown className="size-3.5" />;
  return <Minus className="size-3.5" />;
}

export function IndicatorCard({
  summary,
  previous,
  now,
}: {
  summary: IndicatorSummary;
  /** The prior observation, used only to show a direction of travel. */
  previous?: Observation | null;
  /** Reference time for staleness, captured once per request by the page.
   *
   * Passed in rather than read here so every card on a page judges
   * staleness against the same instant, and so rendering stays pure. */
  now: number;
}) {
  const { indicator, latest, last_run: lastRun } = summary;
  // The pt-BR name, not the backend's en-US domain description. See lib/labels.
  const label = INDICATOR_LABELS[indicator.code];

  const collectionFailed = lastRun?.status === "failed";
  const isStale =
    lastRun !== null &&
    now - new Date(lastRun.finished_at).getTime() > STALE_AFTER_MS;

  const delta =
    latest && previous ? Number(latest.value) - Number(previous.value) : null;

  return (
    <Card className="gap-3">
      <CardHeader className="pb-0">
        <CardDescription className="flex items-center gap-1.5 text-xs">
          {label.name}
          {latest ? <ProvenancePopover observation={latest} /> : null}
        </CardDescription>
        <CardTitle className="text-2xl tabular-nums">
          {latest ? (
            formatRate(latest.value, latest.unit)
          ) : (
            <span className="text-base font-normal text-muted-foreground">
              Sem observações
            </span>
          )}
        </CardTitle>
        {delta !== null && latest && previous ? (
          <CardAction>
            <Badge variant="outline" className="gap-1 tabular-nums">
              <TrendIcon delta={delta} />
              {formatDelta(latest.value, previous.value, latest.unit)}
            </Badge>
          </CardAction>
        ) : null}
      </CardHeader>
      <CardContent className="space-y-1.5">
        {latest ? (
          <p className="text-xs text-muted-foreground">
            Data de referência {formatDate(latest.reference_date)}
          </p>
        ) : (
          <p className="text-xs text-muted-foreground">
            Nada foi coletado para este indicador ainda. Rode uma coleta para
            preenchê-lo.
          </p>
        )}

        {collectionFailed ? (
          <p className="flex items-center gap-1.5 text-xs text-destructive">
            <AlertTriangle className="size-3.5 shrink-0" />
            A última coleta falhou. Este valor pode estar desatualizado.
          </p>
        ) : isStale && lastRun ? (
          <p className="flex items-center gap-1.5 text-xs text-amber-600 dark:text-amber-500">
            <AlertTriangle className="size-3.5 shrink-0" />
            Sincronizado {formatRelativeTime(lastRun.finished_at, now)}
          </p>
        ) : lastRun ? (
          <p className="text-xs text-muted-foreground">
            Sincronizado {formatRelativeTime(lastRun.finished_at, now)}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
