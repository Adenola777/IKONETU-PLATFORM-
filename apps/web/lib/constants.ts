/** Shared by the form (browser) and the API route (server). Keep zod out of this file. */
export const COUNTRIES = [
  { code: "NG", name: "Nigeria", dial: "234" },
  { code: "GH", name: "Ghana", dial: "233" },
  { code: "KE", name: "Kenya", dial: "254" },
] as const;

export const ROLES = ["founder", "investor", "mentor"] as const;
