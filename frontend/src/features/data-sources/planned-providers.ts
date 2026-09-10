/**
 * The integration surface, including the sources that are not built yet.
 *
 * Listed so the page reflects the real plan rather than only the part that
 * happens to work today. A reader deciding whether to trust the dashboard
 * needs to know what it is NOT looking at.
 *
 * Feature data, not routing, so it lives with the feature.
 */

export interface PlannedProvider {
  name: string;
  /** Which integration tier this source is reached through. */
  kind: string;
  implemented: boolean;
  note: string;
}

export const PLANNED_PROVIDERS: PlannedProvider[] = [
  {
    name: "Banco Central — SGS",
    kind: "API pública oficial",
    implemented: true,
    note: "Séries de mercado e macroeconômicas. Sem autenticação e sem dado pessoal.",
  },
  {
    name: "Banco Central — SCR / Registrato",
    kind: "Relatório autenticado",
    implemented: false,
    note: "Exige login gov.br, então vai precisar de autenticação assistida por uma pessoa.",
  },
  {
    name: "Serasa",
    kind: "Conta autenticada",
    implemented: false,
    note: "Score, negativações e propostas. Escala própria, mantida separada dos outros bureaus.",
  },
  {
    name: "Quod / SPC / Equifax",
    kind: "Conta autenticada",
    implemented: false,
    note: "Metodologias independentes. Nunca combinadas em um score único inventado.",
  },
];
