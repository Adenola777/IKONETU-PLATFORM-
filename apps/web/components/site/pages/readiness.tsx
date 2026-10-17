"use client";

import { useEffect, useRef, useState } from "react";
import { useNavVals } from "../side";
import { ReadinessCheckView } from "../views/readiness.view";

// name, weight used to order the first steps, question, what to add, why it matters, what to keep doing
const AREAS: [string, number, string, string, string, string][] = [
  ["Identity", 100, "Is your company registered, and does the record name you as a founder or director?", "Upload your certificate of incorporation or registry record.", "investors want to know the company exists and who stands behind it.", "Keep the record current when directors change."],
  ["Legal", 100, "Is your company registered for tax, and do you hold the contracts, licences or IP filings your business needs?", "Upload your tax registration and your key contracts or licences.", "a company that can trade legally carries less risk.", "Add new contracts and licences as you sign them."],
  ["Financial", 200, "Do you keep monthly accounts or bank statements, and can you show revenue for the last 12 months?", "Upload bank or mobile money statements and your monthly accounts.", "recorded numbers can be reviewed. Remembered numbers cannot.", "Add each month's records when the month closes."],
  ["Product", 200, "Is your product live, and can you show people using it or paying for it?", "Add a link to the live product and evidence such as orders or usage data.", "a product investors can try is easier to believe than a description.", "Post an update each time you ship a major change."],
  ["Market", 100, "Have you documented customer interviews, signed pilot or intent letters, or market research?", "Upload interview notes, letters of intent or a market research document.", "investors want to know the problem exists before they look at the solution.", "Keep your research dated, so investors can see it is current."],
  ["Team", 150, "Can you show who is building the company and the experience the plan needs?", "Add your team members and their credentials.", "investors back people, so they want to see who is building the company.", "Add new team members as they join."],
  ["Media and presence", 100, "Do you have a live website, a pitch deck or one-pager, and any press coverage?", "Add your website, your deck and links to any coverage.", "a public presence lets investors check what you say.", "Add new coverage when it appears."],
  ["Operations", 50, "Can you show how the business runs, such as supplier contracts, premises or the tools you use?", "Upload supplier contracts or other operational evidence.", "operational evidence shows the business can deliver.", "Update it when suppliers or premises change."],
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
