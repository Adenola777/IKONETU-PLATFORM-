"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

/**
 * The remembered side. Choosing a founder or investor link stores the choice in
 * local storage under ikonetu-side, so that side's buttons come first on the next
 * visit. The cookie policy describes this item. Blocked storage changes nothing,
 * because every read and write is guarded.
 */
export type Side = "" | "founder" | "investor";

const KEY = "ikonetu-side";

type SideState = { side: Side; choose: (side: Side) => void };

const SideContext = createContext<SideState>({ side: "", choose: () => {} });

export function readStoredSide(): Side {
  try {
    const stored = window.localStorage.getItem(KEY);
    return stored === "founder" || stored === "investor" ? stored : "";
  } catch {
    return "";
  }
}

export function SideProvider({ children }: { children: React.ReactNode }) {
  const [side, setSide] = useState<Side>("");
  useEffect(() => setSide(readStoredSide()), []);
  const choose = useCallback((next: Side) => {
    try {
      if (next) window.localStorage.setItem(KEY, next);
      else window.localStorage.removeItem(KEY);
    } catch {
      // Storage can be blocked. The choice then lasts only for this page.
    }
    setSide(next);
  }, []);
  const value = useMemo(() => ({ side, choose }), [side, choose]);
  return <SideContext.Provider value={value}>{children}</SideContext.Provider>;
}

/** The values every page reads for the remembered side. */
export function useNavVals() {
  const { side, choose } = useContext(SideContext);
  return {
    side,
    founderFirst: side !== "investor",
    investorFirst: side === "investor",
    chooseFounder: () => choose("founder"),
    chooseInvestor: () => choose("investor"),
    forgetSide: () => choose(""),
  };
}
