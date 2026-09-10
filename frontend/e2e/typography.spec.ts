/**
 * Typography that carries meaning.
 *
 * Both assertions here are regression tests. `font-mono` resolved to an
 * undefined custom property for the whole life of the dashboard, so every
 * monospaced surface silently rendered in the sans face -- the failure is
 * invisible unless something reads the computed style, which is exactly
 * what a browser-driven test can do and a type checker cannot.
 */

import { expect, test, type Locator } from "@playwright/test";

import { SEEDED } from "./helpers/seeded-data";

test.describe("typography", () => {
  test("the document is set in the sans face it loads", async ({ page }) => {
    await page.goto("/");

    // Read through locators, which wait for the element. `querySelector`
    // inside `evaluate` does not, and handed `getComputedStyle` a null.
    const familyOf = (locator: Locator) =>
      locator.evaluate((node) => getComputedStyle(node).fontFamily);

    const families = {
      root: await familyOf(page.locator("html")),
      heading: await familyOf(
        page.getByRole("heading", { level: 1 }).first(),
      ),
      paragraph: await familyOf(page.locator("main p").first()),
    };

    // This application shipped every page in Times New Roman: `font-sans`
    // was applied to <html> while the font loader defined its variable on
    // <body>, so the declaration did not resolve and the document fell
    // back to the browser default. Nothing failed, because no test looked
    // at the face almost every word is set in.
    for (const [where, family] of Object.entries(families)) {
      expect(family, `${where} is set in ${family}`).toMatch(/Geist/);
      expect(family, `${where} fell back to a serif`).not.toMatch(/Times/);
    }
  });

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
