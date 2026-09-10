/**
 * Honest states for data that is missing, failed or not yet built.
 *
 * These exist so the dashboard never has to invent a value. A card with no
 * data says it has no data; a card whose provider does not exist yet says
 * so. Rendering a zero or a placeholder number in either case would make the
 * UI look authoritative about something it does not know.
 *
 * Copy is pt-BR; identifiers and comments are en-US.
 */

import { AlertCircle, Database, PlugZap, Inbox } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

export function ErrorState({
  title = "Não foi possível carregar os dados",
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
        <p className="text-sm font-medium">
          {feature} ainda não foi implementado
        </p>
        <p className="max-w-lg text-xs text-muted-foreground">
          Esta seção faz parte da arquitetura planejada, mas ainda não tem
          módulo no backend. Ela depende de {requires}. Nada é exibido aqui em
          vez de números de exemplo, porque dado financeiro inventado é pior
          do que dado nenhum.
        </p>
      </div>
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
