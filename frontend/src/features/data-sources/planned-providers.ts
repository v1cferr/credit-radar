/**
 * The integration surface, including the sources that are not built yet.
 *
 * Listed so the page reflects the real plan rather than only the part that
 * happens to work today. A reader deciding how much to trust this
 * dashboard needs to know what it is NOT looking at.
 *
 * Three states, not two. "Partial" is the honest description of the SCR
 * reader, which parses a real Registrato report end to end and has nowhere
 * to store the result: calling that implemented would promise a section
 * that does not work, and calling it planned would discard work that is
 * done and tested.
 *
 * Feature data, not routing, so it lives with the feature.
 */

export type ProviderStatus = "implemented" | "partial" | "planned";

export interface PlannedProvider {
  name: string;
  /** Which integration tier this source is reached through. */
  kind: string;
  status: ProviderStatus;
  note: string;
}

export const PROVIDER_STATUS_LABELS: Record<ProviderStatus, string> = {
  implemented: "Em uso",
  partial: "Parcial",
  planned: "Planejada",
};

export const PLANNED_PROVIDERS: PlannedProvider[] = [
  {
    name: "Banco Central — SGS",
    kind: "API pública oficial",
    status: "implemented",
    note: "Séries de mercado e macroeconômicas. Sem autenticação e sem nenhum dado pessoal.",
  },
  {
    name: "Banco Central — SCR / Registrato",
    kind: "Relatório autenticado",
    status: "partial",
    note: "O leitor do relatório já existe e reconhece o histórico mensal completo. Falta persistir a série. O download exige login gov.br, então continuará dependendo de autenticação feita por uma pessoa.",
  },
  {
    name: "Serasa",
    kind: "Conta autenticada",
    status: "planned",
    note: "Score, negativações e propostas de acordo. Escala própria, mantida separada dos outros bureaus.",
  },
  {
    name: "Quod / SPC / Equifax",
    kind: "Conta autenticada",
    status: "planned",
    note: "Metodologias independentes umas das outras. Nunca combinadas em um score único inventado aqui.",
  },
];
