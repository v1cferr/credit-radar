/**
 * What this application says about itself to anything outside it.
 *
 * Titles, descriptions, Open Graph tags, the manifest and the preview
 * image are all quoted verbatim by whatever renders a link: a chat app
 * unfurling a URL, a crawler, an operating system building a home-screen
 * shortcut. None of them is a place for a fact about someone's credit.
 *
 * So this suite reads the head of every page and asserts that no figure
 * appears in it. The seeded values are synthetic, but the shapes are real:
 * if a rate, an amount or a CPF-shaped string can reach a meta tag at all,
 * the real one eventually will.
 */

import { expect, test } from "@playwright/test";

import { SEEDED } from "./helpers/seeded-data";

/** Every route, including the ones that hold real collected data. */
const ROUTES = [
  { path: "/", title: "Visão geral · CreditRadar" },
  { path: "/market", title: "Mercado · CreditRadar" },
  { path: "/data-sources", title: "Fontes de dados · CreditRadar" },
  { path: "/scores", title: "Scores · CreditRadar" },
  { path: "/exposure", title: "Exposição de crédito · CreditRadar" },
];

/** Shapes that must never appear in metadata, whatever the value. */
const FORBIDDEN = [
  { name: "a rate", pattern: /\d+[.,]\d+\s*%/ },
  { name: "a percentage of any kind", pattern: /%\s*a\.[amd]\./ },
  { name: "an amount in reais", pattern: /R\$\s*\d/ },
  { name: "a CPF", pattern: /\d{3}\.\d{3}\.\d{3}-\d{2}/ },
  { name: "a bare eleven-digit number", pattern: /(?<!\d)\d{11}(?!\d)/ },
];

test.describe("metadata", () => {
  for (const route of ROUTES) {
    test(`${route.path} titles itself from its section`, async ({ page }) => {
      await page.goto(route.path);
      await expect(page).toHaveTitle(route.title);
    });

    test(`${route.path} exposes no figure in its head`, async ({ page }) => {
      await page.goto(route.path);

      const head = await page.evaluate(() => {
        const parts: string[] = [document.title];
        for (const meta of document.querySelectorAll("meta")) {
          parts.push(meta.getAttribute("content") ?? "");
        }
        for (const link of document.querySelectorAll("link")) {
          parts.push(link.getAttribute("href") ?? "");
        }
        return parts.join("\n");
      });

      for (const forbidden of FORBIDDEN) {
        expect(
          forbidden.pattern.test(head),
          `${forbidden.name} appears in the head of ${route.path}`,
        ).toBe(false);
      }
    });
  }

  test("the page itself does show the figures", async ({ page }) => {
    // The counterpart to the assertions above: this is not passing because
    // the dashboard has nothing to say, only because it says it in the body.
    await page.goto("/market");
    await expect(
      page.getByText(SEEDED.selicTarget.latestValue).first(),
    ).toBeVisible();
  });

  test("the manifest describes the product only", async ({ request }) => {
    const response = await request.get("/manifest.webmanifest");
    expect(response.ok()).toBe(true);

    const manifest = (await response.json()) as Record<string, unknown>;
    expect(manifest.name).toBe("CreditRadar");
    expect(manifest.lang).toBe("pt-BR");

    const serialized = JSON.stringify(manifest);
    for (const forbidden of FORBIDDEN) {
      expect(forbidden.pattern.test(serialized), forbidden.name).toBe(false);
    }
  });

  test("the preview image is the same for every page", async ({ request }) => {
    // Identical bytes whichever page is shared, which is what proves it was
    // rendered from constants and not from anybody's data.
    const first = await request.get("/opengraph-image");
    expect(first.ok()).toBe(true);
    expect(first.headers()["content-type"]).toContain("image/png");

    const second = await request.get("/opengraph-image");
    expect((await second.body()).equals(await first.body())).toBe(true);
  });

  test("search engines are told to stay away", async ({ page }) => {
    await page.goto("/");

    const robots = await page
      .locator('meta[name="robots"]')
      .getAttribute("content");
    expect(robots).toContain("noindex");
  });
});
