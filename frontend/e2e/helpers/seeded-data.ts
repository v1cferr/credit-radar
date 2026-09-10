/**
 * What `backend/scripts/seed_e2e.py` puts in the database.
 *
 * ALL SYNTHETIC. The values are deliberately unlike the real Banco Central
 * figures, so a failing screenshot from this suite can never be mistaken for
 * a real reading of the credit market.
 *
 * Mirrored here rather than derived from the API, because a test that reads
 * its expectation from the thing it is testing proves nothing. The seed
 * script is the other half of this contract; changing one means changing
 * both, which is the intended friction.
 */

export const SEEDED = {
  /** Healthy daily series, 30 points with a step change part-way. */
  selicTarget: {
    label: "Meta Selic",
    latestValue: "13,25% a.a.",
    latestReferenceDate: "30/08/2026",
    series: "bcdata.sgs.432",
    observationCount: 30,
  },
  /** Healthy monthly series. */
  vehicleRate: {
    label: "Financiamento de veículos",
    latestValue: "24,50% a.a.",
    series: "bcdata.sgs.20749",
  },
  /** The two mortgage regimes, far apart so the UI cannot be collapsing them. */
  mortgageMarket: {
    label: "Imobiliário, taxas de mercado",
    latestValue: "15,75% a.a.",
  },
  mortgageRegulated: {
    label: "Imobiliário, taxas reguladas",
    latestValue: "9,80% a.a.",
  },
  /** Has a value, but its last collection is ten days old. */
  stale: {
    label: "IPCA mensal",
    latestValue: "0,42% a.m.",
  },
  /** Has an older value AND a failed last collection. */
  failed: {
    label: "Selic anualizada",
    latestValue: "12,60% a.a.",
  },
  /** Seeded with nothing at all: no observations, no collection run. */
  neverCollected: {
    label: "IGP-M mensal",
  },
} as const;
