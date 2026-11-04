/*
 * Every ayah of a verb, on request — shared by the app (index.html) and the static verb pages.
 *
 * A verb's page lists every form the Quran uses it in; its ayat (up to ~1,600 for قَالَ) are
 * far too many to carry, so a button fetches them (ayat/NNNN.json, and the translation into
 * the reader's language, ayat/NNNN.<lang>.json) and shows them a page at a time. Each ayah's
 * recitation streams from the reciter's source; nothing is added to the site for it.
 *
 * The container says everything this needs in data- attributes (see fil.pages.render._all_ayat):
 *   data-ayat, data-translation, data-translation-language, data-translation-dir,
 *   data-audio-source ("…/{surah}{ayah}.mp3"), data-audio-attribute (the attribute the page's
 *   own player listens to), data-text (the interface words, JSON).
 * Pure helpers are exported for the tests (tests/js/ayat.test.mjs).
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.FilAyat = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";
  const PAGE_SIZE = 40;
  const AUDIO_ATTRIBUTES = ["data-audio", "data-file"];   // the static pages' player, the app's
  const state = new WeakMap();

  const escapeHtml = (text) => String(text ?? "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
  const threeDigits = (number) => String(number).padStart(3, "0");

  /** The reciter's file for an ayah, from the source's address pattern (fil.recitation.AYAH_STREAM). */
  function ayahAudioUrl(template, ref) {
    const [surah, ayah] = ref.split(":");
    return template.replace("{surah}", threeDigits(surah)).replace("{ayah}", threeDigits(ayah));
  }

  /** "past · they (m.) · object: him/it", each reading of the letters joined by " / " — as fil.pages.render.grammar_label. */
  function grammarLabel(readings, text) {
    return readings.map((reading) => {
      const objects = reading.objects.map((pronoun) => text.forms.objects[pronoun]).join(", ");
      return [text.tenses[reading.tense], reading.passive ? text.forms.passive : "",
              text.pronouns[reading.pronoun], objects ? text.forms.object(objects) : ""]
        .filter(Boolean).join(" · ");
    }).join(" / ");
  }

  function ayahHtml(ayah, translation, options) {
    if (!AUDIO_ATTRIBUTES.includes(options.audioAttribute)) throw new Error(`unknown audio attribute ${options.audioAttribute}`);
    const [surah, number] = ayah.ref.split(":");
    const words = ayah.text.split(" ")
      .map((word, index) => (ayah.hits.includes(index) ? `<mark>${escapeHtml(word)}</mark>` : escapeHtml(word))).join(" ");
    const translated = translation?.text?.[ayah.ref];
    const translationHtml = translated
      ? `<p class="ayah-translation" lang="${options.translationLanguage}" dir="${options.translationDir}">${escapeHtml(translated)}<small>${escapeHtml(translation.by)}${escapeHtml(options.fallbackNote)}</small></p>`
      : "";
    return `<article class="ayah"><p class="ayah-head"><a href="https://quran.com/${surah}/${number}" target="_blank" rel="noopener">${ayah.ref} ↗</a>`
      + `<button type="button" class="play small" ${options.audioAttribute}="${escapeHtml(ayahAudioUrl(options.audioSource, ayah.ref))}" aria-label="${escapeHtml(`${ayah.ref} · ${options.recitedAyah}`)}">▶</button></p>`
      + `<p class="qr ayah-text" lang="ar" dir="rtl">${words}</p>${translationHtml}</article>`;
  }

  // ---------- the button and its list ----------

  function optionsOf(container) {
    const text = JSON.parse(container.dataset.text);
    return {
      text,
      audioSource: container.dataset.audioSource,
      audioAttribute: container.dataset.audioAttribute,
      translationLanguage: container.dataset.translationLanguage,
      translationDir: container.dataset.translationDir,
      fallbackNote: text.fallbackNote || "",
      recitedAyah: text.recitedAyah,
    };
  }

  async function fetchJson(url) {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`${url}: ${response.status}`);
    return response.json();
  }

  async function toggle(container) {
    const button = container.querySelector("[data-all-ayat-toggle]");
    const list = container.querySelector(".all-ayat-list");
    const options = optionsOf(container);
    const opening = button.getAttribute("aria-expanded") !== "true";
    button.setAttribute("aria-expanded", String(opening));
    button.textContent = opening ? options.text.hideAll : options.text.showAll;
    list.hidden = !opening;
    if (opening && !state.has(container)) await load(container, list, options);
  }

  async function load(container, list, options) {
    state.set(container, null);
    list.setAttribute("aria-busy", "true");
    list.innerHTML = `<p class="note">${escapeHtml(options.text.loading)}</p>`;
    try {
      const [arabic, translation] = await Promise.all([
        fetchJson(container.dataset.ayat),
        fetchJson(container.dataset.translation).catch(() => null),   // the Arabic alone still serves
      ]);
      state.set(container, { ayat: arabic.ayat, translation, shown: 0 });
      const looks = container.querySelector("[data-all-ayat-toggle]").className;   // the page's own button style
      list.innerHTML = `<div class="ayat"></div><button type="button" class="${looks}" data-all-ayat-more>${escapeHtml(options.text.showMore)}</button>`;
      showMore(container);
    } catch {
      state.delete(container);
      list.innerHTML = `<p class="note" role="alert">${escapeHtml(options.text.loadFailed)}</p>`;
    } finally {
      list.removeAttribute("aria-busy");
    }
  }

  function showMore(container) {
    const shown = state.get(container);
    const options = optionsOf(container);
    const next = shown.ayat.slice(shown.shown, shown.shown + PAGE_SIZE);
    container.querySelector(".all-ayat-list .ayat")
      .insertAdjacentHTML("beforeend", next.map((ayah) => ayahHtml(ayah, shown.translation, options)).join(""));
    shown.shown += next.length;
    container.querySelector("[data-all-ayat-more]").hidden = shown.shown >= shown.ayat.length;
  }

  if (typeof document !== "undefined") {
    document.addEventListener("click", (event) => {
      const container = event.target.closest("[data-all-ayat]");
      if (!container) return;
      if (event.target.closest("[data-all-ayat-toggle]")) toggle(container);
      else if (event.target.closest("[data-all-ayat-more]")) showMore(container);
    });
  }

  return { PAGE_SIZE, ayahAudioUrl, grammarLabel, ayahHtml };
});
