/**
 * Honest states for data that is missing, failed or not yet built.
 *
 * These exist so the dashboard never has to invent a value. A card with no
 * data says it has no data; a card whose provider does not exist yet says
 * so. Rendering a zero or a placeholder number in either case would make the
 * UI look authoritative about something it does not know.
 */

import { AlertCircle, Database, PlugZap, Inbox } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

export function ErrorState({
  title = "Could not load data",
  message,
}: {
  title?: string;
  message: string;
}) {
  return (
    <Alert variant="destructive">
      <AlertCircle />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  );
}

export function EmptyState({
  title = "No observations yet",
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

/**
 * A section whose backend module does not exist yet.
 *
 * Named for what it is rather than dressed up as a loading state, so the
 * distinction between "still fetching" and "not built" stays visible.
 */
export function NotImplementedState({
  feature,
  requires,
}: {
  feature: string;
  requires: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed p-10 text-center">
      <PlugZap className="size-6 text-muted-foreground" />
      <div className="space-y-1">
        <p className="text-sm font-medium">{feature} is not implemented yet</p>
        <p className="max-w-lg text-xs text-muted-foreground">
          This section is part of the planned architecture but has no backend
          module yet. It needs {requires}. Nothing is shown here rather than
          placeholder figures, because invented financial data is worse than
          none.
        </p>
      </div>
    </div>
  );
}

export function BackendOfflineState({ message }: { message: string }) {
  return (
    <Alert variant="destructive">
      <Database />
      <AlertTitle>Backend unavailable</AlertTitle>
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  );
}
