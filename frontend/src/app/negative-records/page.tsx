import { PlannedPage } from "@/components/app-shell/planned-page";
import { sectionMetadata } from "@/components/app-shell/section-metadata";

export const metadata = sectionMetadata("/negative-records");

export default function NegativeRecordsPage() {
  return <PlannedPage href="/negative-records" />;
}
