"use client";

import { useEffect, useRef, useState } from "react";
import { captionAt, type PitchId, type PitchPlayerHandle } from "../pitch-player";
import { useNavVals } from "../side";
import { ForInvestorsView } from "../views/investors.view";

type Status = "reviewed" | "third" | "submitted";
type Group = "sector" | "stage" | "geo" | "evidence" | "momentum";
type Filters = Record<Group, string[]>;

const FOUNDERS: { id: PitchId; name: string; city: string; country: string; sector: string; stage: string; length: string; days: number; n90: number; lv: [number, number, number]; ev: [string, Status][] }[] = [
  { id: "chama", name: "Chama Books", city: "Nairobi", country: "Kenya", sector: "Fintech", stage: "Earning revenue", length: "0:58", days: 9, n90: 6, lv: [3, 3, 2], ev: [["Revenue", "reviewed"], ["Team", "submitted"]] },
  { id: "clinic", name: "Clinic Queue", city: "Nairobi", country: "Kenya", sector: "Health", stage: "Scaling", length: "0:55", days: 12, n90: 4, lv: [3, 4, 1], ev: [["Registration", "third"], ["Revenue", "reviewed"]] },
  { id: "farmgate", name: "Farmgate Ledger", city: "Accra", country: "Ghana", sector: "Agritech", stage: "Earning revenue", length: "0:59", days: 41, n90: 2, lv: [4, 2, 2], ev: [["Revenue", "reviewed"], ["Registration", "submitted"]] },
  { id: "harvest", name: "Harvest Cold Rooms", city: "Kumasi", country: "Ghana", sector: "Agritech", stage: "First version", length: "0:57", days: 64, n90: 1, lv: [1, 3, 4], ev: [["Registration", "submitted"]] },
  { id: "learnloop", name: "LearnLoop", city: "Lagos", country: "Nigeria", sector: "Edtech", stage: "First version", length: "1:00", days: 5, n90: 5, lv: [2, 4, 2], ev: [["Registration", "third"], ["Revenue", "submitted"]] },
  { id: "mdp", name: "Market Day Pay", city: "Lagos", country: "Nigeria", sector: "Fintech", stage: "Earning revenue", length: "1:00", days: 2, n90: 8, lv: [4, 3, 1], ev: [["Revenue", "reviewed"], ["Registration", "third"]] },
];

const GROUPS: [Group, string, string[]][] = [
  ["sector", "Sector", ["Fintech", "Agritech", "Edtech", "Health", "Other"]],
  ["stage", "Stage", ["Idea", "First version", "Earning revenue", "Scaling"]],
  ["geo", "Geography", ["Nigeria", "Ghana", "Kenya"]],
  ["evidence", "Evidence", ["Revenue reviewed", "Registry record", "Any reviewed evidence"]],
  ["momentum", "Last updated", ["In the last 30 days"]],
];

const NO_FILTERS: Filters = { sector: [], stage: [], geo: [], evidence: [], momentum: [] };
const STATUS_NAME: Record<Status, string> = { reviewed: "Platform reviewed", third: "Third-party evidence", submitted: "Founder submitted" };
const STATUS_CLASS: Record<Status, string> = { reviewed: "chip-i", third: "chip-io", submitted: "chip-n" };
const PREVIEW_SECONDS = 5;

