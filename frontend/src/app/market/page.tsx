/**
 * Brazilian credit-market conditions.
 *
 * The first complete vertical slice: Banco Central SGS -> provider ->
 * domain -> PostgreSQL -> REST -> this page.
 *
 * Two layers. The cards state where every indicator stands now, grouped by
 * what kind of number it is, because a policy rate, a price paid by
 * borrowers and an inflation index are not comparable to each other however
 * similar they look. The charts below answer the questions worth asking of
 * the history, which is why they are grouped rather than one per series:
 * the two mortgage regimes only mean something next to each other.
 */

import { PageHeader } from "@/components/app-shell/page-header";
import { sectionMetadata } from "@/components/app-shell/section-metadata";
import {
  BackendOfflineState,
  EmptyState,
} from "@/components/common/state-messages";
import { IndicatorCard } from "@/features/market/components/indicator-card";
import { IndicatorChart } from "@/features/market/components/indicator-chart";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CHART_PANELS, CHARTED_CODES } from "@/features/market/chart-panels";
import { toSeriesPoints, type PlottedSeries } from "@/features/market/series-points";
import { getIndicatorHistory, getMarketSummary } from "@/lib/api/market";
import { KIND_HEADINGS, UNIT_LABELS } from "@/lib/labels";
import type { IndicatorCode, IndicatorKind } from "@/lib/api/types";

export const metadata = sectionMetadata("/market");

/** Card groups, in the order a borrowing decision is reasoned about. */
const KIND_ORDER: IndicatorKind[] = [
  "policy_rate",
  "market_interest_rate",
  "inflation_index",
];

/** Earliest window any panel asks for, per charted series. */
const WINDOW_FOR = new Map<IndicatorCode, string>(
  CHART_PANELS.flatMap((panel) =>
    panel.codes.map((code) => [code, panel.from] as const),
  ),
);

export default async function MarketPage() {
  const [summary, ...histories] = await Promise.all([
    getMarketSummary(),
    ...CHARTED_CODES.map((code) =>
      getIndicatorHistory(code, { from: WINDOW_FOR.get(code), limit: 5000 }),
    ),
  ]);

  // Tied to when the data was fetched, so every staleness indicator on
  // the page is judged against the same instant.
  const now = summary.fetchedAt;

  const seriesByCode = new Map(
    CHARTED_CODES.map((code, index) => [code, histories[index]]),
  );

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
            {KIND_ORDER.map((kind) => {
              const entries = summary.data.indicators.filter(
                (entry) => entry.indicator.kind === kind,
              );
              if (entries.length === 0) return null;

              return (
                <section key={kind} className="space-y-3">
                  <h2 className="text-sm font-semibold">
                    {KIND_HEADINGS[kind]}
                  </h2>
                  <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                    {entries.map((entry) => (
                      <IndicatorCard
                        key={entry.indicator.code}
                        summary={entry}
                        now={now}
                      />
                    ))}
                  </div>
                </section>
              );
            })}

            <section className="space-y-4">
              <h2 className="text-sm font-semibold">Como isso se moveu</h2>

              {CHART_PANELS.map((panel) => {
                const results = panel.codes.map((code) => ({
                  code,
                  result: seriesByCode.get(code),
                }));

                const failed = results.find(
                  (entry) => entry.result && !entry.result.ok,
                );
                const plotted: PlottedSeries[] = results.flatMap((entry) =>
                  entry.result?.ok
                    ? [
                        {
                          code: entry.code,
                          kind: entry.result.data.indicator.kind,
                          points: toSeriesPoints(entry.result.data),
                        },
                      ]
                    : [],
                );
                const hasPoints = plotted.some(
                  (entry) => entry.points.length > 0,
                );

                return (
                  <Card key={panel.id}>
                    <CardHeader>
                      <CardTitle className="text-sm" role="heading" aria-level={3}>
                        {panel.title}
                      </CardTitle>
                      <CardDescription>{panel.description}</CardDescription>
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        <Badge variant="secondary" className="text-[0.65rem]">
                          {UNIT_LABELS[panel.unit]}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent>
                      {failed?.result && !failed.result.ok ? (
                        <BackendOfflineState message={failed.result.error} />
                      ) : !hasPoints ? (
                        <EmptyState
                          message={
                            "Nada foi coletado para estas séries ainda. " +
                            "Rode uma coleta para preenchê-las."
                          }
                        />
                      ) : (
                        <IndicatorChart series={plotted} />
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </section>
          </>
        )}
      </div>
    </>
  );
}
