/**
 * Page metadata derived from the navigation.
 *
 * One source of truth for a section's name. A page that restated its own
 * title would eventually disagree with the menu that links to it, and the
 * browser tab is exactly where nobody notices.
 *
 * Only the section name reaches metadata. Nothing here reads a figure, a
 * balance, a score or a date of collection: a title, a description, an Open
 * Graph tag and a manifest are all quoted verbatim by whatever renders a
 * link preview, and none of them is a place for a fact about someone's
 * credit. The rule is structural rather than a habit -- these functions
 * have no access to observations at all.
 */

import type { Metadata } from "next";

import { findNavItem } from "@/components/app-shell/navigation";

/** Product name as it trails every section title. */
const PRODUCT = "CreditRadar";

/** Declared here so the layout and the overview cannot disagree on it. */
export const TITLE_TEMPLATE = `%s \u00b7 ${PRODUCT}`;

export function sectionMetadata(href: string): Metadata {
  const item = findNavItem(href);
  if (!item) return {};

  // A layout's title template applies to child segments only, and the
  // overview lives in the same segment as the root layout. Left to the
  // template it would render as "Visão geral" alone, dropping the product
  // name from the browser tab and from an installed home-screen shortcut,
  // so it composes the same string itself.
  return href === "/"
    ? { title: { absolute: TITLE_TEMPLATE.replace("%s", item.title) } }
    : { title: item.title };
}
