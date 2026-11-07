/*
 * Replays a verb animation when it is tapped (the app's verb card and the static verb pages).
 *
 * The drawing is decorative, so it is not a control: no focus, no label. It only plays again
 * for a reader who taps it. The animations are CSS; replaying is stopping them for one frame
 * (the `off` class the SVG carries its own rule for) and letting them start over.
 *
 * `replay` is duck-typed (classList, getBoundingClientRect) so it is tested without a browser
 * (tests/js/animation.test.mjs).
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.FilAnimation = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";
  const REPLAY_CLASS = "off";
  const FIGURE = ".verb-anim";

  function replay(svg) {
    svg.classList.add(REPLAY_CLASS);
    svg.getBoundingClientRect();   // reading the layout makes the browser apply the stop before the restart
    svg.classList.remove(REPLAY_CLASS);
  }

  function replayOnTap(event) {
    const figure = event.target.closest && event.target.closest(FIGURE);
    const svg = figure && figure.querySelector("svg");
    if (svg) replay(svg);
  }

  if (typeof document !== "undefined") document.addEventListener("click", replayOnTap);
  return { replay, replayOnTap };
});
