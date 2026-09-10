/**
 * Overview.
 *
 * Shows what is actually known. Sections whose providers do not exist yet
 * declare that plainly instead of displaying a figure, because a dashboard
 * about someone's credit position is worse than useless if the reader cannot
 * tell a real number from a filler one.
 */

import { AlertTriangle, ShieldQuestion } from "lucide-react";

import { PageHeader } from "@/components/app-shell/page-header";
import {
  BackendOfflineState,
  NotImplementedState,
} from "@/components/common/state-messages";
import { IndicatorCard } from "@/components/market/indicator-card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { getMarketSummary } from "@/lib/api/market";
import type { IndicatorCode } from "@/lib/api/types";

/** Indicators that belong on the overview's market panel. */
const HEADLINE_INDICATORS: IndicatorCode[] = [
  "SELIC_TARGET",
  "VEHICLE_FINANCING_RATE_PF",
  "MORTGAGE_RATE_MARKET_PF",
];

export default async function OverviewPage() {
  const summary = await getMarketSummary();
  // Tied to when the data was fetched, so every staleness indicator on
  // the page is judged against the same instant.
  const now = summary.fetchedAt;

  return (
    <>
      <PageHeader
        title="Overview"
        description="What is currently known about the credit position"
      />

      <div className="flex flex-col gap-6 p-4 md:p-6">
        <Alert>
          <ShieldQuestion />
          <AlertTitle>Personal credit data is not connected yet</AlertTitle>
          <AlertDescription>
            Only public Banco Central market data is collected at this stage.
            Scores, debts, negative records and credit exposure require
            authenticated providers that are not implemented yet, so no figure
            for them is shown anywhere in this dashboard.
          </AlertDescription>
        </Alert>

        <section className="space-y-3">
          <div>
            <h2 className="text-sm font-semibold">Market conditions</h2>
            <p className="text-xs text-muted-foreground">
              Official Banco Central series. These set the benchmark for
              judging whether a financing offer is competitive.
            </p>
          </div>

          {!summary.ok ? (
            <BackendOfflineState message={summary.error} />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {HEADLINE_INDICATORS.map((code) => {
                const entry = summary.data.indicators.find(
                  (item) => item.indicator.code === code,
                );
                return entry ? (
                  <IndicatorCard key={code} summary={entry} now={now} />
                ) : null;
              })}
            </div>
          )}
        </section>

        <section className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Credit profile</CardTitle>
              <CardDescription>
                Scores, negative records and inquiries per bureau
              </CardDescription>
            </CardHeader>
            <CardContent>
              <NotImplementedState
                feature="Credit profile"
                requires="an authenticated bureau provider, keeping each bureau's own scale and history separate"
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Debts and settlement</CardTitle>
              <CardDescription>
                Outstanding debts and the best observed settlement conditions
              </CardDescription>
            </CardHeader>
            <CardContent>
              <NotImplementedState
                feature="Debt intelligence"
                requires="debt discovery across bureaus, creditors and negotiation platforms"
              />
            </CardContent>
          </Card>
        </section>

        <Alert variant="destructive">
          <AlertTriangle />
          <AlertTitle>CreditRadar never acts on your behalf</AlertTitle>
          <AlertDescription>
            This application observes, normalizes and explains. It does not
            accept settlement agreements, generate payments, authorize
            transactions, request loans or open financial products. Any
            operation that creates a financial obligation is yours to perform,
            outside this system.
          </AlertDescription>
        </Alert>
      </div>
    </>
  );
}
