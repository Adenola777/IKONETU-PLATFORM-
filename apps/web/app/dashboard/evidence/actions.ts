"use server";

import { createHash, randomUUID } from "node:crypto";
import { revalidatePath } from "next/cache";
import { formValues, type AppState } from "@/lib/app-state";
import { parseEvidence } from "@/lib/forms";
import { requireFounder } from "@/lib/session";

/**
 * Adds one piece of evidence. Its files go to the founder's own folder in the
 * private evidence bucket, each with a SHA-256 taken here on the server, so a
 * reviewer can spot the same file used twice. Investors never see the files.
 */
export async function submitEvidence(_prev: AppState, form: FormData): Promise<AppState> {
  const values = formValues(form);
  delete values.files;
  const { supabase, user, venture } = await requireFounder();
  const files = form.getAll("files").filter((f): f is File => typeof f === "object" && f !== null && "arrayBuffer" in f && (f as File).size > 0);
  const parsed = parseEvidence({
    signal: String(values.signal ?? ""),
    summary: String(values.summary ?? ""),
    link: String(values.link ?? ""),
    files: files.map((f) => ({ name: f.name, type: f.type, size: f.size })),
  });
  if (!parsed.ok) return { status: "error", message: "Please check the form.", errors: parsed.errors, values };

  const stored: { storage_path: string; sha256: string; mime_type: string; size_bytes: number }[] = [];
  for (const file of files) {
    const bytes = Buffer.from(await file.arrayBuffer());
    const path = `${user.id}/${randomUUID()}`;
    const up = await supabase.storage.from("evidence").upload(path, bytes, { contentType: file.type, upsert: false });
    if (up.error) {
      console.error("evidence upload failed", up.error.message);
      return { status: "error", message: "A file did not upload. Please try again.", errors: {}, values };
    }
    stored.push({ storage_path: path, sha256: createHash("sha256").update(bytes).digest("hex"), mime_type: file.type, size_bytes: bytes.length });
  }

  const made = await supabase
    .from("evidence")
    .insert({ venture_id: venture.id, signal_code: parsed.data.signal, summary: parsed.data.summary, source_ref: parsed.data.link })
    .select("id")
    .single();
  if (made.error) {
    console.error("insert evidence failed", made.error.code);
    return { status: "error", message: "We could not save the evidence. Please try again.", errors: {}, values };
  }
  if (stored.length) {
    const rows = stored.map((s) => ({ evidence_id: made.data.id, ...s }));
    const linked = await supabase.from("evidence_files").insert(rows);
    if (linked.error) {
      console.error("insert evidence files failed", linked.error.code);
      return { status: "error", message: "The evidence is saved, but its files are not. Please add it again.", errors: {} };
    }
  }
  revalidatePath("/dashboard", "layout");
  return { status: "sent", message: "Your evidence is added. A reviewer will look at it, and its status shows below." };
}
