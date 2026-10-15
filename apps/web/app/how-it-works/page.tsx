import type { Metadata } from "next";
import HowItWorksPage from "@/components/site/pages/how";
import { pageMetadata } from "@/lib/pages";

export const metadata: Metadata = pageMetadata("how");

export default function Page() {
  return <HowItWorksPage />;
}
