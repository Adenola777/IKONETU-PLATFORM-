import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { CODE_LIFETIME_SECONDS, PENDING_COOKIE, readPending } from "@/lib/pending-sign-in";
import { AppHeader } from "../../app-header";
import { CodeForm } from "./code-form";

export const metadata: Metadata = { title: "Enter your code | IkonetU", robots: { index: false } };
export const dynamic = "force-dynamic";

/** Shows where the code went, with most of a phone number hidden. */
function describe(pending: NonNullable<ReturnType<typeof readPending>>): string {
  if (pending.kind === "email") return `to ${pending.email}`;
  const how = pending.channel === "sms" ? "by SMS" : "by WhatsApp";
  return `${how} to a number ending ${pending.phone.slice(-4)}`;
}

export default async function CodePage() {
  const pending = readPending((await cookies()).get(PENDING_COOKIE)?.value);
  if (!pending) redirect("/signin");

  return (
    <>
      <AppHeader />
      <main id="main" className="section tint">
        <div className="wrap form-wrap">
          <h1 className="title" style={{ marginBottom: 12 }}>Enter your code</h1>
          {pending.kind === "email" ? (
            <p className="lede" style={{ marginBottom: 36 }}>
              We sent an email {describe(pending)}. Open the sign-in link in it on this device, or enter the 6-digit code
              if the email shows one.
            </p>
          ) : (
            <p className="lede" style={{ marginBottom: 36 }}>We sent a 6-digit code {describe(pending)}.</p>
          )}
          <CodeForm expiresAt={pending.sentAt + CODE_LIFETIME_SECONDS * 1000} isPhone={pending.kind === "phone"} />
        </div>
      </main>
    </>
  );
}
