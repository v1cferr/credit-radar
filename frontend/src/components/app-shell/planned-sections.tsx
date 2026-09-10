/**
 * What the product does not do yet, and what each part is waiting on.
 *
 * Derived from the navigation, so this cannot drift from the menu or from
 * the pages themselves, and so a section's blocker is written down once.
 * The overview used to restate two of these by hand, which is how a stale
 * promise survives in a dashboard.
 *
 * Listed rather than hidden. Someone reading their own credit position
 * needs to know what is missing from the picture: a dashboard that shows
 * only its working half implies the half it is not showing is empty.
 */

import Link from "next/link";

import { NAVIGATION } from "@/components/app-shell/navigation";

export function PlannedSections() {
  const groups = NAVIGATION.map((group) => ({
    label: group.label,
    items: group.items.filter((item) => !item.implemented),
  })).filter((group) => group.items.length > 0);

  return (
    <div className="grid gap-x-8 gap-y-5 sm:grid-cols-2">
      {groups.map((group) => (
        <section key={group.label} className="space-y-2.5">
          <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
            {group.label}
          </h3>
          <ul className="space-y-2.5">
            {group.items.map((item) => (
              <li key={item.href} className="flex gap-2.5">
                <item.icon
                  className="mt-0.5 size-4 shrink-0 text-muted-foreground"
                  aria-hidden
                />
                <div className="min-w-0 space-y-0.5">
                  <Link
                    href={item.href}
                    prefetch={false}
                    className="text-sm font-medium underline-offset-4 hover:underline"
                  >
                    {item.title}
                  </Link>
                  <p className="line-clamp-2 text-xs text-muted-foreground">
                    Depende {item.requires}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
