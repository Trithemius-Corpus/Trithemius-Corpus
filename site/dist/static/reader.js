/* Reader features for work pages: reading-progress sync (continue-reading),
 * keyboard navigation, and footnote popovers. Vanilla JS, no dependencies.
 * Loaded only on work pages (and the homepage for the continue card). */
(function () {
  "use strict";
  var WORK_ID = window.TC_WORK && window.TC_WORK.id;
  var WORK_TITLE = window.TC_WORK && window.TC_WORK.title;
  var WORK_CITATION = window.TC_WORK && window.TC_WORK.citation;

  function $(sel, ctx) { return (ctx || document).querySelector(sel); }
  function $all(sel, ctx) { return Array.prototype.slice.call((ctx || document).querySelectorAll(sel)); }

  function scrollBehavior() {
    try {
      return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "auto" : "smooth";
    } catch (e) { return "auto"; }
  }

  function passageElements() {
    return $all(".english-body [data-passage-id]")
      .filter(function (element) { return element.offsetParent !== null; });
  }

  function passageAtScroll() {
    var list = passageElements();
    if (!list.length) return null;
    var mid = window.innerHeight * 0.35;
    var current = list[0];
    list.forEach(function (element) {
      if (element.getBoundingClientRect().top <= mid + 2) current = element;
    });
    return current;
  }

  function passageURL(id) {
    var target = new URL(window.location.href);
    target.searchParams.delete("resume");
    target.searchParams.set("view", (window.TC_WORK && window.TC_WORK.view) || "read");
    target.searchParams.set("lang", (window.TC_WORK && window.TC_WORK.language) || "en");
    target.searchParams.set("annotations", (window.TC_WORK && window.TC_WORK.annotations) || "visible");
    target.hash = id || "";
    return target.toString();
  }

  // ── 1. Reading-progress sync ──────────────────────────────────────────────
  // Version 2 stores a stable passage ID while retaining the old scroll
  // fraction as a fallback for pre-passage pages and legacy entries.
  function progressKey(id) { return "tc-progress-" + id; }

  if (WORK_ID) {
    var body = $(".english-body") || document.body;
    var ticking = false;
    function recordProgress() {
      ticking = false;
      var h = document.documentElement;
      var max = h.scrollHeight - h.clientHeight;
      var frac = max > 0 ? Math.min(1, Math.max(0, h.scrollTop / max)) : 0;
      var passage = passageAtScroll();
      try {
        var entry = { v: 2, id: WORK_ID, title: WORK_TITLE, frac: frac, t: Date.now(),
                      ch: currentChapterLabel(),
                      passage: passage && passage.getAttribute("data-passage-id") };
        localStorage.setItem(progressKey(WORK_ID), JSON.stringify(entry));
        // index of works read, for the continue card
        var idx = JSON.parse(localStorage.getItem("tc-progress-idx") || "[]");
        idx = idx.filter(function (x) { return x !== WORK_ID; });
        idx.unshift(WORK_ID);
        try { localStorage.setItem("tc-progress-idx", JSON.stringify(idx.slice(0, 20))); } catch (e) {}
      } catch (e) {}
    }
    window.addEventListener("scroll", function () {
      if (!ticking) { window.requestAnimationFrame(recordProgress); ticking = true; }
    }, { passive: true });
    window.addEventListener("load", function () {
      var resume = new URL(window.location.href).searchParams.get("resume");
      if (!window.location.hash && resume !== null) {
        var fraction = Math.min(1, Math.max(0, parseFloat(resume) || 0));
        var root = document.documentElement;
        window.scrollTo(0, fraction * Math.max(0, root.scrollHeight - root.clientHeight));
        try {
          var clean = new URL(window.location.href);
          clean.searchParams.delete("resume");
          window.history.replaceState(null, "", clean.toString());
        } catch (e) {}
      }
      recordProgress();
    });
  }

  function currentChapterLabel() {
    var ch = chapterAtScroll();
    return ch ? ch.label : null;
  }

  // ── 2. Keyboard navigation ────────────────────────────────────────────────
  // j/k = next/prev paragraph;  [ / ] = prev/next chapter;  / = focus search;
  // g = prompt for a work jump. Only when not typing in a field.
  function isTyping(e) {
    var t = e.target;
    return t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable);
  }

  function paragraphs() {
    var identified = passageElements();
    if (identified.length) return identified;
    return $all(".english-body p, .english-body li, .english-body h2, .english-body h3")
      .filter(function (p) { return p.offsetParent !== null; });
  }

  function nearestIndex(list, bias) {
    var mid = window.innerHeight * (bias || 0.35);
    var best = 0, bestDist = Infinity;
    list.forEach(function (el, i) {
      var r = el.getBoundingClientRect();
      var center = r.top + r.height / 2;
      var d = Math.abs(center - mid);
      if (d < bestDist) { bestDist = d; best = i; }
    });
    return best;
  }

  function scrollToEl(el) {
    if (!el) return;
    var r = el.getBoundingClientRect();
    var top = window.pageYOffset + r.top - window.innerHeight * 0.3;
    window.scrollTo({ top: Math.max(0, top), behavior: scrollBehavior() });
  }

  function chapters() {
    return $all(".english-body .chapter, section.chapter").map(function (sec) {
      var seg = sec.getAttribute("data-seg");
      var head = sec.querySelector("h2, h3, .chapter-title");
      return { el: sec, id: sec.id, seg: seg,
               label: head ? head.textContent.trim().slice(0, 60) : ("Part " + seg) };
    });
  }

  function chapterAtScroll() {
    var list = chapters();
    if (!list.length) return null;
    var mid = window.innerHeight * 0.35;
    var cur = list[0];
    list.forEach(function (c) {
      if (c.el.getBoundingClientRect().top <= mid + 2) cur = c;
    });
    return cur;
  }

  function gotoChapter(delta) {
    var list = chapters();
    if (!list.length) return;
    var cur = chapterAtScroll() || list[0];
    var i = list.indexOf(cur);
    var tgt = list[Math.max(0, Math.min(list.length - 1, i + delta))];
    if (tgt) scrollToEl(tgt.el);
  }

  function gotoParagraph(delta) {
    var list = paragraphs();
    if (!list.length) return;
    var i = nearestIndex(list) + delta;
    i = Math.max(0, Math.min(list.length - 1, i));
    scrollToEl(list[i]);
    flash(list[i]);
  }

  function flash(el) {
    if (!el) return;
    el.classList.add("tc-flash");
    setTimeout(function () { el.classList.remove("tc-flash"); }, 700);
  }

  document.addEventListener("keydown", function (e) {
    if (isTyping(e)) return;
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    var k = e.key;
    if (k === "j") { e.preventDefault(); gotoParagraph(1); }
    else if (k === "k") { e.preventDefault(); gotoParagraph(-1); }
    else if (k === "]") { e.preventDefault(); gotoChapter(1); }
    else if (k === "[") { e.preventDefault(); gotoChapter(-1); }
    else if (k === "/") {
      var s = $("#pagefind-input, input[type=search], .nav-search");
      if (s && s.tagName === "A") { window.location = s.href; }
      else if (s) { e.preventDefault(); s.focus(); }
    }
  });

  // ── 3. Stable passage links and citations ─────────────────────────────────
  (function passageTools() {
    var linkButton = $("#rt-copy-link");
    var citeButton = $("#rt-copy-cite");
    var label = $("#rt-passage-label");
    var status = $("#rt-passage-status");
    var active = null;
    var ticking = false;
    if (!linkButton || !citeButton || !passageElements().length) return;

    function setActive(element) {
      if (active === element) return;
      if (active) active.removeAttribute("data-active-passage");
      active = element;
      if (active) active.setAttribute("data-active-passage", "true");
      var id = active && active.getAttribute("data-passage-id");
      linkButton.disabled = !id;
      citeButton.disabled = !id;
      if (label) label.textContent = id ? id.replace("p-en-", "Passage ").replace(/-/g, ".") : "";
    }

    function update() {
      ticking = false;
      setActive(passageAtScroll());
    }

    function copyFallback(value) {
      var area = document.createElement("textarea");
      area.value = value;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      var copied = false;
      try { copied = document.execCommand("copy"); } catch (e) {}
      area.remove();
      return copied ? Promise.resolve() : Promise.reject(new Error("copy failed"));
    }

    function copyText(value, successMessage) {
      var operation = navigator.clipboard && window.isSecureContext
        ? navigator.clipboard.writeText(value)
        : copyFallback(value);
      operation.then(function () {
        if (status) status.textContent = successMessage;
      }).catch(function () {
        if (status) status.textContent = "Copy failed; use the browser address bar.";
      });
    }

    function activeData() {
      if (!active) return null;
      var id = active.getAttribute("data-passage-id");
      if (!id) return null;
      var url = passageURL(id);
      try { window.history.replaceState(null, "", url); } catch (e) {}
      return {
        id: id,
        uri: active.getAttribute("data-passage-uri") || id,
        url: url
      };
    }

    linkButton.addEventListener("click", function () {
      var data = activeData();
      if (data) copyText(data.url, "Passage link copied.");
    });
    citeButton.addEventListener("click", function () {
      var data = activeData();
      if (!data) return;
      var citation = (WORK_CITATION || WORK_TITLE || WORK_ID) +
        " Passage " + data.uri + ". " + data.url;
      copyText(citation, "Passage citation copied.");
    });
    window.addEventListener("scroll", function () {
      if (!ticking) { ticking = true; window.requestAnimationFrame(update); }
    }, { passive: true });
    window.addEventListener("hashchange", function () {
      var id = decodeURIComponent(window.location.hash.slice(1));
      var target = id && document.getElementById(id);
      if (target && !target.hasAttribute("data-passage-id")) target = target.nextElementSibling;
      if (target && target.hasAttribute("data-passage-id")) {
        setActive(target);
        flash(target);
      }
    });
    update();
  })();

  // ── 4. Footnote / errata popovers ─────────────────────────────────────────
  // Any link to an in-page anchor (#fn-*, #errata-*, #note-*) shows its target
  // as a hover/focus popover instead of jumping.
  var popover = null;
  var popoverTrigger = null;
  function ensurePopover() {
    if (popover) return popover;
    popover = document.createElement("div");
    popover.id = "tc-reader-popover";
    popover.className = "tc-popover";
    popover.setAttribute("role", "tooltip");
    popover.hidden = true;
    document.body.appendChild(popover);
    return popover;
  }
  function showPopover(target, href) {
    var p = ensurePopover();
    var dest = href.charAt(0) === "#" ? document.getElementById(href.slice(1)) : null;
    if (!dest) return false;
    if (popoverTrigger && popoverTrigger !== target) {
      removeDescription(popoverTrigger, p.id);
    }
    popoverTrigger = target;
    addDescription(target, p.id);
    // use the footnote's own content (or its parent li/aside)
    var src = dest;
    if (dest.tagName === "A" && dest.parentElement) src = dest.parentElement;
    p.innerHTML = "";
    // clone text content (strip back-links)
    var clone = src.cloneNode(true);
    $all("a[href^='#']", clone).forEach(function (a) { a.remove(); });
    p.appendChild(clone);
    p.hidden = false;
    var r = target.getBoundingClientRect();
    var pw = p.offsetWidth, ph = p.offsetHeight;
    var left = Math.max(8, Math.min(r.left, window.innerWidth - pw - 8));
    var top = r.bottom + window.pageYOffset + 6;
    if (top + ph > window.pageYOffset + window.innerHeight - 8)
      top = r.top + window.pageYOffset - ph - 6;
    p.style.left = left + "px";
    p.style.top = top + "px";
    return true;
  }
  function addDescription(target, id) {
    var ids = (target.getAttribute("aria-describedby") || "").split(/\s+/).filter(Boolean);
    if (ids.indexOf(id) < 0) ids.push(id);
    target.setAttribute("aria-describedby", ids.join(" "));
  }
  function removeDescription(target, id) {
    var ids = (target.getAttribute("aria-describedby") || "").split(/\s+/)
      .filter(function (value) { return value && value !== id; });
    if (ids.length) target.setAttribute("aria-describedby", ids.join(" "));
    else target.removeAttribute("aria-describedby");
  }
  function hidePopover() {
    if (popover) popover.hidden = true;
    if (popoverTrigger && popover) removeDescription(popoverTrigger, popover.id);
    popoverTrigger = null;
  }

  document.addEventListener("mouseover", function (e) {
    var a = e.target.closest && e.target.closest("a[href^='#fn-'], a[href^='#errata-'], a[href^='#note-']");
    if (a && showPopover(a, a.getAttribute("href"))) e.preventDefault();
  });
  document.addEventListener("mouseout", function (e) {
    var a = e.target.closest && e.target.closest("a[href^='#fn-'], a[href^='#errata-'], a[href^='#note-']");
    if (a) hidePopover();
  });
  document.addEventListener("focusin", function (e) {
    var a = e.target.closest && e.target.closest("a[href^='#fn-'], a[href^='#errata-'], a[href^='#note-']");
    if (a) showPopover(a, a.getAttribute("href"));
  });
  document.addEventListener("focusout", function (e) {
    var a = e.target.closest && e.target.closest("a[href^='#fn-'], a[href^='#errata-'], a[href^='#note-']");
    if (a) hidePopover();
  });
  document.addEventListener("click", function (e) {
    var a = e.target.closest && e.target.closest("a[href^='#fn-'], a[href^='#errata-'], a[href^='#note-']");
    if (a && showPopover(a, a.getAttribute("href"))) { e.preventDefault(); return; }
    if (popover && !popover.hidden && !popover.contains(e.target)) hidePopover();
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && popover && !popover.hidden) hidePopover();
  });

  // ── 5. Homepage continue-reading card ─────────────────────────────────────
  function renderContinueCard() {
    var host = $("#continue-reading");
    if (!host) return;
    var idx = [];
    try { idx = JSON.parse(localStorage.getItem("tc-progress-idx") || "[]"); } catch (e) {}
    var best = null;
    for (var i = 0; i < idx.length; i++) {
      try {
        var entry = JSON.parse(localStorage.getItem(progressKey(idx[i])) || "null");
        if (entry && entry.id) { best = entry; break; }
      } catch (e) {}
    }
    if (!best) { host.hidden = true; return; }
    host.hidden = false;
    var pct = Math.round((best.frac || 0) * 100);
    var href = "works/" + encodeURIComponent(best.id) + ".html";
    if (best.passage) {
      href += "?view=read&amp;lang=en&amp;annotations=visible#" + encodeURIComponent(best.passage);
    } else if (best.frac) {
      href += "?resume=" + encodeURIComponent(best.frac);
    }
    host.innerHTML = '<a class="continue-card" href="' + href + '">' +
      '<span class="continue-label">Continue reading</span>' +
      '<span class="continue-title">' + escapeHTML(best.title || "") + '</span>' +
      (best.ch ? '<span class="continue-ch">' + escapeHTML(best.ch) + '</span>' : "") +
      '<span class="continue-pct">' + pct + '% &mdash; ' + relTime(best.t) + "</span>" +
      '<span class="continue-bar"><span style="width:' + pct + '%"></span></span>' +
      "</a>";
  }
  function escapeHTML(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function relTime(t) {
    if (!t) return "";
    var d = (Date.now() - t) / 1000;
    if (d < 60) return "just now";
    if (d < 3600) return Math.floor(d / 60) + "m ago";
    if (d < 86400) return Math.floor(d / 3600) + "h ago";
    return Math.floor(d / 86400) + "d ago";
  }

  renderContinueCard();

  // ── 6. Adjustable type controls ───────────────────────────────────────────
  // CSS custom properties on .english-body drive size/line/width/justify so the
  // reader can resize without reflowing the whole layout. Persisted per-reader.
  (function typeControls() {
    var body = $(".english-body");
    var panel = $("#rt-type-panel");
    if (!body || !panel) return;
    var KEY = "tc-type";
    var defaults = { font: 100, line: 162, width: 44, justify: true };
    var saved = {};
    try { saved = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) {}
    var cfg = { font: num(saved.font, defaults.font), line: num(saved.line, defaults.line),
                width: num(saved.width, defaults.width),
                justify: saved.justify === undefined ? defaults.justify : !!saved.justify };

    function num(v, d) { v = parseInt(v, 10); return isNaN(v) ? d : v; }

    function apply() {
      body.style.fontSize = cfg.font + "%";
      body.style.lineHeight = (cfg.line / 100).toFixed(2);
      body.style.setProperty("--body-max", cfg.width + "rem");
      body.style.maxWidth = cfg.width + "rem";
      body.classList.toggle("rt-ragged", !cfg.justify);
    }
    function save() { try { localStorage.setItem(KEY, JSON.stringify(cfg)); } catch (e) {} }
    function wire(id, key, fmt, isCheck) {
      var el = $(id); if (!el) return;
      var out = $('output[for="' + id.replace("#", "") + '"]');
      if (isCheck) el.checked = cfg[key];
      else el.value = cfg[key];
      if (out) out.textContent = fmt(cfg[key]);
      el.addEventListener("input", function () {
        cfg[key] = isCheck ? el.checked : parseInt(el.value, 10);
        if (out) out.textContent = fmt(cfg[key]);
        apply(); save();
      });
    }
    apply();
    wire("#rt-font", "font", function (v) { return v + "%"; });
    wire("#rt-line", "line", function (v) { return (v / 100).toFixed(2); });
    wire("#rt-width", "width", function (v) { return v + "rem"; });
    wire("#rt-justify", "justify", null, true);
    var tog = $("#rt-type-toggle");
    if (tog) tog.addEventListener("click", function () {
      var open = panel.hidden;
      panel.hidden = !open;
      tog.setAttribute("aria-expanded", open ? "true" : "false");
    });
    var reset = $("#rt-reset");
    if (reset) reset.addEventListener("click", function () {
      cfg = { font: defaults.font, line: defaults.line, width: defaults.width, justify: defaults.justify };
      apply(); save(); location.reload();
    });
  })();

  // ── 7. "What is this?" cipher explainer (first visit) ─────────────────────
  // First-time visitors get a one-paragraph popover anchored to the first
  // inline cipher table on a work page. Dismissible; remembered per browser.
  (function cipherIntro() {
    var KEY = "tc-seen-cipher-intro";
    var seen = false;
    try { seen = localStorage.getItem(KEY) === "1"; } catch (e) {}
    if (seen) return;
    var target = $(".inline-apparatus, .style-c-rendering table");
    if (!target) return;
    var host = $(".english-body") || document.body;
    function reveal() {
      var tip = document.createElement("div");
      tip.className = "tc-cipher-intro";
      tip.innerHTML = "<strong>What is this?</strong> A Trithemius cipher " +
        "substitution table: each plaintext letter (a, b, c&hellip;) maps to a " +
        "Latin word in each column, so a message becomes a pious-looking sentence. " +
        "The facsimile sits beside it for comparison. " +
        "<button type=\"button\" class=\"tc-cipher-intro-close\">Got it</button>";
      host.appendChild(tip);
      var close = $(".tc-cipher-intro-close", tip);
      if (close) close.addEventListener("click", function () {
        tip.remove();
        try { localStorage.setItem(KEY, "1"); } catch (e) {}
      });
    }
    setTimeout(reveal, 1200);
  })();

  // ── 8. Audio narration (SpeechSynthesis proof of concept) ─────────────────
  // Reads the work's English aloud, highlighting the current sentence. Play /
  // pause / stop. Pure client-side via the Web Speech API.
  (function audioNarration() {
    var btn = $("#rt-read");
    var body = $(".english-body");
    if (!btn || !body || !("speechSynthesis" in window)) { if (btn) btn.hidden = true; return; }
    var utter = null;
    var sentences = [];
    var idx = 0;
    var playing = false;

    function setPlaying(on) {
      playing = on;
      btn.classList.toggle("rt-reading", on);
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    }

    function gather() {
      sentences = [];
      $all("p, li", body).forEach(function (p) {
        // split into sentences on . ; ? ! followed by space/end
        var text = p.textContent.replace(/\s+/g, " ").trim();
        if (!text) return;
        var parts = text.match(/[^.!?;]+[.!?;]+(\s|$)|[^.!?;]+$/g) || [text];
        parts.forEach(function (s) { sentences.push({ el: p, text: s.trim() }); });
      });
    }
    function clearHL() { $all(".tc-read-hl", body).forEach(function (s) { s.classList.remove("tc-read-hl"); }); }
    function highlight(i) {
      clearHL();
      if (sentences[i]) sentences[i].el.classList.add("tc-read-hl");
      var r = sentences[i] && sentences[i].el.getBoundingClientRect();
      if (r && (r.bottom < 0 || r.top > window.innerHeight))
        sentences[i].el.scrollIntoView({ block: "center", behavior: scrollBehavior() });
    }
    function speak(i) {
      if (i >= sentences.length) { stop(); return; }
      idx = i;
      highlight(i);
      utter = new SpeechSynthesisUtterance(sentences[i].text);
      utter.rate = 0.95;
      utter.onend = function () { if (playing) speak(idx + 1); };
      utter.onerror = function () { if (playing) stop(); };
      window.speechSynthesis.speak(utter);
    }
    function play() { gather(); if (!sentences.length) return; setPlaying(true); speak(idx); }
    function pause() { setPlaying(false); window.speechSynthesis.cancel(); }
    function stop() { setPlaying(false); window.speechSynthesis.cancel(); idx = 0; clearHL(); }
    setPlaying(false);
    btn.addEventListener("click", function () {
      if (playing) pause();
      else if (window.speechSynthesis.speaking) { setPlaying(true); window.speechSynthesis.resume(); }
      else play();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && playing) pause();
    });
  })();
})();
