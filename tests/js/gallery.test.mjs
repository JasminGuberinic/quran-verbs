// The galleries loop their animations and replay a tapped card (src/fil/site/gallery.js): run by `node --test tests/js`.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { LOOP_MS, loopPeriod, createLooper, activate, pop } = require("../../src/fil/site/gallery.js");

function fakeClock() {
  const timers = new Map();
  let next = 1;
  return {
    timers,
    every: (run, ms) => { timers.set(next, { run, ms }); return next++; },
    cancel: (id) => timers.delete(id),
  };
}

test("a loop is never shorter than the base period, and lets the slowest part finish and rest", () => {
  assert.equal(loopPeriod([]), LOOP_MS);
  assert.equal(loopPeriod([500, 2000]), LOOP_MS);
  assert.equal(loopPeriod([3500, Infinity]), 4700);
});

test("a drawing on screen is replayed at once and every period, and stops when it leaves", () => {
  const clock = fakeClock();
  const replayed = [];
  const looper = createLooper({ replay: (svg) => replayed.push(svg), periodOf: () => 4000, ...clock });
  looper.show("a");
  looper.show("a");                       // seen twice, looped once
  assert.deepEqual(replayed, ["a"]);
  assert.equal(looper.looping(), 1);
  const [timer] = clock.timers.values();
  assert.equal(timer.ms, 4000);
  timer.run();
  assert.deepEqual(replayed, ["a", "a"]);
  looper.hide("a");
  looper.hide("a");
  assert.equal(looper.looping(), 0);
  assert.equal(clock.timers.size, 0);
});

test("a tapped animation card replays its drawing", () => {
  const svg = { name: "svg" };
  const replayed = [];
  activate({ querySelector: (selector) => (selector === "svg" ? svg : null) }, (drawn) => replayed.push(drawn));
  assert.deepEqual(replayed, [svg]);
});

test("a tapped picture card pops its picture again from the start", () => {
  const log = [];
  const img = { classList: { add: (name) => log.push(`add ${name}`), remove: (name) => log.push(`remove ${name}`) },
                getBoundingClientRect: () => log.push("layout") };
  activate({ querySelector: (selector) => (selector === "img" ? img : null) }, () => assert.fail("no svg to replay"));
  assert.deepEqual(log, ["remove pop", "layout", "add pop"]);
  log.length = 0;
  pop(img);
  assert.deepEqual(log, ["remove pop", "layout", "add pop"]);
});
