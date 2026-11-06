// What the scripts draw is marked for browser translation as the build marks the pages
// (src/fil/site/translation.js, fil.pages.untranslated): run by `node --test tests/js`.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const T = require("../../src/fil/site/translation.js");
const A = require("../../src/fil/site/ayat.js");
const UI = require("../../src/fil/site/ui.js");

// ---------- a small document: just what translation.js touches ----------

class FakeText {
  constructor(data) { this.nodeType = 3; this.data = data; this.parentNode = null; }
  get outer() { return this.data; }
}

class FakeElement {
  constructor(tagName, attributes = {}, children = []) {
    this.nodeType = 1;
    this.tagName = tagName.toUpperCase();
    this.attributes = new Map(Object.entries(attributes));
    this.childNodes = [];
    this.parentNode = null;
    this.hidden = false;
    this.listeners = {};
    const element = this;
    this.classList = {
      contains: (name) => element.classes().includes(name),
      add: (name) => { if (!element.classList.contains(name)) element.setAttribute("class", [...element.classes(), name].join(" ")); },
    };
    children.forEach((child) => this.appendChild(typeof child === "string" ? new FakeText(child) : child));
  }
  classes() { return (this.getAttribute("class") || "").split(" ").filter(Boolean); }
  getAttribute(name) { return this.attributes.has(name) ? this.attributes.get(name) : null; }
  setAttribute(name, value) { this.attributes.set(name, String(value)); }
  appendChild(child) { child.parentNode = this; this.childNodes.push(child); return child; }
  insertBefore(child, reference) { child.parentNode = this; this.childNodes.splice(this.childNodes.indexOf(reference), 0, child); }
  removeChild(child) { this.childNodes.splice(this.childNodes.indexOf(child), 1); child.parentNode = null; }
  set textContent(text) { this.childNodes = []; this.appendChild(new FakeText(text)); }
  querySelector(selector) { return selector === "[data-translate-hint-close]" ? this.childNodes.find((child) => child.close) || null : null; }
  addEventListener(name, listener) { this.listeners[name] = listener; }
  get outer() {
    const attributes = [...this.attributes].map(([name, value]) => ` ${name}="${value}"`).join("");
    const tag = this.tagName.toLowerCase();
    return `<${tag}${attributes}>${this.childNodes.map((child) => child.outer).join("")}</${tag}>`;
  }
}

const doc = { createElement: (tag) => new FakeElement(tag), createTextNode: (text) => new FakeText(text) };
const element = (tag, attributes, ...children) => new FakeElement(tag, attributes, children);

// ---------- marking ----------

test("an element in Arabic, or in the app's Arabic typefaces, is left untranslated and reads right to left", () => {
  const app = element("div", {}, element("span", { class: "ar" }, "قَالَ"), element("p", { class: "qr ayah-text" }, "إِنَّ"));
  T.protect(app, doc);
  assert.equal(app.outer, '<div><span class="ar notranslate" lang="ar" dir="rtl" translate="no">قَالَ</span>'
    + '<p class="qr ayah-text notranslate" lang="ar" dir="rtl" translate="no">إِنَّ</p></div>');
});

test("Arabic and transliterations inside translatable text are wrapped; the words around them are not", () => {
  const line = element("p", { class: "note" }, "قَالَ · to say — Fiʿl");
  element("main", { lang: "bs" }, line);
  T.protect(line, doc);
  assert.equal(line.outer, '<p class="note"><span lang="ar" dir="rtl" translate="no" class="notranslate">قَالَ</span>'
    + ' · to say — <span lang="ar-Latn" translate="no" class="notranslate">Fiʿl</span></p>');
});

test("nothing inside an untranslated element is touched, and marking twice changes nothing", () => {
  const quoted = element("p", { class: "translation notranslate", lang: "en", translate: "no" }, "Say: He is Allah — Fiʿl");
  const page = element("div", {}, quoted, element("p", {}, "riječ إِنَّ"));
  T.protect(page, doc);
  const once = page.outer;
  assert.equal(quoted.outer, '<p class="translation notranslate" lang="en" translate="no">Say: He is Allah — Fiʿl</p>');
  T.protect(page, doc);
  assert.equal(page.outer, once);
});

test("in a Persian or Urdu context Arabic script is the reader's own language", () => {
  const meaning = element("p", {}, "معنی (يَنْبَغِي)");
  element("html", { lang: "fa" }, element("body", {}, meaning));
  T.protect(meaning, doc);
  assert.equal(meaning.outer, "<p>معنی (يَنْبَغِي)</p>");
});

test("a report the learner copies is never rewritten", () => {
  const report = element("textarea", {}, "Fiʿl · قَالَ");
  T.protect(element("div", {}, report), doc);
  assert.equal(report.outer, "<textarea>Fiʿl · قَالَ</textarea>");
});

// ---------- what the scripts render ----------

test("every ayah ayat.js lists is untranslated: the Arabic and the published translation under it", () => {
  const ayah = { ref: "112:1", number: 6222, text: "قُلْ هُوَ ٱللَّهُ أَحَدٌ", hits: [0] };
  const translation = { text: { "112:1": "Say: He is Allah, the One!" }, by: "Pickthall" };
  const html = A.ayahHtml(ayah, translation, {
    audioAttribute: "data-audio", audioSource: "https://example.org/{number}.mp3", recitedAyah: "Mishary Alafasy",
    language: "bs", text: { links: UI.bs.forms.links }, translationLanguage: "en", translationDir: "ltr", fallbackNote: "",
  });
  assert.match(html, /<p class="qr ayah-text notranslate" lang="ar" dir="rtl" translate="no">/);
  assert.match(html, /<p class="ayah-translation notranslate" lang="en" dir="ltr" translate="no">Say: He is Allah, the One!/);
  assert.match(html, /<span class="play-icon notranslate" aria-hidden="true" translate="no">▶<\/span>/);
});

// ---------- the hint ----------

const storageOf = (items = {}) => ({ getItem: (key) => items[key] ?? null, setItem: (key, value) => { items[key] = value; }, items });
const hintElement = () => {
  const close = element("button", {});
  close.close = true;
  const hint = element("aside", { "data-translate-hint": "" }, close);
  hint.hidden = true;
  return { hint, close };
};

test("the hint shows the first time, never again, and its close button hides it", () => {
  const storage = storageOf();
  const first = hintElement();
  assert.equal(T.showHintOnce(first.hint, storage), true);
  assert.equal(first.hint.hidden, false);
  first.close.listeners.click();
  assert.equal(first.hint.hidden, true);

  const next = hintElement();
  assert.equal(T.showHintOnce(next.hint, storage), false);
  assert.equal(next.hint.hidden, true);
});

test("where storage is blocked the hint still shows, and nothing throws", () => {
  const blocked = { getItem: () => { throw new Error("blocked"); }, setItem: () => { throw new Error("blocked"); } };
  const { hint } = hintElement();
  assert.equal(T.showHintOnce(hint, blocked), true);
  assert.equal(hint.hidden, false);
  assert.equal(T.showHintOnce(null, storageOf()), false);
});

test("the hint speaks Bosnian and English only: the readers of the other languages already read their own", () => {
  assert.match(UI.bs.translateHint, /Prevedi stranicu u pregledniku/);
  assert.ok(UI.en.translateHint && UI.bs.translateHintLink && UI.en.translateHintLink);
  for (const code of Object.keys(UI).filter((code) => !["bs", "en"].includes(code))) assert.equal(UI[code].translateHint, undefined);
});
