// The exercise page's logic (run by tests/test_practice_js.py, or `node --test tests/js`).
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const E = require("../../src/fil/site/exercises.js");

const item = (id, words = ["noun:ard"]) => ({ id, words, options: [{ code: "subject" }, { code: "object" }, { code: "preposition" }] });
const question = (id) => ({ kind: "case", item: item(id) });
const NOW = 1_000_000_000_000;

test("the shard of a word is the one the build put it in (fil.exercises.shards)", () => {
  // tests/test_exercises.py holds the Python side to the same values.
  assert.deepEqual([E.shardOf("noun:ard", 7), E.shardOf("nuance:insan-bashar", 11), E.shardOf("particle:fi", 1000)], [6, 4, 470]);
  assert.equal(E.shardFile("case", 3), "case-3.json");
});

test("shuffled options keep exactly one right answer, the file's first option", () => {
  const random = E.seeded(3);
  for (let i = 0; i < 50; i++) {
    const options = E.shuffledOptions(item("x"), random);
    assert.equal(options.filter((option) => option.isCorrect).length, 1);
    assert.equal(options.find((option) => option.isCorrect).option.code, "subject");
  }
});

test("a right answer moves a question up a box and away; a wrong one makes it due at once", () => {
  let progress = E.record(E.emptyProgress(), "case:a", true, NOW);
  assert.deepEqual(progress.boxes["case:a"], { box: 0, due: NOW });
  progress = E.record(progress, "case:a", true, NOW);
  assert.deepEqual(progress.boxes["case:a"], { box: 1, due: NOW + E.DAY });
  progress = E.record(progress, "case:a", true, NOW);
  assert.equal(progress.boxes["case:a"].due, NOW + 3 * E.DAY);
  assert.equal(progress.streak, 3);
  progress = E.record(progress, "case:a", false, NOW);
  assert.deepEqual(progress.boxes["case:a"], { box: 0, due: NOW });
  assert.deepEqual([progress.answered, progress.correct, progress.streak, progress.best], [4, 3, 0, 3]);
});

test("recording never changes the progress it was given", () => {
  const before = E.emptyProgress();
  E.record(before, "case:a", true, NOW);
  assert.deepEqual(before, E.emptyProgress());
});

test("a session asks due questions first, then new ones, then the rest by due date", () => {
  const questions = ["missed", "new1", "later", "new2", "soon"].map(question);
  const progress = { ...E.emptyProgress(), boxes: {
    "case:missed": { box: 0, due: NOW - 1 }, "case:later": { box: 3, due: NOW + 9 * E.DAY }, "case:soon": { box: 1, due: NOW + E.DAY } } };
  const order = E.sessionOrder(questions, progress, NOW, E.seeded(1)).map((asked) => asked.item.id);
  assert.equal(order[0], "missed");
  assert.deepEqual(new Set(order.slice(1, 3)), new Set(["new1", "new2"]));
  assert.deepEqual(order.slice(3), ["soon", "later"]);
  assert.equal(E.sessionOrder(questions, progress, NOW, E.seeded(1), 2).length, 2);
});

test("a missed question comes back a few questions later in the same session", () => {
  const queue = ["a", "b", "c", "d", "e", "f"].map(question);
  const again = E.askAgain(queue, 0, queue[0]);
  assert.equal(again.length, 7);
  assert.equal(again[1 + E.AGAIN_AFTER].item.id, "a");
  assert.equal(E.askAgain(queue, 5, queue[5]).at(-1).item.id, "f");   // at the end, it is asked last
});

test("progress storage that throws or holds rubbish is survived", () => {
  const broken = { getItem: () => { throw new Error("blocked"); }, setItem: () => { throw new Error("blocked"); } };
  assert.deepEqual(E.readProgress(broken), E.emptyProgress());
  assert.equal(E.writeProgress(broken, E.emptyProgress()), false);
  assert.deepEqual(E.readProgress({ getItem: () => "{not json" }), E.emptyProgress());
  const kept = new Map();
  const storage = { getItem: (key) => kept.get(key) ?? null, setItem: (key, value) => kept.set(key, value) };
  const progress = E.record(E.emptyProgress(), "case:a", true, NOW);
  assert.equal(E.writeProgress(storage, progress), true);
  assert.deepEqual(E.readProgress(storage), progress);
});

