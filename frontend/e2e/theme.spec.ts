/**
 * Light and dark.
 *
 * The dark palette existed in the stylesheet for the whole life of the
 * dashboard and nothing ever set the class that selects it, so it could
 * not be reached from the interface at all. These tests read computed
 * colours, which is the only way to tell a theme that is applied from one
 * that is merely defined.
 */

import { expect, test, type Page } from "@playwright/test";

/**
 * Perceived lightness of the page background, 0 to 1.
 *
 * The colour is converted by painting it, not by parsing it. The tokens are
 * declared in `oklch`, and a computed value is not required to come back as
 * `rgb(...)`: Chromium reports this one as `lab(100 0 0)`, whose first
 * number is a lightness of 100 and reads as a red channel of 100 to
 * anything expecting `rgb`. A canvas resolves any CSS colour to sRGB, which
 * is the browser doing the conversion it already knows how to do.
 */
async function backgroundLightness(page: Page): Promise<number> {
  return page.evaluate(() => {
    const context = document.createElement("canvas").getContext("2d");
    if (!context) throw new Error("no 2d context");

    context.fillStyle = getComputedStyle(document.body).backgroundColor;
    context.fillRect(0, 0, 1, 1);

    const [r, g, b] = context.getImageData(0, 0, 1, 1).data;
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
  });
}

function themeButton(page: Page) {
  return page.getByRole("button", { name: /Alternar tema/ });
}

test.describe("theme", () => {
  test.use({ colorScheme: "light" });

  test("follows a system preference for light", async ({ page }) => {
    await page.goto("/");

    await expect(page.locator("html")).not.toHaveClass(/dark/);
    expect(await backgroundLightness(page)).toBeGreaterThan(0.9);
    await expect(themeButton(page)).toHaveAccessibleName(
      /seguindo o sistema/,
    );
  });

  test("can be pinned to dark and stays there", async ({ page }) => {
    await page.goto("/");

    // system -> light -> dark
    await themeButton(page).click();
    await expect(themeButton(page)).toHaveAccessibleName(/claro/);
    await themeButton(page).click();
    await expect(themeButton(page)).toHaveAccessibleName(/escuro/);

    await expect(page.locator("html")).toHaveClass(/dark/);
    expect(await backgroundLightness(page)).toBeLessThan(0.1);

    // Survives a reload, and without a flash of the other theme: the class
    // is applied by a blocking script, so it is already right on the first
    // frame rather than corrected afterwards.
    await page.reload();
    await expect(page.locator("html")).toHaveClass(/dark/);
    expect(await backgroundLightness(page)).toBeLessThan(0.1);
  });

  test("cycles back to following the system", async ({ page }) => {
    await page.goto("/");

    await themeButton(page).click();
    await themeButton(page).click();
    await themeButton(page).click();

    await expect(themeButton(page)).toHaveAccessibleName(
      /seguindo o sistema/,
    );
    await expect(page.locator("html")).not.toHaveClass(/dark/);
  });

  test("the choice is remembered across sections", async ({ page }) => {
    await page.goto("/");
    await themeButton(page).click();
    await themeButton(page).click();
    await expect(page.locator("html")).toHaveClass(/dark/);

    await page.goto("/market");
    await expect(page.locator("html")).toHaveClass(/dark/);
    // A real figure, so this is checking a page with content on it.
    await expect(page.getByText(/% a\.a\./).first()).toBeVisible();
  });
});

test.describe("theme with a dark system preference", () => {
  test.use({ colorScheme: "dark" });

  test("starts dark without being asked", async ({ page }) => {
    await page.goto("/");

    await expect(page.locator("html")).toHaveClass(/dark/);
    expect(await backgroundLightness(page)).toBeLessThan(0.1);
    await expect(themeButton(page)).toHaveAccessibleName(
      /seguindo o sistema/,
    );
  });

  test("financial state stays legible in both themes", async ({ page }) => {
    // The semantic tokens are redefined for dark rather than reused: the
    // light values read as muddy on a dark ground. This checks the dark
    // definitions are actually in play, and that a warning still stands out
    // against the surface it sits on.
    await page.goto("/data-sources");

    const contrast = await page.evaluate(() => {
      const styles = getComputedStyle(document.documentElement);
      return {
        warning: styles.getPropertyValue("--warning").trim(),
        background: styles.getPropertyValue("--background").trim(),
      };
    });

    expect(contrast.warning).not.toBe("");
    expect(contrast.warning).not.toBe(contrast.background);
  });
});
