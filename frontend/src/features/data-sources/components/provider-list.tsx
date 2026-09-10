/**
 * Every source this system reads or intends to read.
 *
 * A list rather than a table: the rows share no comparable quantity, and
 * the useful part of each is a sentence, which a narrow table column turns
 * into a column of two-word lines.
 */

import { Badge } from "@/components/ui/badge";
import {
  PLANNED_PROVIDERS,
  PROVIDER_STATUS_LABELS,
  type ProviderStatus,
} from "@/features/data-sources/planned-providers";
import { cn } from "@/lib/utils";

const STATUS_CLASSES: Record<ProviderStatus, string> = {
  implemented: "border-transparent bg-positive-subtle text-positive",
  partial: "border-transparent bg-warning-subtle text-warning",
  planned: "border-transparent bg-neutral-subtle text-neutral",
};

export function ProviderList() {
  return (
    <ul className="divide-y">
      {PLANNED_PROVIDERS.map((provider) => (
        <li
          key={provider.name}
          className="flex flex-col gap-1.5 py-3 first:pt-0 last:pb-0"
        >
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium">{provider.name}</span>
            <Badge
              variant="outline"
              className={cn("text-[0.65rem]", STATUS_CLASSES[provider.status])}
            >
              {PROVIDER_STATUS_LABELS[provider.status]}
            </Badge>
            <Badge variant="secondary" className="text-[0.65rem]">
              {provider.kind}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">{provider.note}</p>
        </li>
      ))}
    </ul>
  );
}
