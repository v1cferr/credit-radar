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
        title="Visão geral"
        description="O que se sabe hoje sobre a posição de crédito"
      />

      <div className="flex flex-col gap-6 p-4 md:p-6">
        <Alert>
          <ShieldQuestion />
          <AlertTitle>Dados pessoais de crédito ainda não conectados</AlertTitle>
          <AlertDescription>
            Nesta etapa só há coleta de dados públicos de mercado do Banco
            Central. Scores, dívidas, negativações e exposição de crédito
            dependem de provedores autenticados que ainda não existem, então
            nenhum número sobre eles é exibido em lugar nenhum deste painel.
          </AlertDescription>
        </Alert>

        <section className="space-y-3">
          <div>
            <h2 className="text-sm font-semibold">Condições de mercado</h2>
            <p className="text-xs text-muted-foreground">
              Séries oficiais do Banco Central. São elas que definem o
              parâmetro para julgar se uma proposta de financiamento está
              competitiva.
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
              <CardTitle className="text-sm">Perfil de crédito</CardTitle>
              <CardDescription>
                Scores, negativações e consultas ao CPF por bureau
              </CardDescription>
            </CardHeader>
            <CardContent>
              <NotImplementedState
                feature="O perfil de crédito"
                requires="um provedor autenticado de bureau, mantendo separadas a escala e o histórico próprios de cada um"
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Dívidas e acordos</CardTitle>
              <CardDescription>
                Dívidas em aberto e as melhores condições de acordo observadas
              </CardDescription>
            </CardHeader>
            <CardContent>
              <NotImplementedState
                feature="A inteligência de dívidas"
                requires="descoberta de dívidas em bureaus, credores e plataformas de negociação"
              />
            </CardContent>
          </Card>
        </section>

        <Alert variant="destructive">
          <AlertTriangle />
          <AlertTitle>O CreditRadar nunca age em seu nome</AlertTitle>
          <AlertDescription>
            Esta aplicação observa, normaliza e explica. Ela não aceita
            acordos, não gera pagamentos, não autoriza transações, não
            solicita empréstimos e não abre produtos financeiros. Qualquer
            operação que crie uma obrigação financeira é feita por você, fora
            deste sistema.
          </AlertDescription>
        </Alert>
      </div>
    </>
  );
}
