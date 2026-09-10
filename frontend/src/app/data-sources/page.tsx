/**
 * Provider health.
 *
 * Answers "can I trust what the rest of the dashboard is showing me?" by
 * reporting, per source, when it was last collected and whether that attempt
 * succeeded.
 */

import { CheckCircle2, CircleSlash, XCircle } from "lucide-react";

import { PageHeader } from "@/components/app-shell/page-header";
import { BackendOfflineState } from "@/components/common/state-messages";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getMarketSummary } from "@/lib/api/market";
import { formatDateTime, formatRelativeTime } from "@/lib/format";
import { COLLECTION_STATUS_LABELS, INDICATOR_LABELS } from "@/lib/labels";
import type { CollectionStatus } from "@/lib/api/types";

/** Providers in the planned architecture, including the unbuilt ones.
 *
 * Listed so the page reflects the real integration surface rather than only
 * the part that happens to work. */
const PLANNED_PROVIDERS = [
  {
    name: "Banco Central — SGS",
    kind: "API pública oficial",
    implemented: true,
    note: "Séries de mercado e macroeconômicas. Sem autenticação e sem dado pessoal.",
  },
  {
    name: "Banco Central — SCR / Registrato",
    kind: "Relatório autenticado",
    implemented: false,
    note: "Exige login gov.br, então vai precisar de autenticação assistida por uma pessoa.",
  },
  {
    name: "Serasa",
    kind: "Conta autenticada",
    implemented: false,
    note: "Score, negativações e propostas. Escala própria, mantida separada dos outros bureaus.",
  },
  {
    name: "Quod / SPC / Equifax",
    kind: "Conta autenticada",
    implemented: false,
    note: "Metodologias independentes. Nunca combinadas em um score único inventado.",
  },
];

function StatusBadge({ status }: { status: CollectionStatus }) {
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

export default async function DataSourcesPage() {
  const summary = await getMarketSummary();
  // Tied to when the data was fetched, so every staleness indicator on
  // the page is judged against the same instant.
  const now = summary.fetchedAt;

  return (
    <>
      <PageHeader
        title="Fontes de dados"
        description="De onde vem cada informação, e se ela está atual"
      />

      <div className="flex flex-col gap-6 p-4 md:p-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Situação da coleta</CardTitle>
            <CardDescription>
              Resultado da última tentativa de coleta de cada série. Uma fonte
              cuja última tentativa falhou aparece como falha mesmo que ainda
              guarde valores antigos.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!summary.ok ? (
              <BackendOfflineState message={summary.error} />
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Indicador</TableHead>
                      <TableHead>Série</TableHead>
                      <TableHead>Situação</TableHead>
                      <TableHead>Última sincronização</TableHead>
                      <TableHead className="text-right">Observações</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {summary.data.indicators.map((entry) => (
                      <TableRow key={entry.indicator.code}>
                        <TableCell className="font-medium">
                          {INDICATOR_LABELS[entry.indicator.code].name}
                        </TableCell>
                        <TableCell className="font-mono text-xs">
                          {entry.latest?.provenance.source_reference ?? "—"}
                        </TableCell>
                        <TableCell>
                          {entry.last_run ? (
                            <StatusBadge status={entry.last_run.status} />
                          ) : (
                            <Badge variant="outline">Nunca coletada</Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-xs">
                          {entry.last_run ? (
                            <span title={formatDateTime(entry.last_run.finished_at)}>
                              {formatRelativeTime(entry.last_run.finished_at, now)}
                            </span>
                          ) : (
                            "—"
                          )}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {entry.last_run?.observation_count ?? 0}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Superfície de integração</CardTitle>
            <CardDescription>
              As fontes são integradas por ordem de estabilidade: API oficial,
              exportação estruturada, relatório para download e, só onde não
              existe nada melhor, automação de navegador autenticada.
              Mecanismos de segurança como CAPTCHA, MFA e login gov.br nunca
              são burlados.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Fonte</TableHead>
                    <TableHead>Integração</TableHead>
                    <TableHead>Situação</TableHead>
                    <TableHead>Observações</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {PLANNED_PROVIDERS.map((provider) => (
                    <TableRow key={provider.name}>
                      <TableCell className="font-medium">{provider.name}</TableCell>
                      <TableCell className="text-xs">{provider.kind}</TableCell>
                      <TableCell>
                        <Badge
                          variant={provider.implemented ? "secondary" : "outline"}
                        >
                          {provider.implemented
                            ? "Implementada"
                            : "Não implementada"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {provider.note}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
