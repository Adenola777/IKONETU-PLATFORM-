import type { Metadata } from "next";
import { AppShell } from "@/components/app/shell";
import { VentureProfileView } from "@/components/app/venture-profile";
import { requireFounder } from "@/lib/session";
import { loadVentureProfile } from "@/lib/venture-profile";

export const metadata: Metadata = { title: "What investors see", robots: { index: false } };
export const dynamic = "force-dynamic";

/** The founder's own profile, laid out exactly as approved investors see it. */
export default async function PreviewPage() {
  const { supabase, venture } = await requireFounder();
  const p = await loadVentureProfile(supabase, venture.id);
  return (
    <AppShell role="founder" current="preview">
      <p className="status status-info" style={{ marginBottom: 24 }}>
        {venture.published_at
          ? "This is your published profile, as approved investors see it."
          : "This is how your profile will look to approved investors once you publish it. It is hidden now."}{" "}
        Investors also see a button to ask you for an introduction.
      </p>
      {p ? <VentureProfileView p={p} now={new Date()} /> : <p className="status status-err">Your profile could not be loaded. Please reload the page.</p>}
    </AppShell>
  );
}
