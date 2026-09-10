# Domain model

## The shape everything follows

```text
Entity + Observation + Source + ObservedAt
```

An entity is the thing being tracked and is stable over time. An observation
is one measured value of it, carrying the date the value refers to and the
provenance of how it was obtained. State is never overwritten.

## Implemented

### `MarketIndicator`

A quantity CreditRadar tracks: code, name, kind, unit, frequency,
description. Codes are internal (`SELIC_TARGET`) and independent of any
source's numbering, so accumulated history survives an upstream renumbering
or a second source for the same concept.

`IndicatorKind` separates a **policy rate** set by the central bank from an
observed **market interest rate**, because they answer different questions:
the first is a macroeconomic condition, the second is the benchmark for
judging whether a specific offer is competitive.

Rates are kept in the unit the source publishes. Annualizing a daily rate
requires choosing a day-count convention (252 vs 365), which is an analytical
decision and must not be hidden inside ingestion.

The catalog holds only what an indicator *means*. Which upstream series
provides it is provider knowledge and lives with the provider.

### `MarketObservation`

One value of one indicator, at one reference date, from one source.

Three invariants are enforced at construction:

- **`reference_date` is independent of `collected_at`** and may be in the
  future. The Copom publishes the Selic target ahead of the dates it applies
  to, so a future reference date is valid data, not a clock error.
- **Financial values reject `float`.** `Decimal(0.1)` is not `0.1`, and this
  dataset exists to compare settlement offers and financing costs where that
  error compounds.
- **The unit must match the catalog.** A per-day rate stored under a
  per-year label is a plausible-looking number that would skew every
  downstream comparison.

### `Provenance`

`source_id`, `source_reference` (the source's own identifier, kept verbatim),
`collector`, `collector_version`, `collected_at`, `request_url`.

`collector_version` is bumped whenever normalization changes in a way that
could produce a different value from the same payload. Without it, a parsing
bug fixed today is indistinguishable from data that was always correct.

Timestamps must be timezone-aware and are normalized to UTC; a naive datetime
silently corrupts comparisons across collection runs.

### `CollectionRun`

One row per collection attempt, successful or not, with a `CollectionStatus`
of `success`, `no_data` or `failed`. Recorded so gaps in the series can be
explained afterwards, and because runs cannot be backfilled — an attempt that
was never recorded is lost.

## Planned

Deliberately not implemented yet. Each needs its provider to exist first, and
building the model before the data would mean guessing at its shape.

- `CreditBureau`, `CreditScoreObservation`, `ScoreFactor`
- `Debt`, `DebtObservation`, `Creditor`, `NegativeRecord`, `SettlementOffer`
- `CreditInquiry`, `CreditContract`, `CreditExposure`, `CreditLimit`
- `FinancialGoal`, `FinancingScenario`, `FinancingOffer`
- `CreditReadinessAssessment`

## Distinctions the model must preserve

These are not synonyms, and collapsing any pair would make the system answer
the wrong question:

| | |
| --- | --- |
| `Debt` ≠ `NegativeRecord` | a debt can exist without a negative record, and a record can outlast payment |
| `Debt` ≠ `SettlementOffer` | an offer is one creditor's price for closing a debt at one moment |
| `CreditScore` ≠ `Creditworthiness` | a score is one bureau's opinion, not the whole picture |
| `Creditworthiness` ≠ `Affordability` | being approved is not the same as being able to pay |
| `CreditAvailability` ≠ `CreditAttractiveness` | credit being offered says nothing about it being worth taking |
| "Can I get this credit?" ≠ "Should I?" | separate analytical questions with separate inputs |

## Bureaus stay separate

Serasa, Quod, SPC and Equifax use different methodologies and scales. Each
keeps its own score, factors, observations, metadata and history. Normalized
abstractions may sit above them, but source-specific meaning is never lost,
and there is no synthetic universal Brazilian score — inventing one would
fabricate authority the project does not have.
