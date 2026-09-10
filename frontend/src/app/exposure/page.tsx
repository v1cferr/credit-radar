import { PlannedPage } from "@/components/app-shell/planned-page";
import { sectionMetadata } from "@/components/app-shell/section-metadata";

export const metadata = sectionMetadata("/exposure");

export default function ExposurePage() {
  return <PlannedPage href="/exposure" />;
}
