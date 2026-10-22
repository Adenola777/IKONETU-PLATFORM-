// The readiness self-check: one question for each of the eleven areas of the IkonetU Score, and a result.
// Nothing is saved or sent. Ported on 17 October 2026 from apps/web/components/site/pages/readiness.tsx.
// Since 21 October 2026 the areas follow AREAS in app/product.py, each reason is that area's AREA_WHY, and
// each weight is the area's weight in rubric v3 (app/score_engine/rubric.py), which orders the first steps.
import { navVals } from "../side.js";

// name, weight used to order the first steps, question, what to add, why it matters, what to keep doing
const AREAS = [
  ["Identity", 9, "Can you show a government ID, such as your national ID number or passport, with your full legal name?", "Upload your government ID and confirm your legal name and address.", "investors want to know who stands behind the company.", "Replace your ID before it expires."],
  ["Registration", 11, "Is your business registered, with a tax identification number?", "Upload your registration certificate and your tax identification number.", "a registered company with a tax number can sign contracts and take investment.", "Add licences and filings as you receive them."],
  ["Business tools", 7, "Does the business use an email address on its own domain, a website and written processes?", "Add your company email domain, your website and your process documents.", "working business tools show that the company runs day to day.", "Update your documents when the way you work changes."],
  ["Team", 9, "Can you show who works in the business, such as staff on payroll, co-founders and advisers?", "Add your team, your payroll records and your advisers.", "investors back people, so they want to see who is building the company.", "Add new people as they join."],
  ["Financial", 14, "Can you show six months of bank or mobile money statements, and revenue that comes in regularly?", "Upload six months of bank or mobile money statements.", "investors can check numbers that are written down.", "Add each month's statement when the month closes."],
  ["Academic", 6, "Can you show your studies or training, such as a degree, a certificate or an entrepreneurship course?", "Add your degree, certificates or courses that relate to the business.", "study and training show the skills the founder brings.", "Add new certificates when you complete them."],
  ["Product or operations", 12, "Is your product live, or can you show the business operating, with users or customers?", "Add a link to the live product, or records of the business operating.", "a product or a working operation is easier to believe than a description.", "Post an update each time you ship or open somewhere new."],
  ["Traction", 14, "Can you show paying customers, signed letters of intent, partnerships or funding received?", "Add your customer numbers, letters of intent and partnership agreements.", "customers and partners show that the market wants what the company sells.", "Update your customer numbers every month."],
  ["Recognition", 4, "Has the business or a founder won an award, a fellowship, a competition or a mentor's endorsement?", "Add the award, the fellowship or a letter from your mentor.", "outside recognition shows that others have judged the work.", "Add each new award as it comes."],
  ["Governance", 4, "Does the company publish a privacy policy and terms, and keep its tax and annual filings up to date?", "Add your tax compliance certificate, your policies and your annual returns.", "good governance lowers the risk of backing the company.", "Renew certificates and filings before they lapse."],
  ["Pitch and media", 10, "Do you have a pitch video of 60 to 90 seconds, a pitch deck and a product demo?", "Record your pitch video and add your deck and a demo.", "a clear pitch and visible progress let investors check what the founder says.", "Add new videos and coverage as they appear."],
];
const LABELS = ["Not yet", "Partly", "Yes, and I can show it"];

export default {
  initial: () => ({ current: 0, answers: {}, error: false, done: false }),
  // The result heading takes focus when the result appears.
  after(prev, next, ctx) {
    if (!prev.done && next.done && ctx.resultEl) ctx.resultEl.focus();
  },
  vals(s, set, ctx) {
    const { current, answers } = s;
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
    const count = (v) => scored.filter((a) => a.v === v).length;
    const areaWord = (n) => `${n} ${n === 1 ? "area" : "areas"}`;

    return {
      ...navVals(),
      formRef: (el) => {
        ctx.formEl = el;
      },
      resultRef: (el) => {
        ctx.resultEl = el;
      },
      questions,
      number: current + 1,
      areaName: AREAS[current] ? AREAS[current][0] : "",
      pct: Math.round(((current + (answers[current] !== undefined ? 1 : 0)) / AREAS.length) * 100),
      isFirst: current === 0,
      nextLabel: current === AREAS.length - 1 ? "See my result" : "Next",
      hasError: s.error,
      done: s.done,
      summary: `You answered yes in ${areaWord(count(2))}, partly in ${areaWord(count(1))} and not yet in ${areaWord(count(0))}.`,
      first,
      strong,
      noneFirst: first.length === 0,
      noneStrong: strong.length === 0,
      answer: (e) => {
        const target = e.target;
        if (!(target instanceof HTMLInputElement) || target.type !== "radio") return;
        const i = Number(target.name.slice(1));
        set((now) => ({ ...now, answers: { ...now.answers, [i]: Number(target.value) }, error: false }));
      },
      next: (e) => {
        e.preventDefault();
        if (answers[current] === undefined) {
          set((now) => ({ ...now, error: true }));
          return;
        }
        if (current === AREAS.length - 1) set((now) => ({ ...now, error: false, done: true }));
        else set((now) => ({ ...now, error: false, current: current + 1 }));
      },
      back: () => {
        if (current > 0) set((now) => ({ ...now, current: current - 1, error: false }));
      },
      restart: () => {
        if (ctx.formEl) ctx.formEl.reset();
        set({ current: 0, answers: {}, error: false, done: false });
      },
    };
  },
};
