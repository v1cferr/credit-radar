/**
 * Automated accessibility checks.
 *
 * axe against every route, in both themes, at the desktop width and again
 * at a phone width. It cannot judge whether a label is meaningful, but it
 * does catch the failures that are invisible while reading code and easy to
 * introduce while restyling: contrast that falls under the threshold in one
 * theme only, a control whose accessible name is an icon, a landmark
 * structure that leaves content outside every region.
 *
 * Both themes are checked because the semantic tokens are defined twice,
 * and contrast is the first thing to break when a palette is lifted for a
 * dark ground.
 */

import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

/** Every route in the application. */
const ROUTES = [
  "/",
  "/market",
  "/data-sources",
  "/scores",
  "/negative-records",
  "/inquiries",
  "/debts",
  "/settlement-offers",
  "/exposure",
  "/financing",
  "/readiness",
  "/goals",
  "/history",
];

async function analyze(page: Page) {
  return new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
}

/** Rule id and the elements it fired on, which is what a fix needs. */
function describe(results: Awaited<ReturnType<typeof analyze>>): string {
  return results.violations
    .map(
      (violation) =>
        `${violation.id} (${violation.impact}): ${violation.help}\n` +
        violation.nodes.map((node) => `    ${node.target}`).join("\n"),
    )
    .join("\n");
}

test.describe("accessibility", () => {
  for (const route of ROUTES) {
    test(`${route} has no violations`, async ({ page }) => {
      await page.goto(route);
      await expect(page.getByRole("heading").first()).toBeVisible();

      const results = await analyze(page);
      expect(describe(results)).toBe("");
    });
  }

  test.describe("in the dark theme", () => {
    test.use({ colorScheme: "dark" });

    for (const route of ["/", "/market", "/data-sources"]) {
      test(`${route} has no violations`, async ({ page }) => {
        await page.goto(route);
        await expect(page.getByRole("heading").first()).toBeVisible();

        const results = await analyze(page);
        expect(describe(results)).toBe("");
      });
    }
  });

  test.describe("on a phone", () => {
    test.use({ viewport: { width: 390, height: 844 } });

    for (const route of ["/", "/market", "/data-sources"]) {
      test(`${route} has no violations`, async ({ page }) => {
        await page.goto(route);
        await expect(page.getByRole("heading").first()).toBeVisible();

        const results = await analyze(page);
        expect(describe(results)).toBe("");
      });
    }
  });
});
