/**
 * What each planned section will contain, and the rule it must not break.
 *
 * A planned page used to show one dashed box saying the section did not
 * exist yet. That is honest but not useful: it tells the reader nothing
 * about what the section is for, and nothing about the distinctions it will
 * have to preserve when it is built.
 *
 * So each section states what it will show and the invariant behind it.
 * These are not aspirations, they are the domain rules this repository
 * already commits to -- that bureaus are never merged into one score, that
 * a credit limit is not a debt, that a readiness figure is a CreditRadar
 * heuristic and not a bank's approval model. Writing them on the page keeps
 * them in front of whoever builds the section, and in front of the reader
 * deciding how much to trust it when it arrives.
 *
 * What is deliberately absent is numbers. No placeholder score, no example
 * balance, no plausible-looking chart. A figure on a page about someone's
 * credit is read as a fact about their credit, whatever label sits next to
 * it.
 *
 * Copy is pt-BR; identifiers and comments are en-US.
 */

export interface SectionPlan {
  /** What the section will show, once it has data. */
  shows: string[];
  /** The distinction the section must preserve, in one sentence. */
  invariant: string;
}

export const SECTION_PLANS: Record<string, SectionPlan> = {
  "/scores": {
    shows: [
      "Um painel por bureau, cada um com a escala que ele próprio publica",
      "A faixa declarada pelo bureau, e não uma faixa inventada aqui",
      "O histórico de cada score e o que mudou entre duas leituras",
    ],
    invariant:
      "Serasa, Quod, SPC e Equifax usam metodologias e escalas diferentes. Nunca serão combinados em um score único: a média de dois números incomparáveis não é informação.",
  },
  "/negative-records": {
    shows: [
      "Cada negativação com credor, valor, data de inclusão e origem",
      "Qual bureau reporta cada uma, já que não reportam as mesmas",
      "Quando cada registro sai, e o que já saiu",
    ],
    invariant:
      "Uma negativação não é uma dívida. A dívida pode existir sem negativação, e o registro pode permanecer por algum tempo depois do pagamento.",
  },
  "/inquiries": {
    shows: [
      "Quem consultou o CPF, quando, e por qual bureau",
      "O volume de consultas ao longo do tempo",
    ],
    invariant:
      "Uma consulta não é um pedido de crédito aprovado nem negado. É o registro de que alguém olhou.",
  },
  "/debts": {
    shows: [
      "Cada dívida por credor e contrato, com saldo, encargos e situação",
      "A mesma dívida vista por fontes diferentes, sem contar duas vezes",
      "O que é cobrança ativa e o que é registro histórico",
    ],
    invariant:
      "Dívida, negativação e proposta de acordo são três coisas distintas. Normalizar credor e contrato é o que impede a mesma dívida de aparecer duplicada.",
  },
  "/settlement-offers": {
    shows: [
      "As propostas de cada plataforma para a mesma dívida",
      "Como as condições mudaram ao longo do tempo",
      "O desconto real sobre o saldo, e não o desconto anunciado",
    ],
    invariant:
      "O CreditRadar nunca aceita um acordo nem gera um pagamento. Ele compara condições; quem fecha é você, fora deste sistema.",
  },
  "/exposure": {
    shows: [
      "O total mensal registrado no SCR do Banco Central",
      "Em dia, vencida, a liberar, coobrigações e limites, separados",
      "A exposição por instituição e por modalidade",
    ],
    invariant:
      "Limite de crédito e crédito a liberar não são dívida. Somá-los ao saldo devedor inflaria a exposição, que é o número usado para decidir se dá para tomar mais crédito.",
  },
  "/financing": {
    shows: [
      "A mesma proposta em SAC e em Price, com o total pago em cada",
      "O CET, e não só a taxa nominal anunciada",
      "A proposta comparada com as taxas de mercado já coletadas",
    ],
    invariant:
      "Uma simulação não é uma oferta, e “consigo crédito?” não é a mesma pergunta que “vale a pena?”. O sistema não solicita nem contrata financiamento.",
  },
  "/readiness": {
    shows: [
      "Indicadores construídos a partir de score, dívidas, exposição e renda",
      "O que pesa mais contra, hoje, e o que mudaria se fosse resolvido",
    ],
    invariant:
      "Qualquer indicador de prontidão aqui é uma heurística do CreditRadar. Nunca é uma previsão do modelo de aprovação de um banco ou de um bureau, que são proprietários e não públicos.",
  },
  "/goals": {
    shows: [
      "Objetivos com prazo e valor, ligados ao que o crédito exige deles",
      "O que precisaria mudar na posição atual para alcançá-los",
    ],
    invariant:
      "Objetivos não movem dinheiro. O sistema não faz aportes, pagamentos nem transferências: ele só torna explícito o que precisaria mudar.",
  },
  "/history": {
    shows: [
      "A linha do tempo dos eventos de crédito já coletados",
      "Quando cada valor mudou, e o que a fonte dizia antes",
      "As tentativas de coleta que falharam, para que uma lacuna tenha explicação",
    ],
    invariant:
      "Nada é sobrescrito. Uma correção da fonte entra como revisão nova ao lado da anterior, porque saber que um número foi corrigido é parte do histórico.",
  },
};
