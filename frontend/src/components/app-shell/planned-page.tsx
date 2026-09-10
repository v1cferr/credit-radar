/**
 * A section that exists in the architecture but has no backend module yet.
 *
 * Driven by the navigation metadata and the section plan, so the page, the
 * sidebar and the overview cannot drift apart, and so each section states
 * specifically what it is waiting on rather than showing a generic "coming
 * soon".
 *
 * Three things, in the order they are useful: what the section will show,
 * the distinction it must preserve when it is built, and what has to exist
 * first. No figures, no placeholder chart, no greyed-out numbers -- a
 * figure on a page about someone's credit is read as a fact about their
 * credit, whatever label sits next to it, and a skeleton where data will go
 * is indistinguishable from data that failed to load.
 *
 * A route that reaches here for a section already implemented is a bug in
 * the routing, not a page to render, so it 404s rather than telling the
 * reader that a working section is unavailable.
 */

import { notFound } from "next/navigation";
import { Check, Construction, ShieldAlert } from "lucide-react";

import { PageHeader } from "@/components/app-shell/page-header";
import { findNavItem } from "@/components/app-shell/navigation";
import { SECTION_PLANS } from "@/features/planned/section-plan";

export function PlannedPage({ href }: { href: string }) {
  const item = findNavItem(href);
  if (!item || item.implemented) notFound();

  const plan = SECTION_PLANS[href];

  return (
    <>
      <PageHeader title={item.title} description="Seção planejada" />

      <div className="flex max-w-3xl flex-col gap-5 p-4 md:p-6">
        <div className="flex items-start gap-3 rounded-lg border border-dashed p-4">
          <Construction
            className="mt-0.5 size-4 shrink-0 text-muted-foreground"
            aria-hidden
          />
          <div className="space-y-1">
            <p className="text-sm font-medium">
              {item.title} ainda não foi implementado
            </p>
            <p className="text-xs text-muted-foreground">
              Faz parte da arquitetura planejada, mas ainda não tem módulo no
              backend. Depende {item.requires}. Nada é exibido aqui em vez
              de números de exemplo, porque dado financeiro inventado é pior
              do que dado nenhum.
            </p>
          </div>
        </div>

        {plan ? (
          <>
            <section className="space-y-2.5">
              <h2 className="text-sm font-semibold">
                O que esta seção vai mostrar
              </h2>
              <ul className="space-y-1.5">
                {plan.shows.map((entry) => (
                  <li key={entry} className="flex gap-2 text-sm">
                    <Check
                      className="mt-0.5 size-3.5 shrink-0 text-muted-foreground"
                      aria-hidden
                    />
                    <span className="text-muted-foreground">{entry}</span>
                  </li>
                ))}
              </ul>
            </section>

            <section className="flex items-start gap-3 rounded-lg border bg-card p-4">
              <ShieldAlert
                className="mt-0.5 size-4 shrink-0 text-informational"
                aria-hidden
              />
              <div className="space-y-1">
                <h2 className="text-sm font-semibold">
                  A regra que esta seção não pode quebrar
                </h2>
                <p className="text-xs text-muted-foreground">
                  {plan.invariant}
                </p>
              </div>
            </section>
          </>
        ) : null}
      </div>
    </>
  );
}
