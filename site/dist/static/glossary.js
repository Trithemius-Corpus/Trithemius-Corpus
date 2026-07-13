/* Bilingual hover glossary for the parallel viewer.
 * Loads lexicon.json, then wraps any Latin terms found in the .pp-latin cells
 * in <span class="lex"> so hovering shows the English gloss in a popover.
 * Wrapping happens client-side so the lexicon stays swappable and the build is
 * unaffected. Vanilla JS, no dependencies. */
(function () {
  "use strict";
  if (!document.querySelector || !document.querySelector(".pp-latin")) return;

  var LEX = null;
  var popover = null;

  function ensurePopover() {
    if (popover) return popover;
    popover = document.createElement("div");
    popover.className = "tc-popover tc-lex-popover";
    popover.setAttribute("role", "tooltip");
    popover.hidden = true;
    document.body.appendChild(popover);
    return popover;
  }

  function showPopover(anchor, entry, term) {
    var p = ensurePopover();
    var html = "<strong>" + escapeHTML(term) + "</strong>";
    if (entry && typeof entry === "object") {
      html += "<div class=\"lex-en\">" + escapeHTML(entry.en || "") + "</div>";
      if (entry.note) html += "<div class=\"lex-note\">" + escapeHTML(entry.note) + "</div>";
    } else if (typeof entry === "string") {
      html += "<div class=\"lex-en\">" + escapeHTML(entry) + "</div>";
    }
    p.innerHTML = html;
    p.hidden = false;
    var r = anchor.getBoundingClientRect();
    var pw = p.offsetWidth, ph = p.offsetHeight;
    p.style.left = Math.max(8, Math.min(r.left, window.innerWidth - pw - 8)) + "px";
    var top = r.bottom + window.pageYOffset + 6;
    if (top + ph > window.pageYOffset + window.innerHeight - 8)
      top = r.top + window.pageYOffset - ph - 6;
    p.style.top = top + "px";
  }
  function hidePopover() { if (popover) popover.hidden = true; }
  function escapeHTML(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function wrapTerms() {
    if (!LEX) return;
    var terms = Object.keys(LEX);
    if (!terms.length) return;
    // sort longest-first so longer stems win over substrings (e.g. 'coniuratio'
    // before 'con'); build ONE combined regex and do a single pass so injected
    // <span> markup is never re-scanned by a later term.
    terms.sort(function (a, b) { return b.length - a.length; });
    var escaped = terms.map(function (t) { return t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); });
    var combined = new RegExp("\\b(" + escaped.join("|") + ")\\w*", "gi");

    function wrapTextNodes(root) {
      var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
      var nodes = [];
      while (walker.nextNode()) nodes.push(walker.currentNode);
      nodes.forEach(function (node) {
        if (!node.nodeValue.trim()) return;
        if (node.parentElement && node.parentElement.classList.contains("lex")) return;
        var text = node.nodeValue;
        if (!combined.test(text)) return;  // no terms present — leave untouched
        combined.lastIndex = 0;
        // split into runs: matched terms become spans, gaps stay as text
        var frag = document.createDocumentFragment();
        var last = 0, m, matched = false;
        while ((m = combined.exec(text)) !== null) {
          var key = m[0].toLowerCase();
          if (!LEX[key]) { continue; }  // matched stem but not an exact lex key
          matched = true;
          if (m.index > last) frag.appendChild(document.createTextNode(text.slice(last, m.index)));
          var span = document.createElement("span");
          span.className = "lex";
          span.setAttribute("data-term", key);
          span.textContent = m[0];
          frag.appendChild(span);
          last = m.index + m[0].length;
        }
        if (!matched) return;  // no real matches after key check
        if (last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
        node.parentNode.replaceChild(frag, node);
      });
    }
    document.querySelectorAll(".pp-latin").forEach(wrapTextNodes);
  }

  // delegated hover handling on the whole parallel grid
  document.addEventListener("mouseover", function (e) {
    var lex = e.target.closest && e.target.closest(".lex");
    if (!lex) return;
    var term = lex.getAttribute("data-term");
    var entry = LEX[term];
    if (entry) { showPopover(lex, entry, term); e.preventDefault(); }
  });
  document.addEventListener("mouseout", function (e) {
    if (e.target.closest && e.target.closest(".lex")) hidePopover();
  });
  // touch: tap to toggle
  document.addEventListener("click", function (e) {
    var lex = e.target.closest && e.target.closest(".lex");
    if (!lex) return;
    var term = lex.getAttribute("data-term");
    if (LEX[term]) { showPopover(lex, LEX[term], term); e.preventDefault(); }
  });

  // load + wrap. Re-wrap after a tick so dynamically-rendered cells exist.
  function assetPrefix() {
    var root = document.querySelector("[data-asset]");
    return root ? (root.getAttribute("data-asset") || "") : "";
  }
  fetch(assetPrefix() + "static/lexicon.json")
    .then(function (r) { return r.json(); })
    .then(function (data) {
      LEX = data.terms || {};
      wrapTerms();
    })
    .catch(function () { /* lexicon optional; fail silently */ });
})();
