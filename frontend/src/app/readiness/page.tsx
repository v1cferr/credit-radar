import { PlannedPage } from "@/components/app-shell/planned-page";
import { sectionMetadata } from "@/components/app-shell/section-metadata";

export const metadata = sectionMetadata("/readiness");

export default function ReadinessPage() {
  return <PlannedPage href="/readiness" />;
}
