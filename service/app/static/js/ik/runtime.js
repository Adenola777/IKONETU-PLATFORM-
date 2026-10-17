// Keeps a part of a page in step with its state, as React kept the website's views. The server sends the
// page already drawn in its first state. The markup carries the bindings the design boards declared:
//   data-t="path"            the element's text is the value at path
//   data-a='{"class":"chip {{m.cls}}"}'   attributes, each a text with {{path}} holes, or one whole hole
//   data-on="click:toggle"   event handlers, each a path to a function
//   data-ref="tourRef"       a function called with the element, as a React ref callback was
//   <template data-if="path">            content shown while the value is true
//   <template data-for="list" data-as="m">  content repeated for each item, as m, with its index as mIndex
// Each block ends at the next <template data-end> of its own level. Paths read the item names first, then
// the component's values, so "m.name" is the current item's name.

const BOOLEAN = new Set(["disabled", "hidden", "required", "checked", "selected", "open", "multiple", "readonly", "muted", "controls", "playsinline"]);
const HOLE = /\{\{\s*([^}]+?)\s*\}\}/g;
const WHOLE = /^\s*\{\{\s*([^}]+?)\s*\}\}\s*$/;

function lookup(scope, path) {
  const parts = path.split(".");
  let value;
  let found = false;
  for (const frame of scope) {
    if (frame && Object.prototype.hasOwnProperty.call(frame, parts[0])) {
      value = frame[parts[0]];
      found = true;
      break;
    }
  }
  if (!found) return undefined;
  for (const p of parts.slice(1)) value = value == null ? undefined : value[p];
  return value;
}

/** A value as text in an attribute: nothing for null, undefined and false, as the boards' t() did. */
function text(value) {
  return value === null || value === undefined || value === false ? "" : String(value);
}

function setAttr(el, name, raw, scope) {
  const whole = WHOLE.exec(raw);
  if (whole) {
    const v = lookup(scope, whole[1]);
    if (BOOLEAN.has(name)) {
      if (v) el.setAttribute(name, "");
      else el.removeAttribute(name);
      if (name in el && typeof el[name] === "boolean") el[name] = Boolean(v);
    } else if (name.startsWith("aria-") && typeof v === "boolean") {
      el.setAttribute(name, String(v));
    } else if (v === null || v === undefined || v === false) {
      el.removeAttribute(name);
    } else {
      el.setAttribute(name, String(v));
    }
    return;
  }
  el.setAttribute(name, raw.replace(HOLE, (_m, p) => text(lookup(scope, p))));
}

/** The nodes of a block, from the node after its opening marker to its own end marker. */
function blockEnd(start) {
  let depth = 0;
  for (let n = start.nextSibling; n; n = n.nextSibling) {
    if (n.nodeName === "TEMPLATE") {
      if (n.hasAttribute("data-if") || n.hasAttribute("data-for")) depth++;
      else if (n.hasAttribute("data-end")) {
        if (depth === 0) return n;
        depth--;
      }
    }
  }
  throw new Error("a block has no end marker");
}

class View {
  constructor(scope) {
    this.scope = scope;
    this.bindings = [];
    this.blocks = [];
    this.refs = [];
  }

  /** Records the bindings of the nodes from `first` up to `stop`, which stay where they are. */
  adopt(first, stop) {
    let n = first;
    while (n && n !== stop) {
      const next = n.nextSibling;
      if (n.nodeType === 1) {
        if (n.nodeName === "TEMPLATE" && (n.hasAttribute("data-if") || n.hasAttribute("data-for"))) {
          const end = blockEnd(n);
          const block = new Block(n, end, this.scope);
          this.blocks.push(block);
          n = end.nextSibling;
          continue;
        }
        if (n.nodeName === "TEMPLATE" && n.hasAttribute("data-end")) {
          n = next;
          continue;
        }
        this.element(n);
      }
      n = next;
    }
  }

  element(el) {
    if (el.hasAttribute("data-component") && this.root !== el) return; // a nested component binds itself
    this.bind(el);
    this.adopt(el.firstChild, null);
  }

