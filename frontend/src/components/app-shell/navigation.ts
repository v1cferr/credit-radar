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
 *
 * Titles and the `requires` text are pt-BR because they reach the screen.
 * Identifiers, hrefs and comments stay en-US.
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
    label: "Resumo",
    items: [
      {
        title: "Visão geral",
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
        requires:
          "um provedor de bureau que informe as negativações ativas",
      },
      {
        title: "Consultas ao CPF",
        href: "/inquiries",
        icon: Activity,
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
        href: "/settlement-offers",
        icon: Handshake,
        implemented: false,
        requires:
          "coleta de propostas em várias plataformas, para que a mesma dívida possa ser comparada entre elas ao longo do tempo",
      },
      {
        title: "Exposição de crédito",
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
        icon: BarChart3,
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

export function findNavItem(href: string): NavItem | undefined {
  return NAVIGATION.flatMap((group) => group.items).find(
    (item) => item.href === href,
  );
}
