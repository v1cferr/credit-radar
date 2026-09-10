/**
 * The frontend/backend contract, checked from both ends of the same request.
 *
 * Reads a value from the API, then asserts the page shows that same value.
 * A UI test alone can pass on a stale build; an API test alone can pass while
 * the page renders something else. Together they pin the contract.
 */

import { expect, test } from "@playwright/test";

import { BACKEND_URL } from "./helpers/environment";
import { SEEDED } from "./helpers/seeded-data";
import { indicatorCard } from "./helpers/ui";

interface Observation {
  indicator_code: string;
  reference_date: string;
  value: string;
  unit: string;
  provenance: {
    source_id: string;
    source_reference: string;
    collector_version: string;
    collected_at: string;
  };
}

test.describe("backend health", () => {
  test("reports the database as reachable", async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/health`);

    expect(response.ok()).toBe(true);
    expect(await response.json()).toEqual({
      status: "ok",
      database: "reachable",
    });
  });
});

test.describe("market API", () => {
  test("serves financial values as strings, not numbers", async ({ request }) => {
    // A JSON number becomes an IEEE-754 double in the browser, which would
    // turn "13.25" into 13.25 with no guarantee about the trailing digits and
    // would lose a published scale like "9.80".
    const response = await request.get(
      `${BACKEND_URL}/api/v1/market/indicators/SELIC_TARGET/observations/latest`,
    );
    const body = (await response.json()) as Observation;

    expect(typeof body.value).toBe("string");
    expect(body.value).toBe("13.25");
  });

  test("carries provenance on every observation", async ({ request }) => {
    const response = await request.get(
      `${BACKEND_URL}/api/v1/market/indicators/SELIC_TARGET/observations/latest`,
    );
    const body = (await response.json()) as Observation;

    expect(body.provenance.source_id).toBe("bcb.sgs");
    expect(body.provenance.source_reference).toBe(SEEDED.selicTarget.series);
    expect(body.provenance.collected_at).toBeTruthy();
  });

  test("returns 404 for an indicator with no observations", async ({ request }) => {
    const response = await request.get(
      `${BACKEND_URL}/api/v1/market/indicators/IGPM_MONTHLY/observations/latest`,
    );

    expect(response.status()).toBe(404);
  });

  test("returns an empty series rather than an error for a known indicator", async ({
    request,
  }) => {
    const response = await request.get(
      `${BACKEND_URL}/api/v1/market/indicators/IGPM_MONTHLY/observations`,
    );

    expect(response.ok()).toBe(true);
    const body = (await response.json()) as { observations: Observation[] };
    expect(body.observations).toEqual([]);
  });

  test("rejects an inverted date range", async ({ request }) => {
    const response = await request.get(
      `${BACKEND_URL}/api/v1/market/indicators/SELIC_TARGET/observations`,
      { params: { from: "2026-12-01", to: "2026-01-01" } },
    );

    expect(response.status()).toBe(422);
  });
});

test.describe("the page shows what the API returned", () => {
  test("the Selic value on screen is the one the API served", async ({ page, request }) => {
    const response = await request.get(
      `${BACKEND_URL}/api/v1/market/indicators/SELIC_TARGET/observations/latest`,
    );
    const observation = (await response.json()) as Observation;

    await page.goto("/market");
    const card = indicatorCard(page, SEEDED.selicTarget.label);

    // Formatted for a Brazilian reader: the dot becomes a comma and the unit
    // is spelled the way the market writes it.
    const displayed = `${observation.value.replace(".", ",")}% a.a.`;
    await expect(card.getByText(displayed)).toBeVisible();
  });

  test("the chart holds as many points as the API reports", async ({ page, request }) => {
    const response = await request.get(
      `${BACKEND_URL}/api/v1/market/indicators/SELIC_TARGET/observations`,
      { params: { from: "2024-01-01", limit: 5000 } },
    );
    const body = (await response.json()) as { observations: Observation[] };

    expect(body.observations).toHaveLength(SEEDED.selicTarget.observationCount);

    await page.goto("/market");
    const line = page.locator("path.recharts-curve").first();
    await expect(line).toBeAttached();

    // Exactly one drawing command per interval between consecutive points,
    // so the line reflects the series the API served rather than happening
    // to be non-empty. Counted by command letter because the curve type
    // decides whether they are cubic or linear.
    const path = (await line.getAttribute("d")) ?? "";
    const segments = path.match(/[CLQ]/g) ?? [];
    expect(segments).toHaveLength(body.observations.length - 1);
  });
});
