/**
 * Portuguese presentation labels for domain values.
 *
 * The interface is pt-BR because it is a personal tool for the Brazilian
 * credit market and the user reads Portuguese. Everything else in this
 * repository stays en-US: code, identifiers, comments, documentation and
 * commit messages.
 *
 * The backend's own `name` and `description` are NOT rendered. They live in
 * the domain catalog, which is en-US on purpose, and they describe what an
 * indicator means for whoever maintains the system. What the user should see
 * it called is a presentation concern, so it lives here, keyed by the stable
 * internal indicator code.
 *
 * Typed as exhaustive Records so a new indicator or unit fails to compile
 * until it has a label, rather than reaching the screen as a raw enum value.
 *
 * No i18n library: there is one locale and adding a framework for it would
 * be machinery without a second case to justify it. A library earns its
 * place the day a second language does.
 */

import type {
  Frequency,
  IndicatorCode,
  IndicatorKind,
  Unit,
} from "@/lib/api/types";

export interface IndicatorLabel {
  /** Short name, for cards and chart titles. */
  name: string;
  /** What it measures and why it matters, for a card's subtitle. */
  description: string;
}

export const INDICATOR_LABELS: Record<IndicatorCode, IndicatorLabel> = {
  SELIC_TARGET: {
    name: "Meta Selic",
    description:
      "Definida pelo Copom e publicada com antecedência, mantida até a próxima reunião. Por isso a série avança para datas futuras.",
  },
  SELIC_ANNUALIZED: {
    name: "Selic anualizada",
    description:
      "Taxa efetivamente praticada no mercado, anualizada na base de 252 dias úteis. Acompanha a meta de perto, mas não é idêntica a ela.",
  },
  IPCA_MONTHLY: {
    name: "IPCA mensal",
    description:
      "Índice oficial de inflação ao consumidor. Sofre revisão após a publicação, e é por isso que as observações são guardadas como revisões em vez de sobrescritas.",
  },
  IGPM_MONTHLY: {
    name: "IGP-M mensal",
    description:
      "Índice geral de preços usado como indexador em vários tipos de contrato, incluindo aluguel e acordos imobiliários.",
  },
  VEHICLE_FINANCING_RATE_PF: {
    name: "Financiamento de veículos",
    description:
      "Taxa média cobrada de pessoas físicas em crédito livre para aquisição de veículos. É o parâmetro para julgar se uma proposta de financiamento está competitiva.",
  },
  MORTGAGE_RATE_MARKET_PF: {
    name: "Imobiliário, taxas de mercado",
    description:
      "Taxa média do crédito imobiliário direcionado contratado a taxas de mercado. É o parâmetro correto para uma proposta fora do regime regulado.",
  },
  MORTGAGE_RATE_REGULATED_PF: {
    name: "Imobiliário, taxas reguladas",
    description:
      "Taxa média do crédito imobiliário sob taxas reguladas pelo CMN ou vinculadas a recursos direcionados (regime SFH/FGTS). Fica estruturalmente abaixo da série de mercado, e as duas nunca devem ser comparadas com a mesma proposta.",
  },
};

export const UNIT_LABELS: Record<Unit, string> = {
  percent_per_year: "porcentagem ao ano",
  percent_per_month: "porcentagem ao mês",
  percent_per_day: "porcentagem ao dia",
  index_points: "pontos de índice",
};

export const FREQUENCY_LABELS: Record<Frequency, string> = {
  daily: "diária",
  business_daily: "dias úteis",
  monthly: "mensal",
};

export const KIND_LABELS: Record<IndicatorKind, string> = {
  policy_rate: "taxa de política monetária",
  market_interest_rate: "taxa de juros de mercado",
  inflation_index: "índice de inflação",
};

/** Human-readable name of a data source, by its internal id. */
export const SOURCE_LABELS: Record<string, string> = {
  "bcb.sgs": "Banco Central do Brasil — SGS",
};
