/*
 * Registers the service worker (sw.js, next to this file at the site's root) once a page has
 * loaded. Every step is guarded: a browser without service workers, a private window or a failed
 * registration leaves the page exactly as it was.
 */
(function () {
  try {
    if (!("serviceWorker" in navigator) || !window.isSecureContext || !document.currentScript) return;
    const worker = new URL("sw.js", document.currentScript.src).href;
    window.addEventListener("load", function () {
      try {
        navigator.serviceWorker.register(worker).catch(function () {});
      } catch (error) { /* never break the page */ }
    });
  } catch (error) { /* never break the page */ }
})();
