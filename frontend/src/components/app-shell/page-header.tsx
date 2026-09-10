/**
 * The bar at the top of every page.
 *
 * Sticky, because the pages below it are long and scrolling through a table
 * of monthly figures should never leave the reader unsure which section
 * they are reading.
 *
 * The description is desktop-only. On a phone the vertical space it costs
 * is better spent on the content, which carries its own context; a
 * description truncated to fit is worse than one that is not there.
 */

import { SidebarTrigger } from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  /** Controls that belong to the page as a whole, e.g. a range selector. */
  actions?: React.ReactNode;
}) {
  return (
    <header className="sticky top-0 z-20 flex min-h-14 shrink-0 items-center gap-2 border-b bg-background/80 px-4 py-2.5 backdrop-blur-sm">
      <SidebarTrigger className="-ml-1" />
      <Separator orientation="vertical" className="mr-1 h-5" />
      <div className="min-w-0 flex-1">
        <h1 className="truncate text-base font-semibold tracking-tight">
          {title}
        </h1>
        {description ? (
          <p className="hidden truncate text-xs text-muted-foreground sm:block">
            {description}
          </p>
        ) : null}
      </div>
      {actions ? (
        <div className="flex shrink-0 items-center gap-2">{actions}</div>
      ) : null}
    </header>
  );
}
