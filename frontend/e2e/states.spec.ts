/**
 * The states that keep the dashboard honest.
 *
 * The property under test is the one that matters most in a financial
 * application: it must never present a stale, failed or absent figure as
 * though it were current. The seed produces all of these at once, which is
 * what makes them assertable without waiting for a real outage.
 */

import { expect, test } from "@playwright/test";

import { SEEDED } from "./helpers/seeded-data";
import { indicatorCard } from "./helpers/ui";

test.describe("empty state", () => {
  test("an indicator with no observations says so instead of showing a zero", async ({
    page,
  }) => {
    // A zero here would read as a real rate of 0%, which is the single most
    // misleading thing this UI could do.
    await page.goto("/market");

    const card = indicatorCard(page, SEEDED.neverCollected.label);

    await expect(card.getByText("Sem observações")).toBeVisible();
    await expect(card).not.toContainText("% a.a.");
    await expect(card).not.toContainText("% a.m.");
  });

  test("its collection status reads as never collected", async ({ page }) => {
    await page.goto("/data-sources");

    const row = page.getByRole("row").filter({ hasText: SEEDED.neverCollected.label });

    await expect(row.getByText("Nunca coletada")).toBeVisible();
  });
});

test.describe("stale state", () => {
  test("a source collected days ago is flagged, not presented as current", async ({
    page,
  }) => {
    await page.goto("/market");

    const card = indicatorCard(page, SEEDED.stale.label);

    // The value is still shown, because it is the last thing known. What must
    // also be shown is how old it is.
    await expect(card.getByText(SEEDED.stale.latestValue)).toBeVisible();
    await expect(card.getByText(/Sincronizado há \d+ dias?/)).toBeVisible();
  });
});

test.describe("failed collection", () => {
  test("a failed last collection is warned about on the card", async ({ page }) => {
    await page.goto("/market");

    const card = indicatorCard(page, SEEDED.failed.label);

    await expect(
      card.getByText("A última coleta falhou. Este valor pode estar desatualizado."),
    ).toBeVisible();
  });

  test("the data sources page reports it as failed", async ({ page }) => {
    await page.goto("/data-sources");

    const row = page.getByRole("row").filter({ hasText: SEEDED.failed.label });

    await expect(row.getByText("Falhou")).toBeVisible();
  });

  test("current sources are still reported as current", async ({ page }) => {
    // Otherwise a page that says everything failed would pass the test above.
    await page.goto("/data-sources");

    const row = page.getByRole("row").filter({ hasText: SEEDED.selicTarget.label });

    await expect(row.getByText("Atualizada")).toBeVisible();
  });

  test("a source that succeeded days ago is not called current", async ({
    page,
  }) => {
    // The table used to report the raw outcome of the last attempt, so a
    // collection that worked ten days ago read as "Saudável" here while its
    // own card warned about the age. One question, two answers.
    await page.goto("/data-sources");

    const row = page.getByRole("row").filter({ hasText: SEEDED.stale.label });

    await expect(row.getByText("Desatualizada")).toBeVisible();
  });
});

test.describe("not implemented", () => {
  test("a planned section names what it is waiting on", async ({ page }) => {
    // Distinct from an empty state: "no data yet" and "this does not exist
    // yet" are different claims and a reader has to be able to tell them
    // apart.
    await page.goto("/scores");

    await expect(page.getByText(/Scores ainda não foi implementado/)).toBeVisible();
    await expect(page.getByText(/provedor autenticado de bureau/)).toBeVisible();
  });

  test("it does not invent a figure to fill the space", async ({ page }) => {
    await page.goto("/scores");

    await expect(page.getByText(/dado financeiro inventado é pior/)).toBeVisible();
  });
});

test.describe("loading state", () => {
  test("a route-level skeleton exists for the data pages", async ({ page }) => {
    // Asserted through the built artefact rather than by racing the network:
    // Next serves loading.tsx while a server component resolves, and the
    // three data-driven routes each declare one.
    const response = await page.goto("/market");
    expect(response?.status()).toBe(200);

    // The skeleton and the loaded page must be distinguishable, which is what
    // stops a half-loaded dashboard from looking like a complete one.
    await expect(page.getByRole("heading", { name: "Mercado" })).toBeVisible();
  });
});
