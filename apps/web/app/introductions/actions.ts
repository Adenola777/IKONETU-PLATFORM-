"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { formValues, type AppState } from "@/lib/app-state";
import { parseIntroductionNote, parseMessage } from "@/lib/forms";
import { logError, logInfo } from "@/lib/log";
import { isRepeat, requestKey } from "@/lib/request-key";
import { requireFounder, requireInvestor, requireViewer } from "@/lib/session";

const ID = /^[0-9a-f-]{36}$/;

/** An approved investor asks a founder for an introduction. The database fills in who is asking. */
export async function requestIntroduction(_prev: AppState, form: FormData): Promise<AppState> {
  const values = formValues(form);
  const { supabase } = await requireInvestor();
  const venture = String(values.venture ?? "");
  if (!ID.test(venture)) return { status: "error", message: "This founder profile could not be found.", errors: {} };
  const parsed = parseIntroductionNote({ note: values.note });
  if (!parsed.ok) return { status: "error", message: "Please check your note.", errors: parsed.errors, values };
  const { error } = await supabase.from("introductions").insert({ venture_id: venture, note: parsed.data.note });
  if (error) {
    const expected = error.code === "23505" || /ten requests a day|not published/.test(error.message);
    if (expected) logInfo("introduction.request_refused", { venture, code: error.code });
    else logError("introduction.request_failed", { venture, code: error.code });
    const message =
      error.code === "23505"
        ? "You have already asked this founder for an introduction."
        : /ten requests a day/.test(error.message)
          ? "You have reached the limit of ten requests a day. Please try again tomorrow."
          : /not published/.test(error.message)
            ? "This founder has hidden their profile."
            : "We could not send your request. Please try again.";
    return { status: "error", message, errors: {}, values };
  }
  revalidatePath(`/investor/ventures/${venture}`);
  revalidatePath("/investor/introductions");
  return { status: "sent", message: "Your request is sent. The founder decides whether to accept it." };
}

/** An investor withdraws a request the founder has not answered. */
export async function withdrawIntroduction(form: FormData) {
  const { supabase } = await requireInvestor();
  const id = String(form.get("id") ?? "");
  if (!ID.test(id)) return;
  const { error } = await supabase.from("introductions").update({ status: "withdrawn" }).eq("id", id);
  if (error) logError("introduction.withdraw_failed", { introduction: id, code: error.code });
  revalidatePath("/investor", "layout");
}

/** The founder accepts or declines. An accepted request opens the conversation. */
export async function answerIntroduction(form: FormData) {
  const { supabase } = await requireFounder();
  const id = String(form.get("id") ?? "");
  const answer = form.get("answer") === "accepted" ? "accepted" : "declined";
  if (!ID.test(id)) return;
  const { error } = await supabase.from("introductions").update({ status: answer }).eq("id", id);
  if (error) {
    logError("introduction.answer_failed", { introduction: id, code: error.code });
    revalidatePath("/dashboard", "layout");
    return;
  }
  revalidatePath("/dashboard", "layout");
  if (answer === "accepted") redirect(`/introductions/${id}`);
}

/** A message in an accepted introduction, from either of the two people involved. */
export async function sendMessage(_prev: AppState, form: FormData): Promise<AppState> {
  const values = formValues(form);
  const { supabase, user } = await requireViewer();
  const id = String(values.introduction ?? "");
  if (!ID.test(id)) return { status: "error", message: "This conversation could not be found.", errors: {} };
  const parsed = parseMessage({ body: values.body });
  if (!parsed.ok) return { status: "error", message: "Please check your message.", errors: parsed.errors, values };
  const { error } = await supabase
    .from("introduction_messages")
    .insert({ introduction_id: id, sender_id: user.id, body: parsed.data.body, request_key: requestKey(form) });
  if (isRepeat(error)) return { status: "sent", message: "Sent." };
  if (error) {
    logError("message.send_failed", { introduction: id, code: error.code });
    return { status: "error", message: "We could not send your message. Please try again.", errors: {}, values };
  }
  revalidatePath(`/introductions/${id}`);
  return { status: "sent", message: "Sent." };
}
