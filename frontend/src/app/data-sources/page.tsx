/**
 * Provider health.
 *
 * Answers "can I trust what the rest of the dashboard is showing me?" by
 * reporting, per source, when it was last collected and whether that attempt
 * succeeded.
 */

import { PageHeader } from "@/components/app-shell/page-header";
import { BackendOfflineState } from "@/components/common/state-messages";
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
import { CollectionHealth } from "@/features/data-sources/components/collection-health";
import { FreshnessBadge } from "@/features/data-sources/components/freshness-badge";
import { ProviderList } from "@/features/data-sources/components/provider-list";
import {
  FRESHNESS_DESCRIPTIONS,
  freshnessOf,
} from "@/features/data-sources/freshness";
import { getMarketSummary } from "@/lib/api/market";
import { formatDateTime, formatRelativeTime } from "@/lib/format";
import { INDICATOR_LABELS } from "@/lib/labels";
import { sectionMetadata } from "@/components/app-shell/section-metadata";

export const metadata = sectionMetadata("/data-sources");

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
        {summary.ok ? (
          <CollectionHealth indicators={summary.data.indicators} now={now} />
        ) : null}

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
                      <TableHead className="hidden sm:table-cell">
                        Série
                      </TableHead>
                      <TableHead>Situação</TableHead>
                      <TableHead>Sincronização</TableHead>
                      <TableHead className="hidden text-right sm:table-cell">
                        Observações
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {summary.data.indicators.map((entry) => (
                      <TableRow key={entry.indicator.code}>
                        <TableCell className="font-medium">
                          {INDICATOR_LABELS[entry.indicator.code].name}
                          {/* On a phone the series column is folded in
                              here, so the provenance stays on screen
                              instead of behind a sideways scroll. */}
                          <span className="block font-mono text-xs font-normal text-muted-foreground sm:hidden">
                            {entry.latest?.provenance.source_reference ?? "—"}
                          </span>
                        </TableCell>
                        <TableCell className="hidden font-mono text-xs sm:table-cell">
                          {entry.latest?.provenance.source_reference ?? "—"}
                        </TableCell>
                        <TableCell>
                          <span
                            title={
                              FRESHNESS_DESCRIPTIONS[
                                freshnessOf(entry.last_run, now)
                              ]
                            }
                          >
                            <FreshnessBadge
                              freshness={freshnessOf(entry.last_run, now)}
                            />
                          </span>
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
                        <TableCell className="numeric hidden text-right sm:table-cell">
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
            <ProviderList />
          </CardContent>
        </Card>
      </div>
    </>
  );
}
