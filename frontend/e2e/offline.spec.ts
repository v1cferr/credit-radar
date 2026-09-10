/**
 * What the dashboard does when the backend is not there.
 *
 * Runs against a second frontend instance whose backend address points at a
 * port nothing listens on. That indirection exists because the pages fetch
 * server-side: a browser-level route intercept cannot simulate this, so the
 * only way to exercise the real failure path is to actually fail it.
 *
 * The property: an unreachable backend must produce a visible, honest error,
 * never a blank panel and never a default figure.
 */

import { expect, test } from "@playwright/test";

test.describe("backend unavailable", () => {
  test("the overview says the backend could not be reached", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByText("Backend indisponível")).toBeVisible();
  });

  test("the page still renders instead of crashing", async ({ page }) => {
    const response = await page.goto("/");

    expect(response?.status()).toBe(200);
    await expect(page.getByRole("heading", { name: "Visão geral" })).toBeVisible();
  });

  test("the market page reports the failure too", async ({ page }) => {
    await page.goto("/market");

    await expect(page.getByRole("heading", { name: "Mercado" })).toBeVisible();
    await expect(page.getByText("Backend indisponível")).toBeVisible();
  });

  test("no financial figure is displayed while the backend is down", async ({ page }) => {
    // The point of the whole exercise. A cached or defaulted rate shown
    // during an outage is worse than an error, because it looks like data.
    await page.goto("/market");

    await expect(page.getByText(/% a\.a\./)).toHaveCount(0);
    await expect(page.getByText(/% a\.m\./)).toHaveCount(0);
  });

  test("the error explains how to start the backend", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByText(/uvicorn credit_radar\.api\.app:app/)).toBeVisible();
  });

  test("navigation still works during an outage", async ({ page }) => {
    await page.goto("/");

    await page.getByRole("link", { name: "Scores", exact: true }).click();

    // A planned section does not depend on the backend, so it must still
    // render normally.
    await expect(page.getByText(/ainda não foi implementado/)).toBeVisible();
  });
});
