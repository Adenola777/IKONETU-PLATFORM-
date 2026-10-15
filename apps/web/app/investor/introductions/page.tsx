import type { Metadata } from "next";
import Link from "next/link";
import { withdrawIntroduction } from "@/app/introductions/actions";
import { AppShell } from "@/components/app/shell";
import { dateText } from "@/lib/product";
import { requireInvestor } from "@/lib/session";

export const metadata: Metadata = { title: "Your introductions", robots: { index: false } };
export const dynamic = "force-dynamic";

const STATUS_NAME = { pending: "Waiting for the founder", accepted: "Accepted", declined: "Declined", withdrawn: "Withdrawn" } as const;
const STATUS_CHIP = { pending: "chip-n", accepted: "chip-i", declined: "chip-none", withdrawn: "chip-none" } as const;

export default async function InvestorIntroductionsPage() {
  const { supabase, user } = await requireInvestor();
  const { data } = await supabase
    .from("introductions")
    .select("id, venture_id, status, venture_name, founder_name, created_at, decided_at")
    .eq("investor_id", user.id)
    .order("created_at", { ascending: false })
    .limit(200);
  const rows = (data ?? []) as { id: string; venture_id: string; status: keyof typeof STATUS_NAME; venture_name: string; founder_name: string; created_at: string; decided_at: string | null }[];

  return (
    <AppShell role="investor" current="requests">
      <h1 className="app-title">Your introductions</h1>
      <p className="app-lede">
        You can send up to ten requests a day. A founder who declines is not asked again by you. An accepted request opens a
        conversation that only the two of you can read.
      </p>
      {rows.length === 0 ? (
        <div className="empty">
          <p>You have not asked for an introduction yet.</p>
          <p><Link href="/investor">Discover founders</Link></p>
        </div>
      ) : (
        <div className="scroll">
          <table className="tbl">
            <thead>
              <tr><th scope="col">Founder</th><th scope="col">Asked on</th><th scope="col">Status</th><th scope="col"><span className="sr-only">Action</span></th></tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td><Link href={`/investor/ventures/${r.venture_id}`}>{r.venture_name}</Link><br /><span className="small">{r.founder_name}</span></td>
                  <td>{dateText(r.created_at)}</td>
                  <td><span className={`chip ${STATUS_CHIP[r.status]}`}>{STATUS_NAME[r.status]}</span></td>
                  <td>
                    {r.status === "accepted" && <Link href={`/introductions/${r.id}`}>Open the conversation</Link>}
                    {r.status === "pending" && (
                      <form action={withdrawIntroduction}>
                        <input type="hidden" name="id" value={r.id} />
                        <button type="submit" className="linkbtn">Withdraw</button>
                      </form>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </AppShell>
  );
}
