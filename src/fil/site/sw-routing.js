/*
 * What the service worker (sw.js) does with a request: a pure decision, no caches, no network,
 * so tests/js/sw-routing.test.mjs can run it under Node.
 *
 *   "bypass"        let the browser handle it (other sites, non-GET, range requests such as audio
 *                   seeking, the worker itself)
 *   "cache-first"   a file whose name is its content (audio/, pictures/): never stale, so the copy we
 *                   have is served and the network is only asked when we have none
 *   "network-first" everything else — pages, scripts, styles, data: always the newest, and the copy
 *                   we kept only when the network fails (offline)
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.FilRouting = factory();
})(typeof self !== "undefined" ? self : this, function () {
  const CONTENT_NAMED_FOLDERS = ["audio/", "pictures/"];
  const WORKER_FILE = "sw.js";

  /** request: {method, url, hasRange}; scope: the worker's scope URL (ends with "/"). */
  function decide(request, scope) {
    if (request.method !== "GET" || request.hasRange) return "bypass";
    const url = new URL(request.url);
    const base = new URL(scope);
    if (url.origin !== base.origin || !url.pathname.startsWith(base.pathname)) return "bypass";
    const inside = url.pathname.slice(base.pathname.length);
    if (inside === WORKER_FILE) return "bypass";
    if (CONTENT_NAMED_FOLDERS.some((folder) => inside.startsWith(folder))) return "cache-first";
    return "network-first";
  }

  /** The cache a decided request is kept in: media outlives builds, the rest is per build. */
  function cacheFor(decision, build) {
    return decision === "cache-first" ? "fil-media" : `fil-pages-${build}`;
  }

  /** The caches to delete when a build's worker activates: every fil- cache but this build's and the media one. */
  function staleCaches(names, build) {
    const keep = new Set(["fil-media", `fil-shell-${build}`, `fil-pages-${build}`]);
    return names.filter((name) => name.startsWith("fil-") && !keep.has(name));
  }

  /** How many of the oldest entries to drop so a cache holds at most `limit`. */
  function overflow(count, limit) {
    return Math.max(0, count - limit);
  }

  return { decide, cacheFor, staleCaches, overflow };
});
