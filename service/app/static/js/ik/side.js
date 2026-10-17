// The remembered side. Choosing a founder or investor link stores the choice in local storage under
// ikonetu-side, so that side's buttons come first on the next visit. The cookie policy describes this item.
// Blocked storage changes nothing, because every read and write is guarded.

const KEY = "ikonetu-side";
let side = "";
const listeners = new Set();

export function readStoredSide() {
  try {
    const stored = window.localStorage.getItem(KEY);
    return stored === "founder" || stored === "investor" ? stored : "";
  } catch {
    return "";
  }
}

export function choose(next) {
  try {
    if (next) window.localStorage.setItem(KEY, next);
    else window.localStorage.removeItem(KEY);
  } catch {
    // Storage can be blocked. The choice then lasts only for this page.
  }
  side = next;
  for (const fn of listeners) fn();
}

export function subscribe(fn) {
  listeners.add(fn);
}

/** Reads the stored side once the page is running, as the Next.js SideProvider did after it started. */
export function start() {
  const stored = readStoredSide();
  if (stored === side) return;
  side = stored;
  for (const fn of listeners) fn();
}

/** The values every page reads for the remembered side. */
export function navVals() {
  return {
    side,
    founderFirst: side !== "investor",
    investorFirst: side === "investor",
    chooseFounder: () => choose("founder"),
    chooseInvestor: () => choose("investor"),
    forgetSide: () => choose(""),
  };
}
