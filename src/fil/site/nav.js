/*
 * The site's navigation on a phone, for the app (index.html) and every static page (fil.pages.navigation):
 *
 *   - the thin top bar ([data-autohide]) slides away while the reader scrolls down into the text and
 *     comes back as soon as they scroll up — so it never sits on half the screen;
 *   - the ☰ menu (details[data-menu]) closes the way a menu should: with its ✕ button, Esc, a tap
 *     outside it or on one of its links, and hands focus back to the ☰ button; while it is open
 *     the page behind it does not scroll, and the phone's Back button closes it (a history step).
 *
 * Without this script the page still works: the menu is a <details> that opens and closes on its
 * own ☰ button, and the top bar simply stays.
 *
 * The decisions are pure functions (nextBarState, isPhoneWidth, clickAction), so `node --test` runs them
 * (tests/js/nav.test.mjs); the DOM is touched only by attach().
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.FilNav = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const PHONE_QUERY = "(max-width: 720px)";   // the same width pages.css and nav.css switch at
  const SCROLL_THRESHOLD = 8;                 // pixels of scroll that count as a direction, not a jitter
  const TOP_ZONE = 56;                        // near the top the bar always shows: there is nothing to make room for
  const HIDDEN_CLASS = "is-tucked";
  const OPEN_MENU_CLASS = "menu-open";
  const MENU_STATE = "filMenuOpen";           // the history entry an open menu adds

  /**
   * Whether the top bar should be tucked away after a scroll to `scrollY`, given the last decision:
   * { isHidden, lastY } in, the same out. Small movements change nothing (lastY stays, so they add up).
   */
  function nextBarState(state, scrollY, { threshold = SCROLL_THRESHOLD, topZone = TOP_ZONE } = {}) {
    if (scrollY <= topZone) return { isHidden: false, lastY: scrollY };
    const moved = scrollY - state.lastY;
    if (Math.abs(moved) < threshold) return state;
    return { isHidden: moved > 0, lastY: scrollY };
  }

  function isPhoneWidth(view) {
    return Boolean(view && view.matchMedia && view.matchMedia(PHONE_QUERY).matches);
  }

  // ---------- the top bar ----------

  function autoHide(bar, view, doc) {
    let state = { isHidden: false, lastY: view.scrollY };
    let isScheduled = false;
    const apply = () => {
      isScheduled = false;
      const isMenuOpen = doc.body.classList.contains(OPEN_MENU_CLASS);
      state = isPhoneWidth(view) && !isMenuOpen ? nextBarState(state, view.scrollY) : { isHidden: false, lastY: view.scrollY };
      bar.classList.toggle(HIDDEN_CLASS, state.isHidden);
    };
    view.addEventListener("scroll", () => {
      if (isScheduled) return;
      isScheduled = true;
      view.requestAnimationFrame(apply);
    }, { passive: true });
    // Moving focus into a tucked bar (a keyboard user tabbing back up) brings it back.
    bar.addEventListener("focusin", () => { state = { isHidden: false, lastY: view.scrollY }; bar.classList.remove(HIDDEN_CLASS); });
  }

  // ---------- the ☰ menu ----------

  /**
   * What a click does while the menu is open: "toggle" on the ☰ button (the <details> does it itself),
   * "follow" a link of the panel (in place of the menu's history entry), "close" for a choice that stays
   * on the page (a language of the app) or a tap outside the panel, "ignore" anything else in the panel.
   */
  function clickAction({ isOnButton, isInsidePanel, isLink, isChoice }) {
    if (isOnButton) return "toggle";
    if (!isInsidePanel) return "close";
    if (isLink) return "follow";
    return isChoice ? "close" : "ignore";
  }

  // An open menu is a step in the browser's history, so the phone's Back closes it instead of leaving the page.
  const isMenuStep = (history) => Boolean(history.state && history.state[MENU_STATE]);

  function menu(details, doc, view) {
    const summary = details.querySelector("summary");
    const panel = details.querySelector("[data-menu-panel]");
    const history = view.history;
    let isClosingByBack = false;
    // A page loaded (or reloaded) on a menu step starts closed: that step must not be taken back out of the page.
    if (isMenuStep(history)) history.replaceState({ ...history.state, [MENU_STATE]: false }, "");
    const shut = (isReturningFocus) => {
      if (!details.open) return;
      details.open = false;
      if (isReturningFocus && summary) summary.focus();
    };
    details.addEventListener("toggle", () => {
      doc.body.classList.toggle(OPEN_MENU_CLASS, details.open);
      doc.documentElement.classList.toggle(OPEN_MENU_CLASS, details.open);
      if (details.open) {
        if (!isMenuStep(history)) history.pushState({ ...(history.state || {}), [MENU_STATE]: true }, "");
        (panel && (panel.querySelector("[aria-current]") || panel.querySelector("a, button")))?.focus({ preventScroll: true });
        return;
      }
      if (!isClosingByBack && isMenuStep(history)) history.back();
      isClosingByBack = false;
    });
    view.addEventListener("popstate", () => {
      if (!details.open) return;
      isClosingByBack = true;
      shut(false);
    });
    doc.addEventListener("keydown", (event) => { if (event.key === "Escape") shut(true); });
    doc.addEventListener("click", (event) => {
      if (!details.open) return;
      const target = event.target;
      const link = target.closest("a[href]");
      const action = clickAction({
        isOnButton: Boolean(summary && summary.contains(target)),
        isInsidePanel: Boolean(panel && panel.contains(target)),
        isLink: Boolean(link),
        isChoice: Boolean(target.closest("[data-language]")),
      });
      if (action === "close") shut(false);
      if (action !== "follow" || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      // The page the link leads to takes the menu's place in history: Back then returns to this page, not to its open menu.
      event.preventDefault();
      view.location.replace(link.href);
    });
  }

  function attach(doc, view) {
    const bar = doc.querySelector("[data-autohide]");
    if (bar) autoHide(bar, view, doc);
    doc.querySelectorAll("details[data-menu]").forEach((details) => menu(details, doc, view));
  }

  if (typeof document !== "undefined" && typeof window !== "undefined") {
    const start = () => attach(document, window);
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
    else start();
  }

  return { PHONE_QUERY, HIDDEN_CLASS, OPEN_MENU_CLASS, MENU_STATE, nextBarState, isPhoneWidth, clickAction, attach };
});
