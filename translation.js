/*
 * What a browser's page translation must leave alone, marked as the page is drawn — the app
 * (index.html) and what the scripts of the static pages render (ayat.js, exercises.js).
 *
 * The static pages are marked when they are built, by fil.pages.untranslated; this file
 * applies the very same rules to what appears later, so a translated page never sees:
 *
 *   - Arabic: an element in Arabic (lang="ar", or the app's .ar / .qr) is marked translate="no",
 *     reads right to left, and says it is Arabic; a run of Arabic script inside translatable
 *     text is wrapped in such a span;
 *   - a transliteration (iḍāfa, Fiʿl): wrapped in a span marked lang="ar-Latn";
 *   - what the renderers mark themselves (a quoted ayah translation, a play icon): translate="no".
 * Every element marked translate="no" also carries the class `notranslate` (older Google Translate).
 * In a Persian or Urdu context Arabic script is the reader's own: only lang="ar" marks it Arabic.
 *
 * It also shows, once per visitor, the hint under the top bar that the browser can translate
 * the page ([data-translate-hint], written by fil.pages.render; the app calls showHintOnce itself).
 *
 * The static pages mark by lang="ar" alone; the app also by its Arabic typefaces' classes.
 *
 * The DOM is duck-typed (nodeType, childNodes, get/setAttribute, classList, insertBefore), so
 * the rules run under `node --test` with a small fake document (tests/js/translation.test.mjs).
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.FilTranslation = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const NO_TRANSLATE_CLASS = "notranslate";
  const ARABIC = "ar";
  const ARABIC_SCRIPT_LANGUAGES = new Set(["ar", "fa", "ur"]);
  const ARABIC_CLASSES = ["ar", "qr"];       // the app's Arabic, by its typeface
  const ELEMENT = 1;
  const TEXT = 3;
  const RAW = new Set(["SCRIPT", "STYLE", "TEXTAREA", "TITLE", "OPTION", "SELECT"]);
  const HINT_SEEN = "fil.translateHint.seen";

  // The same character classes as fil.pages.untranslated (a test holds them equal).
  const ARABIC_LETTER = "\\u0600-\\u06FF\\u0750-\\u077F\\u0870-\\u089F\\u08A0-\\u08FF\\uFB50-\\uFDFF\\uFE70-\\uFEFC";
  const JOINER = " \\u00A0\\u200C\\u200D";
  const ARABIC_RUN = `[${ARABIC_LETTER}]+(?:[${JOINER}]+[${ARABIC_LETTER}]+)*`;
  const TRANSLITERATION_MARK = "āīūḥḍṣṭẓʿʾĀĪŪḤḌṢṬẒ";
  const LATIN_LETTER = "A-Za-z\\u00C0-\\u024F\\u1E00-\\u1EFF\\u02BE\\u02BF";
  const TRANSLITERATED_WORD = `[${LATIN_LETTER}-]*[${TRANSLITERATION_MARK}][${LATIN_LETTER}-]*`;
  const TRANSLITERATION_RUN = `${TRANSLITERATED_WORD}(?: ${TRANSLITERATED_WORD})*`;
  const UNTRANSLATABLE_RUN = new RegExp(`(${ARABIC_RUN})|(${TRANSLITERATION_RUN})`, "gu");

  /**
   * The runs of `text` to leave untranslated, in order: [{ kind: "arabic" | "transliteration", text, index }].
   * Arabic script is not Arabic where the reader's own language is written in it.
   */
  function untranslatableRuns(text, isArabicScript) {
    const runs = [];
    for (const match of text.matchAll(UNTRANSLATABLE_RUN)) {
      if (match[2]) runs.push({ kind: "transliteration", text: match[0], index: match.index });
      else if (!isArabicScript) runs.push({ kind: "arabic", text: match[0], index: match.index });
    }
    return runs;
  }

  /** Mark `node` and everything inside it; its context is read from its ancestors. */
  function protect(node, doc) {
    if (!node) return;
    visit(node, contextAbove(node.parentNode), doc);
  }

  function contextAbove(element) {
    const chain = [];
    for (let at = element; at && at.nodeType === ELEMENT; at = at.parentNode) chain.unshift(at);
    return chain.reduce((context, ancestor) => contextInside(ancestor, context), { isUntranslated: false, isArabicScript: false });
  }

  function contextInside(element, outer) {
    const language = (element.getAttribute("lang") || "").toLowerCase();
    return {
      isUntranslated: outer.isUntranslated || element.getAttribute("translate") === "no" || isArabic(element),
      isArabicScript: language ? ARABIC_SCRIPT_LANGUAGES.has(language.split("-")[0]) : outer.isArabicScript,
    };
  }

  function isArabic(element) {
    const language = element.getAttribute("lang");
    if (language) return language.toLowerCase() === ARABIC;
    return ARABIC_CLASSES.some((name) => element.classList && element.classList.contains(name));
  }

  function visit(node, context, doc) {
    if (node.nodeType === TEXT) {
      if (!context.isUntranslated) wrapRuns(node, context, doc);
      return;
    }
    if (node.nodeType !== ELEMENT || RAW.has(node.tagName)) return;
    markElement(node);
    const inner = contextInside(node, context);
    for (const child of Array.from(node.childNodes)) visit(child, inner, doc);
  }

  /** An Arabic element says so and reads right to left; whatever is left untranslated carries the class. */
  function markElement(element) {
    if (isArabic(element)) {
      if (!element.getAttribute("lang")) element.setAttribute("lang", ARABIC);
      if (!element.getAttribute("dir")) element.setAttribute("dir", "rtl");
      if (!element.getAttribute("translate")) element.setAttribute("translate", "no");
    }
    if (element.getAttribute("translate") === "no") element.classList.add(NO_TRANSLATE_CLASS);
  }

  function wrapRuns(textNode, context, doc) {
    const text = textNode.data;
    const runs = untranslatableRuns(text, context.isArabicScript);
    if (!runs.length) return;
    const parent = textNode.parentNode;
    let position = 0;
    for (const run of runs) {
      if (run.index > position) parent.insertBefore(doc.createTextNode(text.slice(position, run.index)), textNode);
      parent.insertBefore(markedSpan(run, doc), textNode);
      position = run.index + run.text.length;
    }
    if (position < text.length) parent.insertBefore(doc.createTextNode(text.slice(position)), textNode);
    parent.removeChild(textNode);
  }

  function markedSpan(run, doc) {
    const span = doc.createElement("span");
    span.setAttribute("lang", run.kind === "arabic" ? ARABIC : `${ARABIC}-Latn`);
    if (run.kind === "arabic") span.setAttribute("dir", "rtl");
    span.setAttribute("translate", "no");
    span.classList.add(NO_TRANSLATE_CLASS);
    span.textContent = run.text;
    return span;
  }

  /** Keep marking whatever is drawn later. Marking only sets attributes and wraps text, so it settles. */
  function watch(doc, Observer) {
    protect(doc.body, doc);
    const observer = new Observer((mutations) => {
      for (const mutation of mutations) {
        for (const added of mutation.addedNodes) {
          if (added.parentNode) protect(added, doc);
        }
      }
    });
    observer.observe(doc.body, { childList: true, subtree: true });
    return observer;
  }

  // ---------- the hint ----------

  function hasSeenHint(storage) {
    try { return Boolean(storage && storage.getItem(HINT_SEEN)); } catch { return false; }
  }

  function rememberHint(storage) {
    try { if (storage) storage.setItem(HINT_SEEN, "1"); } catch { /* a private window: shown again next time */ }
  }

  /** Show the `hint` element the first time a visitor meets it, never again; its close button hides it. */
  function showHintOnce(hint, storage) {
    if (!hint || hasSeenHint(storage)) return false;
    hint.hidden = false;
    rememberHint(storage);
    const close = hint.querySelector("[data-translate-hint-close]");
    if (close) close.addEventListener("click", () => { hint.hidden = true; });
    return true;
  }

  if (typeof document !== "undefined" && typeof MutationObserver !== "undefined") {
    const start = () => {
      watch(document, MutationObserver);
      let storage = null;
      try { storage = window.localStorage; } catch { storage = null; }
      // A static page's hint; the app offers its own once it knows the reader's language.
      showHintOnce(document.querySelector("[data-translate-hint]"), storage);
    };
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
    else start();
  }

  return { NO_TRANSLATE_CLASS, HINT_SEEN, untranslatableRuns, protect, watch, showHintOnce };
});
