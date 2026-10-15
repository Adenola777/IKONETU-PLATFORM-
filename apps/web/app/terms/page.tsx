import type { Metadata } from "next";
import { TermsView } from "@/components/site/views/terms.view";
import { pageMetadata } from "@/lib/pages";

export const metadata: Metadata = pageMetadata("terms");

export default function Page() {
  return <TermsView />;
}
