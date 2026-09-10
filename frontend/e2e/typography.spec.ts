/**
 * Typography that carries meaning.
 *
 * Both assertions here are regression tests. `font-mono` resolved to an
 * undefined custom property for the whole life of the dashboard, so every
 * monospaced surface silently rendered in the sans face -- the failure is
 * invisible unless something reads the computed style, which is exactly
 * what a browser-driven test can do and a type checker cannot.
 */

import { expect, test } from "@playwright/test";

import { SEEDED } from "./helpers/seeded-data";

test.describe("typography", () => {
  test("source references are set in a monospaced face", async ({ page }) => {
    await page.goto("/data-sources");

    // The reference is rendered twice, once for each breakpoint: on a
    // phone it folds under the indicator name so provenance does not
    // disappear behind a sideways scroll. Only one of the two is ever
    // displayed, so the visible one is the one to measure.
    const reference = page
      .getByText(SEEDED.selicTarget.series, { exact: true })
      .filter({ visible: true })
      .first();
    await expect(reference).toBeVisible();

    const family = await reference.evaluate(
      (node) => getComputedStyle(node).fontFamily,
    );

    // Identifiers like "bcdata.sgs.432" are read character by character and
    // compared against a provider's catalog, which is what a monospaced face
    // is for.
    expect(family).toMatch(/mono/i);
  });

  test("figures meant to be compared use tabular numerals", async ({ page }) => {
    await page.goto("/market");

    const value = page.getByText(SEEDED.selicTarget.latestValue).first();
    await expect(value).toBeVisible();

    const variant = await value.evaluate(
      (node) => getComputedStyle(node).fontVariantNumeric,
    );

    // Proportional digits make a value shift sideways as it changes and stop
    // a column of amounts from lining up.
    expect(variant).toContain("tabular-nums");
  });
});
