/**
 * Types mirroring the backend response schemas in
 * `backend/src/credit_radar/api/schemas.py`.
 *
 * Hand-written on purpose. The API surface is currently one resource area,
 * so generating a client from the OpenAPI document would add a build step
 * and a regeneration ritual to save around fifty lines. Once several
 * resource areas exist (debts, scores, exposure, financing), generation
 * starts paying for itself and should replace this file -- the backend
 * already serves the document at /openapi.json.
 *
 * Financial values arrive as strings, never numbers: a JSON number is an
 * IEEE-754 double here, which would turn "14.00" into 14 and lose the scale
 * the source published.
 */

export type IndicatorCode =
  | "SELIC_TARGET"
  | "SELIC_ANNUALIZED"
  | "IPCA_MONTHLY"
  | "IGPM_MONTHLY"
  | "VEHICLE_FINANCING_RATE_PF"
  | "MORTGAGE_RATE_MARKET_PF"
  | "MORTGAGE_RATE_REGULATED_PF";

export type Unit =
  | "percent_per_year"
  | "percent_per_month"
  | "percent_per_day"
  | "index_points";

export type Frequency = "daily" | "business_daily" | "monthly";

export type IndicatorKind =
  | "policy_rate"
  | "market_interest_rate"
  | "inflation_index";

export type CollectionStatus = "success" | "no_data" | "failed";

export interface Provenance {
  source_id: string;
  source_reference: string;
  collector_version: string;
  collected_at: string;
}

export interface Indicator {
  code: IndicatorCode;
  name: string;
  kind: IndicatorKind;
  unit: Unit;
  frequency: Frequency;
  description: string;
}

export interface Observation {
  indicator_code: IndicatorCode;
  /** The date the value refers to. May be in the future: the Copom
   * publishes the Selic target ahead of the dates it applies to. */
  reference_date: string;
  /** Decimal as text. Parse only for charting; format from the string. */
  value: string;
  unit: Unit;
  provenance: Provenance;
}

export interface CollectionRun {
  status: CollectionStatus;
  started_at: string;
  finished_at: string;
  observation_count: number;
  error_message: string | null;
}

export interface IndicatorSummary {
  indicator: Indicator;
  /** Null when nothing has been collected. Render "no observations yet",
   * never a zero, which would read as a real rate. */
  latest: Observation | null;
  last_run: CollectionRun | null;
}

export interface MarketSummary {
  indicators: IndicatorSummary[];
}

export interface ObservationSeries {
  indicator: Indicator;
  observations: Observation[];
}

export interface Health {
  status: string;
  database: string;
}
