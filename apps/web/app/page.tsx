import type { Metadata } from "next";
import HomePage from "@/components/site/pages/home";
import { pageMetadata } from "@/lib/pages";

export const metadata: Metadata = pageMetadata("home");

export default function Page() {
  return <HomePage />;
}
