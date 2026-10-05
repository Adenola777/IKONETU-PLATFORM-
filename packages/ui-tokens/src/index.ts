/**
 * IkonetU brand tokens. Navy and orange, as agreed on 5 October 2026.
 * Text colours on white meet WCAG 2.2 AA contrast. Orange (#F05C28) is used
 * for fills behind navy text and for accents on navy; small orange text on
 * white uses orangeText (#B93E14), which passes 4.5:1.
 */
export const colors = {
  navy: "#0C1E4A",
  navyDeep: "#071330",
  navyMid: "#152963",
  navyLine: "#3A4C7A",
  orange: "#F05C28",
  orangeText: "#B93E14",
  orangeTextHover: "#8F2F0F",
  orangeTint: "#FDF0EA",
  ink: "#0A0A0A",
  textMid: "#4B4B4B",
  textMuted: "#6B6B6B",
  onNavyMuted: "#D6DCEB",
  line: "#E8E8E8",
  off: "#F8F7F5",
  white: "#FFFFFF",
  success: "#1F7A4D",
  successTint: "#E6F2EC",
  danger: "#A12C10",
  infoTint: "#E6EAF4",
} as const;

export const leagueColors = {
  EARLY: "#9AA3B8",
  RISING: "#3A6EA5",
  INVESTABLE: "#0C1E4A",
  ELITE: "#F05C28",
} as const;

export const fonts = {
  display: "'Fraunces', Georgia, serif",
  body: "'Plus Jakarta Sans', system-ui, sans-serif",
} as const;

export const radius = { sm: 8, md: 12, lg: 16, xl: 20, pill: 999 } as const;

export const space = { 1: 4, 2: 8, 3: 12, 4: 16, 5: 20, 6: 24, 8: 32, 10: 40, 12: 48, 16: 64, 24: 96 } as const;

/** Minimum touch target in CSS pixels (PRD Q-4). */
export const minTouchTarget = 44;
