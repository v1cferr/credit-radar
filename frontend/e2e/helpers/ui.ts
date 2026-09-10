/** Locators expressed in terms of what a reader sees. */

import type { Locator, Page } from "@playwright/test";

/**
 * The card for one indicator, found by the name shown on it.
 *
 * Scoped this way rather than by a test id or a CSS path so the test breaks
 * when the user-visible label changes, which is a real change, and survives
 * a restyling, which is not.
 */
export function indicatorCard(page: Page, label: string): Locator {
  return page.locator('[data-slot="card"]').filter({ hasText: label }).first();
}

/** The provenance disclosure inside a card. */
export function provenanceTrigger(card: Locator): Locator {
  return card.getByRole("button", { name: "Ver a origem deste valor" });
}

/** The sidebar navigation link with a given name. */
export function navLink(page: Page, name: string): Locator {
  return page.getByRole("link", { name, exact: true });
}
