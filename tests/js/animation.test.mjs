// A tap replays a verb animation (src/fil/site/animation.js): run by `node --test tests/js`.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { replay, replayOnTap } = require("../../src/fil/site/animation.js");

function fakeSvg() {
  const log = [];
  return {
    log,
    classList: { add: (name) => log.push(`add ${name}`), remove: (name) => log.push(`remove ${name}`) },
    getBoundingClientRect: () => log.push("layout"),
  };
}

test("replaying stops the animations, forces layout, then lets them start again", () => {
  const svg = fakeSvg();
  replay(svg);
  assert.deepEqual(svg.log, ["add off", "layout", "remove off"]);
});

test("a tap on the figure replays its drawing", () => {
  const svg = fakeSvg();
  const figure = { querySelector: () => svg };
  replayOnTap({ target: { closest: (selector) => (selector === ".verb-anim" ? figure : null) } });
  assert.deepEqual(svg.log, ["add off", "layout", "remove off"]);
});

test("a tap elsewhere does nothing", () => {
  replayOnTap({ target: { closest: () => null } });
});
