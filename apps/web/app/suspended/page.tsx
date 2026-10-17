import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { AppShell } from "@/components/app/shell";
import { homeFor, requireViewer } from "@/lib/session";

export const metadata: Metadata = { title: "Your account is suspended", robots: { index: false } };
export const dynamic = "force-dynamic";

/**
 * Where a suspended founder or staff member lands. Investors have their own
 * page at /investor/pending. The database refuses a suspended account's
 * writes as well, so this page only explains what happened.
 */
export default async function SuspendedPage() {
  const { profile } = await requireViewer();
  if (!profile || profile.role === "investor" || profile.status === "active") redirect(homeFor(profile));
  return (
    <AppShell role="none">
      <div className="app-narrow stack">
        <h1 className="app-title">Your account is suspended</h1>
        <p className="app-lede" style={{ margin: 0 }}>
          An IkonetU admin suspended this account. While it is suspended, investors cannot see your profile, and you cannot change
          it, answer introductions or send messages. If you think this is a mistake, write to{" "}
          <a href="mailto:info@ikonetu.com">info@ikonetu.com</a> from the address you signed in with.
        </p>
      </div>
    </AppShell>
  );
}
