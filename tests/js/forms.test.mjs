// "Koji oblik?" and "Oblik → glagol": the form's number, its pattern and the note after answering.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const E = require("../../src/fil/site/exercises.js");

const WORDS = { meaning: "Značenje", formNotes: { 2: "često pojačava radnju.", q4: "rijedak oblik." } };

test("a form is named by its number and pattern; a four-letter root's code has the same number", () => {
  assert.equal(E.formNumber("2"), "II");
  assert.equal(E.formNumber("q4"), "IV");
  assert.equal(E.formNumber("10"), "X");
  assert.equal(E.formName("2", "فَعَّلَ"), "II · فَعَّلَ");
  assert.deepEqual(E.FORM_KINDS, ["verb-form", "form-verb"]);
});

test("after answering, a form question names the verb's meaning and what the form adds", () => {
  const asked = { options: [{ ar: "فَعَّلَ", code: "2" }, { ar: "فَعَلَ", code: "1" }], gloss: { bs: "učiti", en: "to teach" },
                  facts: { root: "ع ل م", form: "2" } };
  assert.deepEqual(E.explanationLines("verb-form", asked, WORDS, "bs"), ["Značenje: učiti", "II · فَعَّلَ – često pojačava radnju."]);
  const reverse = { options: [{ ar: "عَلَّمَ" }], lead: "فَعَّلَ", gloss: { bs: "učiti", en: "to teach" }, facts: { form: "2" } };
  assert.deepEqual(E.explanationLines("form-verb", reverse, WORDS, "en"), ["Značenje: to teach", "II · فَعَّلَ – često pojačava radnju."]);
});
