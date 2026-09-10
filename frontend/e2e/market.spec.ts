/**
 * The market dashboard against deterministic seeded data.
 *
 * This is the vertical slice the whole project was built to prove, so these
 * assertions are about the numbers a reader would act on: the value, its
 * unit, the date it refers to, and where it came from.
 */

import { expect, test } from "@playwright/test";

import { SEEDED } from "./helpers/seeded-data";
import { indicatorCard, provenanceTrigger } from "./helpers/ui";

test.describe("movement", () => {
  test("reports the change from the previous value, in percentage points", async ({
    page,
  }) => {
    await page.goto("/market");
    const card = indicatorCard(page, SEEDED.selicTarget.label);

    // Percentage points, not percent: the interval between two annual rates
    // is not itself an annual rate.
    await expect(card.getByText(SEEDED.selicTarget.delta)).toBeVisible();
    await expect(
      card.getByText(SEEDED.selicTarget.previousValue),
    ).toBeVisible();
    await expect(
      card.getByText(SEEDED.selicTarget.previousReferenceDate),
    ).toBeVisible();
  });

  test("skips repeated values to find the last real movement", async ({
    page,
  }) => {
    // The eleven observations after the step all carry the current value.
    // A difference against the previous observation would read as no
    // movement, which for a policy rate is what happens between decisions.
    await page.goto("/market");
    const card = indicatorCard(page, SEEDED.selicTarget.label);

    await expect(card.getByText("0,00 p.p.")).toHaveCount(0);
  });

  test("says what the movement means for a borrower", async ({ page }) => {
    // Colour is not the message. A rise in a financing rate is spelled out
    // for anyone who hears the page rather than sees it.
    await page.goto("/market");
    const card = indicatorCard(page, SEEDED.vehicleRate.label);

    await expect(card.getByText(SEEDED.vehicleRate.delta)).toBeVisible();
    await expect(
      card.getByText(/desfavorável para quem toma crédito/),
    ).toBeAttached();
  });

  test("shows no movement for a series that has only one value", async ({
    page,
  }) => {
    await page.goto("/market");
    const card = indicatorCard(page, SEEDED.mortgageMarket.label);

    await expect(card.getByText(SEEDED.mortgageMarket.latestValue)).toBeVisible();
    await expect(card.getByText(/p\.p\./)).toHaveCount(0);
    await expect(card.getByText(/antes/)).toHaveCount(0);
  });
});

test.describe("market dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/market");
  });

  test("shows the current Selic target with its unit", async ({ page }) => {
    const card = indicatorCard(page, SEEDED.selicTarget.label);

    // The unit is part of the assertion on purpose: "13,25" alone could be a
    // monthly rate, and the difference between 13,25% a.a. and 13,25% a.m.
    // is the difference between a normal loan and a catastrophic one.
    await expect(card.getByText(SEEDED.selicTarget.latestValue)).toBeVisible();
  });

  test("shows which date the value refers to", async ({ page }) => {
    // A rate with no reference date cannot be judged, and this series
    // publishes ahead of the dates it applies to.
    const card = indicatorCard(page, SEEDED.selicTarget.label);

    await expect(
      card.getByText(`Referência ${SEEDED.selicTarget.latestReferenceDate}`),
    ).toBeVisible();
  });

  test("keeps the two mortgage regimes separate", async ({ page }) => {
    // The bug this guards against was real: the regulated series was once
    // labelled as market rates, which is a multi-point error in exactly the
    // comparison the product exists to make.
    await expect(
      indicatorCard(page, SEEDED.mortgageMarket.label).getByText(
        SEEDED.mortgageMarket.latestValue,
      ),
    ).toBeVisible();
    await expect(
      indicatorCard(page, SEEDED.mortgageRegulated.label).getByText(
        SEEDED.mortgageRegulated.latestValue,
      ),
    ).toBeVisible();
  });

  test("exposes where a value came from", async ({ page }) => {
    const card = indicatorCard(page, SEEDED.selicTarget.label);

    await provenanceTrigger(card).click();

    const popover = page.getByText("Origem do dado").locator("..");
    await expect(popover.getByText(SEEDED.selicTarget.series)).toBeVisible();
    await expect(popover.getByText("Banco Central do Brasil — SGS")).toBeVisible();
    await expect(
      popover.getByText(SEEDED.selicTarget.latestReferenceDate),
    ).toBeVisible();
  });

  test("renders the historical chart with plotted points", async ({ page }) => {
    // Structural rather than visual: the assertion is that a line was drawn
    // from more than one point, not where any pixel landed.
    const chart = page.locator(".recharts-wrapper").first();
    await expect(chart).toBeVisible();

    const line = page.locator("path.recharts-curve").first();
    await expect(line).toBeAttached();

    const path = await line.getAttribute("d");
    expect(path).toBeTruthy();

    // Counted as drawing commands rather than by splitting on one letter:
    // the curve type decides whether segments are cubic (C) or linear (L),
    // and the test should not break when that styling choice changes.
    const segments = (path ?? "").match(/[CLQ]/g) ?? [];
    expect(segments.length).toBeGreaterThan(5);
  });

  test("explains that the mortgage series are not interchangeable", async ({ page }) => {
    await expect(
      page.getByText(/Crédito imobiliário são duas séries diferentes/),
    ).toBeVisible();
  });
});

test.describe("overview", () => {
  test("surfaces the headline market rates", async ({ page }) => {
    await page.goto("/");

    await expect(
      indicatorCard(page, SEEDED.selicTarget.label).getByText(
        SEEDED.selicTarget.latestValue,
      ),
    ).toBeVisible();
    await expect(
      indicatorCard(page, SEEDED.vehicleRate.label).getByText(
        SEEDED.vehicleRate.latestValue,
      ),
    ).toBeVisible();
  });

  test("says plainly that personal credit data is not connected", async ({ page }) => {
    // The dashboard must not imply it knows things it does not.
    await page.goto("/");

    await expect(
      page.getByText("Dados pessoais de crédito ainda não conectados"),
    ).toBeVisible();
  });
});
