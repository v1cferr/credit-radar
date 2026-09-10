/**
 * Honest states for data that is missing, failed or not yet built.
 *
 * These exist so the dashboard never has to invent a value. A card with no
 * data says it has no data, rather than rendering a zero that would make
 * the interface look authoritative about something it does not know.
 *
 * "This section does not exist yet" is a different claim and lives in
 * `PlannedPage`, which has room to say what the section will be and which
 * rule it will have to keep.
 *
 * Copy is pt-BR; identifiers and comments are en-US.
 */

import { Database, Inbox } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

export function EmptyState({
  title = "Nenhuma observação ainda",
  message,
}: {
  title?: string;
  message: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed p-8 text-center">
      <Inbox className="size-5 text-muted-foreground" />
      <p className="text-sm font-medium">{title}</p>
      <p className="max-w-md text-xs text-muted-foreground">{message}</p>
    </div>
  );
}

export function BackendOfflineState({ message }: { message: string }) {
  return (
    <Alert variant="destructive">
      <Database />
      <AlertTitle>Backend indisponível</AlertTitle>
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  );
}
