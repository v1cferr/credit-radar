/**
 * Tests for the display formatting layer.
 *
 * These functions are the last step before a figure about someone's money
 * reaches the screen, and every one of them is pure, so they are the
 * cheapest correctness there is to buy in this frontend. They exist because
 * `formatDelta` shipped rendering a difference between two annual rates as
 * "+0,25 a.a." -- dropping the percent sign and keeping a per-year suffix
 * that a difference does not have. Nothing failed: no call site passed a
 * previous observation yet, so the wrong string was never rendered. A unit
 * test would have caught it the day it was written.
 */

import { describe, expect, it } from "vitest";

import {
  deltaDirection,
  formatCurrency,
  formatDate,
  formatDecimal,
  formatDelta,
  formatRate,
  formatRelativeTime,
} from "@/lib/format";

describe("formatDecimal", () => {
  it("uses the Brazilian decimal comma and thousands separator", () => {
    expect(formatDecimal("1234.56")).toBe("1.234,56");
  });

  it("preserves the scale the source published", () => {
    // "14.00" is not "14": the trailing zero states two decimals of
    // precision, and dropping it silently reduces what the source said.
    expect(formatDecimal("14.00")).toBe("14,00");
    expect(formatDecimal("14")).toBe("14");
    expect(formatDecimal("0.4200")).toBe("0,4200");
  });

  it("returns the input unchanged when it is not a number", () => {
    expect(formatDecimal("n/a")).toBe("n/a");
  });
});

describe("formatRate", () => {
  it("writes rates in the notation the Brazilian market publishes", () => {
    expect(formatRate("14.75", "percent_per_year")).toBe("14,75% a.a.");
    expect(formatRate("0.52", "percent_per_month")).toBe("0,52% a.m.");
    expect(formatRate("0.0411", "percent_per_day")).toBe("0,0411% a.d.");
  });

  it("separates index points from the figure", () => {
    expect(formatRate("4321.90", "index_points")).toBe("4.321,90 pts");
  });
});

describe("formatCurrency", () => {
  it("formats an amount as Brazilian currency", () => {
    // A non-breaking space follows "R$" in pt-BR, so compare loosely on
    // whitespace rather than pinning the exact codepoint ICU chooses.
    expect(formatCurrency("1250").replace(/\s/g, " ")).toBe("R$ 1.250,00");
    expect(formatCurrency("1250.5").replace(/\s/g, " ")).toBe("R$ 1.250,50");
  });

  it("keeps a scale finer than centavos when the source published one", () => {
    expect(formatCurrency("0.1234").replace(/\s/g, " ")).toBe("R$ 0,1234");
  });
});

describe("formatDelta", () => {
  it("expresses a difference between rates in percentage points", () => {
    // Not "+0,25% a.a.": that would mean a quarter of one percent of the
    // rate itself, which is a different and much smaller number.
    expect(formatDelta("15.00", "14.75", "percent_per_year")).toBe("+0,25 p.p.");
    expect(formatDelta("0.52", "0.60", "percent_per_month")).toBe("-0,08 p.p.");
    expect(formatDelta("0.0411", "0.0400", "percent_per_day")).toBe(
      "+0,0011 p.p.",
    );
  });

  it("shows an explicit sign for a rise and none for no change", () => {
    expect(formatDelta("14.75", "14.75", "percent_per_year")).toBe("0,00 p.p.");
  });

  it("keeps index points as points", () => {
    expect(formatDelta("4322.00", "4300.00", "index_points")).toBe("+22,00 pts");
  });

  it("returns nothing it cannot compute", () => {
    expect(formatDelta("n/a", "14.75", "percent_per_year")).toBe("");
  });
});

describe("deltaDirection", () => {
  it("reports direction without judging it", () => {
    expect(deltaDirection("15.00", "14.75")).toBe("up");
    expect(deltaDirection("14.75", "15.00")).toBe("down");
    expect(deltaDirection("14.75", "14.75")).toBe("flat");
  });

  it("treats an uncomputable difference as no movement", () => {
    expect(deltaDirection("n/a", "14.75")).toBe("flat");
  });
});

describe("formatDate", () => {
  it("writes ISO dates in Brazilian order", () => {
    expect(formatDate("2026-09-16")).toBe("16/09/2026");
  });

  it("does not reinterpret a value that is not an ISO date", () => {
    expect(formatDate("2026-09")).toBe("2026-09");
  });
});

describe("formatRelativeTime", () => {
  const now = Date.parse("2026-09-10T12:00:00Z");

  it("makes staleness legible", () => {
    expect(formatRelativeTime("2026-09-10T11:58:30Z", now)).toBe("há 1 minuto");
    expect(formatRelativeTime("2026-09-10T10:00:00Z", now)).toBe("há 2 horas");
    expect(formatRelativeTime("2026-09-01T12:00:00Z", now)).toBe("há 9 dias");
  });

  it("does not round a fresh collection up to an hour", () => {
    expect(formatRelativeTime("2026-09-10T11:59:30Z", now)).toBe("agora mesmo");
  });

  it("says plainly when a reference instant is ahead of now", () => {
    // A reference date may legitimately be in the future -- the Copom
    // publishes the Selic target ahead of the dates it applies to -- so
    // this must not render as a negative age.
    expect(formatRelativeTime("2026-09-11T12:00:00Z", now)).toBe("no futuro");
  });
});
