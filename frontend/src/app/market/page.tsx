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
import { IndicatorCard } from "@/components/market/indicator-card";
import { IndicatorHistoryChart } from "@/components/market/indicator-history-chart";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { getIndicatorHistory, getMarketSummary } from "@/lib/api/market";
import { UNIT_LABEL } from "@/lib/format";
import type { IndicatorCode } from "@/lib/api/types";

/** Charted series, and how far back each is worth showing.
 *
 * The Selic target is a daily series, so a shorter window keeps the chart
 * readable; the credit rates are monthly and need years to show a trend. */
const CHARTED: Array<{ code: IndicatorCode; from: string; caption: string }> = [
  {
    code: "SELIC_TARGET",
    from: "2024-01-01",
    caption:
      "Set by the Copom and published ahead of the dates it applies to, so the series extends past today.",
  },
  {
    code: "VEHICLE_FINANCING_RATE_PF",
    from: "2023-09-01",
    caption:
      "Average rate on non-earmarked vehicle credit for individuals. The benchmark for a vehicle financing offer.",
  },
];

export default async function MarketPage() {
  const [summary, ...series] = await Promise.all([
    getMarketSummary(),
    ...CHARTED.map((entry) =>
      getIndicatorHistory(entry.code, { from: entry.from, limit: 5000 }),
    ),
  ]);

  // Tied to when the data was fetched, so every staleness indicator on
  // the page is judged against the same instant.
  const now = summary.fetchedAt;

  return (
    <>
      <PageHeader
        title="Market"
        description="Official Banco Central series for the Brazilian credit market"
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
              {CHARTED.map((entry, index) => {
                const result = series[index];
                const indicator = summary.data.indicators.find(
                  (item) => item.indicator.code === entry.code,
                )?.indicator;

                return (
                  <Card key={entry.code}>
                    <CardHeader>
                      <CardTitle className="text-sm">
                        {indicator?.name ?? entry.code}
                      </CardTitle>
                      <CardDescription>{entry.caption}</CardDescription>
                      {indicator ? (
                        <div className="flex flex-wrap gap-1.5 pt-1">
                          <Badge variant="secondary" className="text-[0.65rem]">
                            {UNIT_LABEL[indicator.unit]}
                          </Badge>
                          <Badge variant="outline" className="text-[0.65rem]">
                            {indicator.frequency.replace("_", " ")}
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
                            "Nothing has been collected for this indicator yet. " +
                            "Trigger a collection through the API to populate the series."
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
                    Mortgage rates are two different series
                  </CardTitle>
                  <CardDescription>
                    Real-estate financing at market rates and under the
                    regulated (CMN / FGTS-linked) regime are published
                    separately and differ by several percentage points. An
                    offer must be compared against the regime it belongs to;
                    benchmarking against the wrong one makes an ordinary offer
                    look expensive, or an expensive one look competitive.
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
