import type { Metadata } from "next";
import { AppShell } from "@/components/app/shell";
import { dateText } from "@/lib/product";
import { requireFounder } from "@/lib/session";
import { removeUpdate } from "./actions";
import { UpdateForm } from "./form";

export const metadata: Metadata = { title: "Progress updates", robots: { index: false } };
export const dynamic = "force-dynamic";

export default async function UpdatesPage() {
  const { supabase, venture } = await requireFounder();
  const { data } = await supabase
    .from("venture_updates")
    .select("id, body, created_at")
    .eq("venture_id", venture.id)
    .order("created_at", { ascending: false })
    .limit(100);
  const rows = data ?? [];
  return (
    <AppShell role="founder" current="updates">
      <h1 className="app-title">Progress updates</h1>
      <p className="app-lede">
        Updates show investors that you are still building. Your profile shows when you last updated it, and investors can filter
        for founders who updated in the last 30 or 90 days. Updates never rank you against anyone.
      </p>
      <div className="side">
        <section aria-labelledby="past-h" className="stack">
          <h2 id="past-h" className="app-h2">Your updates ({rows.length})</h2>
          {rows.length === 0 ? (
            <div className="empty"><p>You have not posted an update yet.</p></div>
          ) : (
            <ul className="updates">
              {rows.map((u) => (
                <li key={u.id}>
                  <time dateTime={u.created_at}>{dateText(u.created_at)}</time>
                  <p>{u.body}</p>
                  <form action={removeUpdate}>
                    <input type="hidden" name="id" value={u.id} />
                    <button type="submit" className="linkbtn" style={{ fontSize: 14 }}>Remove this update</button>
                  </form>
                </li>
              ))}
            </ul>
          )}
        </section>
        <aside className="card" aria-labelledby="new-h">
          <h2 id="new-h" className="app-h2">Post an update</h2>
          <UpdateForm />
        </aside>
      </div>
    </AppShell>
  );
}
