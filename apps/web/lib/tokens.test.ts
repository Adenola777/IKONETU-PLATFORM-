import { readFileSync } from "node:fs";
import { colors, leagueColors } from "@ikonetu/ui-tokens";
import { describe, expect, it } from "vitest";

const css = readFileSync(new URL("../app/globals.css", import.meta.url), "utf8");
const cssVar = (name: string) => css.match(new RegExp(`--${name}:\\s*(#[0-9A-Fa-f]{6})`))?.[1]?.toUpperCase();
const kebab = (s: string) => s.replace(/[A-Z]/g, (m) => `-${m.toLowerCase()}`);

describe("globals.css", () => {
  it("uses the brand colours from ui-tokens", () => {
    for (const [name, value] of Object.entries(colors)) {
      const found = cssVar(kebab(name));
      if (found) expect(found, name).toBe(value.toUpperCase());
    }
    expect(cssVar("navy")).toBe(colors.navy);
    expect(cssVar("orange")).toBe(colors.orange);
  });
  it("uses the league colours from ui-tokens", () => {
    for (const [name, value] of Object.entries(leagueColors)) {
      expect(cssVar(`league-${name.toLowerCase()}`), name).toBe(value.toUpperCase());
    }
  });
});
