"use client";

import { useRef, useState } from "react";
import { useNavVals } from "./side";
import { HeaderView } from "./views/header.view";

type Current = "home" | "founders" | "investors" | "how" | "trust" | "signin" | "legal" | "about" | "questions" | "";

function useHeaderVals(current: Current) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuEl = useRef<HTMLButtonElement | null>(null);
  const page = (name: Current) => (current === name ? ("page" as const) : undefined);
  return {
    ...useNavVals(),
    menuOpen,
    menuClosed: !menuOpen,
    navClass: menuOpen ? "open" : "",
    menuRef: (el: HTMLButtonElement | null) => {
      menuEl.current = el;
    },
    toggleMenu: () => setMenuOpen((open) => !open),
    // Escape closes the menu and returns focus to the Menu button.
    navKey: (e: React.KeyboardEvent<HTMLElement>) => {
      if (e.key === "Escape" && menuOpen) {
        setMenuOpen(false);
        menuEl.current?.focus();
      }
    },
    cur: { founders: page("founders"), investors: page("investors"), how: page("how"), trust: page("trust"), signin: page("signin") },
  };
}

export type HeaderVals = ReturnType<typeof useHeaderVals>;

export function SiteHeader({ current }: { current: string }) {
  return <HeaderView v={useHeaderVals(current as Current)} />;
}
