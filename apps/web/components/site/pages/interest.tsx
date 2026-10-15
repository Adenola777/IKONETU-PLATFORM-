"use client";

import { useEffect, useRef, useState } from "react";
import { useNavVals } from "../side";
import { InvestorInterestView } from "../views/interest.view";

type FieldKey = "name" | "email" | "country" | "sector" | "cheque" | "adult" | "privacy" | "consent" | "statement" | "truth";
type Errors = Partial<Record<FieldKey, string>>;
type Answers = { name: string; email: string; country: string; firm: string; sectors: string[]; cheque: string; consent: boolean };

const KEYS: FieldKey[] = ["name", "email", "country", "sector", "cheque", "adult", "privacy", "consent", "statement", "truth"];
const COUNTRY_NAME: Record<string, string> = { NG: "Nigeria", GH: "Ghana", KE: "Kenya", other: "Somewhere else" };
const STATEMENT_NAME: Record<string, string> = { individual: "Individual investor", angel: "Angel investor", fund: "Fund investor" };
// The API names each field differently from the form, so its errors are mapped back to the field they belong to.
const API_FIELD: Record<string, FieldKey> = {
  fullName: "name", email: "email", country: "country", sectors: "sector", chequeSize: "cheque",
  confirmedAdult: "adult", acceptedPrivacy: "privacy", emailConsent: "consent", investorType: "statement", confirmedStatement: "truth",
};
const STEP_ONE: FieldKey[] = ["name", "email", "country", "sector", "cheque", "adult", "privacy", "consent"];

