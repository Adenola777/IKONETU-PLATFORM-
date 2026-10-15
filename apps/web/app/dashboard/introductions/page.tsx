import type { Metadata } from "next";
import Link from "next/link";
import { answerIntroduction } from "@/app/introductions/actions";
import { AppShell } from "@/components/app/shell";
import { dateText, INVESTOR_TYPE_NAME } from "@/lib/product";
import { requireFounder } from "@/lib/session";

export const metadata: Metadata = { title: "Introductions", robots: { index: false } };
export const dynamic = "force-dynamic";

type Intro = {
  id: string; note: string; status: "pending" | "accepted" | "declined" | "withdrawn";
  investor_name: string; investor_type: string; investor_firm: string | null; created_at: string; decided_at: string | null;
};

export default async function FounderIntroductionsPage() {
  const { supabase, user } = await requireFounder();
  const { data } = await supabase
    .from("introductions")
    .select("id, note, status, investor_name, investor_type, investor_firm, created_at, decided_at")
    .eq("founder_id", user.id)
    .order("created_at", { ascending: false })
    .limit(200);
  const rows = (data ?? []) as Intro[];
  const pending = rows.filter((r) => r.status === "pending");
  const open = rows.filter((r) => r.status === "accepted");
  const closed = rows.filter((r) => r.status === "declined" || r.status === "withdrawn");
  const line = (r: Intro) => `${INVESTOR_TYPE_NAME[r.investor_type] ?? r.investor_type}${r.investor_firm ? `, ${r.investor_firm}` : ""}`;

  return (
    <AppShell role="founder" current="introductions">
      <h1 className="app-title">Introductions</h1>
      <p className="app-lede">
        An approved investor asks with a short note, and you decide. You do not have to give a reason. Accepting opens a
        conversation on IkonetU. It does not share your email or phone number, and it does not mean the investor will invest.
      </p>

      <section aria-labelledby="p-h" className="stack">
        <h2 id="p-h" className="app-h2">Waiting for your answer ({pending.length})</h2>
        {pending.length === 0 ? (
          <div className="empty"><p>No request is waiting for you.</p></div>
        ) : (
          <ul className="reqs">
            {pending.map((r) => (
              <li key={r.id} className="card">
                <h3 className="app-h3">{r.investor_name}</h3>
                <p className="small" style={{ margin: "0 0 12px" }}>{line(r)} · asked on {dateText(r.created_at)}</p>
                <blockquote className="quote">{r.note}</blockquote>
                <div className="row" style={{ marginTop: 16 }}>
                  <form action={answerIntroduction}>
                    <input type="hidden" name="id" value={r.id} />
                    <input type="hidden" name="answer" value="accepted" />
                    <button type="submit" className="btn btn-f btn-sm">Accept and open a conversation</button>
                  </form>
                  <form action={answerIntroduction}>
                    <input type="hidden" name="id" value={r.id} />
                    <input type="hidden" name="answer" value="declined" />
                    <button type="submit" className="btn btn-n btn-sm">Decline</button>
                  </form>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="o-h" className="stack" style={{ marginTop: 48 }}>
        <h2 id="o-h" className="app-h2">Conversations ({open.length})</h2>
        {open.length === 0 ? (
          <div className="empty"><p>You have no open conversations.</p></div>
        ) : (
          <ul className="reqs">
            {open.map((r) => (
              <li key={r.id} className="card row" style={{ justifyContent: "space-between" }}>
                <span><strong>{r.investor_name}</strong> <span className="small">{line(r)} · accepted on {dateText(r.decided_at)}</span></span>
                <Link className="btn btn-i btn-sm" href={`/introductions/${r.id}`}>Open the conversation</Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      {closed.length > 0 && (
        <section aria-labelledby="c-h" className="stack" style={{ marginTop: 48 }}>
          <h2 id="c-h" className="app-h2">Closed</h2>
          <ul className="reqs">
            {closed.map((r) => (
              <li key={r.id} className="small">
                {r.investor_name}, {line(r)}: {r.status === "declined" ? "you declined" : "withdrawn by the investor"} on {dateText(r.decided_at)}.
              </li>
            ))}
          </ul>
        </section>
      )}
    </AppShell>
  );
}
