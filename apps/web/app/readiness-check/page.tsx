import type { Metadata } from "next";
import ReadinessCheckPage from "@/components/site/pages/readiness";
import { pageMetadata } from "@/lib/pages";

export const metadata: Metadata = pageMetadata("readiness");

export default function Page() {
  return <ReadinessCheckPage />;
}
