// The site header: the menu on narrow screens, the current page, and the remembered side's buttons.
// Ported on 17 October 2026 from apps/web/components/site/header.tsx.
import { navVals } from "../side.js";

export default {
  initial: () => ({ menuOpen: false }),
  vals(s, set, ctx) {
    const current = (ctx.props && ctx.props.current) || "";
    const page = (name) => (current === name ? "page" : undefined);
    return {
      ...navVals(),
      menuOpen: s.menuOpen,
      menuClosed: !s.menuOpen,
      navClass: s.menuOpen ? "open" : "",
      menuRef: (el) => {
        ctx.menuEl = el;
      },
      toggleMenu: () => set((now) => ({ ...now, menuOpen: !now.menuOpen })),
      // Escape closes the menu and returns focus to the Menu button.
      navKey: (e) => {
        if (e.key === "Escape" && s.menuOpen) {
          set({ menuOpen: false });
          if (ctx.menuEl) ctx.menuEl.focus();
        }
      },
      cur: { founders: page("founders"), investors: page("investors"), trust: page("trust"), signin: page("signin") },
    };
  },
};
