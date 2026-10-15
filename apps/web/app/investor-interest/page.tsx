import type { Metadata } from "next";
import InvestorInterestPage from "@/components/site/pages/interest";
import { pageMetadata } from "@/lib/pages";

export const metadata: Metadata = pageMetadata("interest");

export default function Page() {
  return <InvestorInterestPage />;
}
