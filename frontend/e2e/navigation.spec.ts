/**
 * The application shell: it loads, it navigates, and no route crashes.
 *
 * The cheapest thing that would have caught a broken build, and the widest:
 * every route in the product, including the ones whose backend does not
 * exist yet, since those are rendered by real components too.
 */

import { expect, test } from "@playwright/test";

import { navLink } from "./helpers/ui";

const IMPLEMENTED_ROUTES = [
  { path: "/", heading: "Visão geral" },
  { path: "/market", heading: "Mercado" },
  { path: "/data-sources", heading: "Fontes de dados" },
];

const PLANNED_ROUTES = [
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

test.describe("application shell", () => {
  test("loads the overview with the sidebar", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("heading", { name: "Visão geral" })).toBeVisible();
    await expect(page.getByText("Inteligência de crédito pessoal")).toBeVisible();
  });

  test("states the safety invariant on the overview", async ({ page }) => {
    // Not decoration. A dashboard that reads someone's credit position has to
    // say plainly that it never acts, and that claim should not be removable
    // without a test noticing.
    await page.goto("/");

    await expect(
      page.getByText("O CreditRadar nunca age em seu nome"),
    ).toBeVisible();
    await expect(
      page.getByText(/não aceita\s+acordos/),
    ).toBeVisible();
  });

  test("navigates between implemented sections through the sidebar", async ({ page }) => {
    await page.goto("/");

    await navLink(page, "Mercado").click();
    await expect(page.getByRole("heading", { name: "Mercado" })).toBeVisible();

    await navLink(page, "Fontes de dados").click();
    await expect(page.getByRole("heading", { name: "Fontes de dados" })).toBeVisible();

    await navLink(page, "Visão geral").click();
    await expect(page.getByRole("heading", { name: "Visão geral" })).toBeVisible();
  });
});

test.describe("every route renders", () => {
  for (const route of IMPLEMENTED_ROUTES) {
    test(`${route.path} responds and shows its heading`, async ({ page }) => {
      const response = await page.goto(route.path);

      expect(response?.status()).toBe(200);
      await expect(page.getByRole("heading", { name: route.heading })).toBeVisible();
    });
  }

  for (const path of PLANNED_ROUTES) {
    test(`${path} says it is not implemented instead of crashing`, async ({ page }) => {
      const response = await page.goto(path);

      expect(response?.status()).toBe(200);
      await expect(page.getByText(/ainda não foi implementado/)).toBeVisible();
    });
  }
});

test.describe("desktop viewport", () => {
  test("the phone tab bar is not on screen", async ({ page }) => {
    await page.goto("/");

    // The sidebar is permanently visible here, so the tab bar would be a
    // second copy of the same navigation competing with the content.
    await expect(
      page.getByRole("navigation", { name: "Atalhos de navegação" }),
    ).toBeHidden();
    await expect(navLink(page, "Mercado")).toBeVisible();
  });
});
