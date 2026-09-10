/**
 * Which series the market page charts, and which ones share an axis.
 *
 * Grouped by the question each chart answers rather than one chart per
 * series. The most useful comparison in this application is between the two
 * mortgage regimes, which differ by several percentage points and are
 * published separately: judging an offer against the wrong one makes an
 * ordinary rate look extortionate, or an extortionate one look competitive.
 * That comparison only exists if the two lines are on the same axis.
 *
 * Two rules constrain what may share a panel.
 *
 * A single `unit`, because an axis has one. Plotting "% a.a." against
 * "% a.m." would put a monthly figure a twelfth the size of an annual one
 * next to it and invite reading them as the same quantity.
 *
 * One publication frequency. Series are merged by reference date, so a
 * monthly series beside a daily one would have a value on one date in
 * twenty and render as invisible dots between gaps. The Selic target is
 * charted alone for this reason, though it shares its unit with the
 * financing rates.
 *
 * The window differs by frequency for readability: a daily series needs a
 * shorter one to stay legible, a monthly series needs years before a trend
 * is visible at all.
 */

import type { IndicatorCode, Unit } from "@/lib/api/types";

export interface ChartPanel {
  id: string;
  title: string;
  description: string;
  /** The axis unit. Every series in the panel must publish in it. */
  unit: Unit;
  /** Inclusive start of the charted window, as an ISO date. */
  from: string;
  codes: IndicatorCode[];
}

export const CHART_PANELS: ChartPanel[] = [
  {
    id: "policy",
    title: "Taxa básica de juros",
    description:
      "A meta Selic definida pelo Copom. É o piso a partir do qual todo o resto do crédito é precificado, e vale exatamente o mesmo valor até a decisão seguinte.",
    unit: "percent_per_year",
    from: "2024-01-01",
    codes: ["SELIC_TARGET"],
  },
  {
    id: "financing",
    title: "Quanto custa tomar crédito",
    description:
      "Taxas médias efetivamente praticadas com pessoas físicas, por modalidade. O financiamento imobiliário aparece em dois regimes porque são dois mercados: taxas de mercado e taxas reguladas (CMN / FGTS).",
    unit: "percent_per_year",
    from: "2023-09-01",
    codes: [
      "VEHICLE_FINANCING_RATE_PF",
      "MORTGAGE_RATE_MARKET_PF",
      "MORTGAGE_RATE_REGULATED_PF",
    ],
  },
  {
    id: "inflation",
    title: "Correção monetária",
    description:
      "IPCA e IGP-M, os dois índices que corrigem contratos no Brasil. Qual deles um contrato usa muda quanto ele custa ao longo do tempo.",
    unit: "percent_per_month",
    from: "2023-09-01",
    codes: ["IPCA_MONTHLY", "IGPM_MONTHLY"],
  },
];

/** Every code any panel charts, in panel order, without repetition. */
export const CHARTED_CODES: IndicatorCode[] = [
  ...new Set(CHART_PANELS.flatMap((panel) => panel.codes)),
];
