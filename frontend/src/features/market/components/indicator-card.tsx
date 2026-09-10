/**
 * One market indicator: its current value, how it moved, where it came
 * from and whether the collection behind it is healthy.
 *
 * The four facts are deliberately on the same card. A rate without its
 * reference date could be years old, and a rate whose last collection
 * failed is a rate that may already be wrong -- presenting either as
 * simply "the current rate" is the failure mode this dashboard exists to
 * avoid.
 */

import { AlertTriangle, ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";

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
import {
  describeMovement,
  favourabilityOf,
  type Favourability,
} from "@/features/market/favourability";
import { INDICATOR_LABELS } from "@/lib/labels";
import {
  deltaDirection,
  formatDate,
  formatDelta,
  formatRate,
  formatRelativeTime,
} from "@/lib/format";
import { cn } from "@/lib/utils";
import type { IndicatorSummary } from "@/lib/api/types";

/** How stale a source may be before the card says so. */
const STALE_AFTER_MS = 36 * 60 * 60 * 1000;

const DIRECTION_ICONS = {
  up: ArrowUpRight,
  down: ArrowDownRight,
  flat: Minus,
} as const;

/** Colour pairs from the token set, never raw palette values. */
const FAVOURABILITY_CLASSES: Record<Favourability, string> = {
  positive: "border-transparent bg-positive-subtle text-positive",
  negative: "border-transparent bg-negative-subtle text-negative",
  neutral: "border-transparent bg-neutral-subtle text-neutral",
};

export function IndicatorCard({
  summary,
  now,
}: {
  summary: IndicatorSummary;
  /** Reference time for staleness, captured once per request by the page.
   *
   * Passed in rather than read here so every card on a page judges
   * staleness against the same instant, and so rendering stays pure. */
  now: number;
}) {
  const { indicator, latest, previous, last_run: lastRun } = summary;
  // The pt-BR name, not the backend's en-US domain description. See lib/labels.
  const label = INDICATOR_LABELS[indicator.code];

  const collectionFailed = lastRun?.status === "failed";
  const isStale =
    lastRun !== null &&
    now - new Date(lastRun.finished_at).getTime() > STALE_AFTER_MS;

  const movement =
    latest && previous
      ? (() => {
          const direction = deltaDirection(latest.value, previous.value);
          const favourability = favourabilityOf(indicator.kind, direction);
          return {
            direction,
            favourability,
            delta: formatDelta(latest.value, previous.value, latest.unit),
            description: describeMovement(direction, favourability),
            since: formatDate(previous.reference_date),
            from: formatRate(previous.value, previous.unit),
          };
        })()
      : null;

  const DirectionIcon = movement ? DIRECTION_ICONS[movement.direction] : null;

  return (
    <Card className="gap-3">
      <CardHeader className="pb-0">
        <CardDescription className="flex items-center gap-1.5 text-xs">
          {label.name}
          {latest ? <ProvenancePopover observation={latest} /> : null}
        </CardDescription>
        <CardTitle className="numeric text-2xl font-semibold tracking-tight">
          {latest ? (
            formatRate(latest.value, latest.unit)
          ) : (
            <span className="text-base font-normal text-muted-foreground">
              Sem observações
            </span>
          )}
        </CardTitle>
        {movement && DirectionIcon ? (
          <CardAction>
            <Badge
              variant="outline"
              className={cn(
                "numeric gap-1",
                FAVOURABILITY_CLASSES[movement.favourability],
              )}
              // The colour is a shortcut, not the message: the direction is
              // in the arrow, the sign is in the number, and the reading is
              // spelled out for anyone who hears the page instead of seeing
              // it.
              title={`Antes ${movement.from}, em ${movement.since}`}
            >
              <DirectionIcon className="size-3.5 shrink-0" aria-hidden />
              {movement.delta}
              <span className="sr-only"> ({movement.description})</span>
            </Badge>
          </CardAction>
        ) : null}
      </CardHeader>
      <CardContent className="space-y-1.5">
        {latest ? (
          <p className="text-xs text-muted-foreground">
            Referência {formatDate(latest.reference_date)}
            {movement ? (
              <>
                {" · antes "}
                <span className="numeric">{movement.from}</span>
                {" em "}
                {movement.since}
              </>
            ) : null}
          </p>
        ) : (
          <p className="text-xs text-muted-foreground">
            Nada foi coletado para este indicador ainda. Rode uma coleta para
            preenchê-lo.
          </p>
        )}

        {collectionFailed ? (
          <p className="flex items-center gap-1.5 text-xs text-negative">
            <AlertTriangle className="size-3.5 shrink-0" aria-hidden />
            A última coleta falhou. Este valor pode estar desatualizado.
          </p>
        ) : isStale && lastRun ? (
          <p className="flex items-center gap-1.5 text-xs text-warning">
            <AlertTriangle className="size-3.5 shrink-0" aria-hidden />
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
