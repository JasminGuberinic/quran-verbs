/*
 * One player for every sound on the site — the app (index.html) and the static pages alike.
 *
 * Every play control is a toggle: pressed while its clip plays, it stops it. Starting a clip
 * stops whatever was playing, and a clip that ends hands its button back. While a button
 * plays it is marked `.playing` and tells assistive technology so: a button with its own
 * aria-label ("Listen") is relabelled "Stop" in the reader's language; a button whose text
 * is its name (a word of an ayah) is marked aria-pressed instead. A button's play icon,
 * when it has one (`.play-icon`), shows a stop square.
 *
 * Buttons are duck-typed (classList, get/set/removeAttribute, querySelector) and the clip
 * comes from an injected `makeAudio`, so the logic is tested without a browser
 * (tests/js/player.test.mjs). On a static page the script wires itself from its own tag:
 *   <script src="player.js" data-attribute="data-audio" data-stop-label="Zaustavi" defer>
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.FilPlayer = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";
  const STOP_TEXT = "■";
  const STOP_SVG = '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="3.5" y="3.5" width="9" height="9" rx="1"/></svg>';
  const ORIGINAL_LABEL = "data-play-label";
  const ORIGINAL_ICON = "data-play-icon";

  /** The stop icon in the same idiom as the play icon it replaces (drawn or typed). */
  function stopIconFor(playIcon) {
    return playIcon.includes("<svg") ? STOP_SVG : STOP_TEXT;
  }

  /** Show a button as playing (or not): class, accessible state, and icon. */
  function markPlaying(button, playing, stopLabel) {
    button.classList.toggle("playing", playing);
    markLabel(button, playing, stopLabel);
    markIcon(button, playing);
  }

  function markLabel(button, playing, stopLabel) {
    const original = button.getAttribute(ORIGINAL_LABEL) ?? button.getAttribute("aria-label");
    if (original === null) {
      button.setAttribute("aria-pressed", String(playing));
      return;
    }
    if (playing) {
      button.setAttribute(ORIGINAL_LABEL, original);
      button.setAttribute("aria-label", stopLabel);
    } else {
      button.setAttribute("aria-label", original);
      button.removeAttribute(ORIGINAL_LABEL);
    }
  }

  function markIcon(button, playing) {
    const icon = button.querySelector(".play-icon");
    if (!icon) return;
    if (playing) {
      const original = icon.getAttribute(ORIGINAL_ICON) ?? icon.innerHTML;
      icon.setAttribute(ORIGINAL_ICON, original);
      icon.innerHTML = stopIconFor(original);
      return;
    }
    const original = icon.getAttribute(ORIGINAL_ICON);
    if (original === null) return;
    icon.innerHTML = original;
    icon.removeAttribute(ORIGINAL_ICON);
  }

  /**
   * A player: `toggle(button, src)` for a tap, `play(button, src)` to start regardless,
   * `stop()` to silence everything. `stopLabel()` gives the reader's word for "Stop".
   */
  function createPlayer({ makeAudio, stopLabel = () => "Stop" }) {
    let current = null;   // { audio, button }

    function stop() {
      if (!current) return;
      const { audio, button } = current;
      current = null;
      audio.pause();
      if (button) markPlaying(button, false, stopLabel());
    }

    function play(button, src) {
      stop();
      const audio = makeAudio(src);
      const playing = { audio, button };
      current = playing;
      if (button) markPlaying(button, true, stopLabel());
      const finish = () => { if (current === playing) stop(); };
      audio.addEventListener("ended", finish);
      audio.addEventListener("error", finish);
      Promise.resolve(audio.play()).catch(finish);
    }

    function toggle(button, src) {
      if (current && current.button === button) {
        stop();
        return false;
      }
      play(button, src);
      return true;
    }

    return { play, stop, toggle, isPlaying: (button) => Boolean(current && current.button === button) };
  }

  /** Wire a document: a tap (or Enter/Space on a non-button control) toggles its sound. */
  function attach(doc, attribute, player) {
    const target = (event) => {
      const button = event.target.closest?.(`[${attribute}]`);
      return button && !button.disabled ? button : null;
    };
    doc.addEventListener("click", (event) => {
      const button = target(event);
      if (button) player.toggle(button, button.getAttribute(attribute));
    });
    doc.addEventListener("keydown", (event) => {
      const button = target(event);
      if (!button || button.tagName === "BUTTON" || (event.key !== "Enter" && event.key !== " ")) return;
      event.preventDefault();
      player.toggle(button, button.getAttribute(attribute));
    });
  }

  // A static page loads this file with its settings on the tag; the app wires its own.
  const script = typeof document !== "undefined" ? document.currentScript : null;
  if (script && script.dataset.attribute) {
    const label = script.dataset.stopLabel || "Stop";
    attach(document, script.dataset.attribute, createPlayer({ makeAudio: (src) => new Audio(src), stopLabel: () => label }));
  }

  return { STOP_TEXT, STOP_SVG, createPlayer, markPlaying, attach };
});
