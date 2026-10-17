/**
 * The answers an investor profile chooses from. They match the checks on
 * investor_profiles. The investor_interest table, which the retired interest
 * form wrote, uses the same lists and keeps the rows it already holds.
 */
export const INTEREST_COUNTRIES = ["NG", "GH", "KE", "other"] as const;
export const INTEREST_SECTORS = ["Fintech", "Agritech", "Edtech", "Health", "Other"] as const;
export const CHEQUE_SIZES = ["Under $25,000", "$25,000 to $100,000", "$100,000 to $500,000", "Over $500,000", "Prefer not to say"] as const;
export const INVESTOR_TYPES = ["individual", "angel", "fund"] as const;
