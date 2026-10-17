// The how-it-works page: the remembered side and the walkthrough.
// Ported on 17 October 2026 from apps/web/components/site/pages/how.tsx.
import { navVals } from "../side.js";
import { walkVals } from "../walkthrough.js";

export default {
  initial: () => ({ walkTranscriptOpen: false }),
  vals(s, set, ctx) {
    return { ...navVals(), ...walkVals(s, set, ctx) };
  },
};
