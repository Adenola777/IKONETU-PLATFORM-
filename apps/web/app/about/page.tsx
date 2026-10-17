import type { Metadata } from "next";
import { AboutView } from "@/components/site/views/about.view";
import { pageMetadata } from "@/lib/pages";

export const metadata: Metadata = pageMetadata("about");

export default function Page() {
  return <AboutView />;
}
