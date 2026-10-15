import type { Metadata } from "next";
import { TrustView } from "@/components/site/views/trust.view";
import { pageMetadata } from "@/lib/pages";

export const metadata: Metadata = pageMetadata("trust");

export default function Page() {
  return <TrustView />;
}
