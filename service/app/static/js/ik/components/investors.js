// The for-investors page: the sample discovery with its filters, previews and introduction notes.
// Ported on 17 October 2026 from apps/web/components/site/pages/investors.tsx. Since 21 October 2026 each
// sample's readiness check counts the eleven areas of the IkonetU Score (strong, building, gap).
import { captionAt, reducedMotion } from "../pitches.js";
import { navVals } from "../side.js";

const FOUNDERS = [
  { id: "chama", name: "Chama Books", city: "Nairobi", country: "Kenya", sector: "Fintech", stage: "Earning revenue", length: "0:58", days: 9, n90: 6, lv: [4, 4, 3], ev: [["Revenue", "reviewed"], ["Team", "submitted"]] },
  { id: "clinic", name: "Clinic Queue", city: "Nairobi", country: "Kenya", sector: "Health", stage: "Scaling", length: "0:55", days: 12, n90: 4, lv: [5, 4, 2], ev: [["Registration", "third"], ["Revenue", "reviewed"]] },
  { id: "farmgate", name: "Farmgate Ledger", city: "Accra", country: "Ghana", sector: "Agritech", stage: "Earning revenue", length: "0:59", days: 41, n90: 2, lv: [5, 3, 3], ev: [["Revenue", "reviewed"], ["Registration", "submitted"]] },
  { id: "harvest", name: "Harvest Cold Rooms", city: "Kumasi", country: "Ghana", sector: "Agritech", stage: "First version", length: "0:57", days: 64, n90: 1, lv: [2, 4, 5], ev: [["Registration", "submitted"]] },
  { id: "learnloop", name: "LearnLoop", city: "Lagos", country: "Nigeria", sector: "Edtech", stage: "First version", length: "1:00", days: 5, n90: 5, lv: [3, 5, 3], ev: [["Registration", "third"], ["Revenue", "submitted"]] },
  { id: "mdp", name: "Market Day Pay", city: "Lagos", country: "Nigeria", sector: "Fintech", stage: "Earning revenue", length: "1:00", days: 2, n90: 8, lv: [5, 4, 2], ev: [["Revenue", "reviewed"], ["Registration", "third"]] },
];

const GROUPS = [
  ["sector", "Sector", ["Fintech", "Agritech", "Edtech", "Health", "Other"]],
  ["stage", "Stage", ["Idea", "First version", "Earning revenue", "Scaling"]],
  ["geo", "Geography", ["Nigeria", "Ghana", "Kenya"]],
  ["evidence", "Evidence", ["Revenue reviewed", "Registry record", "Any reviewed evidence"]],
  ["momentum", "Last updated", ["In the last 30 days"]],
];

const NO_FILTERS = { sector: [], stage: [], geo: [], evidence: [], momentum: [] };
const STATUS_NAME = { reviewed: "Platform reviewed", third: "Third-party evidence", submitted: "Founder submitted" };
const STATUS_CLASS = { reviewed: "chip-i", third: "chip-io", submitted: "chip-n" };
const PREVIEW_SECONDS = 5;

function stopPreview(ctx) {
  if (ctx.timer) clearInterval(ctx.timer);
  ctx.timer = null;
}

export default {
  initial: (ctx) => {
    // A preview that has finished does not start again until the pointer leaves the thumbnail.
    ctx.doneId = "";
    return { filters: NO_FILTERS, requested: "", preview: { id: "", at: 0 } };
  },
  vals(s, set, ctx) {
    const { filters } = s;
    const has = (f, area, status) => f.ev.some(([a, st]) => a === area && st === status);
    const matches = FOUNDERS.filter((f) => {
      if (filters.sector.length && !filters.sector.includes(f.sector)) return false;
      if (filters.stage.length && !filters.stage.includes(f.stage)) return false;
      if (filters.geo.length && !filters.geo.includes(f.country)) return false;
      if (filters.evidence.includes("Revenue reviewed") && !has(f, "Revenue", "reviewed")) return false;
      if (filters.evidence.includes("Registry record") && !has(f, "Registration", "third")) return false;
      if (filters.evidence.includes("Any reviewed evidence") && !f.ev.some(([, st]) => st === "reviewed" || st === "third")) return false;
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
          toggle: () => set((now) => ({
            ...now,
            filters: { ...now.filters, [key]: on ? now.filters[key].filter((x) => x !== value) : [...now.filters[key], value] },
            requested: "",
          })),
        };
      }),
    }));

    const results = matches.map((f) => {
      const previewing = s.preview.id === f.id;
      return {
        name: f.name,
        length: f.length,
        strong: f.lv[0],
        building: f.lv[1],
        gap: f.lv[2],
        cells: Array.from({ length: 11 }, (_, i) => ({ c: i < f.lv[0] ? "s" : i < f.lv[0] + f.lv[1] ? "b" : "" })),
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
        previewCaption: previewing ? captionAt(f.id, s.preview.at) : "",
        previewPct: previewing ? Math.round((s.preview.at / PREVIEW_SECONDS) * 100) : 0,
        noteOpen: s.requested === f.id,
        noteId: `note-${f.id}`,
        watch: () => {
          stopPreview(ctx);
          set((now) => ({ ...now, preview: { id: "", at: 0 } }));
          if (ctx.registry.player) ctx.registry.player.open(f.id);
        },
        // Pointing at a thumbnail plays a muted preview of five seconds. It never runs under reduced motion.
        previewStart: () => {
          if (reducedMotion() || ctx.doneId === f.id) return;
          stopPreview(ctx);
          let at = 0;
          set((now) => ({ ...now, preview: { id: f.id, at } }));
          ctx.timer = setInterval(() => {
            at = Math.min(PREVIEW_SECONDS, at + 0.25);
            if (at >= PREVIEW_SECONDS) {
              stopPreview(ctx);
              ctx.doneId = f.id;
              set((now) => ({ ...now, preview: { id: "", at: 0 } }));
            } else {
              set((now) => ({ ...now, preview: { id: f.id, at } }));
            }
          }, 250);
        },
        request: () => set((now) => ({ ...now, requested: now.requested === f.id ? "" : f.id })),
      };
    });

    const count = Object.values(filters).reduce((n, list) => n + list.length, 0);
    return {
      ...navVals(),
      playerRef: null,
      filterGroups,
      results,
      noMatches: matches.length === 0,
      noFilters: count === 0,
      matchText: `${matches.length === 1 ? "1 sample founder matches" : `${matches.length} sample founders match`}. Sorted by company name.`,
      clearFilters: () => set((now) => ({ ...now, filters: NO_FILTERS, requested: "" })),
      previewStop: () => {
        ctx.doneId = "";
        stopPreview(ctx);
        set((now) => (now.preview.id ? { ...now, preview: { id: "", at: 0 } } : now));
      },
    };
  },
};
