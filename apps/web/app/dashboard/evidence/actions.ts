"use server";

import { createHash, randomUUID } from "node:crypto";
import { revalidatePath } from "next/cache";
import { formValues, type AppState } from "@/lib/app-state";
import { parseEvidence } from "@/lib/forms";
import { logError } from "@/lib/log";
import { isRepeat, requestKey } from "@/lib/request-key";
import { requireFounder } from "@/lib/session";

/**
 * Adds one piece of evidence. Its files go to the founder's own folder in the
 * private evidence bucket, each with a SHA-256 taken here on the server, so a
 * reviewer can spot the same file used twice. Investors never see the files.
 *
 * The evidence and its file records are saved together by submit_evidence(),
 * in one transaction. If that fails, the files just uploaded are removed, so
 * nothing is left half saved. The form's request key makes a second copy of
 * the same submission a no-op, and it is checked before any file is uploaded.
 */
export async function submitEvidence(_prev: AppState, form: FormData): Promise<AppState> {
  const values = formValues(form);
  delete values.files;
  delete values.requestKey;
  const { supabase, user, venture } = await requireFounder();
  const key = requestKey(form);
  const files = form.getAll("files").filter((f): f is File => typeof f === "object" && f !== null && "arrayBuffer" in f && (f as File).size > 0);
  const parsed = parseEvidence({
    signal: String(values.signal ?? ""),
    summary: String(values.summary ?? ""),
    link: String(values.link ?? ""),
    files: files.map((f) => ({ name: f.name, type: f.type, size: f.size })),
  });
  if (!parsed.ok) return { status: "error", message: "Please check the form.", errors: parsed.errors, values };

  if (key) {
    const seen = await supabase.from("evidence").select("id").eq("venture_id", venture.id).eq("request_key", key).maybeSingle();
    if (seen.data) return ADDED;
  }

  const stored: { storage_path: string; sha256: string; mime_type: string; size_bytes: number }[] = [];
  const removeStored = async () => {
    if (!stored.length) return;
    const gone = await supabase.storage.from("evidence").remove(stored.map((s) => s.storage_path));
    if (gone.error) logError("evidence.cleanup_failed", { venture: venture.id, files: stored.length, code: gone.error.message });
  };
  for (const file of files) {
    const bytes = Buffer.from(await file.arrayBuffer());
    const path = `${user.id}/${randomUUID()}`;
    const up = await supabase.storage.from("evidence").upload(path, bytes, { contentType: file.type, upsert: false });
    if (up.error) {
      logError("evidence.upload_failed", { venture: venture.id, code: up.error.message });
      await removeStored();
      return { status: "error", message: "A file did not upload. Please try again.", errors: {}, values };
    }
    stored.push({ storage_path: path, sha256: createHash("sha256").update(bytes).digest("hex"), mime_type: file.type, size_bytes: bytes.length });
  }

  const made = await supabase.rpc("submit_evidence", {
    p_venture: venture.id,
    p_signal: parsed.data.signal,
    p_summary: parsed.data.summary,
    p_link: parsed.data.link,
    p_request_key: key,
    p_files: stored,
  });
  if (made.error) {
    await removeStored();
    if (isRepeat(made.error)) return ADDED;
    logError("evidence.save_failed", { venture: venture.id, code: made.error.code });
    return { status: "error", message: "We could not save the evidence. Please try again.", errors: {}, values };
  }
  revalidatePath("/dashboard", "layout");
  return ADDED;
}

const ADDED: AppState = { status: "sent", message: "Your evidence is added. A reviewer will look at it, and its status shows below." };
