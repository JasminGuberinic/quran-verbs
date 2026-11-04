// Fairness tests for the practice questions (run by tests/test_practice_js.py, or `node --test tests/js`).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const P = require("../../src/fil/site/practice.js");
const LANGUAGES = ["bs", "en", "tr", "de", "sq", "fr", "id", "ur", "bn", "fa", "ru", "ms", "es", "sw", "so", "hi"];
const VERBS_DIR = new URL("../../build/site/verbs/", import.meta.url);

function realCards() {
  if (!existsSync(VERBS_DIR)) return null;
  return readdirSync(VERBS_DIR).filter((name) => name.endsWith(".json"))
    .map((name) => JSON.parse(readFileSync(new URL(name, VERBS_DIR), "utf8")));
}

const cell = (tense, pronoun, plain, quran = true) => ({ tense, pronoun, plain, arabic: plain, quran, spoken: "x" });
const SAY = {
  root: "قول", form: 1, lemma: "قالَ", meaning: { en: "to say", bs: "reći, kazati" },
  principal: [cell("present", "huwa", "يَقُولُ")],
  cells: [cell("present", "hiya", "تَقُولُ"), cell("present", "anta", "تَقُولُ"), cell("present", "huwa", "يَقُولُ"),
          cell("present", "ana", "أَقُولُ"), cell("past", "huwa", "قَالَ"), cell("present", "nahnu", "نَقُولُ")],
  ayat: [], sentences: [],
};

test("one spelling with two readings is never a 'wrong' option against itself", () => {
  const random = P.seeded(7);
  for (let i = 0; i < 300; i++) {
    const question = P.builders.form(SAY, [SAY], "en", random);
    assert.deepEqual(P.problemsWith(question), []);
    if (question.cell.plain === "تَقُولُ") assert.equal(question.readings.length, 2);
  }
});

test("a verb with no table is never asked about, only offered as a wrong meaning", () => {
  const NEAR = { root: "قرب", form: 1, lemma: "قَرِبَ", meaning: { en: "to approach", bs: "prići" },
                 principal: [], cells: [], ayat: [], sentences: [] };
  for (const type of [...P.TYPES, "mix"]) {
    const questions = P.session(type, [NEAR, SAY], { random: P.seeded(3), size: 5 });
    assert.ok(questions.every((question) => P.keyOf(question.card) === P.keyOf(SAY)), type);
  }
});

test("a connecting alif's vowel does not make two options look different", () => {
  assert.equal(P.spellingKey("اِعْلَمْ"), P.spellingKey("اعْلَمْ"));
  assert.equal(P.spellingKey("ٱعْلَمْ"), P.spellingKey("اعْلَمْ"));
  assert.notEqual(P.spellingKey("يَقُولُ"), P.spellingKey("تَقُولُ"));
});

test("meanings that share a word overlap", () => {
  assert.ok(P.meaningsOverlap("doći", "doći, donijeti"));
  assert.ok(!P.meaningsOverlap("to say", "to come"));
});

const cards = realCards();

test("every question in thousands of sessions over the real cards is fair, in every language", { skip: !cards && "build/site not built" }, () => {
  for (const language of LANGUAGES) {
    for (const type of [...P.TYPES, "mix"]) {
      for (let seed = 1; seed <= 25; seed++) {
        const questions = P.session(type, cards, { language, random: P.seeded(seed * 31 + type.length) });
        assert.ok(questions.length > 0, `${type}/${language} produced no questions`);
        const identities = new Set();
        for (const question of questions) {
          assert.deepEqual(P.problemsWith(question), [], `${type}/${language}: ${question.item}`);
          assertFairIndependently(question, language);
          const identity = `${question.type}|${P.keyOf(question.card)}|${question.item}`;
          assert.ok(!identities.has(identity), `repeated ${identity}`);
          identities.add(identity);
        }
      }
    }
  }
});

test("a full session is offered for every exercise", { skip: !cards && "build/site not built" }, () => {
  for (const type of [...P.TYPES, "mix"]) {
    assert.equal(P.session(type, cards, { random: P.seeded(3) }).length, P.SESSION_SIZE, type);
  }
});

test("reverse cards only use verbs whose meaning is unique", { skip: !cards && "build/site not built" }, () => {
  for (const language of LANGUAGES) {
    const unique = P.uniquelyMeant(cards, language);
    for (const card of unique) {
      for (const other of cards) {
        if (P.keyOf(other) === P.keyOf(card)) continue;
        assert.ok(!P.meaningsOverlap(other.meaning[language] || other.meaning.en, card.meaning[language] || card.meaning.en));
      }
    }
  }
});

// Checked from first principles, not through problemsWith — a rule that is wrong there
// must still be caught here.
function assertFairIndependently(question, language) {
  if (question.type === "ayah") return;
  const correct = question.options.filter((option) => option.correct);
  assert.equal(correct.length, 1);
  if (question.type === "form") {
    const rightSpelling = P.spellingKey(question.cell.plain);
    for (const option of question.options) {
      if (!option.correct) assert.notEqual(P.spellingKey(option.cell.plain), rightSpelling, "another reading offered as wrong");
    }
    return;
  }
  const looks = question.options.map((option) => P.spellingKey(option.label));
  assert.equal(new Set(looks).size, looks.length, "two options look alike");
  if (question.type === "sentence") assert.equal(correct[0].label, question.target.arabic);
  if (question.type === "listen") assert.equal(correct[0].label, question.cell.plain);
  if (question.type === "meaning") {
    const right = question.card.meaning[language] || question.card.meaning.en;
    assert.equal(correct[0].label, right);
  }
}

test("a sentence blank never offers the same form spelt with a connecting-alif vowel", () => {
  const KNOW = {
    root: "علم", form: 1, lemma: "عَلِمَ", meaning: { en: "to know" }, principal: [], ayat: [],
    cells: [cell("imperative", "anta", "اِعْلَمْ"), cell("present", "ana", "أَعْلَمُ"), cell("past", "huwa", "عَلِمَ"),
            cell("past", "hum", "عَلِمُوا"), cell("present", "huwa", "يَعْلَمُ")],
    sentences: [{ arabic: "اعْلَمْ ذَلِكَ", translation: { en: "Know that." },
                  words: [{ arabic: "اعْلَمْ", target: true }, { arabic: "ذَلِكَ", target: false }] }],
  };
  const random = P.seeded(11);
  for (let i = 0; i < 200; i++) {
    const question = P.builders.sentence(KNOW, [KNOW], "en", random);
    const labels = question.options.map((option) => option.label);
    assert.ok(!labels.includes("اِعْلَمْ"), `offered both spellings: ${labels}`);
  }
});