test("only the questions about the asked word, when one is asked", () => {
  const items = [item("a", ["noun:ard"]), item("b", ["noun:bayt"])];
  assert.deepEqual(E.aboutWord(items, "noun:bayt").map((found) => found.id), ["b"]);
  assert.equal(E.aboutWord(items, "").length, 2);
});

test("a root's words, asked together: the questions about any of them, each once, from each word's shard", () => {
  const items = [item("a", ["verb:qala"]), item("b", ["noun:bayt"]), item("c", ["noun:qawl", "verb:qala"])];
  assert.deepEqual(E.askedWords("verb:qala,noun:qawl"), ["verb:qala", "noun:qawl"]);
  assert.deepEqual(E.aboutWord(items, "verb:qala,noun:qawl").map((found) => found.id), ["a", "c"]);
  assert.deepEqual(E.uniqueById([...items, items[2]]).map((found) => found.id), ["a", "b", "c"]);
  const shards = E.shardsFor("noun:ard,nuance:insan-bashar", 7, () => 0);
  assert.deepEqual(shards, [...new Set([E.shardOf("noun:ard", 7), E.shardOf("nuance:insan-bashar", 7)])]);
  assert.deepEqual(E.shardsFor("", 7, () => 0.5), [3]);
});

const WORDS = E.withTemplates({
  roles: { subject: "nominativ – subjekat" }, effects: { JUS: "jusiv" },
  roleWhy: { subject: "Subjekat je u nominativu." }, inBosnian: "Na bosanskom: „{0}“.",
  afterPreposition: "Iza prijedloga genitiv.", renderedAs: "Na bosanskom: {0}.", bosnianCases: { L: "lokativ" },
  rules: { thingsPlural: "Množina stvari." }, agreesIn: "Padež ({0}), određenost ({1}).",
  cases: { ACC: "akuzativ" }, states: { indefinite: "neodređen" },
  meaning: "Značenje", why: "Zašto", inThisAyah: "U ovom ajetu", use: "Upotreba",
  questionOf: "Pitanje {0} / {1}", score: "{0} od {1} · niz {2} · najbolji {3}", sessionScore: "{0} od {1}",
  verb: "Glagol", formIs: "Oblik: {0}.", tenses: { past: "prošlo", present: "sadašnje" },
  pronouns: { ana: "ja", anta: "ti (m.)", hiya: "ona" },
});

test("option labels: Arabic as it is, a meaning in the page's language, a code by its name", () => {
  assert.equal(E.optionLabel("picture", { ar: "أَرْض" }, WORDS, "bs"), "أَرْض");
  assert.equal(E.optionLabel("listen", { bs: "zemlja", en: "earth" }, WORDS, "bs"), "zemlja");
  assert.equal(E.optionLabel("case", { code: "subject" }, WORDS, "bs"), "nominativ – subjekat");
  assert.equal(E.optionLabel("particle", { code: "JUS" }, WORDS, "bs"), "jusiv");
  assert.equal(WORDS.score(3, 4, 2, 5), "3 od 4 · niz 2 · najbolji 5");
});

test("a verb under its animation is labelled by its Arabic, with its meaning beside it", () => {
  const verb = { ar: "أَكَلَ", bs: "jesti", en: "to eat" };
  assert.equal(E.optionLabel("animation", verb, WORDS, "bs"), "أَكَلَ");
  assert.equal(E.optionMeaning(verb, "bs"), "jesti");
  assert.equal(E.optionMeaning({ ar: "أَكَلَ", en: "to eat" }, "bs"), "to eat");   // English until it is translated
  assert.equal(E.optionMeaning({ ar: "أَرْض" }, "bs"), "");                          // a picture's word: Arabic alone
  assert.equal(E.optionMeaning({ bs: "zemlja", en: "earth" }, "bs"), "");           // a meaning option is its own label
});

