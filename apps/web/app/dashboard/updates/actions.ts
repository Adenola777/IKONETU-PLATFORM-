"use server";

import { revalidatePath } from "next/cache";
import { formValues, type AppState } from "@/lib/app-state";
import { parseUpdate } from "@/lib/forms";
import { requireFounder } from "@/lib/session";

export async function postUpdate(_prev: AppState, form: FormData): Promise<AppState> {
  const values = formValues(form);
  const { supabase, venture } = await requireFounder();
  const parsed = parseUpdate({ body: values.body });
  if (!parsed.ok) return { status: "error", message: "Please check the update.", errors: parsed.errors, values };
  const { error } = await supabase.from("venture_updates").insert({ venture_id: venture.id, body: parsed.data.body });
  if (error) {
    console.error("post update failed", error.code);
    return { status: "error", message: "We could not post the update. Please try again.", errors: {}, values };
  }
  revalidatePath("/dashboard", "layout");
  return { status: "sent", message: "Your update is posted." };
}

export async function removeUpdate(form: FormData) {
  const { supabase, venture } = await requireFounder();
  const id = String(form.get("id") ?? "");
  if (!/^[0-9a-f-]{36}$/.test(id)) return;
  const { error } = await supabase.from("venture_updates").delete().eq("id", id).eq("venture_id", venture.id);
  if (error) console.error("remove update failed", error.code);
  revalidatePath("/dashboard", "layout");
}
