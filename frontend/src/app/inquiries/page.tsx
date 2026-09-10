import { PlannedPage } from "@/components/app-shell/planned-page";
import { sectionMetadata } from "@/components/app-shell/section-metadata";

export const metadata = sectionMetadata("/inquiries");

export default function InquiriesPage() {
  return <PlannedPage href="/inquiries" />;
}
