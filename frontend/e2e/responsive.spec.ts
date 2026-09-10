/**
 * The interface on a phone.
 *
 * This application is used from a phone as often as from a desk -- looking
 * up whether a rate moved before answering a bank is a standing-in-a-queue
 * activity -- so the small viewport is tested, not assumed.
 *
 * The properties: the sections that hold data are one tap away, the whole
 * map is still reachable, and nothing scrolls sideways. Horizontal overflow
 * is the failure mode of a dense financial layout on a narrow screen, and
 * it is invisible in a desktop run.
 */

import { expect, test } from "@playwright/test";

import { SEEDED } from "./helpers/seeded-data";

/** One route per layout shape: cards, charts, a table, an empty state. */
const ROUTES = ["/", "/market", "/data-sources", "/scores"];

test.describe("phone viewport", () => {
  test("the tab bar offers the sections that hold data", async ({ page }) => {
    await page.goto("/");

    const tabBar = page.getByRole("navigation", {
      name: "Atalhos de navegação",
    });
    await expect(tabBar).toBeVisible();

    await expect(tabBar.getByRole("link", { name: "Resumo" })).toBeVisible();
    await expect(tabBar.getByRole("link", { name: "Mercado" })).toBeVisible();
    await expect(tabBar.getByRole("link", { name: "Fontes" })).toBeVisible();

    // Planned sections are not tabs: a destination that can only report its
    // own absence does not earn a permanent place on a phone screen.
    await expect(tabBar.getByRole("link", { name: /Scores/ })).toHaveCount(0);
  });

  test("a tab goes straight to its section", async ({ page }) => {
    await page.goto("/");

    await page
      .getByRole("navigation", { name: "Atalhos de navegação" })
      .getByRole("link", { name: "Mercado" })
      .click();

    await expect(page.getByRole("heading", { name: "Mercado" })).toBeVisible();
    await expect(
      page.getByText(SEEDED.selicTarget.latestValue),
    ).toBeVisible();
  });

  test("the full menu is reachable from the tab bar", async ({ page }) => {
    await page.goto("/");

    // The sidebar is a drawer here, so the full menu is not on screen until
    // it is asked for. Scoped to the drawer rather than to the page,
    // because the overview links to planned sections in its own content.
    await expect(page.getByRole("dialog")).toHaveCount(0);

    await page.getByRole("button", { name: "Mais" }).click();

    const menu = page.getByRole("dialog");
    await expect(menu).toBeVisible();

    await menu.getByRole("link", { name: /^Scores/ }).click();
    await expect(page.getByRole("heading", { name: "Scores" })).toBeVisible();
  });

  test("the sidebar starts hidden and reopens from the header", async ({
    page,
  }) => {
    await page.goto("/");

    // The navigation starts out of the way; the overview itself must still
    // be readable, because a quick check is the mobile use case.
    await expect(
      page.getByRole("heading", { name: "Visão geral" }),
    ).toBeVisible();
    await expect(page.getByText("Inteligência de crédito pessoal")).toBeHidden();

    await page.getByRole("button", { name: "Alternar menu lateral" }).click();

    await expect(
      page.getByText("Inteligência de crédito pessoal"),
    ).toBeVisible();
  });

  for (const route of ROUTES) {
    test(`${route} does not scroll sideways`, async ({ page }) => {
      await page.goto(route);
      await expect(page.getByRole("heading").first()).toBeVisible();

      const overflow = await page.evaluate(() => {
        const root = document.documentElement;
        return root.scrollWidth - root.clientWidth;
      });

      // One pixel of slack for subpixel rounding of borders.
      expect(overflow).toBeLessThanOrEqual(1);
    });
  }

  test("the tab bar does not cover the end of the content", async ({ page }) => {
    await page.goto("/data-sources");

    const lastRow = page.getByRole("row").last();
    await lastRow.scrollIntoViewIfNeeded();

    const rowBox = await lastRow.boundingBox();
    const tabBox = await page
      .getByRole("navigation", { name: "Atalhos de navegação" })
      .boundingBox();

    expect(rowBox).not.toBeNull();
    expect(tabBox).not.toBeNull();
    // The row must end above where the fixed bar begins.
    expect(rowBox!.y + rowBox!.height).toBeLessThanOrEqual(tabBox!.y + 1);
  });
});
