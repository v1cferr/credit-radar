/**
 * Where a value came from.
 *
 * CreditRadar combines independent systems whose numbers can legitimately
 * disagree, so any displayed value must be traceable to a source, a series
 * and an observation time. This is the UI half of the provenance the backend
 * records with every observation.
 */

import { Info } from "lucide-react";

import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Separator } from "@/components/ui/separator";
import { formatDate, formatDateTime, formatRelativeTime } from "@/lib/format";
import type { Observation } from "@/lib/api/types";

const SOURCE_NAMES: Record<string, string> = {
  "bcb.sgs": "Banco Central do Brasil — SGS",
};

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[6.5rem_1fr] gap-2 text-xs">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono break-all">{value}</span>
    </div>
  );
}

export function ProvenancePopover({ observation }: { observation: Observation }) {
  const { provenance } = observation;
  const sourceName = SOURCE_NAMES[provenance.source_id] ?? provenance.source_id;

  return (
    <Popover>
      <PopoverTrigger
        className="text-muted-foreground transition-colors hover:text-foreground"
        aria-label="Show where this value came from"
      >
        <Info className="size-3.5" />
      </PopoverTrigger>
      <PopoverContent className="w-80 space-y-2">
        <p className="text-sm font-medium">Data provenance</p>
        <Separator />
        <div className="space-y-1.5">
          <Row label="Source" value={sourceName} />
          <Row label="Series" value={provenance.source_reference} />
          <Row label="Reference" value={formatDate(observation.reference_date)} />
          <Row
            label="Collected"
            value={`${formatDateTime(provenance.collected_at)} (${formatRelativeTime(
              provenance.collected_at,
            )})`}
          />
          <Row label="Parser" value={`v${provenance.collector_version}`} />
        </div>
      </PopoverContent>
    </Popover>
  );
}
