/* Cipher Lab — interactive Trithemius cipher tools.
 * Phase 0 bootstrap: load cipher-data.json and wire up the encoder + spirit
 * index. The tabula recta, comparison, and numerical calculator are built up
 * in later phases but the data is loaded here. No frameworks; vanilla ES5+. */
(function () {
  "use strict";
  var DATA = null;

  function $(id) { return document.getElementById(id); }
  function $all(sel, ctx) { return Array.prototype.slice.call((ctx || document).querySelectorAll(sel)); }
  function el(tag, cls, txt) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (txt != null) e.textContent = txt;
    return e;
  }

  // ── Encoder / decoder ──────────────────────────────────────────────────────
  // Ave Maria: each plaintext letter → a Latin word from a substitution column,
  // Trithemius's 24-letter alphabet merges u/v and i/j: the printed claves
  // have entries for `v` and `i` only. Normalise modern input so `u` and `j`
  // encipher instead of falling through as literal characters.
  function toPeriodLetter(ch) {
    ch = ch.toLowerCase();
    if (ch === "u") return "v";
    if (ch === "j") return "i";
    return ch;
  }

  // cycling through the columns by position (polyalphabetic across columns).
  function encodeAveMaria(text) {
    if (!DATA) return "";
    var cols = DATA.ave_maria.columns;
    if (!cols.length) return "(no substitution data loaded)";
    var out = [];
    var ci = 0;
    for (var i = 0; i < text.length; i++) {
      var ch = toPeriodLetter(text[i]);
      if (DATA.alphabet_24.indexOf(ch) < 0) { out.push(text[i]); continue; }
      // find a column that has a word for this letter
      var col, attempts = 0;
      do { col = cols[ci % cols.length]; ci++; attempts++; }
      while (!col.words[ch] && attempts < cols.length);
      out.push(col.words[ch] || "[" + ch + "]");
    }
    return out.join(" ");
  }

  function encodeMono(text) {
    if (!DATA || !DATA.ave_maria.columns.length) return "";
    var col = DATA.ave_maria.columns[0];
    var out = [];
    for (var i = 0; i < text.length; i++) {
      var ch = toPeriodLetter(text[i]);
      out.push(col.words[ch] ? col.words[ch] : text[i]);
    }
    return out.join(" ");
  }

  function decodeCiphertext(text) {
    if (!DATA) return "";
    var cols = DATA.ave_maria.columns;
    if (!cols.length) return "(no substitution data loaded)";

    // Follow the same rotating columns as the encoder. A global reverse lookup
    // is ambiguous because one devotional word can represent different letters
    // in different columns. Some substitutions are multi-word phrases, so use
    // longest-phrase matching at the current position.
    function words(value) {
      var clean = value.toLowerCase().replace(/[^a-z]+/g, " ").trim();
      return clean ? clean.split(/\s+/) : [];
    }
    var tokens = words(text);
    var out = [], ti = 0, ci = 0;
    while (ti < tokens.length) {
      var match = null, matchedCi = ci;
      // Mirror encodeAveMaria's handling of incomplete OCR columns: advance
      // until a column containing the observed substitution is found.
      for (var attempt = 0; attempt < cols.length && !match; attempt++) {
        var candidateCi = ci + attempt;
        var col = cols[candidateCi % cols.length];
        Object.keys(col.words).forEach(function (letter) {
          var phrase = words(col.words[letter]);
          if (!phrase.length || phrase.length > tokens.length - ti) return;
          for (var k = 0; k < phrase.length; k++) {
            if (phrase[k] !== tokens[ti + k]) return;
          }
          if (!match || phrase.length > match.length) {
            match = { letter: letter, length: phrase.length };
            matchedCi = candidateCi;
          }
        });
      }
      if (match) {
        out.push(match.letter);
        ti += match.length;
        ci = matchedCi + 1;
      } else {
        out.push("·");
        ti++;
        ci++;
      }
    }
    return out.join("");
  }

  function updateEncoder() {
    if (!DATA) return;
    var mode = $("enc-mode").value;
    var input = $("enc-input").value;
    var out = $("enc-output"), note = $("enc-note");
    if (mode === "ave-maria") {
      out.textContent = encodeAveMaria(input);
      note.textContent = "Each letter becomes a real Polygraphia word, columns rotating by position.";
    } else if (mode === "mono") {
      out.textContent = encodeMono(input);
      note.textContent = "Single substitution column (the first alphabet).";
    } else {
      out.textContent = decodeCiphertext(input);
      note.textContent = "Position-aware reverse lookup, following the same rotating columns as the encoder.";
    }
  }

  // ── Spirit index ───────────────────────────────────────────────────────────
  function renderSpirits(filter) {
    var host = $("spirit-list");
    host.innerHTML = "";
    if (!DATA || !DATA.spirits.length) { host.textContent = "(no spirit data)"; return; }
    var f = (filter || "").toLowerCase();
    DATA.spirits.forEach(function (s) {
      if (f && s.name.toLowerCase().indexOf(f) < 0 && s.direction.toLowerCase().indexOf(f) < 0) return;
      var card = el("div", "spirit-card");
      // name links to the spirit's first mention in the Steganographia
      // parallel viewer (which has per-segment #seg-N anchors)
      var nm = el("a", "spirit-name", s.name);
      if (s.segment != null) {
        nm.href = "works/" + s.work_id + "_parallel.html#seg-" + s.segment;
        nm.title = "Open in the Steganographia parallel viewer, segment " + s.segment;
      } else {
        nm.href = "works/" + s.work_id + "_parallel.html";
        nm.title = "Open in the Steganographia parallel viewer";
      }
      card.appendChild(nm);
      card.appendChild(el("div", "spirit-dir", "Wind: " + s.direction));
      if (s.glyphs) card.appendChild(el("div", "spirit-glyph", s.glyphs));
      if (s.numbers && s.numbers.length)
        card.appendChild(el("div", "spirit-num", "Offices: " + s.numbers.join(" · ")));
      host.appendChild(card);
    });
    if (!host.children.length) host.textContent = "(no match)";
  }

  // ── Tabula recta (interactive 24×24 grid) ──────────────────────────────────
  // Generated algorithmically: row i is the alphabet rotated by i places
  // (a Caesar shift). Hover/click a cell to highlight its row, column, and the
  // cipher letter at their intersection.
  function buildTabula() {
    var host = $("tabula-grid");
    if (!host || !DATA) return;
    var alpha = DATA.tabula_recta.alphabet;
    var N = alpha.length;
    var readout = $("tabula-readout");
    var tbl = el("table");
    // header row (empty corner + column letters)
    var thead = el("thead"), htr = el("tr");
    htr.appendChild(el("th")); // corner
    alpha.forEach(function (c) { htr.appendChild(el("th", null, c)); });
    thead.appendChild(htr); tbl.appendChild(thead);
    var tbody = el("tbody");
    var _loop = function (ri) {
      var tr = el("tr");
      tr.appendChild(el("th", "tabula-rowhead", alpha[ri]));
      var _loop2 = function (ci) {
        // cipher letter = alphabet at (ri + ci) mod N
        var ch = alpha[(ri + ci) % N];
        var td = el("td", null, ch);
        td.setAttribute("data-r", ri);
        td.setAttribute("data-c", ci);
        td.addEventListener("mouseenter", function () { highlightCell(ri, ci); });
        td.addEventListener("click", function () {
          if (readout) readout.textContent =
            "row " + alpha[ri] + " × col " + alpha[ci] + " → " + ch;
        });
        tr.appendChild(td);
      };
      for (var ci = 0; ci < N; ci++) _loop2(ci);
      tbody.appendChild(tr);
    };
    for (var ri = 0; ri < N; ri++) _loop(ri);
    tbl.appendChild(tbody);
    host.innerHTML = "";
    host.appendChild(tbl);

    function highlightCell(r, c) {
      $all("td.tabula-row-hi, td.tabula-col-hi, td.tabula-cell-hi", host)
        .forEach(function (e) { e.className = ""; });
      // highlight column header + cells in that column
      $all("tbody tr", host).forEach(function (tr, ri) {
        var cell = tr.children[c + 1];
        cell.classList.add("tabula-col-hi");
        var rowhead = tr.children[0];
        rowhead.classList.toggle("tabula-col-hi", ri === r);
        if (ri === r) {
          for (var k = 1; k < tr.children.length; k++) tr.children[k].classList.add("tabula-row-hi");
        }
      });
      var hit = host.querySelector('td[data-r="' + r + '"][data-c="' + c + '"]');
      if (hit) { hit.classList.remove("tabula-row-hi", "tabula-col-hi"); hit.classList.add("tabula-cell-hi"); }
      if (readout) readout.textContent =
        "row " + alpha[r] + " × col " + alpha[c] + " → " + alpha[(r + c) % N];
    }
  }

  // ── Side-by-side cipher comparison ─────────────────────────────────────────
  // One plaintext encoded four ways to show why Trithemius escalated complexity.
  function cmpAveMaria(text) { return encodeAveMaria(text); }
  function cmpMono(text) {
    if (!DATA) return "";
    var col = DATA.ave_maria.columns[0];
    var out = [];
    for (var i = 0; i < text.length; i++) {
      var ch = toPeriodLetter(text[i]);
      out.push(col.words[ch] || (DATA.alphabet_24.indexOf(ch) < 0 ? text[i] : "[" + ch + "]"));
    }
    return out.join(" ");
  }
  function cmpTabula(text) {
    if (!DATA) return "";
    var alpha = DATA.tabula_recta.alphabet;
    // polyalphabetic with a repeating keyword shift (default 'b'=1 per position)
    var out = [];
    for (var i = 0; i < text.length; i++) {
      var ch = toPeriodLetter(text[i]);
      var idx = alpha.indexOf(ch);
      out.push(idx < 0 ? text[i] : alpha[(idx + (i + 1)) % alpha.length]);
    }
    return out.join("");
  }
  function cmpSecondLetter(text) {
    // Book IV cipher: each plaintext letter becomes the 2nd letter of a word.
    if (!DATA) return "";
    var col = DATA.ave_maria.columns[0];
    // invert: build letter→word, then take the word's 2nd char as the cipher
    var out = [];
    for (var i = 0; i < text.length; i++) {
      var ch = toPeriodLetter(text[i]);
      var w = col.words[ch];
      if (!w) { out.push(text[i]); continue; }
      out.push(w.length >= 2 ? w[1] : w[0]); // 2nd letter
    }
    return out.join(" ");
  }
  function updateCompare() {
    var host = $("cmp-output");
    if (!host) return;
    var text = $("cmp-input").value;
    if (!text.trim()) { host.innerHTML = "<p class='lab-pending'>Type text above to compare.</p>"; return; }
    var items = [
      { label: "Simple substitution", fn: cmpMono, note: "One letter → one fixed word (monoalphabetic)." },
      { label: "Ave Maria (rotating)", fn: cmpAveMaria, note: "Columns rotate by position — reads as a prayer." },
      { label: "Tabula recta (polyalpha)", fn: cmpTabula, note: "Each letter shifted by its position (pre-Vigenère)." },
      { label: "Book IV second-letter", fn: cmpSecondLetter, note: "Cipher letter = 2nd letter of a fabricated word." },
    ];
    host.innerHTML = "";
    items.forEach(function (it) {
      var div = el("div", "cmp-item");
      div.appendChild(el("div", "cmp-label", it.label));
      div.appendChild(el("div", "cmp-text", it.fn(text) || "(—)"));
      div.appendChild(el("div", "cmp-note", it.note));
      host.appendChild(div);
    });
  }

  // ── Numerical-letter calculator ────────────────────────────────────────────
  function updateNumber() {
    var out = $("num-out");
    if (!out || !DATA) return;
    var n = parseInt($("num-in").value, 10);
    if (isNaN(n) || n < 1) { out.textContent = "Enter a positive number."; return; }
    var byNum = DATA.numerical_letters.by_number;
    var ambigCodes = DATA.numerical_letters.ambiguous_codes || {};
    var code = byNum[String(n)];
    if (!code) {
      out.innerHTML = "<strong>" + n + "</strong> has no direct code in the parsed table " +
        "(the OCR'd source may be incomplete here — see the facsimile).";
      return;
    }
    // flag if this code also maps to other numbers (real OCR collision)
    var flag = "";
    if (ambigCodes[code] && ambigCodes[code].length > 1) {
      flag = " <span class='lab-warn'>(⚠ code “" + code + "” also means " +
        ambigCodes[code].filter(function (x) { return x !== n; }).join(", ") +
        " — OCR collision)</span>";
    }
    out.innerHTML = "<strong>" + n + "</strong> → <code>" + code + "</code>" + flag;
  }

  // ── Init ───────────────────────────────────────────────────────────────────
  function init(data) {
    DATA = data;
    $("enc-input").addEventListener("input", updateEncoder);
    $("enc-mode").addEventListener("change", updateEncoder);
    $("enc-input").value = "hidethegold";
    updateEncoder();

    $("spirit-search").addEventListener("input", function () { renderSpirits(this.value); });
    renderSpirits("");

    buildTabula();

    $("cmp-input").addEventListener("input", updateCompare);
    $("cmp-input").value = "ave";
    updateCompare();

    $("num-in").addEventListener("input", updateNumber);
    updateNumber();
  }

  // asset prefix is injected on the .cipher-lab root via data-asset (handles
  // the tools page being at site root → empty prefix, vs. a nested page).
  function assetPrefix() {
    var root = document.querySelector(".cipher-lab");
    return root ? (root.getAttribute("data-asset") || "") : "";
  }

  // Prefer cipher data inlined into the page (window.CIPHER_DATA) so the tools
  // work from file:// too; fall back to fetching the JSON when served over HTTP
  // and the inline payload isn't present.
  if (window.CIPHER_DATA) {
    init(window.CIPHER_DATA);
  } else {
    fetch(assetPrefix() + "static/cipher-data.json")
      .then(function (r) { return r.json(); })
      .then(init)
      .catch(function () {
        var host = document.querySelector(".cipher-lab");
        if (host) host.insertAdjacentHTML("afterbegin",
          "<p class='lab-error'>Could not load cipher data. If you opened this file directly, the tools need a web server.</p>");
      });
  }
})();
