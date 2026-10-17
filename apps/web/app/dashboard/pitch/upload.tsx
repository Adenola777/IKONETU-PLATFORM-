"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { FieldError, invalidProps } from "@/components/app/ui";
import { PITCH_MAX_BYTES, PITCH_MAX_SECONDS, PITCH_TYPES } from "@/lib/forms";
import { browserClient } from "@/lib/supabase/browser";
import { recordPitch } from "./actions";

const EXT: Record<string, string> = { "video/mp4": "mp4", "video/webm": "webm", "video/quicktime": "mov" };

/** Reads a video's length in the browser, before anything is uploaded. */
function readDuration(url: string): Promise<number> {
  return new Promise((resolve) => {
    const v = document.createElement("video");
    v.preload = "metadata";
    v.onloadedmetadata = () => resolve(Number.isFinite(v.duration) ? v.duration : 0);
    v.onerror = () => resolve(0);
    v.src = url;
  });
}

/**
 * The founder chooses a video and types what they say. The video goes from
 * the browser straight to the founder's own folder in storage, and the server
 * then records it with the transcript.
 */
export function PitchUpload({ userId, hasPitch, transcript }: { userId: string; hasPitch: boolean; transcript: string }) {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [duration, setDuration] = useState(0);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const text = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => () => {
    if (preview) URL.revokeObjectURL(preview);
  }, [preview]);

  const choose = async (e: React.ChangeEvent<HTMLInputElement>) => {
    setMessage(null);
    const f = e.target.files?.[0] ?? null;
    if (preview) URL.revokeObjectURL(preview);
    setPreview("");
    setFile(null);
    setDuration(0);
    if (!f) return;
    if (!(PITCH_TYPES as readonly string[]).includes(f.type)) return setErrors({ video: "Choose an MP4, WebM or MOV video." });
    if (f.size > PITCH_MAX_BYTES) return setErrors({ video: "The video must be 50 MB or smaller. Record at 720p, or shorten it." });
    const url = URL.createObjectURL(f);
    const seconds = await readDuration(url);
    if (!seconds) {
      URL.revokeObjectURL(url);
      return setErrors({ video: "This browser cannot read this video. Export it as an MP4 (H.264) file, or try another browser." });
    }
    if (seconds > PITCH_MAX_SECONDS) {
      URL.revokeObjectURL(url);
      return setErrors({ video: `This video is ${Math.round(seconds)} seconds long. Keep the pitch to 90 seconds or less.` });
    }
    setErrors({});
    setFile(f);
    setPreview(url);
    setDuration(seconds);
  };

  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setMessage(null);
    const words = text.current?.value.trim() ?? "";
    const next: Record<string, string> = {};
    if (!file) next.video = "Choose your pitch video.";
    if (words.length < 20) next.transcript = "Type what you say in the pitch, in at least 20 characters.";
    setErrors(next);
    if (Object.keys(next).length || !file) return;

    const supabase = browserClient();
    if (!supabase) return setMessage({ ok: false, text: "Uploads are not open yet. Please try again soon." });
    setBusy(true);
    const path = `${userId}/${crypto.randomUUID()}.${EXT[file.type]}`;
    const up = await supabase.storage.from("pitches").upload(path, file, { contentType: file.type, upsert: false });
    if (up.error) {
      setBusy(false);
      return setMessage({ ok: false, text: "The upload did not finish. Check your connection and try again." });
    }
    const saved = await recordPitch({ path, mimeType: file.type, size: file.size, duration, transcript: words });
    setBusy(false);
    if (saved.status === "error") return setMessage({ ok: false, text: saved.message });
    setMessage({ ok: true, text: "Your pitch is saved." });
    setFile(null);
    router.refresh();
  };

  return (
    <form className="form" onSubmit={submit} noValidate>
      {message && <p className={`status ${message.ok ? "status-ok" : "status-err"}`} role={message.ok ? "status" : "alert"}>{message.text}</p>}
      <div className="field">
        <label htmlFor="p-video">{hasPitch ? "Choose a new video to replace your pitch" : "Your pitch video"}</label>
        <input id="p-video" type="file" accept={PITCH_TYPES.join(",")} onChange={choose} className="input" aria-describedby="p-video-hint" {...invalidProps("video", errors.video)} />
        <p id="p-video-hint" className="hint">MP4, WebM or MOV, up to 90 seconds and 50 MB. A one-minute video recorded at 720p is usually well under 50 MB.</p>
        <FieldError id="video" message={errors.video} />
      </div>
      {preview && (
        <div className="player" style={{ maxWidth: 560 }}>
          <video src={preview} controls playsInline aria-label="Preview of the video you chose" />
        </div>
      )}
      <div className="field">
        <label htmlFor="p-transcript">What you say in the pitch</label>
        <textarea id="p-transcript" ref={text} name="transcript" className="input" rows={6} maxLength={2000} defaultValue={transcript} aria-describedby="p-transcript-hint" {...invalidProps("transcript", errors.transcript)} />
        <p id="p-transcript-hint" className="hint">
          Investors read this, and the captions are made from it. Each caption is timed by the length of its sentence, so write it in
          the order you speak.
        </p>
        <FieldError id="transcript" message={errors.transcript} />
      </div>
      <button type="submit" className="btn btn-f" style={{ alignSelf: "flex-start" }} disabled={busy}>
        {busy ? "Uploading…" : hasPitch ? "Replace my pitch" : "Upload my pitch"}
      </button>
    </form>
  );
}
