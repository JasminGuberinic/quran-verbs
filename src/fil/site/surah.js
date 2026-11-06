/*
 * The surah pages' order switch (fil.pages.surah_render): the word lists read in the order the
 * surah first uses each word, or — on request — the most frequent in the surah first.
 *
 * Every row carries data-order (its place by first appearance) and data-count (how often the
 * surah uses it); every list that may be reordered is marked data-sortable. Without this script
 * the switch stays hidden and the lists keep the surah's order. Lists with the same data-sortable are one list
 * shown in parts (the first words, then the rest folded): sorting deals the rows back part by part.
 * The pure part runs under
 * `node --test` (tests/js/surah.test.mjs).
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.FilSurah = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  /** Rows as { order, count }-bearing items, ordered "order" (first appearance) or "count" (most frequent first, then first appearance). */
  function sortedRows(rows, by) {
    const order = (row) => Number(row.order);
    const count = (row) => Number(row.count);
    const byFirst = (a, b) => order(a) - order(b);
    return [...rows].sort(by === "count" ? (a, b) => count(b) - count(a) || byFirst(a, b) : byFirst);
  }

  /** Sorted rows dealt back into the lists of one group, each keeping its size (the shown list, then the folded one). */
  function dealt(rows, sizes, by) {
    const sorted = sortedRows(rows, by);
    let start = 0;
    return sizes.map((size) => sorted.slice(start, (start += size)));
  }

  function sortLists(doc, by) {
    const groups = new Map();
    for (const list of doc.querySelectorAll("[data-sortable]")) {
      const group = groups.get(list.dataset.sortable) || [];
      groups.set(list.dataset.sortable, [...group, list]);
    }
    for (const lists of groups.values()) {
      const rows = lists.flatMap((list) => [...list.children])
        .map((element) => ({ element, order: element.dataset.order, count: element.dataset.count }));
      dealt(rows, lists.map((list) => list.children.length), by)
        .forEach((part, index) => lists[index].append(...part.map((row) => row.element)));
    }
    for (const button of doc.querySelectorAll("[data-sort-by]")) {
      button.setAttribute("aria-pressed", String(button.dataset.sortBy === by));
    }
  }

  if (typeof document !== "undefined") {
    const start = () => {
      const switcher = document.querySelector("[data-sort-switch]");
      if (!switcher) return;
      switcher.hidden = false;
      switcher.addEventListener("click", (event) => {
        const button = event.target.closest("[data-sort-by]");
        if (button) sortLists(document, button.dataset.sortBy);
      });
    };
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
    else start();
  }

  return { sortedRows, dealt };
});
