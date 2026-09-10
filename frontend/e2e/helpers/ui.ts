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

/**
 * The navigation link for a given section.
 *
 * A planned section carries a screen-reader-only "(seção planejada)" in the
 * link, so its accessible name is the title plus that suffix. Matching it
 * as optional keeps the call sites written in terms of the section, and
 * still fails if the title itself changes.
 *
 * `.first()` because a phone viewport also renders the bottom tab bar, and
 * the sections that appear in both are reachable under the same name from
 * either one.
 */
export function navLink(page: Page, name: string): Locator {
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return page
    .getByRole("link", {
      name: new RegExp(`^${escaped}( \\(seção planejada\\))?$`),
    })
    .first();
}
