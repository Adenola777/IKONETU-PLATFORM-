"use client";

import { useEffect, useRef, useState } from "react";
import { useNavVals } from "../side";
import { ReadinessCheckView } from "../views/readiness.view";

// name, weight used to order the first steps, question, what to add, why it matters, what to keep doing
const AREAS: [string, number, string, string, string, string][] = [
  ["Problem and market", 120, "Can you show that the problem is real, for example with customer interviews or market research?", "Upload interview notes or market research.", "investors want to know the problem exists before they look at the solution.", "Keep your research dated, so investors can see it is current."],
  ["Product", 140, "Is your product live, and are people using it?", "Add a link to the live product and a test account.", "a product investors can try is easier to believe than a description.", "Add a note each time you ship a major change."],
  ["Traction", 160, "Can you show growth over the last six months, in users, volume or revenue?", "Add six months of user, volume or revenue figures.", "figures over time show direction, not just a single good month.", "Add each month’s figures when the month closes."],
  ["Customers", 120, "Do you have signed contracts, letters of intent or customer references?", "Collect references or letters of intent from customers.", "customers saying it themselves carries more weight than the founder saying it.", "Keep references current and ask new customers too."],
  ["Business model", 120, "Can you explain your pricing and what each sale costs you?", "Write down your pricing and the cost of each sale.", "it shows how the company makes money.", "Update it when your pricing or costs change."],
  ["Team", 120, "Does your team have the experience the plan needs, and will each member confirm their role?", "Invite your team members to confirm their roles.", "confirmed roles show who is building the company.", "Add new team members as they join."],
  ["Financials", 120, "Do you keep monthly accounts or bank statements for the business?", "Start monthly management accounts and keep the bank statements.", "recorded numbers can be reviewed. Remembered numbers cannot.", "Keep monthly accounts up to date."],
  ["Impact or strategic fit", 100, "Can you describe the outcome your business creates and how you measure it?", "Describe the outcome you create and one way to measure it.", "some investors look for a particular outcome or focus.", "Report the measure as it changes."],
];
const LABELS = ["Not yet", "Partly", "Yes, and I can show it"];

function useReadinessCheckVals() {
  const nav = useNavVals();
  const [current, setCurrent] = useState(0);
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [error, setError] = useState(false);
  const [done, setDone] = useState(false);
  const form = useRef<HTMLFormElement | null>(null);
  const result = useRef<HTMLHeadingElement | null>(null);

  // The result heading takes focus when the result appears.
  useEffect(() => {
    if (done) result.current?.focus();
  }, [done]);

  const questions = AREAS.map((a, i) => ({
    text: a[2],
    hidden: i !== current,
    opts: LABELS.map((label, value) => ({ name: `q${i}`, value: String(value), label })),
  }));
  const scored = AREAS.map((a, i) => ({ name: a[0], max: a[1], advice: a[3], why: a[4], keep: a[5], v: answers[i] }));
  const first = scored
    .filter((a) => a.v !== undefined && a.v < 2)
    .sort((x, y) => (x.v ?? 0) - (y.v ?? 0) || y.max - x.max)
    .slice(0, 3);
  const strong = scored.filter((a) => a.v === 2);
  const count = (v: number) => scored.filter((a) => a.v === v).length;
  const areaWord = (n: number) => `${n} ${n === 1 ? "area" : "areas"}`;

  return {
    ...nav,
    formRef: (el: HTMLFormElement | null) => {
      form.current = el;
    },
    resultRef: (el: HTMLHeadingElement | null) => {
      result.current = el;
    },
    questions,
    number: current + 1,
    areaName: AREAS[current]?.[0] ?? "",
    pct: Math.round(((current + (answers[current] !== undefined ? 1 : 0)) / 8) * 100),
    isFirst: current === 0,
    nextLabel: current === 7 ? "See my result" : "Next",
    hasError: error,
    done,
    summary: `You answered yes in ${areaWord(count(2))}, partly in ${areaWord(count(1))} and not yet in ${areaWord(count(0))}.`,
    first,
    strong,
    noneFirst: first.length === 0,
    noneStrong: strong.length === 0,
    answer: (e: React.FormEvent<HTMLFormElement>) => {
      const target = e.target;
      if (!(target instanceof HTMLInputElement) || target.type !== "radio") return;
      const i = Number(target.name.slice(1));
      setAnswers((now) => ({ ...now, [i]: Number(target.value) }));
      setError(false);
    },
    next: (e: React.FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      if (answers[current] === undefined) {
        setError(true);
        return;
      }
      setError(false);
      if (current === 7) setDone(true);
      else setCurrent(current + 1);
    },
    back: () => {
      if (current > 0) {
        setCurrent(current - 1);
        setError(false);
      }
    },
    restart: () => {
      form.current?.reset();
      setCurrent(0);
      setAnswers({});
      setError(false);
      setDone(false);
    },
  };
}

export type ReadinessCheckVals = ReturnType<typeof useReadinessCheckVals>;

export default function ReadinessCheckPage() {
  return <ReadinessCheckView v={useReadinessCheckVals()} />;
}
