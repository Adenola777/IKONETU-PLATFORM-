"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { formValues, type AppState } from "@/lib/app-state";
import { parseVenture } from "@/lib/forms";
import { requireFounder } from "@/lib/session";
import { createClient } from "@/lib/supabase/server";

export async function signOut() {
  const supabase = await createClient();
  if (supabase) await supabase.auth.signOut();
  redirect("/");
}

/**
 * Publishes the founder's profile to approved investors, or hides it. The
 * database refuses to publish a venture without a pitch.
 */
export async function setPublished(form: FormData) {
  const { supabase, venture } = await requireFounder();
  const publish = form.get("publish") === "yes";
  const { error } = await supabase
    .from("ventures")
    .update({ published_at: publish ? new Date().toISOString() : null })
    .eq("id", venture.id);
  if (error) console.error("set published failed", error.code, error.message);
  revalidatePath("/dashboard");
}

/** Changes the venture's details. */
export async function updateVenture(_prev: AppState, form: FormData): Promise<AppState> {
  const values = formValues(form);
  const { supabase, venture } = await requireFounder();
  const parsed = parseVenture({
    name: values.name,
    sector: values.sector,
    stage: values.stage,
    description: values.description,
    website: values.website,
    ask: values.ask,
  });
  if (!parsed.ok) return { status: "error", message: "Please check the form.", errors: parsed.errors, values };
  const { error } = await supabase.from("ventures").update(parsed.data).eq("id", venture.id);
  if (error) {
    console.error("update venture failed", error.code);
    return { status: "error", message: "We could not save the changes. Please try again.", errors: {}, values };
  }
  revalidatePath("/dashboard");
  return { status: "sent", message: "Your venture's details are saved." };
}