function reducedMotion() {
  try {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch {
    return false;
  }
}

function useForInvestorsVals() {
  const nav = useNavVals();
  const [filters, setFilters] = useState<Filters>(NO_FILTERS);
  const [requested, setRequested] = useState("");
  const [preview, setPreview] = useState<{ id: string; at: number }>({ id: "", at: 0 });
  const playerRef = useRef<PitchPlayerHandle>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  // A preview that has finished does not start again until the pointer leaves the thumbnail.
  const doneId = useRef("");

  const stopPreview = () => {
    if (timer.current) clearInterval(timer.current);
    timer.current = null;
  };
  useEffect(() => stopPreview, []);

  const has = (f: (typeof FOUNDERS)[number], area: string, status: Status) => f.ev.some(([a, s]) => a === area && s === status);
  const matches = FOUNDERS.filter((f) => {
    if (filters.sector.length && !filters.sector.includes(f.sector)) return false;
    if (filters.stage.length && !filters.stage.includes(f.stage)) return false;
    if (filters.geo.length && !filters.geo.includes(f.country)) return false;
    if (filters.evidence.includes("Revenue reviewed") && !has(f, "Revenue", "reviewed")) return false;
    if (filters.evidence.includes("Registry record") && !has(f, "Registration", "third")) return false;
    if (filters.evidence.includes("Any reviewed evidence") && !f.ev.some(([, s]) => s === "reviewed" || s === "third")) return false;
    if (filters.momentum.length && f.days > 30) return false;
    return true;
  });

  const filterGroups = GROUPS.map(([key, label, chips]) => ({
    label,
    chips: chips.map((value) => {
      const on = filters[key].includes(value);
      return {
        label: value,
        on,
        toggle: () => {
          setFilters((now) => ({ ...now, [key]: on ? now[key].filter((x) => x !== value) : [...now[key], value] }));
          setRequested("");
        },
      };
    }),
  }));

  const results = matches.map((f) => {
    const previewing = preview.id === f.id;
    return {
      name: f.name,
      length: f.length,
      strong: f.lv[0],
      building: f.lv[1],
      gap: f.lv[2],
      cells: Array.from({ length: 8 }, (_, i) => ({ c: i < f.lv[0] ? "s" : i < f.lv[0] + f.lv[1] ? "b" : "" })),
      meta: `${f.city}, ${f.country} · ${f.sector} · ${f.stage} · ${f.length} pitch · ${f.n90} ${f.n90 === 1 ? "update" : "updates"} in 90 days`,
      momText: `Updated ${f.days} days ago`,
      momCls: f.days <= 30 ? "chip-f" : "chip-n",
      momDot: f.days <= 30 ? "#F26B1D" : "#858FA1",
      watchLabel: `Watch the ${f.name} pitch, ${f.length}`,
      evidence: f.ev.map(([area, status]) => ({
        label: `${area} · ${STATUS_NAME[status]}`,
        cls: STATUS_CLASS[status],
        reviewed: status === "reviewed",
        third: status === "third",
        submitted: status === "submitted",
      })),
      previewing,
      previewCaption: previewing ? captionAt(f.id, preview.at) : "",
      previewPct: previewing ? Math.round((preview.at / PREVIEW_SECONDS) * 100) : 0,
      noteOpen: requested === f.id,
      noteId: `note-${f.id}`,
      watch: () => {
        stopPreview();
        setPreview({ id: "", at: 0 });
        playerRef.current?.open(f.id);
      },
      // Pointing at a thumbnail plays a muted preview of five seconds. It never runs under reduced motion.
      previewStart: () => {
        if (reducedMotion() || doneId.current === f.id) return;
        stopPreview();
        let at = 0;
        setPreview({ id: f.id, at });
        timer.current = setInterval(() => {
          at = Math.min(PREVIEW_SECONDS, at + 0.25);
          if (at >= PREVIEW_SECONDS) {
            stopPreview();
            doneId.current = f.id;
            setPreview({ id: "", at: 0 });
          } else {
            setPreview({ id: f.id, at });
          }
        }, 250);
      },
      request: () => setRequested((open) => (open === f.id ? "" : f.id)),
    };
  });

  const count = Object.values(filters).reduce((n, list) => n + list.length, 0);
  return {
    ...nav,
    playerRef,
    filterGroups,
    results,
    noMatches: matches.length === 0,
    noFilters: count === 0,
    matchText: `${matches.length === 1 ? "1 sample founder matches" : `${matches.length} sample founders match`}. Sorted by company name.`,
    clearFilters: () => {
      setFilters(NO_FILTERS);
      setRequested("");
    },
    previewStop: () => {
      doneId.current = "";
      stopPreview();
      setPreview((now) => (now.id ? { id: "", at: 0 } : now));
    },
  };
}

export type ForInvestorsVals = ReturnType<typeof useForInvestorsVals>;

export default function ForInvestorsPage() {
  return <ForInvestorsView v={useForInvestorsVals()} />;
}
