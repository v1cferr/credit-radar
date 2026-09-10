import { PlannedPage } from "@/components/app-shell/planned-page";
import { sectionMetadata } from "@/components/app-shell/section-metadata";

export const metadata = sectionMetadata("/scores");

export default function ScoresPage() {
  return <PlannedPage href="/scores" />;
}
