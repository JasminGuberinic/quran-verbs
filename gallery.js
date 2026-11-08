/*
 * The galleries (fil.pages.gallery_render): the verb animations loop while they are on screen,
 * and a tapped card plays its drawing again — the animation from its start, the picture a
 * small pop. Its sound is site/player.js's job (the card is a [data-audio] button).
 *
 * The shipped animations are one-shot CSS whose last pose is their first, so looping is
 * replaying them (site/animation.js) every period: never shorter than LOOP_MS, and long enough
 * for the slowest part of the drawing to finish and rest a moment. A reader who asked for
 * reduced motion gets no loop (and the SVGs themselves then stand still).
 *
 * The looper takes its clock and its replay injected, so it is tested without a browser
 * (tests/js/gallery.test.mjs).
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.FilGallery = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";
  const LOOP_MS = 3500;
  const REST_MS = 1200;
  const CARD = "[data-gallery]";
  const POP_CLASS = "pop";

  /** The loop period of a drawing whose parts end at `endTimes` (ms). */
  function loopPeriod(endTimes) {
    const finite = endTimes.filter((time) => Number.isFinite(time));
    const longest = finite.length ? Math.max(...finite) : 0;
    return Math.max(LOOP_MS, Math.ceil(longest + REST_MS));
  }

  /** Replays each shown drawing every period until it is hidden again. */
  function createLooper({ replay, periodOf, every, cancel }) {
    const timers = new Map();
    return {
      show(svg) {
        if (timers.has(svg)) return;
        replay(svg);
        timers.set(svg, every(() => replay(svg), periodOf(svg)));
      },
      hide(svg) {
        if (!timers.has(svg)) return;
        cancel(timers.get(svg));
        timers.delete(svg);
      },
      looping: () => timers.size,
    };
  }

  /** Restart a CSS animation carried by a class: take it off, read the layout, put it back. */
  function pop(element) {
    element.classList.remove(POP_CLASS);
    element.getBoundingClientRect();
    element.classList.add(POP_CLASS);
  }

  /** A tapped card plays its drawing again. */
  function activate(card, replay) {
    const svg = card.querySelector("svg");
    if (svg) {
      replay(svg);
      return;
    }
    const picture = card.querySelector("img");
    if (picture) pop(picture);
  }

  function endTimesOf(svg) {
    if (typeof svg.getAnimations !== "function") return [];
    return svg.getAnimations({ subtree: true }).map((animation) => animation.effect.getComputedTiming().endTime);
  }

  function wire(doc, win) {
    const replay = win.FilAnimation ? win.FilAnimation.replay : () => {};
    doc.addEventListener("click", (event) => {
      const card = event.target.closest && event.target.closest(CARD);
      if (card) activate(card, replay);
    });
    const still = win.matchMedia && win.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (still || !win.IntersectionObserver || !win.FilAnimation) return;
    const looper = createLooper({ replay, periodOf: (svg) => loopPeriod(endTimesOf(svg)),
                                  every: (run, ms) => win.setInterval(run, ms), cancel: (id) => win.clearInterval(id) });
    const observer = new win.IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) looper.show(entry.target);
        else looper.hide(entry.target);
      }
    }, { threshold: 0.5 });
    doc.querySelectorAll(`${CARD} svg`).forEach((svg) => observer.observe(svg));
  }

  if (typeof document !== "undefined" && typeof window !== "undefined") {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => wire(document, window));
    else wire(document, window);
  }
  return { LOOP_MS, loopPeriod, createLooper, activate, pop };
});
