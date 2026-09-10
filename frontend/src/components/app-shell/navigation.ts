/**
 * Information architecture.
 *
 * Grouped by the question each area answers rather than by data source,
 * because the point of this application is that one question is usually
 * answered by several sources at once.
 *
 * `implemented` is honest metadata: the navigation shows the whole intended
 * product, and marks what does not exist yet instead of hiding it or
 * pretending it works.
 */

import {
  Activity,
  BarChart3,
  Calculator,
  CircleDollarSign,
  Database,
  FileWarning,
  Gauge,
  Handshake,
  History,
  LayoutDashboard,
  Landmark,
  Target,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  title: string;
  href: string;
  icon: LucideIcon;
  implemented: boolean;
  /** What has to exist before this section can show real data. */
  requires?: string;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const NAVIGATION: NavGroup[] = [
  {
    label: "Summary",
    items: [
      {
        title: "Overview",
        href: "/",
        icon: LayoutDashboard,
        implemented: true,
      },
    ],
  },
  {
    label: "Credit profile",
    items: [
      {
        title: "Scores",
        href: "/scores",
        icon: BarChart3,
        implemented: false,
        requires:
          "an authenticated bureau provider (Serasa, Quod, SPC or Equifax), each keeping its own scale and history",
      },
      {
        title: "Negative records",
        href: "/negative-records",
        icon: FileWarning,
        implemented: false,
        requires: "a bureau provider that reports active negative records",
      },
      {
        title: "Credit inquiries",
        href: "/inquiries",
        icon: Activity,
        implemented: false,
        requires: "a bureau provider that reports CPF inquiries",
      },
    ],
  },
  {
    label: "Obligations",
    items: [
      {
        title: "Debts",
        href: "/debts",
        icon: CircleDollarSign,
        implemented: false,
        requires:
          "debt discovery across bureaus, creditors and negotiation platforms, with creditor and contract normalization",
      },
      {
        title: "Settlement offers",
        href: "/settlement-offers",
        icon: Handshake,
        implemented: false,
        requires:
          "offer collection from several platforms, so the same debt can be compared across them over time",
      },
      {
        title: "Credit exposure",
        href: "/exposure",
        icon: Landmark,
        implemented: false,
        requires: "the Banco Central SCR / Registrato provider",
      },
    ],
  },
  {
    label: "Decisions",
    items: [
      {
        title: "Market",
        href: "/market",
        icon: BarChart3,
        implemented: true,
      },
      {
        title: "Financing",
        href: "/financing",
        icon: Calculator,
        implemented: false,
        requires:
          "the amortization engines (SAC and Price) and CET calculation, to compare an offer against market rates",
      },
      {
        title: "Readiness",
        href: "/readiness",
        icon: Gauge,
        implemented: false,
        requires:
          "score, debt, exposure and income data, since a readiness indicator built on any one of them alone would be misleading",
      },
      {
        title: "Goals",
        href: "/goals",
        icon: Target,
        implemented: false,
        requires: "financial goal modelling",
      },
    ],
  },
  {
    label: "Audit",
    items: [
      {
        title: "Data sources",
        href: "/data-sources",
        icon: Database,
        implemented: true,
      },
      {
        title: "History",
        href: "/history",
        icon: History,
        implemented: false,
        requires: "a credit event timeline across the collected series",
      },
    ],
  },
];

export function findNavItem(href: string): NavItem | undefined {
  return NAVIGATION.flatMap((group) => group.items).find(
    (item) => item.href === href,
  );
}
