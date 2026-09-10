import { Skeleton } from "@/components/ui/skeleton";

/** Placeholder shown while backend data is in flight.
 *
 * Deliberately shaped like the content it replaces, and deliberately
 * distinct from the "no data" and "not implemented" states: a reader must
 * be able to tell "still loading" from "there is nothing here". */
export function DashboardSkeleton({ cards = 3 }: { cards?: number }) {
  return (
    <div className="flex flex-col gap-6 p-4 md:p-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: cards }).map((_, index) => (
          <div key={index} className="space-y-3 rounded-xl border p-6">
            <Skeleton className="h-3 w-32" />
            <Skeleton className="h-7 w-24" />
            <Skeleton className="h-3 w-40" />
          </div>
        ))}
      </div>
      <div className="space-y-3 rounded-xl border p-6">
        <Skeleton className="h-3 w-48" />
        <Skeleton className="h-[280px] w-full" />
      </div>
    </div>
  );
}
