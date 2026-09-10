/**
 * Overview.
 *
 * Ordered by what a reader needs first: whether the data can be trusted,
 * then what it says, then what is missing from the picture.
 *
 * Collection health leads because it changes how everything below it should
 * be read -- a rate whose source failed this morning is not the same claim
 * as one confirmed an hour ago. Then the market conditions, which are the
 * benchmark any financing offer has to be judged against. Then, plainly,
 * the parts of the product that do not exist yet: someone reading their own
 * credit position has to know what is absent from it, because a dashboard
 * that shows only its working half implies the other half is empty.
 *
 * Nothing here is filler. No section displays a figure the backend cannot
 * currently provide.
 */

import { ShieldCheck } from "lucide-react";

import { PageHeader } from "@/components/app-shell/page-header";
import { PlannedSections } from "@/components/app-shell/planned-sections";
import { BackendOfflineState } from "@/components/common/state-messages";
import { CollectionHealth } from "@/features/data-sources/components/collection-health";
import { IndicatorCard } from "@/features/market/components/indicator-card";
import { sectionMetadata } from "@/components/app-shell/section-metadata";
import { getMarketSummary } from "@/lib/api/market";
import type { IndicatorCode } from "@/lib/api/types";

export const metadata = sectionMetadata("/");

/**
 * Indicators that belong on the overview.
 *
 * The policy rate, because it sets the floor for everything else, and the
 * two financing rates a person actually borrows at. The remaining series
 * are on the market page: an overview that lists all seven is a market
 * page with a different name.
 */
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
        title="Visão geral"
        description="O que se sabe hoje sobre a posição de crédito"
      />

      <div className="flex flex-col gap-6 p-4 md:p-6">
        {!summary.ok ? (
          <BackendOfflineState message={summary.error} />
        ) : (
          <>
            <CollectionHealth
              indicators={summary.data.indicators}
              now={now}
            />

            <section className="space-y-3">
              <div className="space-y-0.5">
                <h2 className="text-sm font-semibold">
                  Condições de mercado
                </h2>
                <p className="text-xs text-muted-foreground">
                  Séries oficiais do Banco Central. São elas que definem o
                  parâmetro para julgar se uma proposta de financiamento está
                  competitiva.
                </p>
              </div>

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
            </section>
          </>
        )}

        <section className="space-y-4 rounded-lg border border-dashed p-4 md:p-5">
          <div className="space-y-1">
            <h2 className="text-sm font-semibold">
              Dados pessoais de crédito ainda não conectados
            </h2>
            <p className="max-w-3xl text-xs text-muted-foreground">
              Por enquanto só há coleta de dados públicos de mercado do Banco
              Central. Score, dívidas, negativações e exposição dependem de
              provedores que ainda não existem, e nenhum número sobre eles é
              exibido em lugar nenhum deste painel — dado financeiro
              inventado é pior do que dado nenhum.
            </p>
          </div>

          <PlannedSections />
        </section>

        <section className="flex gap-3 rounded-lg border bg-card p-4">
          <ShieldCheck
            className="mt-0.5 size-4 shrink-0 text-informational"
            aria-hidden
          />
          <div className="space-y-1">
            <h2 className="text-sm font-semibold">
              O CreditRadar nunca age em seu nome
            </h2>
            <p className="max-w-3xl text-xs text-muted-foreground">
              Esta aplicação observa, normaliza e explica. Ela não aceita
              acordos, não gera pagamentos, não autoriza transações, não
              solicita empréstimos e não abre produtos financeiros. Qualquer
              operação que crie uma obrigação financeira é feita por você,
              fora deste sistema.
            </p>
          </div>
        </section>
      </div>
    </>
  );
}
