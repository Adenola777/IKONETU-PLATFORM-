// The home page: the sample profile with its investor and founder views, the guided tour and the notes.
// Ported on 17 October 2026 from apps/web/components/site/pages/home.tsx. The walkthrough video was taken
// off the page on 21 October 2026, and the profile moved to the eleven areas of the IkonetU Score.
import { navVals, readStoredSide } from "../side.js";

const TOUR = [
  ["pitch", "The pitch", "Every profile starts with a one-minute pitch. Investors watch it first, with captions."],
  ["details", "The details and the ask", "Stage, location, sector, what the founder is raising, and the readiness check across eleven areas."],
  ["evidence", "The evidence", "Eleven areas show what the founder has added, who supplied each piece and whether IkonetU reviewed it."],
  ["revenue", "How one piece of evidence was reviewed", "Revenue is open as an example. It shows what was submitted, how it was reviewed and when."],
  ["intro", "The introduction", "An investor who wants to talk asks for an introduction, and the founder decides."],
];

// id, name, summary, evidence status, founder status, submitted, review, date, who can see
const MODULES = [
  ["identity", "Identity", "Founder's national ID", "reviewed", "done", "Amara Okafor's national identity number and passport.", "A reviewer matched the name and photograph with the passport.", "24 September 2026", "Investors see your description, this status and what was compared. Your identity documents stay with you and the reviewer."],
  ["registration", "Registration", "Company registration", "third", "done", "A certificate of incorporation naming Amara Okafor as a director.", "The registration matches the record in the CAC public registry.", "25 September 2026", "Investors see your description, this status and what was compared. The certificate stays with you and the reviewer."],
  ["tools", "Business tools", "Company email and website", "submitted", "progress", "Email addresses on the company's own domain and a link to the website.", "Not reviewed by IkonetU yet.", "Added 2 October 2026", "Investors see your description and this status."],
  ["team", "Team", "4 team members", "submitted", "progress", "The roles and experience of the four people building Market Day Pay.", "Not reviewed by IkonetU yet.", "Added 30 September 2026", "Investors see your description and this status. Identity documents are never shown."],
  ["revenue", "Financial", "Revenue, last 12 months", "reviewed", "done", "Management accounts and 12 months of business bank statements.", "A reviewer compared the reported revenue with the bank statements. This is not an audit.", "3 October 2026", "Investors see your description, this status and what was compared. The statements stay with you and the reviewer."],
  ["academic", "Academic", "Degree and courses", "none", "action", "Nothing yet.", "Nothing to review yet.", "Not added", "Investors will see your description and its status once you add it."],
  ["product", "Product or operations", "Live on Android and USSD", "reviewed", "done", "A link to the Android app, the USSD short code and a test account.", "A reviewer opened both and made a test payment.", "28 September 2026", "Investors see your description, this status and what was compared. The test account stays private."],
  ["traction", "Traction", "3 signed letters of intent", "third", "done", "Signed letters of intent from three market associations in Lagos.", "A reviewer confirmed each letter with the association that signed it.", "1 October 2026", "Investors see your description, this status and what was compared. The signatories’ contact details stay private."],
  ["recognition", "Recognition", "Awards and endorsements", "none", "action", "Nothing yet.", "Nothing to review yet.", "Not added", "Investors will see your description and its status once you add it."],
  ["governance", "Governance", "Privacy policy and terms", "submitted", "progress", "Links to the privacy policy and the terms on the website.", "Not reviewed by IkonetU yet.", "Added 2 October 2026", "Investors see your description and this status."],
  ["media", "Pitch and media", "Pitch video and deck", "submitted", "progress", "The one-minute pitch, a pitch deck and the app store page.", "Not reviewed by IkonetU yet.", "Added 2 October 2026", "Investors see your description and this status."],
];

const EVIDENCE_NAME = { reviewed: "Platform reviewed", third: "Third-party evidence available", submitted: "Founder submitted", none: "Not added yet" };
const EVIDENCE_CLASS = { reviewed: "chip-i", third: "chip-io", submitted: "chip-n", none: "chip-none" };
const PROGRESS_NAME = { done: "Complete", progress: "In progress", action: "Action needed" };
const PROGRESS_CLASS = { done: "chip-n", progress: "chip-n", action: "chip-f" };

