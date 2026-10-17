import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { AppShell } from "@/components/app/shell";
import { Icon } from "@/components/site/icons";
import { dateText, INVESTOR_TYPE_NAME } from "@/lib/product";
import { requireViewer } from "@/lib/session";
import { MessageForm } from "../message-form";

export const metadata: Metadata = { title: "Conversation", robots: { index: false } };
export const dynamic = "force-dynamic";

/** The conversation an accepted introduction opens. Only the founder and the investor can read it. */
export default async function ConversationPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^[0-9a-f-]{36}$/.test(id)) notFound();
  const { supabase, user, profile } = await requireViewer();
  const intro = await supabase
    .from("introductions")
    .select("id, venture_id, founder_id, investor_id, note, status, investor_name, investor_type, investor_firm, venture_name, founder_name, created_at, decided_at")
    .eq("id", id)
    .maybeSingle();
  const i = intro.data;
  if (!i || (i.founder_id !== user.id && i.investor_id !== user.id)) notFound();
  const iAmFounder = i.founder_id === user.id;
  if (!iAmFounder && profile?.status !== "active") notFound();
  const messages = await supabase
    .from("introduction_messages")
    .select("id, sender_id, body, created_at")
    .eq("introduction_id", id)
    .order("created_at", { ascending: true })
    .limit(500);
  const investorLine = `${i.investor_name}, ${INVESTOR_TYPE_NAME[i.investor_type] ?? i.investor_type}${i.investor_firm ? `, ${i.investor_firm}` : ""}`;
  const who = (sender: string) => (sender === user.id ? "You" : sender === i.founder_id ? i.founder_name : i.investor_name);

  return (
    <AppShell role={iAmFounder ? "founder" : "investor"} current={iAmFounder ? "introductions" : "requests"}>
      <Link href={iAmFounder ? "/dashboard/introductions" : "/investor/introductions"} className="back">
        <Icon name="arrow-left" size={16} /> All introductions
      </Link>
      <h1 className="app-title">{iAmFounder ? investorLine : `${i.founder_name}, ${i.venture_name}`}</h1>
      <p className="app-lede">
        {i.status === "accepted"
          ? `${i.founder_name} accepted this introduction on ${dateText(i.decided_at)}. Only the two of you can read this conversation.`
          : i.status === "pending"
            ? `${i.founder_name} has not answered this request yet. The conversation opens if the request is accepted.`
            : i.status === "declined"
              ? `${i.founder_name} declined this request. There is no conversation.`
              : "This request was withdrawn. There is no conversation."}
      </p>
      <div className="app-narrow stack">
        <ol className="msgs" aria-label="Messages">
          <li className={`msg ${iAmFounder ? "" : "msg-me"}`}>
            <span className="who">{iAmFounder ? i.investor_name : "You"} asked for an introduction on {dateText(i.created_at)}</span>
            <p>{i.note}</p>
          </li>
          {(messages.data ?? []).map((m) => (
            <li key={m.id} className={`msg ${m.sender_id === user.id ? "msg-me" : ""}`}>
              <span className="who">{who(m.sender_id)}, {dateText(m.created_at)}</span>
              <p>{m.body}</p>
            </li>
          ))}
        </ol>
        {i.status === "accepted" && (
          <>
            <MessageForm introduction={i.id} />
            <p className="small" style={{ margin: 0 }}>
              New messages appear when the page reloads. <Link href={`/introductions/${i.id}`}>Reload the conversation</Link>
            </p>
            <p className="small" style={{ margin: 0 }}>
              IkonetU does not provide investment advice and takes no part in any investment. Your own diligence decides.
            </p>
          </>
        )}
      </div>
    </AppShell>
  );
}
