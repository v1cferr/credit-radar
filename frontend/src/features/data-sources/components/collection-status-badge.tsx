/**
 * The outcome of a source's last collection attempt.
 *
 * A component rather than inline markup because the mapping from status to
 * how it looks is a decision, and the route file should not be where it
 * lives.
 */

import { CheckCircle2, CircleSlash, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { COLLECTION_STATUS_LABELS } from "@/lib/labels";
import type { CollectionStatus } from "@/lib/api/types";

export function CollectionStatusBadge({ status }: { status: CollectionStatus }) {
  const label = COLLECTION_STATUS_LABELS[status];

  if (status === "success") {
    return (
      <Badge variant="secondary" className="gap-1">
        <CheckCircle2 className="size-3" />
        {label}
      </Badge>
    );
  }

  if (status === "no_data") {
    return (
      <Badge variant="outline" className="gap-1">
        <CircleSlash className="size-3" />
        {label}
      </Badge>
    );
  }

  return (
    <Badge variant="destructive" className="gap-1">
      <XCircle className="size-3" />
      {label}
    </Badge>
  );
}
