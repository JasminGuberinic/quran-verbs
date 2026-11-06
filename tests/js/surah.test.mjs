// The surah pages' order switch (run by `node --test tests/js`).
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const S = require("../../src/fil/site/surah.js");

const rows = [
  { id: "lam", order: "5", count: "3" },
  { id: "qala", order: "0", count: "1" },
  { id: "ahad", order: "3", count: "2" },
  { id: "allah", order: "2", count: "2" },
];

test("by first appearance, the surah's own order", () => {
  assert.deepEqual(S.sortedRows(rows, "order").map((row) => row.id), ["qala", "allah", "ahad", "lam"]);
});

test("by frequency, the commonest first and equals in the surah's order", () => {
  assert.deepEqual(S.sortedRows(rows, "count").map((row) => row.id), ["lam", "allah", "ahad", "qala"]);
});

test("sorting leaves the rows it was given as they were", () => {
  const before = rows.map((row) => row.id);
  S.sortedRows(rows, "count");
  assert.deepEqual(rows.map((row) => row.id), before);
});

test("a list shown in parts is sorted as one, each part keeping its size", () => {
  const parts = S.dealt(rows, [3, 1], "count");
  assert.deepEqual(parts.map((part) => part.map((row) => row.id)), [["lam", "allah", "ahad"], ["qala"]]);
});
