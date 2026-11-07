// What the service worker does with a request (src/fil/site/sw-routing.js): run by `node --test tests/js`.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const R = require("../../src/fil/site/sw-routing.js");
const SCOPE = "https://example.github.io/quran-verbs/";
const get = (path, extra = {}) => ({ method: "GET", url: SCOPE + path, hasRange: false, ...extra });

test("pages, scripts and data are fetched network-first so a deploy is never hidden", () => {
  for (const path of ["", "bs/", "en/qala/", "ui.js", "pages.css", "data.json", "verbs/0001.json", "index.html?lang=bs"]) {
    assert.equal(R.decide(get(path), SCOPE), "network-first", path);
  }
});

test("content-named audio and pictures are cache-first", () => {
  assert.equal(R.decide(get("audio/ab12cd.m4a"), SCOPE), "cache-first");
  assert.equal(R.decide(get("pictures/tree.svg"), SCOPE), "cache-first");
});

test("other sites, other methods, range requests and the worker itself are left to the browser", () => {
  assert.equal(R.decide({ method: "GET", url: "https://cdn.islamic.network/quran/audio/64/ar.alafasy/1.mp3", hasRange: false }, SCOPE), "bypass");
  assert.equal(R.decide({ method: "GET", url: "https://fonts.googleapis.com/css2", hasRange: false }, SCOPE), "bypass");
  assert.equal(R.decide({ method: "POST", url: SCOPE + "bs/", hasRange: false }, SCOPE), "bypass");
  assert.equal(R.decide(get("audio/ab12cd.m4a", { hasRange: true }), SCOPE), "bypass");
  assert.equal(R.decide(get("sw.js"), SCOPE), "bypass");
  assert.equal(R.decide({ method: "GET", url: "https://example.github.io/other/page", hasRange: false }, SCOPE), "bypass");
});

test("media outlives builds; pages are kept per build", () => {
  assert.equal(R.cacheFor("cache-first", "abc"), "fil-media");
  assert.equal(R.cacheFor("network-first", "abc"), "fil-pages-abc");
});

test("a new build deletes every old fil- cache but the media one", () => {
  const names = ["fil-shell-old", "fil-pages-old", "fil-media", "fil-shell-new", "fil-pages-new", "someone-else"];
  assert.deepEqual(R.staleCaches(names, "new"), ["fil-shell-old", "fil-pages-old"]);
});

test("a cache over its limit drops only the overflow", () => {
  assert.equal(R.overflow(10, 300), 0);
  assert.equal(R.overflow(305, 300), 5);
});
