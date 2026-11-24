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

  function passageAtScroll(list) {
    list = list || passageElements();
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
  // Version 3 keys progress by the published reading path, including the track.
  function progressKey(id) { return "tc-progress-" + id; }

  if (WORK_ID) {
    var track = window.TC_WORK.track ||
      (window.location.pathname.endsWith("-trithemius-4b.html") ? "trithemius-4b" : "earlier");
    var readingPath = window.TC_WORK.readingPath ||
      "works/" + WORK_ID + (track === "trithemius-4b" ? "-trithemius-4b.html" : ".html");
    var alternatePassages = track === "trithemius-4b" ? $all(".english-body [id^='p-t4b-']") : null;
    var ticking = false;
    function recordProgress() {
      ticking = false;
      var h = document.documentElement;
      var max = h.scrollHeight - h.clientHeight;
      var frac = max > 0 ? Math.min(1, Math.max(0, h.scrollTop / max)) : 0;
      var passage = pinnedPassage || passageAtScroll(alternatePassages);
      try {
        var entry = { v: 3, id: WORK_ID, track: track, path: readingPath, title: WORK_TITLE,
                      frac: frac, t: Date.now(),
                      ch: currentChapterLabel(),
                      passage: passage && (passage.getAttribute("data-passage-id") || passage.id) };
        localStorage.setItem(progressKey(readingPath), JSON.stringify(entry));
        var idx = JSON.parse(localStorage.getItem("tc-progress-idx") || "[]");
        idx = idx.filter(function (x) { return x !== readingPath; });
        idx.unshift(readingPath);
        try { localStorage.setItem("tc-progress-idx", JSON.stringify(idx.slice(0, 20))); } catch (e) {}
      } catch (e) {}
    }
    window.addEventListener("scroll", function () {
      if (!ticking) { window.requestAnimationFrame(recordProgress); ticking = true; }
    }, { passive: true });
    window.addEventListener("hashchange", function () { window.requestAnimationFrame(recordProgress); });
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
    selectPassage(el.hasAttribute("data-passage-id") ? el : null);
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
  function linkedPassage(id) {
    var node = id && document.getElementById(id);
    if (node && alternatePassages && alternatePassages.includes(node)) return node;
    if (node && node.classList.contains("passage-anchor")) node = node.nextElementSibling;
    return node && node.hasAttribute("data-passage-id") ? node : null;
  }

  var pinnedPassage = linkedPassage(decodeURIComponent(window.location.hash.slice(1)));
  function selectPassage(element) {
    pinnedPassage = element;
    if (element) document.dispatchEvent(new CustomEvent("tc:select-passage", { detail: element }));
  }

  if (WORK_ID) {
    // An explicit citation survives layout shifts and focusing the toolbar.
    // Return to viewport tracking when the reader deliberately scrolls the text.
    function releaseSelection() { pinnedPassage = null; }
    window.addEventListener("wheel", releaseSelection, { passive: true });
    window.addEventListener("touchmove", releaseSelection, { passive: true });
    window.addEventListener("pointerdown", function (event) {
      if (event.clientX >= document.documentElement.clientWidth) releaseSelection();
    });
    window.addEventListener("keydown", function (event) {
      if (!isTyping(event) && ["PageUp", "PageDown", "Home", "End", "ArrowUp", "ArrowDown", " "].includes(event.key)) {
        releaseSelection();
      }
    });
    window.addEventListener("hashchange", function () {
      var id = decodeURIComponent(window.location.hash.slice(1));
      var target = linkedPassage(id);
      selectPassage(target);
      if (target) flash(target);
    });
  }

  function facsimileTarget(element) {
    var work = window.TC_WORK || {};
    var id = element && element.getAttribute("data-passage-id");
    var segment = latinSegment(element);
    var exact = (work.reviewedCanvases || {})[id];
    var number = exact || (work.iiifCanvasMap || {})[segment];
    var origin = exact ? "&passage=" + encodeURIComponent(id) : "";
    return {
      page: number,
      url: number && work.iiifViewer ? work.iiifViewer + origin + "#canvas=" + number : null,
      label: exact ? "Reviewed source page" : number ? "Approximate source page" : "Browse source"
    };
  }

  function latinSegment(element) {
    return element && (element.getAttribute("data-latin-segment") || element.getAttribute("data-segment"));
  }

  (function passageTools() {
    var linkButton = $("#rt-copy-link");
    var citeButton = $("#rt-copy-cite");
    var label = $("#rt-passage-label");
    var status = $("#rt-passage-status");
    var facsimile = $("#rt-facsimile");
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
      if (facsimile && active) {
        var source = facsimileTarget(active);
        facsimile.href = source.url || window.TC_WORK.institutionalSource;
        facsimile.title = source.label;
        facsimile.querySelector(".rt-label").textContent = " " + source.label;
      }
      document.dispatchEvent(new CustomEvent("tc:passage", { detail: {
        element: active, id: id, segment: active && active.getAttribute("data-segment")
      }}));
    }

    function update() {
      ticking = false;
      // Latin-only Study temporarily hides every English passage.
      var visible = pinnedPassage || passageAtScroll();
      if (visible) setActive(visible);
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
    document.addEventListener("tc:select-passage", function (event) { setActive(event.detail); });
    setActive(pinnedPassage || passageAtScroll());
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
    if ("showPopover" in HTMLElement.prototype) popover.setAttribute("popover", "auto");
    else popover.hidden = true;
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
    if (typeof p.showPopover === "function") p.showPopover();
    else p.hidden = false;
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
  function popoverIsOpen(element) {
    try { return element && element.matches(":popover-open"); }
    catch (e) { return false; }
  }
  function hidePopover() {
    if (popover) {
      if (typeof popover.hidePopover === "function" && popoverIsOpen(popover)) popover.hidePopover();
      else popover.hidden = true;
    }
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
    if (popover && (popoverIsOpen(popover) || !popover.hidden) && !popover.contains(e.target)) hidePopover();
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && popover && (popoverIsOpen(popover) || !popover.hidden)) hidePopover();
  });

  // ── 5. Unified Read / Study / Source workspace ───────────────────────────
  (function studyReader() {
    var shell = $("#study-reader"), modeLinks = $all("[data-reader-mode]");
    var latinPane = $("[data-study-pane='latin']"), sourcePane = $("[data-study-pane='source']");
    var sourceFrame = $("#study-source-frame"), options = $("#study-options");
    var minimap = $("#study-minimap"), minimapList = $("#study-minimap-list");
    var progress = $(".study-progress"), activePassage = null;
    var layerButtons = $all("button[data-text-layer]");
    if (!shell || !modeLinks.length || !window.TC_WORK) return;
    activePassage = linkedPassage(decodeURIComponent(window.location.hash.slice(1))) || passageAtScroll();

    function selectedMode() {
      var value = new URL(window.location.href).searchParams.get("view");
      return ["read", "study", "source"].indexOf(value) >= 0 ? value : "read";
    }
    function showSource(element) {
      var source = facsimileTarget(element);
      var precision = $("#study-source-precision");
      if (precision) precision.textContent = source.label;
      if (source.url && sourceFrame.getAttribute("src") !== source.url) sourceFrame.setAttribute("src", source.url);
      if (!source.url) sourceFrame.removeAttribute("src");
    }
    function applyMode(mode, updateURL) {
      if (mode === "source" && !sourcePane) mode = "study";
      var cursor = pinnedPassage || activePassage;
      if (mode === "read") selectLayer("normalized");
      shell.setAttribute("data-mode", mode);
      modeLinks.forEach(function (link) {
        if (link.getAttribute("data-reader-mode") === mode) link.setAttribute("aria-current", "page");
        else link.removeAttribute("aria-current");
      });
      if (latinPane) latinPane.hidden = mode !== "study";
      if (sourcePane) sourcePane.hidden = mode !== "source";
      if (options) options.hidden = mode === "read";
      if (minimap) minimap.hidden = mode === "read";
      if (mode === "study") highlightLatin(cursor);
      if (mode === "source" && sourceFrame) {
        showSource(cursor);
      }
      window.TC_WORK.view = mode;
      if (updateURL) {
        var url = new URL(window.location.href); url.searchParams.set("view", mode);
        if (cursor) url.hash = cursor.getAttribute("data-passage-id");
        try { window.history.replaceState(null, "", url); } catch (e) {}
        selectPassage(cursor);
      }
      if (cursor && (updateURL || pinnedPassage)) window.requestAnimationFrame(function () {
        cursor.scrollIntoView({ block: "center", behavior: "auto" }); flash(cursor);
      });
    }
    modeLinks.forEach(function (link) {
      link.addEventListener("click", function (event) {
        event.preventDefault(); applyMode(link.getAttribute("data-reader-mode"), true);
      });
    });

    function englishForLatin(number) {
      if (latinSegment(activePassage) === String(number)) return activePassage;
      return $(".english-body [data-latin-segment='" + number + "']") ||
        $(".english-body [data-passage-id][data-segment='" + number + "']:not([data-latin-segment])");
    }
    function highlightLatin(passage) {
      var n = latinSegment(passage);
      var latin = n && $("#latin-seg-" + n);
      $all(".study-latin-segment[data-active-segment]").forEach(function (el) {
        if (el !== latin) el.removeAttribute("data-active-segment");
      });
      if (!latin) return;
      latin.setAttribute("data-active-segment", "true");
      if (shell.getAttribute("data-mode") === "study" && latinPane.scrollHeight > latinPane.clientHeight) {
        var offset = latin.getBoundingClientRect().top - latinPane.getBoundingClientRect().top;
        if (offset < 0 || offset >= latinPane.clientHeight) latinPane.scrollTop += offset;
      }
    }
    function renderLatin(data) {
      var host = $("#study-latin-content"); if (!host) return; host.innerHTML = "";
      data.segments.forEach(function (segment) {
        var section = document.createElement("section");
        section.className = "study-latin-segment"; section.id = "latin-seg-" + segment.segment;
        section.tabIndex = 0; section.setAttribute("data-segment", segment.segment);
        section.setAttribute("aria-label", "Latin source segment " + segment.segment);
        var heading = document.createElement("h3"); heading.textContent = "Segment " + segment.segment;
        var text = document.createElement("pre"); text.textContent = segment.latin || "[No Latin OCR available]";
        section.appendChild(heading); section.appendChild(text); host.appendChild(section);
        section.addEventListener("click", function () {
          var target = englishForLatin(segment.segment);
          if (target) { scrollToEl(target); target.setAttribute("tabindex", "-1"); target.focus({ preventScroll: true }); }
        });
      });
      highlightLatin(activePassage);
    }
    function renderMinimap() {
      if (!minimapList) return; minimapList.innerHTML = "";
      chapters().forEach(function (chapter) {
        var item = document.createElement("li"), link = document.createElement("a");
        link.href = "#" + chapter.id; link.textContent = chapter.label;
        item.appendChild(link); minimapList.appendChild(item);
      });
    }
    if (window.TC_WORK.passageIndex && window.fetch) {
      fetch(window.TC_WORK.passageIndex).then(function (response) {
        if (!response.ok) throw new Error("passage index " + response.status); return response.json();
      }).then(function (data) { renderLatin(data); renderMinimap(); }).catch(function () {
        if (latinPane) latinPane.innerHTML = "<h2>Diplomatic Latin OCR</h2><p>The aligned layer could not load. Use the permanent Latin / English artifact link below.</p>";
      });
    }
    document.addEventListener("tc:passage", function (event) {
      activePassage = event.detail.element;
      highlightLatin(activePassage);
      if (sourceFrame && shell.getAttribute("data-mode") === "source") {
        showSource(activePassage);
      }
      var list = passageElements(), position = activePassage ? list.indexOf(activePassage) + 1 : 0;
      var percent = list.length ? Math.round(position / list.length * 100) : 0;
      if (progress) { progress.setAttribute("aria-valuenow", percent); progress.style.setProperty("--study-progress", percent + "%"); var bar = $("span", progress); if (bar) bar.style.height = percent + "%"; }
    });
    window.addEventListener("message", function (event) {
      if (!sourceFrame || event.source !== sourceFrame.contentWindow || event.origin !== window.location.origin || !event.data || event.data.type !== "tc:canvas") return;
      if (facsimileTarget(activePassage).page === event.data.canvas) return;
      var segment = null;
      Object.keys(window.TC_WORK.iiifCanvasMap || {}).some(function (key) {
        if (Number(window.TC_WORK.iiifCanvasMap[key]) === Number(event.data.canvas)) { segment = key; return true; }
        return false;
      });
      var reviewed = Object.keys(window.TC_WORK.reviewedCanvases || {}).find(function (id) {
        return window.TC_WORK.reviewedCanvases[id] === event.data.canvas;
      });
      var target = linkedPassage(reviewed) || (segment && englishForLatin(segment));
      if (target && target !== activePassage) {
        var url = new URL(window.location.href); url.hash = target.getAttribute("data-passage-id");
        try { window.history.replaceState(null, "", url); } catch (e) {}
        scrollToEl(target); flash(target);
      }
    });
    function selectLayer(layer) {
      shell.setAttribute("data-text-layer", layer);
      layerButtons.forEach(function (button) {
        button.setAttribute("aria-pressed", String(button.getAttribute("data-text-layer") === layer));
      });
    }
    layerButtons.forEach(function (button) {
      button.addEventListener("click", function () {
        selectLayer(button.getAttribute("data-text-layer"));
      });
    });
    var annotations = $("#rt-annotations-toggle");
    if (annotations) annotations.addEventListener("click", function () {
      var shown = annotations.getAttribute("aria-pressed") !== "false";
      annotations.setAttribute("aria-pressed", shown ? "false" : "true");
      shell.classList.toggle("annotations-hidden", shown);
      window.TC_WORK.annotations = shown ? "hidden" : "visible";
    });
    applyMode(selectedMode(), false);
    if (activePassage) document.dispatchEvent(new CustomEvent("tc:passage", { detail: {
      element: activePassage,
      id: activePassage.getAttribute("data-passage-id"),
      segment: activePassage.getAttribute("data-segment")
    }}));
  })();

  // ── 6. In-work search and match-density strip ────────────────────────────
  (function inWorkSearch() {
    var toggle = $("#rt-search-toggle"), panel = $("#rt-search-panel"), input = $("#rt-work-search");
    var count = $("#rt-search-count"), strip = $("#rt-match-strip");
    if (!toggle || !panel || !input) return;
    toggle.setAttribute("data-search-ready", "true");
    var matches = [], current = -1;
    function clear() {
      passageElements().forEach(function (el) { el.classList.remove("study-search-match", "study-search-current"); });
      matches = []; current = -1; if (strip) strip.innerHTML = "";
    }
    function gotoMatch(index) {
      if (!matches.length) return;
      if (current >= 0) matches[current].classList.remove("study-search-current");
      current = (index + matches.length) % matches.length;
      matches[current].classList.add("study-search-current");
      var url = new URL(window.location.href); url.hash = matches[current].id;
      try { window.history.replaceState(null, "", url); } catch (e) {}
      scrollToEl(matches[current]);
      count.textContent = (current + 1) + " of " + matches.length + " matches";
    }
    function find() {
      clear(); var query = input.value.trim().toLocaleLowerCase();
      if (query.length < 2) { count.textContent = query ? "Enter at least 2 characters" : "No search"; return; }
      var all = passageElements();
      matches = all.filter(function (el) { return el.textContent.toLocaleLowerCase().indexOf(query) >= 0; });
      matches.forEach(function (el) { el.classList.add("study-search-match"); });
      if (strip) matches.forEach(function (el) {
        var mark = document.createElement("span"); mark.style.top = (all.indexOf(el) / Math.max(1, all.length - 1) * 100) + "%"; strip.appendChild(mark);
      });
      count.textContent = matches.length ? matches.length + (matches.length === 1 ? " match" : " matches") : "No matches";
      if (matches.length) gotoMatch(0);
    }
    toggle.addEventListener("click", function () { panel.hidden = !panel.hidden; toggle.setAttribute("aria-expanded", panel.hidden ? "false" : "true"); if (!panel.hidden) input.focus(); });
    input.addEventListener("input", find);
    panel.addEventListener("submit", function (event) { event.preventDefault(); gotoMatch(current + 1); });
    $("#rt-search-prev").addEventListener("click", function () { gotoMatch(current - 1); });
    $("#rt-search-next").addEventListener("click", function () { gotoMatch(current + 1); });
    $("#rt-search-close").addEventListener("click", function () { clear(); input.value = ""; panel.hidden = true; toggle.setAttribute("aria-expanded", "false"); toggle.focus(); });
  })();

  // ── 7. Homepage continue-reading card ─────────────────────────────────────
  function renderContinueCard() {
    var host = $("#continue-reading");
    if (!host) return;
    var idx = [];
    var catalog;
    try {
      idx = JSON.parse(localStorage.getItem("tc-progress-idx") || "[]");
      catalog = JSON.parse($("#resume-editions").textContent);
    } catch (e) { return; }
    for (var i = 0; i < idx.length; i++) {
      try {
        var entry = JSON.parse(localStorage.getItem(progressKey(idx[i])) || "null");
        if (!entry || !Object.hasOwn(catalog, entry.id)) continue;
        var editions = catalog[entry.id];
        var tracks = Object.keys(editions);
        if (entry.v === 3) {
          tracks = tracks.filter(function (key) { return key === entry.track && editions[key] === entry.path; });
        } else if (entry.passage) {
          // Earlier bookmarks used only p-en- anchors. An alternate anchor
          // also identifies its track if the bookmark was imported.
          if (entry.passage.startsWith("p-en-")) tracks = tracks.filter(function (key) { return key === "earlier"; });
          if (entry.passage.startsWith("p-t4b-")) tracks = tracks.filter(function (key) { return key === "trithemius-4b"; });
        }
        if (!tracks.length) continue;
        var prompt = tracks.length > 1 ? "<p>This saved position has no edition recorded. Choose a translation to resume.</p>" : "";
        host.innerHTML = prompt + tracks.map(function (key) {
          return continueCard(entry, editions[key], key === "trithemius-4b" ? "Trithemius 4B" : "Earlier edition");
        }).join("");
        host.hidden = false;
        return;
      } catch (e) {}
    }
  }
  function continueCard(entry, path, edition) {
    var pct = Math.round((entry.frac || 0) * 100);
    var href = path;
    if (entry.passage) {
      href += "?view=read&amp;lang=en&amp;annotations=visible#" + encodeURIComponent(entry.passage);
    } else if (entry.frac) {
      href += "?resume=" + encodeURIComponent(entry.frac);
    }
    return '<a class="continue-card" href="' + href + '">' +
      '<span class="continue-label">Continue reading · ' + edition + '</span>' +
      '<span class="continue-title">' + escapeHTML(entry.title || "") + '</span>' +
      (entry.ch ? '<span class="continue-ch">' + escapeHTML(entry.ch) + '</span>' : "") +
      '<span class="continue-pct">' + pct + '% &mdash; ' + relTime(entry.t) + "</span>" +
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
