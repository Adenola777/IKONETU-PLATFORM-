import type { Metadata } from "next";
import { PrivacyView } from "@/components/site/views/privacy.view";
import { pageMetadata } from "@/lib/pages";

export const metadata: Metadata = pageMetadata("privacy");

export default function Page() {
  return <PrivacyView />;
}
