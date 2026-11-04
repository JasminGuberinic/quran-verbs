// The full ayat list of a verb (src/fil/site/ayat.js): run by tests/test_practice_js.py, or `node --test tests/js`.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const A = require("../../src/fil/site/ayat.js");
const UI = require("../../src/fil/site/ui.js");
const STREAM = "https://cdn.islamic.network/quran/audio/64/ar.alafasy/{number}.mp3";
const OPTIONS = { audioSource: STREAM, audioAttribute: "data-audio", translationLanguage: "en", translationDir: "ltr",
                  fallbackNote: " · no free translation", recitedAyah: "Whole ayah", language: "en",
                  text: { links: UI.en.forms.links } };
const AYAH = { ref: "2:6", number: 13, text: "إِنَّ ٱلَّذِينَ كَفَرُوا۟ سَوَآءٌ", hits: [2] };

test("an ayah streams from the reciter's source by its number in the whole Quran", () => {
  assert.equal(A.ayahAudioUrl(STREAM, AYAH), "https://cdn.islamic.network/quran/audio/64/ar.alafasy/13.mp3");
  assert.equal(A.ayahAudioUrl(STREAM, { ref: "114:6", number: 6236 }), "https://cdn.islamic.network/quran/audio/64/ar.alafasy/6236.mp3");
  assert.throws(() => A.ayahAudioUrl(STREAM, { ref: "2:6" }));   // never a guessed address
});

test("the verb is marked, the ayah is linked and playable, its translation credited", () => {
  const html = A.ayahHtml(AYAH, { by: "Pickthall", text: { "2:6": "Those who <disbelieve>" } }, OPTIONS);
  assert.match(html, /<mark>كَفَرُوا۟<\/mark>/);
  assert.equal((html.match(/<mark>/g) || []).length, 1);
  assert.match(html, /href="https:\/\/quran.com\/2\/6"/);
  assert.match(html, /data-audio="https:\/\/cdn.islamic.network\/quran\/audio\/64\/ar.alafasy\/13.mp3"/);
  assert.match(html, /<a href="https:\/\/quranwbw.com\/2\/6" target="_blank" rel="noopener">Word by word: quranwbw.com ↗<\/a>/);
  assert.doesNotMatch(html, /islam\.ba/);
  assert.match(html, /aria-label="2:6 · Whole ayah"/);
  assert.match(html, /Those who &lt;disbelieve&gt;<small>Pickthall · no free translation<\/small>/);
});

test("an ayah without a translation still shows its Arabic", () => {
  const html = A.ayahHtml(AYAH, null, OPTIONS);
  assert.doesNotMatch(html, /ayah-translation/);
  assert.match(html, /lang="ar" dir="rtl"/);
});

test("a play button only ever uses an attribute the page's player listens to", () => {
  assert.throws(() => A.ayahHtml(AYAH, null, { ...OPTIONS, audioAttribute: "onclick" }));
  assert.match(A.ayahHtml(AYAH, null, { ...OPTIONS, audioAttribute: "data-file" }), /data-file="/);
});

test("grammar reads tense, voice, subject and objects in the reader's language", () => {
  const readings = [{ tense: "past", pronoun: "hum", passive: false, objects: ["huwa"] }];
  assert.equal(A.grammarLabel(readings, UI.en), "past · they (m.) · object: him/it");
  assert.equal(A.grammarLabel(readings, UI.bs), "prošlo · oni · objekat: njega/to");
  const twoWays = [{ tense: "present", pronoun: "anta", passive: false, objects: [] },
                   { tense: "present", pronoun: "hiya", passive: false, objects: [] }];
  assert.equal(A.grammarLabel(twoWays, UI.en), "present · you (m.) / present · she");
});

test("every active language labels every pronoun as an object", () => {
  const pronouns = Object.keys(UI.en.pronouns);
  for (const code of ["bs", "en", "tr", "fr", "id", "ur", "bn", "fa"]) {
    assert.deepEqual(Object.keys(UI[code].forms.objects).sort(), [...pronouns].sort(), code);
    assert.deepEqual(Object.keys(UI[code].forms).sort(), Object.keys(UI.en.forms).sort(), code);
  }
});

test("a Bosnian reader is also sent to the ayah's translation on islam.ba", () => {
  assert.deepEqual(A.ayahLinks("2:255", "bs").map((link) => link.url),
                   ["https://islam.ba/kuran/2/255", "https://quranwbw.com/2/255"]);
  assert.deepEqual(A.ayahLinks("2:255", "tr").map((link) => link.url), ["https://quranwbw.com/2/255"]);
  const html = A.ayahLinksHtml("2:255", "bs", UI.bs.forms.links);
  assert.match(html, />Prijevod na islam.ba ↗</);
  const compact = A.ayahLinksHtml("2:255", "bs", UI.bs.forms.links, true);
  assert.match(compact, /title="Prijevod na islam.ba">islam.ba<\/a>/);
});

test("a present names its mood, so يَقُولُ and يَقُلْ read differently", () => {
  const says = [{ tense: "present", pronoun: "huwa", passive: false, objects: [], mood: "indicative" }];
  const letSay = [{ ...says[0], mood: "jussive" }];
  assert.equal(A.grammarLabel(says, UI.en), "present · indicative · he");
  assert.equal(A.grammarLabel(letSay, UI.en), "present · jussive · he");
  assert.notEqual(A.grammarLabel(says, UI.bs), A.grammarLabel(letSay, UI.bs));
  for (const code of ["bs", "en", "tr", "fr", "id", "ur", "bn", "fa"]) {
    assert.deepEqual(Object.keys(UI[code].forms.moods).sort(), ["indicative", "jussive", "subjunctive"], code);
  }
});
