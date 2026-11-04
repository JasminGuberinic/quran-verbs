// The full ayat list of a verb (src/fil/site/ayat.js): run by tests/test_practice_js.py, or `node --test tests/js`.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const A = require("../../src/fil/site/ayat.js");
const UI = require("../../src/fil/site/ui.js");
const STREAM = "https://everyayah.com/data/Alafasy_64kbps/{surah}{ayah}.mp3";
const OPTIONS = { audioSource: STREAM, audioAttribute: "data-audio", translationLanguage: "en", translationDir: "ltr",
                  fallbackNote: " · no free translation", recitedAyah: "Whole ayah" };
const AYAH = { ref: "2:6", text: "إِنَّ ٱلَّذِينَ كَفَرُوا۟ سَوَآءٌ", hits: [2] };

test("an ayah streams from the reciter's source, both numbers in three digits", () => {
  assert.equal(A.ayahAudioUrl(STREAM, "2:6"), "https://everyayah.com/data/Alafasy_64kbps/002006.mp3");
  assert.equal(A.ayahAudioUrl(STREAM, "114:6"), "https://everyayah.com/data/Alafasy_64kbps/114006.mp3");
});

test("the verb is marked, the ayah is linked and playable, its translation credited", () => {
  const html = A.ayahHtml(AYAH, { by: "Pickthall", text: { "2:6": "Those who <disbelieve>" } }, OPTIONS);
  assert.match(html, /<mark>كَفَرُوا۟<\/mark>/);
  assert.equal((html.match(/<mark>/g) || []).length, 1);
  assert.match(html, /href="https:\/\/quran.com\/2\/6"/);
  assert.match(html, /data-audio="https:\/\/everyayah.com\/data\/Alafasy_64kbps\/002006.mp3"/);
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
