/**
 * The planned sections and their plans have to be the same set.
 *
 * They live in two modules on purpose -- one is the menu, the other is
 * content -- and nothing in the type system ties a `Record<string, ...>` to
 * a runtime array. Without this test, marking a section as implemented
 * would leave an orphaned plan behind, and adding a planned section would
 * render a page with no plan on it. Both fail silently.
 */

import { describe, expect, it } from "vitest";

import { NAV_ITEMS } from "@/components/app-shell/navigation";
import { SECTION_PLANS } from "@/features/planned/section-plan";

const plannedHrefs = NAV_ITEMS.filter((item) => !item.implemented).map(
  (item) => item.href,
);

describe("section plans", () => {
  it("covers every planned section", () => {
    const missing = plannedHrefs.filter((href) => !(href in SECTION_PLANS));
    expect(missing).toEqual([]);
  });

  it("has no plan for a section that is not planned", () => {
    const orphaned = Object.keys(SECTION_PLANS).filter(
      (href) => !plannedHrefs.includes(href),
    );
    expect(orphaned).toEqual([]);
  });

  it("says something concrete about each one", () => {
    for (const [href, plan] of Object.entries(SECTION_PLANS)) {
      expect(plan.shows.length, `${href} lists nothing it will show`).toBeGreaterThan(
        1,
      );
      expect(plan.invariant.length, `${href} states no invariant`).toBeGreaterThan(
        40,
      );
    }
  });

  it("states no figure, so nothing reads as a fact about a credit position", () => {
    // A number on one of these pages would be read as real, whatever label
    // sits beside it. The only digits allowed are inside a name.
    const forbidden = /\d+[.,]\d+|R\$|\d+\s*%/;
    for (const [href, plan] of Object.entries(SECTION_PLANS)) {
      for (const line of [...plan.shows, plan.invariant]) {
        expect(forbidden.test(line), `${href}: "${line}"`).toBe(false);
      }
    }
  });
});
