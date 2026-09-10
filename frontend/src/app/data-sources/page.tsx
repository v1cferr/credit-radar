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
import type { CollectionStatus } from "@/lib/api/types";

/** Providers in the planned architecture, including the unbuilt ones.
 *
 * Listed so the page reflects the real integration surface rather than only
 * the part that happens to work. */
const PLANNED_PROVIDERS = [
  {
    name: "Banco Central — SGS",
    kind: "Official public API",
    status: "Implemented",
    note: "Market and macroeconomic series. No authentication, no personal data.",
  },
  {
    name: "Banco Central — SCR / Registrato",
    kind: "Authenticated report",
    status: "Not implemented",
    note: "Requires gov.br authentication. Will need human-assisted sign-in.",
  },
  {
    name: "Serasa",
    kind: "Authenticated account",
    status: "Not implemented",
    note: "Score, negative records and offers. Own scale, kept separate from other bureaus.",
  },
  {
    name: "Quod / SPC / Equifax",
    kind: "Authenticated account",
    status: "Not implemented",
    note: "Independent methodologies. Never merged into a single synthetic score.",
  },
];

function StatusBadge({ status }: { status: CollectionStatus }) {
  if (status === "success") {
    return (
      <Badge variant="secondary" className="gap-1">
        <CheckCircle2 className="size-3" />
        Healthy
      </Badge>
    );
  }
  if (status === "no_data") {
    return (
      <Badge variant="outline" className="gap-1">
        <CircleSlash className="size-3" />
        No data
      </Badge>
    );
  }
  return (
    <Badge variant="destructive" className="gap-1">
      <XCircle className="size-3" />
      Failed
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
        title="Data sources"
        description="Where the data comes from, and whether it is current"
      />

      <div className="flex flex-col gap-6 p-4 md:p-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Collection status</CardTitle>
            <CardDescription>
              Result of the most recent collection attempt for each series. A
              source whose last attempt failed is shown as failed even if it
              still holds older values.
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
                      <TableHead>Indicator</TableHead>
                      <TableHead>Series</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Last synchronized</TableHead>
                      <TableHead className="text-right">Observations</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {summary.data.indicators.map((entry) => (
                      <TableRow key={entry.indicator.code}>
                        <TableCell className="font-medium">
                          {entry.indicator.name}
                        </TableCell>
                        <TableCell className="font-mono text-xs">
                          {entry.latest?.provenance.source_reference ?? "—"}
                        </TableCell>
                        <TableCell>
                          {entry.last_run ? (
                            <StatusBadge status={entry.last_run.status} />
                          ) : (
                            <Badge variant="outline">Never collected</Badge>
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
            <CardTitle className="text-sm">Integration surface</CardTitle>
            <CardDescription>
              Sources are integrated in order of stability: official API,
              structured export, downloadable report, then authenticated
              browser automation only where nothing better exists. Security
              mechanisms such as CAPTCHA, MFA and gov.br sign-in are never
              bypassed.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Source</TableHead>
                    <TableHead>Integration</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Notes</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {PLANNED_PROVIDERS.map((provider) => (
                    <TableRow key={provider.name}>
                      <TableCell className="font-medium">{provider.name}</TableCell>
                      <TableCell className="text-xs">{provider.kind}</TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            provider.status === "Implemented"
                              ? "secondary"
                              : "outline"
                          }
                        >
                          {provider.status}
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
