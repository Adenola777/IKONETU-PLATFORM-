import type { Metadata } from "next";
import { PitchVideo } from "@/components/app/pitch-video";
import { AppShell } from "@/components/app/shell";
import { clockText, dateText } from "@/lib/product";
import { requireFounder } from "@/lib/session";
import { removePitch } from "./actions";
import { TranscriptForm } from "./transcript-form";
import { PitchUpload } from "./upload";

export const metadata: Metadata = { title: "Your pitch", robots: { index: false } };
export const dynamic = "force-dynamic";

export default async function PitchPage() {
  const { supabase, user, venture } = await requireFounder();
  const pitch = await supabase
    .from("pitches")
    .select("storage_path, duration_seconds, transcript, updated_at")
    .eq("venture_id", venture.id)
    .maybeSingle();
  const signed = pitch.data ? await supabase.storage.from("pitches").createSignedUrl(pitch.data.storage_path, 3600) : null;

  return (
    <AppShell role="founder" current="pitch">
      <h1 className="app-title">Your one-minute pitch</h1>
      <p className="app-lede">
        Say who you are, what your venture does, who it is for and what you have done so far. Investors see the video with captions
        and your transcript. Your profile cannot be published without a pitch.
      </p>
      <div className="side">
        <div className="stack">
          {pitch.data ? (
            <section className="card" aria-labelledby="cur-h">
              <h2 id="cur-h" className="app-h2">Your current pitch</h2>
              <p className="small" style={{ marginTop: 0 }}>
                {clockText(Number(pitch.data.duration_seconds))} long, saved on {dateText(pitch.data.updated_at)}.
              </p>
              {signed?.data?.signedUrl ? (
                <PitchVideo src={signed.data.signedUrl} transcript={pitch.data.transcript} duration={Number(pitch.data.duration_seconds)} title={`${venture.name} pitch`} />
              ) : (
                <p className="status status-err">The video could not be loaded. Please reload the page.</p>
              )}
            </section>
          ) : null}
          <section className="card" aria-labelledby="up-h">
            <h2 id="up-h" className="app-h2">{pitch.data ? "Replace your pitch" : "Upload your pitch"}</h2>
            <PitchUpload userId={user.id} hasPitch={Boolean(pitch.data)} transcript={pitch.data?.transcript ?? ""} />
          </section>
        </div>
        {pitch.data && (
          <aside className="stack" aria-label="Change the pitch">
            <section className="card">
              <h2 className="app-h3">Change the transcript only</h2>
              <TranscriptForm transcript={pitch.data.transcript} />
            </section>
            <section className="card">
              <h2 className="app-h3">Remove your pitch</h2>
              <p className="body2">Removing the pitch also hides your profile from investors, because a profile needs a pitch.</p>
              <form action={removePitch} style={{ marginTop: 12 }}>
                <button type="submit" className="btn btn-n btn-sm">Remove my pitch</button>
              </form>
            </section>
          </aside>
        )}
      </div>
    </AppShell>
  );
}
