/**
 * A section that exists in the architecture but has no backend module yet.
 *
 * Driven by the navigation metadata so the page and the sidebar cannot drift
 * apart, and so each one states specifically what it is waiting on rather
 * than showing a generic "coming soon".
 */

import { notFound } from "next/navigation";

import { PageHeader } from "@/components/app-shell/page-header";
import { findNavItem } from "@/components/app-shell/navigation";
import { NotImplementedState } from "@/components/common/state-messages";

export function PlannedPage({ href }: { href: string }) {
  const item = findNavItem(href);
  if (!item) notFound();

  return (
    <>
      <PageHeader title={item.title} description="Seção planejada" />
      <div className="p-4 md:p-6">
        <NotImplementedState
          feature={item.title}
          requires={item.requires ?? "further backend work"}
        />
      </div>
    </>
  );
}
