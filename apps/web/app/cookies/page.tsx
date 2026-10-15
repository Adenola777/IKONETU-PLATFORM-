import type { Metadata } from "next";
import { CookiesView } from "@/components/site/views/cookies.view";
import { pageMetadata } from "@/lib/pages";

export const metadata: Metadata = pageMetadata("cookies");

export default function Page() {
  return <CookiesView />;
}
