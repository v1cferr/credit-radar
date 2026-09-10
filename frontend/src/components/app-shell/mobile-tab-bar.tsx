"use client";

/**
 * Bottom tab bar, phones only.
 *
 * The sidebar already collapses into a drawer on small screens, but that
 * puts every destination two taps away and offers thirteen items at once
 * when it opens. The tab bar gives one-tap access to the sections that
 * actually hold data and leaves the full map behind "Mais".
 *
 * Shown and hidden with a media query rather than the `useIsMobile` hook:
 * a CSS breakpoint is correct in the server-rendered HTML at every viewport
 * width, while a JavaScript one can only be correct after hydration, which
 * on a phone means the first paint is wrong.
 *
 * Bottom placement is where a thumb reaches, and the safe-area inset keeps
 * the row clear of the home indicator on a notched phone.
 *
 * Prefetching is off for the same reason as in the sidebar: these routes
 * are rendered on demand against the backend, and prefetching them all
 * turns opening one page into rendering every page.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";

import { MOBILE_TAB_ITEMS } from "@/components/app-shell/navigation";
import { useSidebar } from "@/components/ui/sidebar";
import { cn } from "@/lib/utils";

export function MobileTabBar() {
  const pathname = usePathname();
  const { setOpenMobile } = useSidebar();

  return (
    <nav
      aria-label="Atalhos de navegação"
      className="fixed inset-x-0 bottom-0 z-30 border-t bg-background/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-sm md:hidden"
    >
      <ul className="grid auto-cols-fr grid-flow-col">
        {MOBILE_TAB_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                prefetch={false}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "flex min-h-14 flex-col items-center justify-center gap-1 px-1 text-[0.7rem] font-medium transition-colors",
                  isActive
                    ? "text-foreground"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                <item.icon className="size-5 shrink-0" aria-hidden />
                <span className="truncate">
                  {item.shortTitle ?? item.title}
                </span>
              </Link>
            </li>
          );
        })}
        <li>
          <button
            type="button"
            onClick={() => setOpenMobile(true)}
            className="flex min-h-14 w-full flex-col items-center justify-center gap-1 px-1 text-[0.7rem] font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            <Menu className="size-5 shrink-0" aria-hidden />
            <span>Mais</span>
          </button>
        </li>
      </ul>
    </nav>
  );
}
