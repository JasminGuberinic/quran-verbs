/*
 * Fiʿl's service worker: the app shell is kept from the first visit, and the pages, sounds and
 * data a visitor opens are kept as they are opened, so the site works offline.
 *
 * The build id and the shell list below are filled in by `fil pages` (fil.pages.pwa). The caches carry the
 * build id, so a deploy installs a new worker, which deletes the old caches: nothing is served
 * stale for ever. Which request gets which treatment is decided in sw-routing.js.
 */
importScripts("sw-routing.js");

const BUILD = "__BUILD__";
const SHELL = JSON.parse('__SHELL__');
const SHELL_CACHE = `fil-shell-${BUILD}`;
const MEDIA_ENTRY_LIMIT = 400;     // content-named sounds and pictures
const PAGE_ENTRY_LIMIT = 300;      // pages and data the visitor opened
const OFFLINE_PAGE = "404.html";

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(SHELL_CACHE).then((cache) => cache.addAll(["./", ...SHELL])).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(FilRouting.staleCaches(names, BUILD).map((name) => caches.delete(name))))
      .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const decision = FilRouting.decide(
    { method: request.method, url: request.url, hasRange: request.headers.has("range") }, self.registration.scope);
  if (decision === "bypass") return;
  const cacheName = FilRouting.cacheFor(decision, BUILD);
  event.respondWith(decision === "cache-first" ? cacheFirst(request, cacheName) : networkFirst(request, cacheName));
});

async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  await keep(cacheName, request, response, MEDIA_ENTRY_LIMIT);
  return response;
}

async function networkFirst(request, cacheName) {
  try {
    const response = await fetch(request);
    await keep(cacheName, request, response, PAGE_ENTRY_LIMIT);
    return response;
  } catch (error) {
    return (await caches.match(request, { ignoreSearch: request.mode === "navigate" }))
      || (request.mode === "navigate" ? await caches.match(OFFLINE_PAGE) : undefined)
      || Response.error();
  }
}

/** Keep a good response, and the cache within its limit by dropping its oldest entries. */
async function keep(cacheName, request, response, limit) {
  if (!response || response.status !== 200 || response.type !== "basic") return;
  try {
    const cache = await caches.open(cacheName);
    await cache.put(request, response.clone());
    const keys = await cache.keys();
    await Promise.all(keys.slice(0, FilRouting.overflow(keys.length, limit)).map((key) => cache.delete(key)));
  } catch (error) {
    // A full disk or a private window: the page is served all the same.
  }
}