// The three steps the score engine gives the sample profile's evidence, with each area's reason (AREA_WHY).
const NEXT_STEPS = [
  { num: 1, title: "Grants received", why: "Customers and partners show that the market wants what the company sells.", action: "Add evidence" },
  { num: 2, title: "Elevator pitch video, 60 to 90 seconds", why: "A clear pitch and visible progress let investors check what the founder says.", action: "Add evidence" },
  { num: 3, title: "Full-time employees on payroll", why: "Investors back people, so they want to see who is building the company.", action: "Add evidence" },
];

function reducedMotion() {
  try {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch {
    return false;
  }
}

export default {
  initial: () => ({ view: "investor", module: "", step: 0, introNote: false, cardNote: false }),
  // A remembered founder opens the profile in the founder view.
  mounted(_ctx, component) {
    if (readStoredSide() === "founder") component.set((s) => ({ ...s, view: "founder" }));
  },
  // Starting the tour scrolls to the profile and moves focus to the tour panel.
  after(prev, next, ctx) {
    if (prev.step === 0 && next.step > 0) {
      if (ctx.profileEl) ctx.profileEl.scrollIntoView({ behavior: reducedMotion() ? "auto" : "smooth", block: "start" });
      if (ctx.tourEl) ctx.tourEl.focus({ preventScroll: true });
    }
  },
  vals(s, set, ctx) {
    const nav = navVals();
    const founderView = s.view === "founder";
    const current = s.step ? TOUR[s.step - 1] : undefined;
    const tourKey = current ? current[0] : "";
    const tour = {
      pitch: tourKey === "pitch" ? "tour-on" : "",
      details: tourKey === "details" ? "tour-on" : "",
      evidence: tourKey === "evidence" ? "tour-on" : "",
      intro: tourKey === "intro" ? "tour-on" : "",
    };
    const openModule = tourKey === "revenue" ? "revenue" : s.module;

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
      toggle: () => set((now) => ({ ...now, module: now.module === id ? "" : id })),
    }));

    return {
      ...nav,
      playerRef: null,
      hasSide: Boolean(nav.side),
      sideName: nav.side === "investor" ? "investor" : "founder",
      isFounderSide: nav.side === "founder",
      isInvestorSide: nav.side === "investor",
      cardNoteOpen: s.cardNote,
      toggleCardNote: () => set((now) => ({ ...now, cardNote: !now.cardNote })),
      watchHero: () => ctx.registry.player && ctx.registry.player.open("mdp"),

      isInvestorView: !founderView,
      isFounderView: founderView,
      showInvestorView: () => set((now) => ({ ...now, view: "investor" })),
      showFounderView: () => set((now) => ({ ...now, view: "founder", step: 0, introNote: false })),
      introNoteOpen: s.introNote && !founderView,
      requestProfile: () => set((now) => ({ ...now, introNote: !now.introNote })),
      modules,
      nextSteps: NEXT_STEPS,

      touring: s.step > 0,
      notTouring: s.step === 0,
      tour,
      tourStep: s.step,
      tourTitle: current ? current[1] : "",
      tourText: current ? current[2] : "",
      tourFirst: s.step <= 1,
      tourNextLabel: s.step === 5 ? "Finish" : "Next",
      startTour: () => set((now) => ({ ...now, step: 1, view: "investor", module: "", introNote: false })),
      tourBack: () => set((now) => ({ ...now, step: now.step > 1 ? now.step - 1 : now.step })),
      tourNext: () => set((now) => ({ ...now, step: now.step >= 5 ? 0 : now.step + 1 })),
      endTour: () => set((now) => ({ ...now, step: 0 })),
      tourRef: (el) => {
        ctx.tourEl = el;
      },
      profileRef: (el) => {
        ctx.profileEl = el;
      },
    };
  },
};
