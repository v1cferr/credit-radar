import { PlannedPage } from "@/components/app-shell/planned-page";
import { sectionMetadata } from "@/components/app-shell/section-metadata";

export const metadata = sectionMetadata("/financing");

export default function FinancingPage() {
  return <PlannedPage href="/financing" />;
}
