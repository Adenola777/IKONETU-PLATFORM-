// The sample pitches. They have no video, so a timer runs the captions to show how captions and the
// transcript behave. The founders and the words are illustrative. Copied on 17 October 2026 from
// apps/web/components/site/pitch-player.tsx.

export const PITCHES = {
  mdp: { name: "Market Day Pay", meta: "Lagos, Nigeria · Fintech · Earning revenue", dur: 60, lines: [
    [0, "I'm Amara Okafor, founder of Market Day Pay."],
    [6, "Market traders in Lagos lose sales when buyers carry no cash."],
    [14, "Our app and USSD code let any trader take a payment in seconds."],
    [24, "We are live with 1,200 traders across four markets."],
    [34, "Payment volume has grown every month for a year."],
    [44, "We are raising $150,000 to reach 5,000 paying merchants."],
    [54, "Request an introduction to see the checked figures."]] },
  chama: { name: "Chama Books", meta: "Nairobi, Kenya · Fintech · Earning revenue", dur: 58, lines: [
    [0, "I'm Wanjiru Kamau, and I run Chama Books."],
    [7, "Savings groups in Kenya still keep their records on paper."],
    [16, "Chama Books keeps contributions and loans in one shared ledger."],
    [28, "Three hundred groups use it every month."],
    [40, "We are raising a pre-seed round to grow beyond Nairobi."]] },
  farmgate: { name: "Farmgate Ledger", meta: "Accra, Ghana · Agritech · Earning revenue", dur: 59, lines: [
    [0, "I'm Kofi Mensah, founder of Farmgate Ledger."],
    [7, "Farmers near Accra often sell with no written record."],
    [16, "We give each sale a receipt that both sides can check."],
    [28, "Buyers pay a small fee for each recorded purchase."],
    [40, "We are raising a seed round to cover two more regions."]] },
  learnloop: { name: "LearnLoop", meta: "Lagos, Nigeria · Edtech · First version", dur: 60, lines: [
    [0, "I'm Tolu Adeyemi, and LearnLoop helps teachers plan."],
    [8, "Teachers spend their evenings writing lesson notes by hand."],
    [18, "LearnLoop turns the curriculum into ready lesson plans."],
    [30, "Forty schools are trying it this term."],
    [44, "We are raising a pre-seed round to start charging schools."]] },
  clinic: { name: "Clinic Queue", meta: "Nairobi, Kenya · Health · Scaling", dur: 55, lines: [
    [0, "I'm Achieng Otieno, founder of Clinic Queue."],
    [7, "Patients in Nairobi can wait hours to see a doctor."],
    [15, "Clinic Queue lets them book a slot by text message."],
    [26, "Twelve clinics pay us a monthly fee."],
    [38, "We are raising a seed round to reach fifty clinics."]] },
  harvest: { name: "Harvest Cold Rooms", meta: "Kumasi, Ghana · Agritech · First version", dur: 57, lines: [
    [0, "I'm Yaw Boateng, and we build solar cold rooms."],
    [7, "Tomato farmers lose part of each harvest to the heat."],
    [16, "Our cold rooms keep produce fresh for up to two weeks."],
    [28, "Farmers rent space by the crate."],
    [40, "We are raising a pre-seed round to build three more rooms."]] },
};

export function clock(seconds) {
  const n = Math.floor(seconds);
  return `${Math.floor(n / 60)}:${String(n % 60).padStart(2, "0")}`;
}

/** The caption showing at a moment of a pitch. */
export function captionAt(id, at) {
  let text = "";
  for (const [start, line] of PITCHES[id].lines) if (at >= start) text = line;
  return text;
}

export function reducedMotion() {
  try {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch {
    return false;
  }
}
