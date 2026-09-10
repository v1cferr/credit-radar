import { PlannedPage } from "@/components/app-shell/planned-page";
import { sectionMetadata } from "@/components/app-shell/section-metadata";

export const metadata = sectionMetadata("/settlement-offers");

export default function SettlementOffersPage() {
  return <PlannedPage href="/settlement-offers" />;
}
