import type { Metadata } from "next";
import { QuestionsView } from "@/components/site/views/questions.view";
import { pageMetadata } from "@/lib/pages";

export const metadata: Metadata = pageMetadata("questions");

export default function Page() {
  return <QuestionsView />;
}
