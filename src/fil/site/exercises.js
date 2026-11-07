/*
 * Fiʿl exercises (Vježbe): shows the questions `fil pages` built and checks the answers.
 *
 * The questions are made and gated at build time (fil.exercises): each lists its right option
 * first, and nothing here makes up Arabic. This file only orders, shows and grades them:
 *
 *   - a session is SESSION_SIZE questions: those due again first (a missed one is due at once),
 *     then new ones, then the rest by when they fall due;
 *   - a missed question comes back AGAIN_AFTER questions later in the same session;
 *   - light spaced repetition (Leitner boxes): a right answer moves a question up a box and
 *     away for BOX_DAYS[box] days, a wrong one back to box 0;
 *   - progress (boxes, score, streak) lives in this browser only (localStorage, every access
 *     wrapped: a private window or blocked storage just means nothing is remembered).
 *
 * The pure part (no DOM) runs under `node --test` (tests/js/exercises.test.mjs); the page part
 * wires itself to <div id="exercises" data-…> on the static exercise pages (fil.pages.exercise_render).
 * Sounds play through the site's one player (player.js): every sound button carries data-audio.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.FilExercises = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const SESSION_SIZE = 10;
  const AGAIN_AFTER = 3;
  const BOX_DAYS = [0, 1, 3, 7, 21];
  const DAY = 24 * 60 * 60 * 1000;
  const STORAGE_KEY = "fil.exercises.v1";
  const KEY_OPTIONS = ["1", "2", "3", "4"];

  // ---------- the shard a word's questions are in (fil.exercises.shards computes the same) ----------

  /** FNV-1a (32 bits) of the word id's UTF-8 bytes, modulo the shard count. */
  function shardOf(word, count) {
    let hash = 0x811c9dc5;
    for (const byte of new TextEncoder().encode(word)) {
      hash = Math.imul(hash ^ byte, 0x01000193) >>> 0;
    }
    return hash % count;
  }

  const shardFile = (kind, number) => `${kind}-${number}.json`;

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

  // ---------- a question ----------

  /** The question's options in a random order, each marked right or not (the file lists the right one first). */
  function shuffledOptions(item, random) {
    return shuffle(item.options.map((option, index) => ({ option, isCorrect: index === 0 })), random);
  }

  const questionKey = (question) => `${question.kind}:${question.item.id}`;

  /** The words asked for: one ("noun:ard"), or a root's several, comma-separated ("verb:qala,noun:qawl"). */
  function askedWords(word) {
    return (word || "").split(",").filter(Boolean);
  }

  /** Only the questions practising an asked word, when any is asked for. */
  function aboutWord(items, word) {
    const asked = askedWords(word);
    return asked.length ? items.filter((item) => asked.some((one) => item.words.includes(one))) : items;
  }

  /** The shards a kind's questions about the asked words are in (one random shard when none is asked). */
  function shardsFor(word, count, random) {
    const asked = askedWords(word);
    return asked.length ? [...new Set(asked.map((one) => shardOf(one, count)))] : [Math.floor(random() * count)];
  }

  /** Each question once, though two asked words may bring it from two shards. */
  function uniqueById(items) {
    const seen = new Set();
    return items.filter((item) => !seen.has(item.id) && seen.add(item.id));
  }

  // ---------- loading: one shard that fails must not cost the learner the session ----------

  const SHARD_ATTEMPTS = 2;

  /** A shard's questions, asked for again once before it is given up on. */
  async function fetchWithRetry(fetchShard, path, attempts = SHARD_ATTEMPTS) {
    try {
      return await fetchShard(path);
    } catch (error) {
      if (attempts <= 1) throw error;
      return fetchWithRetry(fetchShard, path, attempts - 1);
    }
  }

  /**
   * The shards that loaded, as { kind, items }; a shard that keeps failing is skipped and the
   * session goes on with the others. Rejects only when not one shard loads.
   */
  async function loadShards(requests, fetchShard) {
    const settled = await Promise.allSettled(requests.map(({ path }) => fetchWithRetry(fetchShard, path)));
    const loaded = requests
      .map(({ kind }, index) => ({ kind, outcome: settled[index] }))
      .filter(({ outcome }) => outcome.status === "fulfilled")
      .map(({ kind, outcome }) => ({ kind, items: outcome.value }));
    if (requests.length && !loaded.length) throw new Error("no exercise shard loaded");
    return loaded;
  }

  /** The questions of each wanted kind, in the order the kinds are wanted, each question once. */
  function questionsOf(loaded, wanted, word) {
    return wanted.flatMap((kind) => {
      const items = loaded.filter((shard) => shard.kind === kind).flatMap((shard) => shard.items);
      return uniqueById(aboutWord(items, word)).map((item) => ({ kind, item }));
    });
  }

  // ---------- progress ----------

  function emptyProgress() {
    return { boxes: {}, answered: 0, correct: 0, streak: 0, best: 0 };
  }

  /** The progress after one answer; the old one is left as it was. */
  function record(progress, key, isCorrect, now) {
    const box = isCorrect ? Math.min((progress.boxes[key]?.box ?? -1) + 1, BOX_DAYS.length - 1) : 0;
    const due = isCorrect ? now + BOX_DAYS[box] * DAY : now;
    const streak = isCorrect ? progress.streak + 1 : 0;
    return {
      boxes: { ...progress.boxes, [key]: { box, due } },
      answered: progress.answered + 1,
      correct: progress.correct + (isCorrect ? 1 : 0),
      streak,
      best: Math.max(progress.best, streak),
    };
  }

  /**
   * The questions of a session: due ones first (the earliest due first — a missed one is due at
   * once), then ones never asked (in random order), then the rest by when they fall due.
   */
  function sessionOrder(questions, progress, now, random, size = SESSION_SIZE) {
    const boxOf = (question) => progress.boxes[questionKey(question)];
    const due = questions.filter((question) => boxOf(question) && boxOf(question).due <= now)
      .sort((a, b) => boxOf(a).due - boxOf(b).due);
    const fresh = shuffle(questions.filter((question) => !boxOf(question)), random);
    const later = questions.filter((question) => boxOf(question) && boxOf(question).due > now)
      .sort((a, b) => boxOf(a).due - boxOf(b).due);
    return [...due, ...fresh, ...later].slice(0, size);
  }

  /** The queue with a missed question put back AGAIN_AFTER places after the current one. */
  function askAgain(queue, position, question) {
    const at = Math.min(position + 1 + AGAIN_AFTER, queue.length);
    return [...queue.slice(0, at), question, ...queue.slice(at)];
  }

  // ---------- storage: this browser only, and never trusted to work ----------

  function readProgress(storage) {
    try {
      const stored = JSON.parse(storage.getItem(STORAGE_KEY) || "null");
      return stored && typeof stored === "object" && stored.boxes ? { ...emptyProgress(), ...stored } : emptyProgress();
    } catch {
      return emptyProgress();
    }
  }

  function writeProgress(storage, progress) {
    try {
      storage.setItem(STORAGE_KEY, JSON.stringify(progress));
      return true;
    } catch {
      return false;
    }
  }

  // ---------- what the learner reads after answering ----------

  // The kinds about a verb's forms: their facts name the verb and the cells (tense:person) a form is.
  const VERB_FORM_KINDS = ["form-meaning", "meaning-form", "quran-form", "hear-reciter"];

  // The kinds about which of the ten forms a verb is in: a form's code is its number ("4"), or "q4" for a four-letter root.
  const FORM_KINDS = ["verb-form", "form-verb"];
  const ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"];

  /** "4" and "q4" → "IV": the number a form is known by. */
  function formNumber(code) {
    return ROMAN[Number(String(code).replace("q", ""))] || "";
  }

  /** "4" → "IV · أَفْعَلَ": a form as a learner names it, its number and its pattern. */
  function formName(code, pattern) {
    return `${formNumber(code)} · ${pattern}`;
  }

  /** "present:anta,present:hiya" → "sadašnje · ti (m.) / sadašnje · ona": every reading of the form. */
  function cellNames(readings, words) {
    return readings.split(",").map((cell) => {
      const [tense, person] = cell.split(":");
      return `${words.tenses[tense]} · ${words.pronouns[person]}`;
    }).join(" / ");
  }

  /** The lines of explanation for an answered question, as plain text in the page's language. */
  function explanationLines(kind, item, words, language) {
    const text = (texts) => (texts ? texts[language] || texts.en : "");
    const facts = item.facts || {};
    const lines = [];
    if (kind === "case") {
      lines.push(words.roleWhy[facts.role]);
      if (item.gloss) lines.push(words.inBosnian(text(item.gloss)));
    }
    if (kind === "preposition") {
      // The Bosnian case belongs to the Bosnian rendering only.
      const bosnianCase = facts.bosnianCase && language === "bs" ? ` (${words.bosnianCases[facts.bosnianCase]})` : "";
      lines.push(words.afterPreposition);
      if (item.gloss) lines.push(words.renderedAs(text(item.gloss) + bosnianCase));
    }
    if (kind === "agreement") {
      lines.push(words.rules[facts.rule]);
      lines.push(words.agreesIn(words.cases[facts.case], words.states[facts.state]));
    }
    if (kind === "particle" && item.gloss) lines.push(`${words.use}: ${text(item.gloss)}`);
    if (facts.readings) lines.push(words.formIs(cellNames(facts.readings, words)));
    if (VERB_FORM_KINDS.includes(kind) && item.gloss) lines.push(`${words.verb}: ${facts.verb} – ${text(item.gloss)}`);
    if ((kind === "picture" || kind === "nuance" || FORM_KINDS.includes(kind)) && item.gloss) lines.push(`${words.meaning}: ${text(item.gloss)}`);
    if (FORM_KINDS.includes(kind) && facts.form) {
      const pattern = kind === "form-verb" ? item.lead : item.options[0].ar;
      lines.push(`${formName(facts.form, pattern)} – ${words.formNotes[facts.form]}`);
    }
    if (item.explanation) lines.push(`${kind === "nuance" ? words.why : words.inThisAyah}: ${text(item.explanation)}`);
    return lines.filter(Boolean);
  }

  /** The meaning written beside an Arabic option (a verb named by both, under its animation), or "". */
  function optionMeaning(option, language) {
    if (!option.ar) return "";
    return option[language] || option.en || "";
  }

  /** How an option is labelled: its Arabic, its meaning in the page's language, or the name of its code. */
  function optionLabel(kind, option, words, language) {
    if (option.ar) return option.ar;
    if (option.code) return kind === "case" ? words.roles[option.code] : words.effects[option.code];
    return option[language] || option.en;
  }

  // ---------- the page ----------

  function start(doc, element, words, location, storage, now = () => Date.now(), random = Math.random) {
    const root = element.dataset.root;
    const language = element.dataset.language;
    const shards = JSON.parse(element.dataset.shards);
    const params = new URLSearchParams(location.search);
    const word = params.get("w") || "";
    const wanted = (params.get("t") || element.dataset.kinds).split(",").filter((kind) => kind in shards);
    let progress = readProgress(storage);
    let queue = [];
    let position = 0;
    let sessionRight = 0;

    const $ = (selector) => element.querySelector(selector);
    const make = (tag, attributes = {}, content = "") => {
      const made = doc.createElement(tag);
      for (const [name, value] of Object.entries(attributes)) made.setAttribute(name, value);
      if (content) made.textContent = content;
      return made;
    };
    // Arabic is never handed to the browser's page translation (site/translation.js says why).
    const arabic = (tag, content, extra = {}) => {
      const made = make(tag, { lang: "ar", dir: "rtl", class: "ar", ...extra, translate: "no" }, content);
      made.classList.add("notranslate");
      return made;
    };
    const soundButton = (path, label) => {
      const button = make("button", { type: "button", class: "play", "data-audio": root + path, "aria-label": label });
      button.innerHTML = '<span class="play-icon notranslate" aria-hidden="true" translate="no">▶</span>';
      return button;
    };

    function load() {
      $(".exercise-status").textContent = words.loading;
      const requests = wanted.flatMap((kind) => shardsFor(word, shards[kind], random)
        .map((number) => ({ kind, path: `${root}exercises/${shardFile(kind, number)}` })));
      const fetchShard = (path) => fetch(path).then((response) => {
        if (!response.ok) throw new Error(response.statusText);
        return response.json();
      });
      // A surah's link says so (&s=surah); several words are otherwise a root's.
      const severalOnly = (params.get("s") === "surah" ? words.surahOnly : words.rootOnly) || words.wordOnly;
      loadShards(requests, fetchShard).then((loaded) => {
        const questions = questionsOf(loaded, wanted, word);
        $(".exercise-status").textContent = !questions.length ? words.empty : askedWords(word).length > 1 ? severalOnly : word ? words.wordOnly : "";
        if (questions.length) begin(questions);
      }).catch(() => { $(".exercise-status").textContent = words.loadFailed; });
    }

    function begin(questions) {
      queue = sessionOrder(questions, progress, now(), random);
      position = 0;
      sessionRight = 0;
      show();
    }

    function show() {
      const card = $(".exercise-card");
      card.replaceChildren();
      const { kind, item } = queue[position];
      card.append(make("p", { class: "eyebrow" }, `${words.kinds[kind].name} · ${words.questionOf(position + 1, queue.length)}`));
      card.append(make("h2", { id: "exercise-question", tabindex: "-1" }, words.kinds[kind].question));
      card.append(prompt(kind, item));
      const options = make("div", { class: "exercise-options", role: "group", "aria-labelledby": "exercise-question" });
      shuffledOptions(item, random).forEach(({ option, isCorrect }, index) => {
        const label = optionLabel(kind, option, words, language);
        const button = optionButton(kind, option, label);
        button.classList.add("exercise-option");
        button.dataset.correct = String(isCorrect);
        button.prepend(make("span", { class: "key", "aria-hidden": "true" }, String(index + 1)));
        button.addEventListener("click", () => answer(button));
        options.append(button);
      });
      card.append(options, make("div", { class: "exercise-feedback", "aria-live": "polite" }));
      card.querySelector("h2").focus();
      renderScore();
    }

    /** An option as a button: Arabic, a form's number and pattern, or a meaning. */
    function optionButton(kind, option, label) {
      if (option.ar && option.code && kind === "verb-form") {
        const button = make("button", { type: "button", class: "form-option" });
        button.append(make("span", { class: "form-number" }, formNumber(option.code)), arabic("span", label));
        return button;
      }
      const meaning = optionMeaning(option, language);
      if (meaning) {
        const button = make("button", { type: "button", class: "word-option" });
        button.append(arabic("span", label), make("span", { class: "option-meaning" }, meaning));
        return button;
      }
      return option.ar ? arabic("button", label, { type: "button" }) : make("button", { type: "button" }, label);
    }

    function prompt(kind, item) {
      const box = make("div", { class: "exercise-prompt" });
      if (item.picture) box.append(make("img", { src: root + item.picture, alt: words.pictureAlt, width: "160", height: "160", class: "exercise-picture" }));
      if (item.animation) box.append(drawing(item.animation));
      if (item.sound) box.append(soundButton(item.sound, words.listen), make("span", { class: "note" }, words.listen));
      if (item.passage) box.append(passage(item));
      if (item.lead) box.append(lead(kind, item.lead, item));
      if (item.facts && item.facts.root && FORM_KINDS.includes(kind)) {
        const root = make("p", { class: "note" }, `${words.root}: `);
        root.append(arabic("span", item.facts.root, { class: "ar exercise-root" }));
        box.append(root);
      }
      // Značenje → oblik: the meaning is the question itself, not a hint beside it.
      if (item.translation) {
        box.append(make("p", { class: kind === "meaning-form" ? "lead exercise-meaning" : "note" }, item.translation[language] || item.translation.en));
      }
      return box;
    }

    /** The question's animation (our own gated SVG, from the build): a tap plays it again (site/animation.js). */
    function drawing(svg) {
      const figure = make("div", { class: "verb-anim exercise-animation", "aria-hidden": "true" });
      figure.innerHTML = svg;
      return figure;
    }

    /** Once answered, the drawing says the verb too: a tap plays its sound (site/player.js) and the drawing. */
    function voiceDrawing(item) {
      const figure = $(".exercise-animation");
      if (!figure || !item.answerSound) return;
      figure.removeAttribute("aria-hidden");
      for (const [name, value] of Object.entries({ "data-audio": root + item.answerSound, role: "button", tabindex: "0", "aria-label": words.listen })) {
        figure.setAttribute(name, value);
      }
    }

    /** The preposition with the blank its noun fills, or the particle the question is about. */
    function lead(kind, text, item) {
      if (kind === "form-verb") {
        const named = make("p", { class: "exercise-lead form-lead" }, `${formNumber(item.facts.form)} · `);
        named.append(arabic("span", text));
        return named;
      }
      const line = arabic("p", "", { class: "ar exercise-lead" });
      line.append(make("span", {}, text));
      if (kind === "preposition") line.append(" ", make("span", { class: "blank", "aria-label": words.blank }, "____"));
      return line;
    }

    function passage(item) {
      const marked = new Set(item.marked || []);
      const blanks = new Set(item.blanks || []);
      const line = arabic("p", "", { class: item.ref ? "qr exercise-passage" : "ar exercise-passage" });
      item.passage.forEach((text, index) => {
        if (index) line.append(" ");
        if (blanks.has(index)) line.append(make("span", { class: "blank", "aria-label": words.blank }, "____"));
        else if (marked.has(index)) line.append(make("mark", {}, text));
        else line.append(text);
      });
      return line;
    }

    function answer(chosen) {
      const { kind, item } = queue[position];
      const isCorrect = chosen.dataset.correct === "true";
      for (const button of element.querySelectorAll(".exercise-option")) {
        button.disabled = true;
        if (button.dataset.correct === "true") button.classList.add("right");
      }
      if (!isCorrect) chosen.classList.add("wrong");
      chosen.setAttribute("aria-pressed", "true");
      progress = record(progress, `${kind}:${item.id}`, isCorrect, now());
      if (!writeProgress(storage, progress)) $(".exercise-storage").textContent = words.noStorage;
      if (isCorrect) sessionRight += 1;
      else queue = askAgain(queue, position, queue[position]);
      voiceDrawing(item);
      feedback(kind, item, isCorrect);
      renderScore();
    }

    function feedback(kind, item, isCorrect) {
      const box = $(".exercise-feedback");
      const right = item.options[0];
      box.append(make("p", { class: isCorrect ? "verdict right" : "verdict wrong" }, isCorrect ? words.right : words.wrong));
      if (!isCorrect) {
        const line = make("p", {}, `${words.rightAnswer} `);
        const label = optionLabel(kind, right, words, language);
        if (right.ar && right.code && kind === "verb-form") line.append(`${formNumber(right.code)} · `);
        line.append(right.ar ? arabic("span", label) : make("b", {}, label));
        const meaning = optionMeaning(right, language);
        if (meaning) line.append(` – ${meaning}`);
        box.append(line);
      }
      if (item.answerWord) {
        const said = make("p", { class: "exercise-answer" });
        if (item.answerSound) said.append(soundButton(item.answerSound, words.listen), " ");
        said.append(arabic("span", item.answerWord, { class: item.ref ? "qr" : "ar" }));
        if (item.ref) {
          const [surah, ayah] = item.ref.split(":");
          said.append(" ", make("a", { href: `https://quran.com/${surah}/${ayah}`, target: "_blank", rel: "noopener" }, `${item.ref} ↗`));
        }
        box.append(said);
      } else if (item.answerSound) {
        // A practice sentence: hear it whole once it is answered.
        box.append(make("p", { class: "exercise-answer" }, ""));
        box.lastChild.append(soundButton(item.answerSound, words.listen), ` ${words.listen}`);
      }
      for (const line of explanationLines(kind, item, words, language)) box.append(make("p", {}, line));
      if (item.quranTranslation) {
        // A published translation of the Quran: never machine-translated into a new one.
        box.append(make("p", { class: "translation notranslate", lang: "en", translate: "no" },
                        `${item.quranTranslation.text} — ${item.quranTranslation.by}`));
      }
      const next = make("button", { type: "button", class: "button exercise-next" }, position + 1 < queue.length ? words.next : words.finish);
      next.addEventListener("click", advance);
      box.append(next);
      next.focus();
    }

    function advance() {
      position += 1;
      if (position < queue.length) {
        show();
        return;
      }
      const card = $(".exercise-card");
      card.replaceChildren(make("h2", { tabindex: "-1" }, words.done),
                           make("p", { class: "lead" }, words.sessionScore(sessionRight, queue.length)));
      const again = make("button", { type: "button", class: "button" }, words.again);
      again.addEventListener("click", load);
      card.append(again);
      card.querySelector("h2").focus();
    }

    function renderScore() {
      $(".exercise-score").textContent = words.score(progress.correct, progress.answered, progress.streak, progress.best);
    }

    // Keys 1–4 choose an answer; Enter on the page goes on once a question is answered.
    doc.addEventListener("keydown", (event) => {
      if (event.altKey || event.ctrlKey || event.metaKey) return;
      const options = [...element.querySelectorAll(".exercise-option")];
      const index = KEY_OPTIONS.indexOf(event.key);
      if (index >= 0 && options[index] && !options[index].disabled) {
        event.preventDefault();
        options[index].click();
      }
    });
    $(".exercise-reset")?.addEventListener("click", () => {
      progress = emptyProgress();
      writeProgress(storage, progress);
      renderScore();
    });
    renderScore();
    load();
  }

  /** On an exercise page: find the container and the interface text, then start. */
  function boot() {
    const element = document.getElementById("exercises");
    if (!element) return;
    let storage;
    try { storage = window.localStorage; } catch { storage = null; }
    const safeStorage = storage || { getItem: () => null, setItem: () => { throw new Error("no storage"); } };
    const words = withTemplates(JSON.parse(element.dataset.text));
    element.hidden = false;
    start(document, element, words, window.location, safeStorage);
  }

  /** The interface text arrives as JSON (fil.pages.exercise_render); its templates have numbered holes. */
  function withTemplates(words) {
    const fill = (template) => (...values) => values.reduce((text, value, index) => text.replace(`{${index}}`, value), template);
    const templated = ["questionOf", "score", "sessionScore", "inBosnian", "renderedAs", "agreesIn", "formIs"];
    return { ...words, ...Object.fromEntries(templated.map((name) => [name, fill(words[name])])) };
  }

  if (typeof document !== "undefined") {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
    else boot();
  }

  return {
    SESSION_SIZE, AGAIN_AFTER, BOX_DAYS, DAY, STORAGE_KEY,
    shardOf, shardFile, seeded, shuffle, shuffledOptions, aboutWord, askedWords, shardsFor, uniqueById, SHARD_ATTEMPTS, fetchWithRetry, loadShards, questionsOf, emptyProgress, record, sessionOrder, askAgain,
    readProgress, writeProgress, explanationLines, optionLabel, optionMeaning, withTemplates, cellNames, VERB_FORM_KINDS, FORM_KINDS, formNumber, formName,
  };
});
