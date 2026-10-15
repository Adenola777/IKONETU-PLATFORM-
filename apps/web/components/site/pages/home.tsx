"use client";

import { useEffect, useRef, useState } from "react";
import type { PitchPlayerHandle } from "../pitch-player";
import { readStoredSide, useNavVals } from "../side";
import { HomeView } from "../views/home.view";
import { useWalkVals } from "../walkthrough";

type ModuleId = "traction" | "product" | "customers" | "revenue" | "model" | "team" | "roadmap" | "registration";
type Evidence = "reviewed" | "third" | "submitted" | "none";
type Progress = "done" | "progress" | "action";

const TOUR = [
  ["pitch", "The pitch", "Every profile starts with a one-minute pitch. Investors watch it first, with captions."],
  ["details", "The details and the ask", "Stage, location, sector, what the founder is raising, and the readiness check across eight areas."],
  ["evidence", "The evidence", "Eight modules show what the founder has added. Each one says who supplied it and whether IkonetU reviewed it."],
  ["revenue", "How one piece of evidence was reviewed", "Revenue is open as an example: what was submitted, how it was reviewed and when."],
  ["intro", "The introduction", "An investor who wants to talk requests an introduction. The founder accepts or declines."],
] as const;

// id, name, summary, evidence status, founder status, submitted, review, date, who can see
const MODULES: [ModuleId, string, string, Evidence, Progress, string, string, string, string][] = [
  ["traction", "Traction", "Monthly payment volume, last 12 months", "reviewed", "done", "Twelve monthly exports from the payments dashboard.", "An IkonetU reviewer compared the totals with the business bank statements.", "3 October 2026", "Investors see the monthly totals and this status. The exports and statements stay with you and the reviewer."],
  ["product", "Product", "Live on Android and USSD", "reviewed", "done", "A link to the Android app, the USSD short code and a test account.", "A reviewer opened both and made a test payment.", "28 September 2026", "Investors see the links and this status. The test account stays private."],
  ["customers", "Customers", "3 of 5 merchant references", "third", "progress", "Three signed reference letters from market traders, with their contact details.", "A reviewer spoke to each of the three referees.", "1 October 2026", "Investors see how many references exist and this status. The referees’ contact details stay private."],
  ["revenue", "Revenue", "Last 12 months", "reviewed", "done", "Management accounts and 12 months of business bank statements.", "A reviewer compared the reported revenue with the bank statements. This is not an audit.", "3 October 2026", "Investors see monthly revenue and this status. The statements stay with you and the reviewer."],
  ["model", "Business model", "Pricing and the cost of each payment", "none", "action", "Nothing yet.", "Nothing to review yet.", "Not added", "Investors will see your pricing and costs once you add them."],
  ["team", "Team", "4 members, 2 roles confirmed", "submitted", "progress", "Four team profiles. Two members confirmed their role from their own accounts.", "Not reviewed by IkonetU yet.", "Added 30 September 2026", "Investors see names and roles. Identity documents are never shown."],
  ["roadmap", "Roadmap", "Milestones for the next 12 months", "none", "action", "Nothing yet.", "Nothing to review yet.", "Not added", "Investors will see the milestones you add."],
  ["registration", "Registration", "Certificate of incorporation", "third", "done", "A certificate of incorporation and a tax identification number.", "The registration matches the record in the CAC public registry.", "25 September 2026", "Investors see the registry match and this status. The tax number stays private."],
];

const EVIDENCE_NAME: Record<Evidence, string> = { reviewed: "Platform reviewed", third: "Third-party evidence available", submitted: "Founder submitted", none: "Not added yet" };
const EVIDENCE_CLASS: Record<Evidence, string> = { reviewed: "chip-i", third: "chip-io", submitted: "chip-n", none: "chip-none" };
const PROGRESS_NAME: Record<Progress, string> = { done: "Complete", progress: "In progress", action: "Action needed" };
const PROGRESS_CLASS: Record<Progress, string> = { done: "chip-n", progress: "chip-n", action: "chip-f" };

const NEXT_STEPS = [
  { num: 1, title: "Explain your pricing and the cost of each payment", why: "Business model is the one area with no evidence yet, and it shows investors how the company makes money.", action: "Add pricing" },
  { num: 2, title: "Add two more merchant references", why: "References let investors hear from paying customers directly.", action: "Add references" },
  { num: 3, title: "Add milestones for the next 12 months", why: "Milestones show what the money you raise would pay for.", action: "Add milestones" },
];

