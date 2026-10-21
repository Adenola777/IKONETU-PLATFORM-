// The for-founders page: the eleven areas of the IkonetU Score and the sample momentum weeks.
// Ported on 17 October 2026 from apps/web/components/site/pages/founders.tsx. The areas follow AREAS in
// app/product.py since 21 October 2026, and the sample levels match the sample profile on the home page.
import { navVals } from "../side.js";

const AREAS = [
  ["Identity", 3, "Who the founder is, verified against a government ID.", "A national ID number or passport, and your full legal name and address."],
  ["Registration", 3, "Whether the business is registered and can trade.", "A registration certificate, a tax identification number and any operating licence."],
  ["Business tools", 2, "Whether the company runs on professional tools.", "An email address on your own domain, your website and your process documents."],
  ["Team", 2, "Who is building the company.", "Staff on payroll, co-founders, advisers and the founders' backgrounds."],
  ["Financial", 3, "Whether money comes in and is recorded.", "Six months of bank or mobile money statements, recurring revenue and a payment gateway."],
  ["Academic", 1, "The skills the founder brings from study and training.", "A degree, certifications, research or an entrepreneurship course."],
  ["Product or operations", 3, "Whether the product is live or the business is operating.", "A live product with users, a published app, or a verified location with customers."],
  ["Traction", 3, "Whether customers and partners want what you sell.", "Verified customer numbers, letters of intent, partnerships, grants or prior funding."],
  ["Recognition", 1, "Whether others have judged the work.", "Awards, fellowships, competition wins or a mentor's endorsement."],
  ["Governance", 2, "Whether the company is run with care.", "A tax compliance certificate, annual returns, a privacy policy and a board."],
  ["Pitch and media", 2, "Whether investors can see and hear the pitch.", "A pitch video of 60 to 90 seconds, a pitch deck, a demo video and press clips."],
];
const LEVEL_NAME = { 3: "Strong", 2: "Building", 1: "Gap" };

// Sample updates, by week number counted from the week of 20 July 2026.
const WEEK_NOTES = {
  1: ["Started a pilot with a market traders association."],
  2: ["Switched on USSD payments for every trader."],
  4: ["Added three months of business bank statements."],
  7: ["Reached 1,000 active traders."],
  8: ["Hired a field agent for a second market."],
  11: ["Added two merchant references."],
  12: ["Revenue evidence verified by IkonetU.", "Shipped receipt sharing on WhatsApp."],
};
const MONDAY = Date.UTC(2026, 6, 20);
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function weekLabel(i) {
  const d = new Date(MONDAY + i * 7 * 86400000);
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} 2026`;
}

export default {
  initial: () => ({ area: "", week: 12 }),
  vals(s, set) {
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
        open: s.area === key,
        panelId: key,
        toggle: () => set((now) => ({ ...now, area: now.area === key ? "" : key })),
      };
    });
    const weeks = Array.from({ length: 13 }, (_, i) => {
      const notes = WEEK_NOTES[i] || [];
      return {
        name: `Week of ${weekLabel(i)}${notes.length ? `, ${notes.length} ${notes.length === 1 ? "update" : "updates"}` : ", no update"}`,
        bg: notes.length ? "#F26B1D" : "#E7EAF0",
        on: s.week === i,
        pick: () => set((now) => ({ ...now, week: i })),
      };
    });
    const chosen = WEEK_NOTES[s.week] || [];
    return {
      ...navVals(),
      areas,
      weeks,
      weekTitle: `Week of ${weekLabel(s.week)}`,
      weekUpdates: chosen.map((text) => ({ text })),
      weekEmpty: chosen.length === 0,
    };
  },
};
