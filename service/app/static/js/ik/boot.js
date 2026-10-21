// Starts each interactive part of a website page: every element with data-component, with the props in
// its data-props. The pitch player starts first, so the page can open it, and the remembered side is read
// once all of them run, as the Next.js app read it after it started.
import { mount } from "./runtime.js";
import * as side from "./side.js";
import header from "./components/header.js";
import player from "./components/player.js";
import home from "./components/home.js";
import founders from "./components/founders.js";
import investors from "./components/investors.js";
import readiness from "./components/readiness.js";

const COMPONENTS = { header, player, home, founders, investors, readiness };
const registry = {};

const roots = [...document.querySelectorAll("[data-component]")];
roots.sort((a, b) => (a.dataset.component === "player" ? -1 : 0) - (b.dataset.component === "player" ? -1 : 0));
const mounted = [];
for (const root of roots) {
  const define = COMPONENTS[root.dataset.component];
  if (!define) continue;
  const ctx = { props: root.dataset.props ? JSON.parse(root.dataset.props) : {}, registry, root };
  const component = mount(root, define, ctx);
  mounted.push(component);
  side.subscribe(() => component.set((s) => ({ ...s })));
}
side.start();
