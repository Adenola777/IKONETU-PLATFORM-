import type { Metadata } from "next";
import ForInvestorsPage from "@/components/site/pages/investors";
import { pageMetadata } from "@/lib/pages";

export const metadata: Metadata = pageMetadata("investors");

export default function Page() {
  return <ForInvestorsPage />;
}
