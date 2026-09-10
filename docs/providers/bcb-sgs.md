# Banco Central do Brasil — SGS

SGS (*Sistema Gerenciador de Séries Temporais*) publishes Brazil's official
macroeconomic and credit-market series as an unauthenticated JSON API. It is
the highest-preference integration type in this project's acquisition
strategy — an official API — which made it the right place to validate the
provider architecture before attempting any authenticated bureau.

Base URL: `https://api.bcb.gov.br/dados/serie`

## Payload contract

```json
[{"data": "16/09/2026", "valor": "14.00"}]
```

Both fields are strings. `data` is `dd/MM/yyyy`. `valor` is a decimal string
with a dot separator, parsed as `Decimal`, never `float`.

Monthly series are dated at the first day of the month they describe.

## Series in use

Every code was confirmed against the Banco Central open-data catalog, not
inferred from a plausible-looking value.

| Internal indicator | SGS | Official series |
| --- | --- | --- |
| `SELIC_TARGET` | 432 | Meta Selic definida pelo Copom (% p.a., daily) |
| `SELIC_ANNUALIZED` | 1178 | Selic annualized, 252 business days (% p.a.) |
| `IPCA_MONTHLY` | 433 | IPCA, monthly change (%) |
| `IGPM_MONTHLY` | 189 | IGP-M, monthly change (%) |
| `VEHICLE_FINANCING_RATE_PF` | 20749 | Non-earmarked credit — individuals — vehicle acquisition (% p.a.) |
| `MORTGAGE_RATE_MARKET_PF` | 20772 | Earmarked credit — individuals — real estate at **market** rates (% p.a.) |
| `MORTGAGE_RATE_REGULATED_PF` | 20773 | Earmarked credit — individuals — real estate at **regulated** rates (% p.a.) |

### The mortgage series are not interchangeable

Series 20772 and 20773 measure different regimes and differ materially. For
2026-07:

| Series | Regime | Value |
| --- | --- | --- |
| 20772 | market rates | 14.28% p.a. |
| 20773 | regulated (CMN / FGTS-linked, SFH) | 10.92% p.a. |

A first implementation used 20773 while describing it as the market-rate
series. Benchmarking an offer against the wrong regime is a 3+ percentage
point error, and it errs in the direction that matters: comparing a
market-rate offer against the regulated average makes an ordinary offer look
expensive, while the reverse makes an expensive offer look competitive. Both
are now tracked as separate indicators, and which one applies is a property
of the offer being judged.

## Upstream behaviours

These were found by testing against the live API. Each one shapes the
provider, and none would have surfaced from unit tests alone.

### Reference dates can be in the future

The Selic target is set by the Copom and published forward until the next
decision. On 2026-09-09, series 432 returned an observation dated
2026-09-16.

A model assuming "observations describe the past" would reject valid data.
`reference_date` is therefore independent of `collected_at` and unbounded by
it.

### "Latest N" is capped at 20

```text
GET /dados/serie/bcdata.sgs.432/dados/ultimos/30?formato=json
→ 400 {"erro": {"detail": "... A quantidade máxima de valores deve ser 20"}}
```

Deterministic. The date-range form carries **no** such cap: a single request
for 2020-01-01 to 2026-09-16 on the daily Selic series returned 2,451 rows
in under a second.

So history and backfill use the range form, and `fetch_latest` refuses a
larger request rather than clamping it — a caller that asked for 90 points
would otherwise receive 20 and treat them as the complete series.

### An empty result is 404, not an empty array

```text
GET /dados/serie/bcdata.sgs.433/dados?dataInicial=01/01/2030&dataFinal=01/02/2030
→ 404 {"erro": {"statusCode": 404, "detail": "... Value(s) not found"}}
```

This is a successful interaction with nothing to return, so it maps to a
`no_data` collection run rather than a failure.

### An invalid series code hangs

A request for a nonexistent series does not return an error status; the
connection stays open until the client gives up. An explicit timeout is
therefore a correctness requirement, not a tuning knob, and retries are kept
low because each one costs a full timeout for what is likely a permanent
fault.

### Rows may carry no measurement

Some series include rows whose `valor` is blank for unmeasured periods.
These are skipped, never stored as zero: zero is a real rate and "not
measured" is not. Periods a series simply does not cover are absent from the
response rather than blank.

### Rapid successive requests are unreliable

Repeated calls in quick succession returned inconsistent `502`s that
disappeared with a few seconds' spacing. Treated as transient and retryable;
worth spacing out a bulk backfill across many series.

## Encoding note

`dd/MM/yyyy` parameters survive URL encoding — `01%2F09%2F2026` is accepted —
so the standard query-parameter encoding needs no special handling.

## Testing

Provider tests run against a mocked transport with fixtures captured from
these public endpoints, plus one synthetic fixture for the unmeasured-row
case. Parsing is verified separately from network interaction, so the suite
is deterministic and never depends on the API being reachable.
