"use client";

import { useState } from "react";
import { useNavVals } from "../side";
import { ForFoundersView } from "../views/founders.view";

type Level = 1 | 2 | 3;

const AREAS: [string, Level, string, string][] = [
  ["Identity", 3, "Whether the company is registered and who stands behind it.", "A registry record or certificate of incorporation, and the founder's government ID."],
  ["Legal", 2, "Whether the company can trade legally.", "A tax registration, contracts, licences or IP filings."],
  ["Financial", 3, "Whether the numbers are recorded and can be checked.", "Bank or mobile money statements, monthly accounts and revenue for the last 12 months."],
  ["Product", 3, "Whether the product exists, works and is used.", "A live link, a test account, signed orders or usage data."],
  ["Market", 3, "Whether the problem is real and people want the product.", "Customer interviews, signed pilot or intent letters, or market research."],
  ["Team", 2, "Who is building the company and whether they can deliver the plan.", "Team members and their credentials, or a programme they completed."],
  ["Media and presence", 2, "Whether investors can check the company in public.", "A live website, a social profile, a pitch deck or press coverage."],
  ["Operations", 1, "Whether the business can deliver.", "Supplier contracts, premises or the tools the business runs on."],
];
const LEVEL_NAME: Record<Level, string> = { 3: "Strong", 2: "Building", 1: "Gap" };

// Sample updates, by week number counted from the week of 20 July 2026.
const WEEK_NOTES: Record<number, string[]> = {
  1: ["Started a pilot with a market traders association."],
  2: ["Switched on USSD payments for every trader."],
  4: ["Added three months of business bank statements."],
  7: ["Reached 1,000 active traders."],
  8: ["Hired a field agent for a second market."],
  11: ["Added two merchant references."],
  12: ["Revenue evidence reviewed by IkonetU.", "Shipped receipt sharing on WhatsApp."],
};
const MONDAY = Date.UTC(2026, 6, 20);
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function weekLabel(i: number) {
  const d = new Date(MONDAY + i * 7 * 86400000);
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} 2026`;
}

function useForFoundersVals() {
  const nav = useNavVals();
  const [area, setArea] = useState("");
  const [week, setWeek] = useState(12);

  const areas = AREAS.map(([name, level, counts, example], i) => {
    const key = `area-${i}`;
    return {
      name,
      level: LEVEL_NAME[level],
      counts,
      example,
      c1: level === 3 ? "s" : "b",
      c2: level >= 2 ? (level === 3 ? "s" : "b") : "",
      c3: level === 3 ? "s" : "",
      open: area === key,
      panelId: key,
      toggle: () => setArea((open) => (open === key ? "" : key)),
    };
  });

  const weeks = Array.from({ length: 13 }, (_, i) => {
    const notes = WEEK_NOTES[i] ?? [];
    return {
      name: `Week of ${weekLabel(i)}${notes.length ? `, ${notes.length} ${notes.length === 1 ? "update" : "updates"}` : ", no update"}`,
      bg: notes.length ? "#F26B1D" : "#E7EAF0",
      on: week === i,
      pick: () => setWeek(i),
    };
  });
  const chosen = WEEK_NOTES[week] ?? [];

  return {
    ...nav,
    areas,
    weeks,
    weekTitle: `Week of ${weekLabel(week)}`,
    weekUpdates: chosen.map((text) => ({ text })),
    weekEmpty: chosen.length === 0,
  };
}

export type ForFoundersVals = ReturnType<typeof useForFoundersVals>;

export default function ForFoundersPage() {
  return <ForFoundersView v={useForFoundersVals()} />;
}
