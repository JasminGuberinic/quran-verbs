// Every play control is a toggle (src/fil/site/player.js): run by `node --test tests/js`.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const P = require("../../src/fil/site/player.js");
const UI = require("../../src/fil/site/ui.js");

class FakeAudio {
  constructor(src) { this.src = src; this.paused = true; this.listeners = {}; }
  addEventListener(name, listener) { this.listeners[name] = listener; }
  play() { this.paused = false; return Promise.resolve(); }
  pause() { this.paused = true; }
  end() { this.paused = true; this.listeners.ended?.(); }
}

class FakeElement {
  constructor(attributes = {}, iconHtml = null) {
    this.attributes = { ...attributes };
    this.classes = new Set();
    this.classList = { toggle: (name, on) => (on ? this.classes.add(name) : this.classes.delete(name)) };
    this.icon = iconHtml === null ? null : new FakeElement({}, null);
    if (this.icon) this.icon.innerHTML = iconHtml;
  }
  getAttribute(name) { return name in this.attributes ? this.attributes[name] : null; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  removeAttribute(name) { delete this.attributes[name]; }
  querySelector(selector) { return selector === ".play-icon" ? this.icon : null; }
}

function setUp() {
  const clips = [];
  const player = P.createPlayer({ makeAudio: (src) => { const audio = new FakeAudio(src); clips.push(audio); return audio; },
                                  stopLabel: () => UI.bs.stop });
  return { player, clips };
}

test("a play button pressed again stops its clip and shows play again", () => {
  const { player, clips } = setUp();
  const button = new FakeElement({ "aria-label": "Poslušaj" }, "▶");

  player.toggle(button, "a.m4a");
  assert.equal(clips[0].paused, false);
  assert.ok(button.classes.has("playing"));
  assert.equal(button.getAttribute("aria-label"), "Zaustavi");
  assert.equal(button.icon.innerHTML, P.STOP_TEXT);

  player.toggle(button, "a.m4a");
  assert.equal(clips[0].paused, true);
  assert.ok(!button.classes.has("playing"));
  assert.equal(button.getAttribute("aria-label"), "Poslušaj");
  assert.equal(button.icon.innerHTML, "▶");
  assert.equal(clips.length, 1);
});

test("starting another clip stops the one playing and hands its button back", () => {
  const { player, clips } = setUp();
  const first = new FakeElement({ "aria-label": "Poslušaj" }, "▶");
  const second = new FakeElement({ "aria-label": "Cijeli ajet" }, "▶");

  player.toggle(first, "a.m4a");
  player.toggle(second, "b.mp3");

  assert.equal(clips[0].paused, true);
  assert.equal(clips[1].paused, false);
  assert.equal(first.getAttribute("aria-label"), "Poslušaj");
  assert.ok(!first.classes.has("playing") && second.classes.has("playing"));
});

test("a clip that ends returns its button to play", () => {
  const { player, clips } = setUp();
  const button = new FakeElement({ "aria-label": "Listen" }, '<svg viewBox="0 0 16 16"><path/></svg>');

  player.toggle(button, "a.m4a");
  assert.equal(button.icon.innerHTML, P.STOP_SVG);
  clips[0].end();

  assert.ok(!player.isPlaying(button));
  assert.equal(button.getAttribute("aria-label"), "Listen");
  assert.match(button.icon.innerHTML, /<path/);
});

test("a stale clip ending never touches the button now playing", () => {
  const { player, clips } = setUp();
  const first = new FakeElement({ "aria-label": "a" }, "▶");
  const second = new FakeElement({ "aria-label": "b" }, "▶");

  player.toggle(first, "a.m4a");
  player.toggle(second, "b.m4a");
  clips[0].end();

  assert.ok(player.isPlaying(second) && second.classes.has("playing"));
});

test("a word named by its own text is marked pressed instead of relabelled", () => {
  const { player } = setUp();
  const word = new FakeElement();

  player.toggle(word, "w.m4a");
  assert.equal(word.getAttribute("aria-pressed"), "true");
  assert.equal(word.getAttribute("aria-label"), null);

  player.toggle(word, "w.m4a");
  assert.equal(word.getAttribute("aria-pressed"), "false");
});

test("a clip that cannot play hands its button back", async () => {
  const button = new FakeElement({ "aria-label": "Listen" }, "▶");
  const player = P.createPlayer({ makeAudio: (src) => Object.assign(new FakeAudio(src), { play: () => Promise.reject(new Error("blocked")) }) });

  player.toggle(button, "a.m4a");
  await new Promise((resolve) => setImmediate(resolve));

  assert.ok(!player.isPlaying(button));
  assert.equal(button.getAttribute("aria-label"), "Listen");
});

test("play always starts, even on the button already playing", () => {
  const { player, clips } = setUp();
  const button = new FakeElement({ "aria-label": "Listen" }, "▶");

  player.play(button, "a.m4a");
  player.play(button, "a.m4a");

  assert.equal(clips.length, 2);
  assert.ok(player.isPlaying(button));
  assert.equal(button.getAttribute("aria-label"), "Zaustavi");
});

test("every active language names the stop button", () => {
  for (const code of ["bs", "en", "tr", "fr", "id", "ur", "bn", "fa"]) assert.ok(UI[code].stop, code);
});
