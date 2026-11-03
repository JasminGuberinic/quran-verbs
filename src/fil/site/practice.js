/*
 * Fiʿl practice: the questions behind every exercise, and the rules that make each one fair.
 *
 * Pure functions over verb cards (the JSON `fil site` writes) — no DOM, no audio, no
 * storage — so the same code runs in the page and under `node --test`. Every question is
 * built and then checked by `problemsWith`; a question that breaks a rule is never shown:
 *
 *   - exactly one offered option is correct;
 *   - no two options look the same (spellings folded the way a reader sees them);
 *   - a form that has several readings (تَقُولُ: "she says" and "you say") is never paired
 *     with another of its own readings as a "wrong" option — the learner is told all of them;
 *   - a meaning question never offers a second verb whose meaning overlaps the right one
 *     (جَاءَ and أَتَى both mean "to come").
 *
 * A session is a fixed number of questions with no verb-and-item asked twice; weaker verbs
 * (lower Leitner box) come up more often.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.FilPractice = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const SESSION_SIZE = 10;
  const OPTION_COUNT = 4;
  const TYPES = ["meaning", "form", "listen", "ayah", "sentence"];

  // ---------- spelling and meaning, the way a learner perceives them ----------

  const SILENT_MARKS = /[ۜ۟-۪ۨ-ۭٓـ]/g;   // Uthmani pause/silence marks, madda sign, tatweel

  /** A spelling folded so that two words a reader sees as the same compare equal. */
  function spellingKey(text) {
    let word = text.normalize("NFD").replace(SILENT_MARKS, "").replace(/ٱ/g, "ا");
    word = word.replace(/(^|\s)ا[َُِ]/g, "$1ا");   // vowel on a connecting alif
    return word.normalize("NFC");
  }

  // Words that carry no meaning of their own in a gloss ("to say", "bojati se").
  const STOPWORDS = new Set(["to", "the", "a", "an", "of", "for", "oneself", "se"]);

  /** The content words of a meaning in one language, lower-cased. */
  function meaningWords(meaning) {
    return new Set(meaning.toLowerCase().split(/[\s,;()/]+/).filter((word) => word && !STOPWORDS.has(word)));
  }

  function meaningsOverlap(a, b) {
    const wordsA = meaningWords(a);
    return [...meaningWords(b)].some((word) => wordsA.has(word));
  }

  const meaningIn = (card, language) => card.meaning[language] || card.meaning.en;
  const keyOf = (card) => `${card.root}_${card.form}`;

  // ---------- randomness that tests can pin ----------

  function seeded(seed) {
    let state = seed >>> 0 || 1;
    return () => {
      state = (state * 1664525 + 1013904223) >>> 0;
      return state / 4294967296;
    };
  }

  function shuffle(items, random) {
    const copy = [...items];
    for (let i = copy.length - 1; i > 0; i--) {
      const j = Math.floor(random() * (i + 1));
      [copy[i], copy[j]] = [copy[j], copy[i]];
    }
    return copy;
  }

  const pick = (items, random) => items[Math.floor(random() * items.length)];

  /** Choose a verb, weaker ones more often: weight 1 / (1 + box). */
  function weightedCard(cards, boxOf, random) {
    const weights = cards.map((card) => 1 / (1 + (boxOf(card) || 0)));
    let roll = random() * weights.reduce((sum, weight) => sum + weight, 0);
    for (let i = 0; i < cards.length; i++) {
      roll -= weights[i];
      if (roll <= 0) return cards[i];
    }
    return cards[cards.length - 1];
  }

  /** Up to `count` items whose keys differ from each other and from every key in `taken`. */
  function distinctBy(items, keyFn, taken, count) {
    const seen = new Set(taken);
    const chosen = [];
    for (const item of items) {
      const key = keyFn(item);
      if (seen.has(key)) continue;
      seen.add(key);
      chosen.push(item);
      if (chosen.length === count) break;
    }
    return chosen;
  }

  // ---------- the questions ----------

  /** Cells of a card that read exactly like `cell` — every reading of that one spelling. */
  function readingsOf(card, cell) {
    const key = spellingKey(cell.plain);
    return card.cells.filter((other) => spellingKey(other.plain) === key);
  }

  const builders = {
    /** See and hear a form; choose its verb's meaning. */
    meaning(card, cards, language, random) {
      const cell = pick(card.principal, random);
      const right = meaningIn(card, language);
      const others = shuffle(cards.filter((other) => keyOf(other) !== keyOf(card)), random)
        .filter((other) => !meaningsOverlap(meaningIn(other, language), right));
      const wrong = distinctBy(others, (other) => meaningIn(other, language), [right], OPTION_COUNT - 1);
      return {
        type: "meaning", card, item: cell.plain, cell,
        options: shuffle([{ label: right, correct: true },
          ...wrong.map((other) => ({ label: meaningIn(other, language), correct: false }))], random),
      };
    },

    /** See a form; say who does it and when. Every reading of the spelling counts as right. */
    form(card, cards, language, random) {
      const attested = card.cells.filter((cell) => cell.quran);
      const cell = pick(attested.length ? attested : card.cells, random);
      const readings = readingsOf(card, cell);
      const sameSpelling = new Set(readings.map(labelKey));
      const wrong = distinctBy(shuffle(card.cells, random).filter((other) => !sameSpelling.has(labelKey(other))),
        labelKey, [labelKey(cell)], OPTION_COUNT - 1);
      return {
        type: "form", card, item: cell.plain, cell, readings,
        options: shuffle([{ cell, correct: true }, ...wrong.map((other) => ({ cell: other, correct: false }))], random),
      };
    },

    /** Hear a form; choose how it is written. */
    listen(card, cards, language, random) {
      const cell = pick(card.cells, random);
      const wrong = distinctBy(shuffle(card.cells, random), (other) => spellingKey(other.plain),
        [spellingKey(cell.plain)], OPTION_COUNT - 1);
      return {
        type: "listen", card, item: cell.plain, cell, readings: readingsOf(card, cell),
        options: shuffle([{ label: cell.plain, correct: true },
          ...wrong.map((other) => ({ label: other.plain, correct: false }))], random),
      };
    },

    /** Hear an ayah; tap its verb. */
    ayah(card, cards, language, random) {
      if (!card.ayat.length) return null;
      const ayah = pick(card.ayat, random);
      return { type: "ayah", card, item: ayah.ref, ayah };
    },

    /** Complete a practice sentence with the right form; its translation is the clue. */
    sentence(card, cards, language, random) {
      if (!card.sentences.length) return null;
      const sentence = pick(card.sentences, random);
      const target = sentence.words.find((word) => word.target);
      const forms = card.cells.map((cell) => cell.plain);
      const wrong = distinctBy(shuffle(forms, random), spellingKey, [spellingKey(target.arabic)], OPTION_COUNT - 1);
      return {
        type: "sentence", card, item: sentence.arabic, sentence, target,
        options: shuffle([{ label: target.arabic, correct: true },
          ...wrong.map((form) => ({ label: form, correct: false }))], random),
      };
    },
  };

  function labelKey(cell) {
    return `${cell.tense}:${cell.pronoun}`;
  }

  /** Why a question must not be shown — empty when it is fair. */
  function problemsWith(question) {
    const problems = [];
    if (question.type === "ayah") {
      if (!question.ayah.words.some((word) => word.hit)) problems.push("the ayah has no verb to find");
      return problems;
    }
    const options = question.options;
    if (options.length < 2) problems.push("fewer than two options");
    if (options.filter((option) => option.correct).length !== 1) problems.push("not exactly one correct option");
    if (question.type === "form") {
      const keys = options.map((option) => labelKey(option.cell));
      if (new Set(keys).size !== keys.length) problems.push("two options name the same cell");
      const correctSpelling = spellingKey(question.cell.plain);
      for (const option of options) {
        if (!option.correct && spellingKey(option.cell.plain) === correctSpelling) {
          problems.push("a 'wrong' option is another reading of the same spelling");
        }
      }
      return problems;
    }
    const seen = options.map((option) => question.type === "meaning" ? option.label : spellingKey(option.label));
    if (new Set(seen).size !== seen.length) problems.push("two options look the same");
    if (question.type === "meaning") {
      const right = options.find((option) => option.correct).label;
      for (const option of options) {
        if (!option.correct && meaningsOverlap(option.label, right)) problems.push(`"${option.label}" overlaps the right meaning`);
      }
    }
    return problems;
  }

  /**
   * A session: `size` fair questions of `type` ("mix" draws a type per question), never the
   * same verb-and-item twice. Returns fewer when the cards cannot supply that many.
   */
  function session(type, cards, { language = "en", boxOf = () => 0, random = Math.random, size = SESSION_SIZE } = {}) {
    const questions = [];
    const asked = new Set();
    for (let attempt = 0; questions.length < size && attempt < size * 40; attempt++) {
      const kind = type === "mix" ? pick(TYPES, random) : type;
      const card = weightedCard(cards, boxOf, random);
      const question = builders[kind](card, cards, language, random);
      if (!question) continue;
      const identity = `${kind}|${keyOf(card)}|${question.item}`;
      if (asked.has(identity) || problemsWith(question).length) continue;
      asked.add(identity);
      questions.push(question);
    }
    return questions;
  }

  /** Verbs whose meaning in `language` overlaps no other verb's — safe to ask in reverse. */
  function uniquelyMeant(cards, language) {
    return cards.filter((card) => cards.every((other) =>
      keyOf(other) === keyOf(card) || !meaningsOverlap(meaningIn(other, language), meaningIn(card, language))));
  }

  return { SESSION_SIZE, TYPES, spellingKey, meaningsOverlap, seeded, session, problemsWith, builders, uniquelyMeant, readingsOf, keyOf };
});
