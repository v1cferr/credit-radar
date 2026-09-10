import { PlannedPage } from "@/components/app-shell/planned-page";
import { sectionMetadata } from "@/components/app-shell/section-metadata";

export const metadata = sectionMetadata("/history");

export default function HistoryPage() {
  return <PlannedPage href="/history" />;
}
