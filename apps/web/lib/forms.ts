import { RUBRIC_V2 } from "@ikonetu/score-engine";
import { z } from "zod";
import { firstErrors, STAGES, type FieldErrors } from "./account";
import { SECTORS } from "./product";

/**
 * The rules for the forms of the founder, investor and staff pages. Each rule
 * matches a check in the database, so a form reports a problem before the
 * database refuses the row.
 */
type Parsed<T> = { ok: true; data: T } | { ok: false; errors: FieldErrors };

function parse<T>(schema: z.ZodType<T>, input: unknown): Parsed<T> {
  const r = schema.safeParse(input);
  return r.success ? { ok: true, data: r.data } : { ok: false, errors: firstErrors(r.error) };
}

const STAGE_CODES = STAGES.map((s) => s.code) as unknown as readonly ["idea", "mvp", "revenue", "scaling"];
const SIGNAL_CODES = RUBRIC_V2.signals.map((s) => s.code) as [string, ...string[]];

const webAddress = (message: string) =>
  z
    .string()
    .trim()
    .max(300, "That address is too long.")
    .transform((v) => (v === "" ? null : /^https?:\/\//i.test(v) ? v : `https://${v}`))
    .refine((v) => {
      if (v === null) return true;
      try {
        const u = new URL(v);
        return (u.protocol === "https:" || u.protocol === "http:") && u.hostname.includes(".");
      } catch {
        return false;
      }
    }, message);

// ---------------------------------------------------------------- evidence
export const EVIDENCE_FILE_TYPES = ["application/pdf", "image/jpeg", "image/png"] as const;
export const EVIDENCE_FILE_MAX = 10 * 1024 * 1024;
export const EVIDENCE_FILES_MAX = 3;

export type FileInfo = { name: string; type: string; size: number };

const evidenceSchema = z
  .object({
    signal: z.enum(SIGNAL_CODES, { message: "Choose what this evidence shows." }),
    summary: z.string().trim().min(10, "Describe the evidence in at least 10 characters.").max(280, "Keep the description to 280 characters."),
    link: webAddress("Enter a full web address, for example kolapay.ng/press."),
    files: z
      .array(z.object({ name: z.string(), type: z.string(), size: z.number() }))
      .max(EVIDENCE_FILES_MAX, `Add up to ${EVIDENCE_FILES_MAX} files.`)
      .refine((fs) => fs.every((f) => (EVIDENCE_FILE_TYPES as readonly string[]).includes(f.type)), "Add PDF, JPEG or PNG files only.")
      .refine((fs) => fs.every((f) => f.size > 0 && f.size <= EVIDENCE_FILE_MAX), "Each file must be 10 MB or smaller."),
  })
  .refine((d) => d.files.length > 0 || d.link !== null, { path: ["files"], message: "Add a file or a link, so a reviewer can check it." });

export function parseEvidence(input: { signal: string; summary: string; link: string; files: FileInfo[] }) {
  return parse(evidenceSchema, input);
}

/** The signals a founder can add evidence for, grouped by area, with their labels. */
export function signalOptions() {
  return RUBRIC_V2.signals.map((s) => ({ code: s.code, label: s.label, category: s.category, mode: s.mode }));
}

export function signalLabel(code: string): string {
  return RUBRIC_V2.signals.find((s) => s.code === code)?.label ?? code;
}

// ---------------------------------------------------------------- pitch
export const PITCH_TYPES = ["video/mp4", "video/webm", "video/quicktime"] as const;
export const PITCH_MAX_BYTES = 50 * 1024 * 1024;
export const PITCH_MAX_SECONDS = 90;

const pitchSchema = z.object({
  path: z.string().regex(/^[0-9a-f-]{36}\/[0-9a-f-]{36}\.(mp4|webm|mov)$/, "The upload did not finish. Please try again."),
  mimeType: z.enum(PITCH_TYPES, { message: "Upload an MP4, WebM or MOV video." }),
  size: z.number().int().positive().max(PITCH_MAX_BYTES, "The video must be 50 MB or smaller."),
  duration: z.number().positive("We could not read the video's length.").max(PITCH_MAX_SECONDS, "Keep the pitch to 90 seconds or less."),
  transcript: z.string().trim().min(20, "Type what you say in the pitch, in at least 20 characters.").max(2000, "Keep the transcript to 2,000 characters."),
});

export function parsePitch(input: unknown) {
  return parse(pitchSchema, input);
}

const transcriptSchema = z.object({
  transcript: z.string().trim().min(20, "Type what you say in the pitch, in at least 20 characters.").max(2000, "Keep the transcript to 2,000 characters."),
});

export function parseTranscript(input: unknown) {
  return parse(transcriptSchema, input);
}

// ---------------------------------------------------------------- updates, notes and messages
const updateSchema = z.object({
  body: z.string().trim().min(10, "Write at least 10 characters.").max(600, "Keep the update to 600 characters."),
});
export function parseUpdate(input: unknown) {
  return parse(updateSchema, input);
}

const noteSchema = z.object({
  note: z.string().trim().min(20, "Say why you want to talk, in at least 20 characters.").max(600, "Keep the note to 600 characters."),
});
export function parseIntroductionNote(input: unknown) {
  return parse(noteSchema, input);
}

const messageSchema = z.object({
  body: z.string().trim().min(1, "Write a message.").max(2000, "Keep the message to 2,000 characters."),
});
export function parseMessage(input: unknown) {
  return parse(messageSchema, input);
}

// ---------------------------------------------------------------- venture details
const ventureSchema = z.object({
  name: z.string().trim().min(1, "Enter your venture's name.").max(120, "The venture name is too long."),
  sector: z.enum(SECTORS, { message: "Choose your sector." }),
  stage: z.enum(STAGE_CODES, { message: "Choose your stage." }),
  description: z
    .string()
    .trim()
    .max(280, "Keep the description to 280 characters.")
    .transform((v) => (v === "" ? null : v)),
  website: webAddress("Enter a full web address, for example kolapay.ng."),
});
export function parseVenture(input: unknown) {
  return parse(ventureSchema, input);
}

// ---------------------------------------------------------------- staff decisions
export const REVIEW_LANES = [
  { code: "human", name: "Platform reviewed", hint: "You compared it with its source, such as a statement, a document or a live product." },
  { code: "government", name: "Third-party evidence: a government record", hint: "A government registry or authority holds a matching record." },
  { code: "source", name: "Third-party evidence: another outside source", hint: "An outside source backs it, such as a bank, a customer or a publisher." },
] as const;

const decisionSchema = z.discriminatedUnion("decision", [
  z.object({
    decision: z.literal("approve"),
    lane: z.enum(["human", "government", "source"], { message: "Choose how you checked it." }),
    publicNote: z.string().trim().min(5, "Say what you compared, in a sentence investors will read.").max(280, "Keep the note to 280 characters."),
    itemCount: z.number({ invalid_type_error: "Enter a whole number." }).int("Enter a whole number.").min(0).max(1000).nullable(),
    months: z.number({ invalid_type_error: "Enter a whole number." }).int("Enter a whole number.").min(0).max(600).nullable(),
    revenueUsd: z.number({ invalid_type_error: "Enter an amount in US dollars." }).min(0).max(1e12).nullable(),
    stage: z.enum(STAGE_CODES).nullable(),
  }),
  z.object({
    decision: z.enum(["reject", "needs_more"]),
    reason: z.string().trim().min(5, "Give the founder a reason, in a sentence.").max(600, "Keep the reason to 600 characters."),
  }),
]);

export function parseDecision(form: FormData) {
  const text = (k: string) => String(form.get(k) ?? "").trim();
  const num = (k: string) => (text(k) === "" ? null : Number(text(k).replace(/,/g, "")));
  const decision = text("decision");
  const input =
    decision === "approve"
      ? {
          decision,
          lane: text("lane"),
          publicNote: text("publicNote"),
          itemCount: num("itemCount"),
          months: num("months"),
          revenueUsd: num("revenueUsd"),
          stage: text("stage") === "" ? null : text("stage"),
        }
      : { decision, reason: text("reason") };
  if (!["approve", "reject", "needs_more"].includes(decision)) return { ok: false as const, errors: { decision: "Choose a decision." } };
  return parse(decisionSchema, input);
}
