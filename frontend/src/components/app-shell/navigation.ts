/**
 * Information architecture.
 *
 * Grouped by the question each area answers rather than by data source,
 * because the point of this application is that one question is usually
 * answered by several sources at once. "Do I have a debt problem?" is
 * answered by a bureau, a creditor and the Banco Central SCR together, and
 * a menu organized by provider would scatter that answer across three
 * places.
 *
 * The groups are ordered the way the questions arrive: what is true now,
 * who I am to the market, what I owe, what I should do about it, and
 * whether any of it can be trusted.
 *
 * `implemented` is honest metadata. The navigation shows the whole intended
 * product and marks what does not exist yet, rather than hiding it or
 * pretending it works. It is a discriminated union: a planned section
 * cannot be declared without saying what it is waiting on, because "coming
 * soon" is not information and a section that has forgotten its own
 * blocker is how a placeholder quietly becomes permanent.
 *
 * Titles, `shortTitle` and `requires` are pt-BR because they reach the
 * screen. Identifiers, hrefs and comments stay en-US.
 */

import {
  BarChart3,
  Calculator,
  CircleDollarSign,
  Database,
  FileWarning,
  Gauge,
  Handshake,
  History,
  Landmark,
  LayoutDashboard,
  LineChart,
  Search,
  Target,
  type LucideIcon,
} from "lucide-react";

interface NavItemBase {
  title: string;
  /** Title for the mobile tab bar, where the full one does not fit. */
  shortTitle?: string;
  href: string;
  icon: LucideIcon;
}

export type NavItem = NavItemBase &
  (
    | { implemented: true }
    /** What has to exist before this section can show real data. */
    | { implemented: false; requires: string }
  );

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const NAVIGATION: NavGroup[] = [
  {
    label: "Resumo",
    items: [
      {
        title: "Visão geral",
        shortTitle: "Resumo",
        href: "/",
        icon: LayoutDashboard,
        implemented: true,
      },
    ],
  },
  {
    label: "Perfil de crédito",
    items: [
      {
        title: "Scores",
        href: "/scores",
        icon: BarChart3,
        implemented: false,
        requires:
          "um provedor autenticado de bureau (Serasa, Quod, SPC ou Equifax), cada um mantendo sua própria escala e seu próprio histórico",
      },
      {
        title: "Negativações",
        href: "/negative-records",
        icon: FileWarning,
        implemented: false,
        requires: "um provedor de bureau que informe as negativações ativas",
      },
      {
        title: "Consultas ao CPF",
        shortTitle: "Consultas",
        href: "/inquiries",
        icon: Search,
        implemented: false,
        requires: "um provedor de bureau que informe as consultas ao CPF",
      },
    ],
  },
  {
    label: "Obrigações",
    items: [
      {
        title: "Dívidas",
        href: "/debts",
        icon: CircleDollarSign,
        implemented: false,
        requires:
          "descoberta de dívidas em bureaus, credores e plataformas de negociação, com normalização de credor e contrato",
      },
      {
        title: "Propostas de acordo",
        shortTitle: "Acordos",
        href: "/settlement-offers",
        icon: Handshake,
        implemented: false,
        requires:
          "coleta de propostas em várias plataformas, para que a mesma dívida possa ser comparada entre elas ao longo do tempo",
      },
      {
        title: "Exposição de crédito",
        shortTitle: "Exposição",
        href: "/exposure",
        icon: Landmark,
        implemented: false,
        requires: "o provedor do SCR / Registrato do Banco Central",
      },
    ],
  },
  {
    label: "Decisões",
    items: [
      {
        title: "Mercado",
        href: "/market",
        icon: LineChart,
        implemented: true,
      },
      {
        title: "Financiamento",
        href: "/financing",
        icon: Calculator,
        implemented: false,
        requires:
          "os motores de amortização (SAC e Price) e o cálculo do CET, para comparar uma proposta com as taxas de mercado",
      },
      {
        title: "Prontidão",
        href: "/readiness",
        icon: Gauge,
        implemented: false,
        requires:
          "dados de score, dívidas, exposição e renda, já que um indicador de prontidão construído sobre qualquer um deles isolado seria enganoso",
      },
      {
        title: "Objetivos",
        href: "/goals",
        icon: Target,
        implemented: false,
        requires: "a modelagem de objetivos financeiros",
      },
    ],
  },
  {
    label: "Auditoria",
    items: [
      {
        title: "Fontes de dados",
        shortTitle: "Fontes",
        href: "/data-sources",
        icon: Database,
        implemented: true,
      },
      {
        title: "Histórico",
        href: "/history",
        icon: History,
        implemented: false,
        requires:
          "uma linha do tempo de eventos de crédito sobre as séries coletadas",
      },
    ],
  },
];

/** Every item, flattened, in the order the groups declare them. */
export const NAV_ITEMS: NavItem[] = NAVIGATION.flatMap((group) => group.items);

/**
 * The sections the mobile tab bar offers directly.
 *
 * Only what actually shows data. A tab bar is for the destinations reached
 * most often, and a section that can only report its own absence is not
 * one of them -- it stays one tap away in the full menu.
 */
export const MOBILE_TAB_ITEMS: NavItem[] = NAV_ITEMS.filter(
  (item) => item.implemented,
);

export function findNavItem(href: string): NavItem | undefined {
  return NAV_ITEMS.find((item) => item.href === href);
}
