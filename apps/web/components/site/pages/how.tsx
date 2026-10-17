"use client";

import { useNavVals } from "../side";
import { HowItWorksView } from "../views/how.view";
import { useWalkVals } from "../walkthrough";

function useHowItWorksVals() {
  return { ...useNavVals(), ...useWalkVals() };
}

export type HowItWorksVals = ReturnType<typeof useHowItWorksVals>;

export default function HowItWorksPage() {
  return <HowItWorksView v={useHowItWorksVals()} />;
}