function reducedMotion() {
  try {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch {
    return false;
  }
}

function useHomeVals() {
  const nav = useNavVals();
  const walk = useWalkVals();
  const [view, setView] = useState<"investor" | "founder">("investor");
  const [module, setModule] = useState<ModuleId | "">("");
  const [step, setStep] = useState(0);
  const [introNote, setIntroNote] = useState(false);
  const [cardNote, setCardNote] = useState(false);
  const playerRef = useRef<PitchPlayerHandle>(null);
  const profileEl = useRef<HTMLDivElement | null>(null);
  const tourEl = useRef<HTMLDivElement | null>(null);
  const lastStep = useRef(0);

  // A remembered founder opens the profile in the founder view.
  useEffect(() => {
    if (readStoredSide() === "founder") setView("founder");
  }, []);

  // Starting the tour scrolls to the profile and moves focus to the tour panel.
  useEffect(() => {
    const was = lastStep.current;
    lastStep.current = step;
    if (was === 0 && step > 0) {
      profileEl.current?.scrollIntoView({ behavior: reducedMotion() ? "auto" : "smooth", block: "start" });
      tourEl.current?.focus({ preventScroll: true });
    }
  }, [step]);

  const founderView = view === "founder";
  const current = step ? TOUR[step - 1] : undefined;
  const tourKey = current ? current[0] : "";
  const tour = {
    pitch: tourKey === "pitch" ? "tour-on" : "",
    details: tourKey === "details" ? "tour-on" : "",
    evidence: tourKey === "evidence" ? "tour-on" : "",
    intro: tourKey === "intro" ? "tour-on" : "",
  };
  const openModule = tourKey === "revenue" ? "revenue" : module;

  const modules = MODULES.map(([id, name, summary, ev, progress, submitted, checked, when, who]) => ({
    name,
    summary,
    status: founderView ? PROGRESS_NAME[progress] : EVIDENCE_NAME[ev],
    chipCls: founderView ? PROGRESS_CLASS[progress] : EVIDENCE_CLASS[ev],
    icReviewed: !founderView && ev === "reviewed",
    icThird: !founderView && ev === "third",
    icSubmitted: !founderView && ev === "submitted",
    icNone: !founderView && ev === "none",
    icDone: founderView && progress === "done",
    icProgress: founderView && progress === "progress",
    icAction: founderView && progress === "action",
    open: openModule === id,
    panelId: `mod-${id}`,
    submitted,
    checked,
    when,
    who,
    showWho: founderView,
    tourCls: tourKey === "revenue" && id === "revenue" ? "tour-on" : "",
    toggle: () => setModule((open) => (open === id ? "" : id)),
  }));

  return {
    ...nav,
    ...walk,
    playerRef,
    hasSide: Boolean(nav.side),
    sideName: nav.side === "investor" ? "investor" : "founder",
    isFounderSide: nav.side === "founder",
    isInvestorSide: nav.side === "investor",
    cardNoteOpen: cardNote,
    toggleCardNote: () => setCardNote((open) => !open),
    watchHero: () => playerRef.current?.open("mdp"),

    isInvestorView: !founderView,
    isFounderView: founderView,
    showInvestorView: () => setView("investor"),
    showFounderView: () => {
      setView("founder");
      setStep(0);
      setIntroNote(false);
    },
    introNoteOpen: introNote && !founderView,
    requestProfile: () => setIntroNote((open) => !open),
    modules,
    nextSteps: NEXT_STEPS,

    touring: step > 0,
    notTouring: step === 0,
    tour,
    tourStep: step,
    tourTitle: current ? current[1] : "",
    tourText: current ? current[2] : "",
    tourFirst: step <= 1,
    tourNextLabel: step === 5 ? "Finish" : "Next",
    startTour: () => {
      setStep(1);
      setView("investor");
      setModule("");
      setIntroNote(false);
    },
    tourBack: () => setStep((s) => (s > 1 ? s - 1 : s)),
    tourNext: () => setStep((s) => (s >= 5 ? 0 : s + 1)),
    endTour: () => setStep(0),
    tourRef: (el: HTMLDivElement | null) => {
      tourEl.current = el;
    },
    profileRef: (el: HTMLDivElement | null) => {
      profileEl.current = el;
    },
  };
}

export type HomeVals = ReturnType<typeof useHomeVals>;

export default function HomePage() {
  return <HomeView v={useHomeVals()} />;
}
