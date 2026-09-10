import { PlannedPage } from "@/components/app-shell/planned-page";
import { sectionMetadata } from "@/components/app-shell/section-metadata";

export const metadata = sectionMetadata("/goals");

export default function GoalsPage() {
  return <PlannedPage href="/goals" />;
}