function useInvestorInterestVals() {
  const nav = useNavVals();
  const [step, setStep] = useState(1);
  const [errors, setErrors] = useState<Errors>({});
  const [statement, setStatement] = useState("");
  const [data, setData] = useState<Answers | null>(null);
  const [sending, setSending] = useState(false);
  const [serverError, setServerError] = useState("");
  const head = useRef<HTMLHeadingElement | null>(null);
  const done = useRef<HTMLHeadingElement | null>(null);
  const lastStep = useRef(1);

  // Each change of step moves focus to the new heading, so a screen reader announces it.
  useEffect(() => {
    if (lastStep.current === step) return;
    lastStep.current = step;
    const target = step === 3 ? done.current : head.current;
    target?.focus({ preventScroll: true });
    target?.scrollIntoView({ block: "start" });
  }, [step]);

  const e = Object.fromEntries(
    KEYS.flatMap((k) => [
      [k, errors[k] ?? ""],
      [`${k}Ok`, !errors[k]],
      [`${k}Bad`, Boolean(errors[k])],
    ]),
  ) as Record<FieldKey, string> & Record<`${FieldKey}Ok` | `${FieldKey}Bad`, boolean>;
  const n = Object.keys(errors).length;

  const send = async (answers: Answers, investorType: string, website: string) => {
    setSending(true);
    setServerError("");
    try {
      const res = await fetch("/api/v1/investor-interest", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          fullName: answers.name,
          email: answers.email,
          country: answers.country,
          firm: answers.firm,
          sectors: answers.sectors,
          chequeSize: answers.cheque,
          investorType,
          confirmedAdult: true,
          acceptedPrivacy: true,
          emailConsent: answers.consent,
          confirmedStatement: true,
          website,
        }),
      });
      const reply = (await res.json().catch(() => ({}))) as { ok?: boolean; message?: string; errors?: Record<string, string> };
      if (res.ok && reply.ok) {
        setStep(3);
        return;
      }
      const fieldErrors: Errors = {};
      for (const [key, message] of Object.entries(reply.errors ?? {})) {
        const field = API_FIELD[key];
        if (field) fieldErrors[field] = message;
      }
      if (Object.keys(fieldErrors).some((k) => STEP_ONE.includes(k as FieldKey))) {
        setErrors(fieldErrors);
        setStep(1);
        return;
      }
      setErrors(fieldErrors);
      setServerError(reply.message ?? "Something went wrong on our side. Please try again.");
    } catch {
      setServerError("We could not reach IkonetU. Check your connection and try again.");
    } finally {
      setSending(false);
    }
  };

  return {
    ...nav,
    form1Ref: () => {},
    form2Ref: () => {},
    headRef: (el: HTMLHeadingElement | null) => {
      head.current = el;
    },
    doneRef: (el: HTMLHeadingElement | null) => {
      done.current = el;
    },
    e,
    hasErrors: n > 0,
    errorCount: n === 1 ? "One answer needs a change. It is marked below." : `${n} answers need a change. Each is marked below.`,
    notStep1: step !== 1,
    notStep2: step !== 2,
    isDone: step === 3,
    step1Cls: "on",
    step2Cls: step >= 2 ? "on" : "",
    needsConfirm: Boolean(statement),
    sending,
    serverError,
    submitLabel: sending ? "Sending…" : "Register my interest",
    firstName: (data?.name ?? "").split(" ")[0] ?? "",
    email: data?.email ?? "",
    summary: {
      country: COUNTRY_NAME[data?.country ?? ""] ?? "",
      firm: data?.firm || "Not given",
      sectors: (data?.sectors ?? []).join(", "),
      cheque: data?.cheque ?? "",
      statement: STATEMENT_NAME[statement] ?? "",
    },
    submit1: (ev: React.FormEvent<HTMLFormElement>) => {
      ev.preventDefault();
      const f = ev.currentTarget;
      const field = (name: string) => f.elements.namedItem(name);
      const val = (name: string) => {
        const el = field(name);
        if (el instanceof HTMLInputElement) return el.value.trim();
        if (el instanceof RadioNodeList) return el.value.trim();
        return "";
      };
      const on = (name: string) => {
        const el = field(name);
        return el instanceof HTMLInputElement && el.checked;
      };
      const answers: Answers = {
        name: val("name"),
        email: val("email").toLowerCase(),
        country: val("country"),
        firm: val("firm"),
        sectors: Array.from(f.querySelectorAll<HTMLInputElement>('input[name="sector"]:checked')).map((x) => x.value),
        cheque: val("cheque"),
        consent: on("consent"),
      };
      const next: Errors = {};
      if (answers.name.length < 2) next.name = "Enter your full name.";
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(answers.email)) next.email = "Enter a valid email address.";
      if (!answers.country) next.country = "Choose where you are based.";
      if (!answers.sectors.length) next.sector = "Choose at least one sector.";
      if (!answers.cheque) next.cheque = "Choose a cheque size, or prefer not to say.";
      if (!on("adult")) next.adult = "You must be 18 or older to register.";
      if (!on("privacy")) next.privacy = "Confirm that you have read the privacy policy.";
      if (!answers.consent) next.consent = "We need your agreement to email you about investor access.";
      setErrors(next);
      if (Object.keys(next).length) return;
      setData(answers);
      setStep(2);
    },
    pick: (ev: React.FormEvent<HTMLFormElement>) => {
      const target = ev.target;
      if (target instanceof HTMLInputElement && target.name === "statement") {
        setStatement(target.value);
        setErrors({});
      }
    },
    submit2: (ev: React.FormEvent<HTMLFormElement>) => {
      ev.preventDefault();
      if (sending || !data) return;
      const truth = ev.currentTarget.elements.namedItem("truth");
      const next: Errors = {};
      if (!statement) next.statement = "Choose the one that describes you best.";
      else if (!(truth instanceof HTMLInputElement && truth.checked)) next.truth = "Confirm that this describes you.";
      setErrors(next);
      if (Object.keys(next).length) return;
      // The hidden website field is a trap for bots. People never see it, so it stays empty.
      const trap = document.getElementById("ii-website");
      void send(data, statement, trap instanceof HTMLInputElement ? trap.value : "");
    },
    back: () => {
      setStep(1);
      setErrors({});
      setServerError("");
    },
  };
}

export type InvestorInterestVals = ReturnType<typeof useInvestorInterestVals>;

export default function InvestorInterestPage() {
  return <InvestorInterestView v={useInvestorInterestVals()} />;
}