  bind(el) {
    const t = el.getAttribute("data-t");
    if (t) this.bindings.push(() => {
      const v = text(lookup(this.scope, t));
      if (el.textContent !== v) el.textContent = v;
    });
    const a = el.getAttribute("data-a");
    if (a) {
      const attrs = JSON.parse(a);
      this.bindings.push(() => {
        for (const name of Object.keys(attrs)) setAttr(el, name, attrs[name], this.scope);
      });
    }
    const on = el.getAttribute("data-on");
    if (on) {
      for (const pair of on.split(" ")) {
        const [type, path] = pair.split(":");
        el.addEventListener(type, (event) => {
          const fn = lookup(this.scope, path);
          if (typeof fn === "function") fn(event);
        });
      }
    }
    const ref = el.getAttribute("data-ref");
    if (ref) this.refs.push([ref, el]);
  }

  update(scope) {
    this.scope = scope;
    for (const b of this.bindings) b();
    for (const block of this.blocks) block.update(scope);
    for (const [path, el] of this.refs) {
      const fn = lookup(scope, path);
      if (typeof fn === "function") fn(el);
    }
  }

  unmount() {
    for (const block of this.blocks) block.unmount();
    for (const [path] of this.refs) {
      const fn = lookup(this.scope, path);
      if (typeof fn === "function") fn(null);
    }
  }
}

class Block {
  constructor(start, end, scope) {
    this.start = start;
    this.end = end;
    this.kind = start.hasAttribute("data-if") ? "if" : "for";
    this.path = start.getAttribute(this.kind === "if" ? "data-if" : "data-for");
    this.as = start.getAttribute("data-as") || "item";
    this.items = []; // one View per shown copy
    // The server drew this block's first state. It is drawn again from its template, which gives the
    // same nodes and records their bindings.
    this.clear();
    this.render(scope);
  }

  clear() {
    while (this.start.nextSibling && this.start.nextSibling !== this.end) this.start.nextSibling.remove();
  }

  copy(scope) {
    const fragment = this.start.content.cloneNode(true);
    const first = fragment.firstChild;
    const view = new View(scope);
    view.adopt(first, null);
    this.end.before(fragment);
    view.update(scope);
    return view;
  }

  render(scope) {
    const value = lookup(scope, this.path);
    if (this.kind === "if") {
      this.shown = Boolean(value);
      if (this.shown) this.items = [this.copy(scope)];
      return;
    }
    const list = Array.isArray(value) ? value : [];
    this.items = list.map((item, i) => this.copy([{ [this.as]: item, [this.as + "Index"]: i }, ...scope]));
  }

  update(scope) {
    const value = lookup(scope, this.path);
    if (this.kind === "if") {
      if (Boolean(value) === this.shown) {
        if (this.shown) this.items[0].update(scope);
        return;
      }
      this.unmount();
      this.clear();
      this.render(scope);
      return;
    }
    const list = Array.isArray(value) ? value : [];
    if (list.length !== this.items.length) {
      this.unmount();
      this.clear();
      this.render(scope);
      return;
    }
    list.forEach((item, i) => this.items[i].update([{ [this.as]: item, [this.as + "Index"]: i }, ...scope]));
  }

  unmount() {
    for (const view of this.items) view.unmount();
    this.items = [];
  }
}

/**
 * Binds a component to its root element. `define` gives the first state and turns a state into the
 * values the markup reads, including the functions its handlers call.
 */
export function mount(root, define, ctx) {
  let state = define.initial(ctx);
  let rendered = state;
  let queued = false;
  const component = {
    get state() { return state; },
    /** Changes the state, as a React state setter did, and draws the change once the current task ends. */
    set(change) {
      const next = typeof change === "function" ? change(state) : { ...state, ...change };
      if (next === state) return;
      state = next;
      if (!queued) {
        queued = true;
        queueMicrotask(flush);
      }
    },
  };
  function flush() {
    queued = false;
    const prev = rendered;
    rendered = state;
    component.vals = define.vals(state, component.set, ctx);
    view.update([component.vals]);
    if (define.after) define.after(prev, state, ctx, component);
  }
  component.vals = define.vals(state, component.set, ctx);
  const view = new View([component.vals]);
  view.root = root;
  view.bind(root);
  view.adopt(root.firstChild, null);
  view.update([component.vals]);
  if (define.mounted) define.mounted(ctx, component);
  return component;
}

export { lookup, text };
