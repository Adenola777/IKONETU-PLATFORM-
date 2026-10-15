"use server";

import { revalidatePath } from "next/cache";
import { formValues, type AppState } from "@/lib/app-state";
import { parsePitch, parseTranscript } from "@/lib/forms";
import { requireFounder } from "@/lib/session";

/**
 * Records a pitch the browser has just uploaded to the founder's own folder.
 * A new pitch replaces the old one, and the old file is removed. Row level
 * security checks that the path is in the founder's folder.
 */
export async function recordPitch(input: unknown): Promise<AppState> {
  const { supabase, user, venture } = await requireFounder();
  const parsed = parsePitch(input);
  if (!parsed.ok) return { status: "error", message: Object.values(parsed.errors)[0] ?? "Please check the pitch.", errors: parsed.errors };
  const p = parsed.data;
  if (!p.path.startsWith(`${user.id}/`)) return { status: "error", message: "The upload did not finish. Please try again.", errors: {} };

  const old = await supabase.from("pitches").select("storage_path").eq("venture_id", venture.id).maybeSingle();
  const row = { storage_path: p.path, mime_type: p.mimeType, size_bytes: p.size, duration_seconds: Math.round(p.duration * 10) / 10, transcript: p.transcript };
  const saved = old.data
    ? await supabase.from("pitches").update(row).eq("venture_id", venture.id)
    : await supabase.from("pitches").insert({ venture_id: venture.id, ...row });
  if (saved.error) {
    console.error("record pitch failed", saved.error.code);
    await supabase.storage.from("pitches").remove([p.path]);
    return { status: "error", message: "We could not save your pitch. Please try again.", errors: {} };
  }
  if (old.data && old.data.storage_path !== p.path) await supabase.storage.from("pitches").remove([old.data.storage_path]);
  revalidatePath("/dashboard", "layout");
  return { status: "sent", message: "Your pitch is saved." };
}

/** Changes the transcript of the current pitch, and with it the captions. */
export async function saveTranscript(_prev: AppState, form: FormData): Promise<AppState> {
  const values = formValues(form);
  const { supabase, venture } = await requireFounder();
  const parsed = parseTranscript({ transcript: values.transcript });
  if (!parsed.ok) return { status: "error", message: "Please check the transcript.", errors: parsed.errors, values };
  const { error, count } = await supabase.from("pitches").update(parsed.data, { count: "exact" }).eq("venture_id", venture.id);
  if (error || !count) return { status: "error", message: "We could not save the transcript. Please try again.", errors: {}, values };
  revalidatePath("/dashboard", "layout");
  return { status: "sent", message: "The transcript and captions are saved." };
}

/** Removes the pitch. A published profile is hidden first, because a profile needs a pitch. */
export async function removePitch() {
  const { supabase, venture } = await requireFounder();
  const old = await supabase.from("pitches").select("storage_path").eq("venture_id", venture.id).maybeSingle();
  if (!old.data) return;
  if (venture.published_at) await supabase.from("ventures").update({ published_at: null }).eq("id", venture.id);
  const { error } = await supabase.from("pitches").delete().eq("venture_id", venture.id);
  if (error) {
    console.error("remove pitch failed", error.code);
    return;
  }
  await supabase.storage.from("pitches").remove([old.data.storage_path]);
  revalidatePath("/dashboard", "layout");
}