test("the explanation after answering says why, in the page's language", () => {
  const caseItem = { facts: { role: "subject", case: "NOM" }, gloss: { bs: "kuća", en: "house" } };
  assert.deepEqual(E.explanationLines("case", caseItem, WORDS, "bs"), ["Subjekat je u nominativu.", "Na bosanskom: „kuća“."]);
  const after = { facts: { case: "GEN", bosnianCase: "L" }, gloss: { bs: "na zemlji", en: "in the earth" } };
  assert.deepEqual(E.explanationLines("preposition", after, WORDS, "bs"), ["Iza prijedloga genitiv.", "Na bosanskom: na zemlji (lokativ)."]);
  assert.equal(E.explanationLines("preposition", after, WORDS, "en")[1], "Na bosanskom: in the earth.");   // no Bosnian case in English
  const agreeing = { facts: { rule: "thingsPlural", case: "ACC", state: "indefinite" } };
  assert.deepEqual(E.explanationLines("agreement", agreeing, WORDS, "bs"), ["Množina stvari.", "Padež (akuzativ), određenost (neodređen)."]);
  const nuance = { gloss: { bs: "čovjek", en: "man" }, explanation: { bs: "Ljudska narav.", en: "Human nature." } };
  assert.deepEqual(E.explanationLines("nuance", nuance, WORDS, "en"), ["Značenje: man", "Zašto: Human nature."]);
});

test("a verb form's explanation names every reading of it and its verb", () => {
  assert.equal(E.cellNames("present:anta,present:hiya", WORDS), "sadašnje · ti (m.) / sadašnje · ona");
  const form = { facts: { readings: "present:anta,present:hiya", verb: "قَالَ" }, gloss: { bs: "reći", en: "to say" } };
  assert.deepEqual(E.explanationLines("form-meaning", form, WORDS, "bs"),
    ["Oblik: sadašnje · ti (m.) / sadašnje · ona.", "Glagol: قَالَ – reći"]);
  const quranic = { facts: { verb: "قَالَ" }, gloss: { bs: "reći", en: "to say" } };
  assert.deepEqual(E.explanationLines("quran-form", quranic, WORDS, "en"), ["Glagol: قَالَ – to say"]);
  const heard = E.explanationLines("hear-reciter", { ...form, facts: { readings: "present:anta", verb: "قَالَ" } }, WORDS, "bs");
  assert.deepEqual(heard, ["Oblik: sadašnje · ti (m.).", "Glagol: قَالَ – reći"]);
  assert.deepEqual(E.VERB_FORM_KINDS, ["form-meaning", "meaning-form", "quran-form", "hear-reciter"]);
});

// ---------- one shard that fails must not cost the session ----------

/** A fetch that fails for the paths it is told to (as often as it is told to) and counts its calls. */
function flakyFetch(shards, failures) {
  const calls = {};
  const fetchShard = async (path) => {
    calls[path] = (calls[path] || 0) + 1;
    if (calls[path] <= (failures[path] || 0)) throw new Error(`${path} failed`);
    return shards[path];
  };
  return { fetchShard, calls };
}

test("a shard that fails once is asked for again and its questions are used", async () => {
  const { fetchShard, calls } = flakyFetch({ "case-0.json": [item("a")] }, { "case-0.json": 1 });
  const loaded = await E.loadShards([{ kind: "case", path: "case-0.json" }], fetchShard);
  assert.deepEqual(loaded, [{ kind: "case", items: [item("a")] }]);
  assert.equal(calls["case-0.json"], 2);
});

test("a shard that keeps failing is skipped and the session goes on with the shards that loaded", async () => {
  const shards = { "case-0.json": [item("a")], "case-1.json": [item("b")], "agreement-0.json": [item("c")] };
  const { fetchShard, calls } = flakyFetch(shards, { "case-1.json": Infinity });
  const requests = [
    { kind: "case", path: "case-0.json" }, { kind: "case", path: "case-1.json" }, { kind: "agreement", path: "agreement-0.json" },
  ];
  const loaded = await E.loadShards(requests, fetchShard);
  assert.equal(calls["case-1.json"], E.SHARD_ATTEMPTS);
  const questions = E.questionsOf(loaded, ["case", "agreement"], "");
  assert.deepEqual(questions.map(({ kind, item: one }) => `${kind}:${one.id}`), ["case:a", "agreement:c"]);
});

test("only when no shard loads does loading fail", async () => {
  const { fetchShard } = flakyFetch({}, { "case-0.json": Infinity, "case-1.json": Infinity });
  await assert.rejects(E.loadShards([{ kind: "case", path: "case-0.json" }, { kind: "case", path: "case-1.json" }], fetchShard));
});

test("questions from two shards are each kept once and only about the asked word", () => {
  const loaded = [
    { kind: "case", items: [item("a"), item("b", ["noun:sama"])] },
    { kind: "case", items: [item("a")] },
  ];
  assert.deepEqual(E.questionsOf(loaded, ["case"], "noun:ard").map(({ item: one }) => one.id), ["a"]);
});
