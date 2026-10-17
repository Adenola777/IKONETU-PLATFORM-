import type { Metadata } from "next";
import ForFoundersPage from "@/components/site/pages/founders";
import { pageMetadata } from "@/lib/pages";

export const metadata: Metadata = pageMetadata("founders");

export default function Page() {
  return <ForFoundersPage />;
}
