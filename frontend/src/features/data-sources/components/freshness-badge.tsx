/**
 * How current one source is.
 *
 * A component rather than inline markup because the mapping from state to
 * how it looks is a decision, and a route file is not where it belongs.
 * Every state carries an icon and a word as well as a colour, so the
 * reading survives a greyscale screen or colour blindness.
 */

import {
  AlertTriangle,
  CheckCircle2,
  CircleSlash,
  Clock,
  XCircle,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  FRESHNESS_LABELS,
  FRESHNESS_TONE,
  type Freshness,
  type Tone,
} from "@/features/data-sources/freshness";
import { cn } from "@/lib/utils";

const ICONS: Record<Freshness, typeof CheckCircle2> = {
  fresh: CheckCircle2,
  stale: AlertTriangle,
  failed: XCircle,
  no_data: CircleSlash,
  never: Clock,
};

const TONE_CLASSES: Record<Tone, string> = {
  positive: "border-transparent bg-positive-subtle text-positive",
  warning: "border-transparent bg-warning-subtle text-warning",
  negative: "border-transparent bg-negative-subtle text-negative",
  neutral: "border-transparent bg-neutral-subtle text-neutral",
};

export function FreshnessBadge({ freshness }: { freshness: Freshness }) {
  const Icon = ICONS[freshness];

  return (
    <Badge
      variant="outline"
      className={cn("gap-1", TONE_CLASSES[FRESHNESS_TONE[freshness]])}
    >
      <Icon className="size-3 shrink-0" aria-hidden />
      {FRESHNESS_LABELS[freshness]}
    </Badge>
  );
}
