/**
 * Brazilian credit-market conditions.
 *
 * The first complete vertical slice: Banco Central SGS -> provider ->
 * domain -> PostgreSQL -> REST -> this page.
 */

import { PageHeader } from "@/components/app-shell/page-header";
import {
  BackendOfflineState,
  EmptyState,
} from "@/components/common/state-messages";
import { IndicatorCard } from "@/features/market/components/indicator-card";
import { IndicatorHistoryChart } from "@/features/market/components/indicator-history-chart";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CHARTED_SERIES } from "@/features/market/charted-series";
import { getIndicatorHistory, getMarketSummary } from "@/lib/api/market";
import { FREQUENCY_LABELS, INDICATOR_LABELS, UNIT_LABELS } from "@/lib/labels";

export default async function MarketPage() {
  const [summary, ...series] = await Promise.all([
    getMarketSummary(),
    ...CHARTED_SERIES.map((entry) =>
      getIndicatorHistory(entry.code, { from: entry.from, limit: 5000 }),
    ),
  ]);

  // Tied to when the data was fetched, so every staleness indicator on
  // the page is judged against the same instant.
  const now = summary.fetchedAt;

  return (
    <>
      <PageHeader
        title="Mercado"
        description="Séries oficiais do Banco Central para o mercado de crédito brasileiro"
      />

      <div className="flex flex-col gap-6 p-4 md:p-6">
        {!summary.ok ? (
          <BackendOfflineState message={summary.error} />
        ) : (
          <>
            <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {summary.data.indicators.map((entry) => (
                <IndicatorCard
                  key={entry.indicator.code}
                  summary={entry}
                  now={now}
                />
              ))}
            </section>

            <section className="space-y-4">
              {CHARTED_SERIES.map((entry, index) => {
                const result = series[index];
                const label = INDICATOR_LABELS[entry.code];
                const indicator = summary.data.indicators.find(
                  (item) => item.indicator.code === entry.code,
                )?.indicator;

                return (
                  <Card key={entry.code}>
                    <CardHeader>
                      <CardTitle className="text-sm">{label.name}</CardTitle>
                      <CardDescription>{label.description}</CardDescription>
                      {indicator ? (
                        <div className="flex flex-wrap gap-1.5 pt-1">
                          <Badge variant="secondary" className="text-[0.65rem]">
                            {UNIT_LABELS[indicator.unit]}
                          </Badge>
                          <Badge variant="outline" className="text-[0.65rem]">
                            {FREQUENCY_LABELS[indicator.frequency]}
                          </Badge>
                        </div>
                      ) : null}
                    </CardHeader>
                    <CardContent>
                      {!result.ok ? (
                        <BackendOfflineState message={result.error} />
                      ) : result.data.observations.length === 0 ? (
                        <EmptyState
                          message={
                            "Nada foi coletado para este indicador ainda. " +
                            "Rode uma coleta para preencher a série."
                          }
                        />
                      ) : (
                        <IndicatorHistoryChart series={result.data} />
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </section>

            <section>
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">
                    Crédito imobiliário são duas séries diferentes
                  </CardTitle>
                  <CardDescription>
                    O financiamento imobiliário a taxas de mercado e o sob
                    taxas reguladas (regime CMN / FGTS) são publicados
                    separadamente e diferem em vários pontos percentuais. Uma
                    proposta precisa ser comparada com o regime a que pertence:
                    usar o parâmetro errado faz uma proposta comum parecer
                    caríssima, ou uma caríssima parecer competitiva.
                  </CardDescription>
                </CardHeader>
              </Card>
            </section>
          </>
        )}
      </div>
    </>
  );
}
