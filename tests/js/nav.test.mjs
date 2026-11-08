// The phone's navigation (src/fil/site/nav.js): when the thin top bar tucks away, what a click does
// while the ☰ menu is open, and the menu as a step of history. Run by `node --test tests/js`.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const N = require("../../src/fil/site/nav.js");
const UI = require("../../src/fil/site/ui.js");

// ---------- the top bar ----------

test("the bar stays near the top of the page, whatever the direction", () => {
  assert.deepEqual(N.nextBarState({ isHidden: true, lastY: 300 }, 40), { isHidden: false, lastY: 40 });
});

test("scrolling down into the text tucks the bar away; scrolling up brings it back", () => {
  const down = N.nextBarState({ isHidden: false, lastY: 100 }, 140);
  assert.equal(down.isHidden, true);
  const up = N.nextBarState(down, 120);
  assert.equal(up.isHidden, false);
});

test("a jitter smaller than the threshold changes nothing, and small moves add up", () => {
  const start = { isHidden: false, lastY: 200 };
  assert.equal(N.nextBarState(start, 204), start);
  assert.equal(N.nextBarState(N.nextBarState(start, 204), 212).isHidden, true);
});

test("only a phone-width view tucks the bar", () => {
  const view = (matches) => ({ matchMedia: (query) => ({ matches: matches && query === N.PHONE_QUERY }) });
  assert.equal(N.isPhoneWidth(view(true)), true);
  assert.equal(N.isPhoneWidth(view(false)), false);
  assert.equal(N.isPhoneWidth(undefined), false);
});

// ---------- the menu ----------

test("a click on the ☰ button is left to the <details>", () => {
  assert.equal(N.clickAction({ isOnButton: true, isInsidePanel: false, isLink: false, isChoice: false }), "toggle");
});

test("a tap outside the panel closes it", () => {
  assert.equal(N.clickAction({ isOnButton: false, isInsidePanel: false, isLink: true, isChoice: false }), "close");
});

test("a link of the panel is followed; a language of the app closes the menu; the panel's own space does nothing", () => {
  assert.equal(N.clickAction({ isOnButton: false, isInsidePanel: true, isLink: true, isChoice: false }), "follow");
  assert.equal(N.clickAction({ isOnButton: false, isInsidePanel: true, isLink: false, isChoice: true }), "close");
  assert.equal(N.clickAction({ isOnButton: false, isInsidePanel: true, isLink: false, isChoice: false }), "ignore");
});

// ---------- the menu in a page: a small fake document ----------

class FakeClassList {
  constructor() { this.names = new Set(); }
  toggle(name, on) { if (on) this.names.add(name); else this.names.delete(name); }
  add(name) { this.names.add(name); }
  remove(name) { this.names.delete(name); }
  contains(name) { return this.names.has(name); }
}

class FakeTarget {
  constructor() { this.listeners = {}; }
  addEventListener(type, listener) { (this.listeners[type] ||= []).push(listener); }
  dispatch(type, event = {}) { (this.listeners[type] || []).forEach((listener) => listener(event)); }
}

function page() {
  const doc = new FakeTarget();
  doc.body = { classList: new FakeClassList() };
  doc.documentElement = { classList: new FakeClassList() };
  const focused = [];
  const summary = { contains: (node) => node === summary, focus: () => focused.push("summary") };
  const row = { focus: () => focused.push("row") };
  const panel = { contains: (node) => node === panel || node === row, querySelector: (selector) => (selector === "[aria-current]" ? row : null) };
  const details = new FakeTarget();
  let isOpen = false;
  Object.defineProperty(details, "open", { get: () => isOpen, set: (value) => { if (value !== isOpen) { isOpen = value; details.dispatch("toggle"); } } });
  details.querySelector = (selector) => (selector === "summary" ? summary : selector === "[data-menu-panel]" ? panel : null);
  doc.querySelector = () => null;
  doc.querySelectorAll = (selector) => (selector === "details[data-menu]" ? [details] : []);
  const entries = [{ page: true }];
  const view = new FakeTarget();
  view.history = {
    get state() { return entries[entries.length - 1]; },
    pushState: (state) => entries.push(state),
    replaceState: (state) => { entries[entries.length - 1] = state; },
    back: () => { entries.pop(); view.dispatch("popstate"); },
  };
  const outside = { closest: () => null };
  return { doc, view, details, entries, focused, outside, panel, row };
}

test("opening the menu adds a history step, and the phone's Back closes it without leaving the page", () => {
  const { doc, view, details, entries } = page();
  N.attach(doc, view);
  details.open = true;
  assert.equal(entries.length, 2);
  assert.ok(doc.body.classList.contains(N.OPEN_MENU_CLASS));
  view.history.back();
  assert.equal(details.open, false);
  assert.equal(entries.length, 1);
  assert.equal(doc.body.classList.contains(N.OPEN_MENU_CLASS), false);
});

test("closing with Esc takes the menu's step back out of history and returns focus to the ☰ button", () => {
  const { doc, view, details, entries, focused } = page();
  N.attach(doc, view);
  details.open = true;
  assert.deepEqual(focused, ["row"]);          // the current section's row
  doc.dispatch("keydown", { key: "Escape" });
  assert.equal(details.open, false);
  assert.equal(entries.length, 1);
  assert.deepEqual(focused, ["row", "summary"]);
});

test("a tap outside the panel closes the menu", () => {
  const { doc, view, details, outside } = page();
  N.attach(doc, view);
  details.open = true;
  doc.dispatch("click", { target: outside });
  assert.equal(details.open, false);
});

test("a page reloaded on the menu's step starts closed, and closing never steps out of the page", () => {
  const { doc, view, details, entries } = page();
  entries[0] = { [N.MENU_STATE]: true };
  N.attach(doc, view);
  details.open = true;
  details.open = false;
  assert.equal(entries.length, 1);
});

// ---------- the words ----------

test("every language names the menu, its button and its sections", () => {
  for (const [code, words] of Object.entries(UI)) {
    for (const key of ["button", "label", "sections"]) assert.ok(words.menu[key], `${code}: menu.${key}`);
    assert.ok(words.close && words.language && words.prev && words.next, code);
  }
});

test("the section lists the pager leads back to are named in the languages those sections are written in", () => {
  for (const code of ["bs", "en"]) {
    for (const section of ["nouns", "adjectives", "nuances", "particles", "pronouns", "roots", "surahs", "exercises"]) {
      assert.ok(UI[code].menu.lists[section], `${code}: menu.lists.${section}`);
    }
  }
});
