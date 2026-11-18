/* Match explicit editorial forms and phrases in the original diplomatic text. */
export function foldLatin(value) {
  return value.toLowerCase().normalize("NFD").replace(/\p{M}/gu, "")
    .replace(/ſ/g, "s").replace(/æ/g, "ae").replace(/œ/g, "oe")
    .replace(/j/g, "i").replace(/v/g, "u");
}

export function glossaryFor(entries, genre) {
  const byForm = new Map();
  const byLemma = new Map();
  let maxWords = 1;
  const eligible = entries.filter(entry => entry.clusters === "all" || entry.clusters.includes(genre));
  for (const entry of eligible) {
    const lemma = foldLatin(entry.lemma);
    if (!byLemma.has(lemma)) byLemma.set(lemma, []);
    byLemma.get(lemma).push(entry);
  }
  for (const entry of eligible) {
    for (const form of [entry.lemma, ...entry.forms]) {
      const normalized = foldLatin(form).trim().replace(/\s+/g, " ");
      if (!byForm.has(normalized)) byForm.set(normalized, new Set());
      // A technical description of the same lemma also applies to an explicitly
      // attested inflection. Keep both definitions and their provenance.
      for (const sense of byLemma.get(foldLatin(entry.lemma))) byForm.get(normalized).add(sense);
      maxWords = Math.max(maxWords, normalized.split(" ").length);
    }
  }
  return { byForm, maxWords };
}

export function glossaryMatches(text, index) {
  const tokens = Array.from(text.matchAll(/[\p{L}\p{M}\p{N}]+/gu));
  const matches = [];
  for (let i = 0; i < tokens.length; i++) {
    let phrase = "";
    let longest;
    for (let j = i; j < Math.min(tokens.length, i + index.maxWords); j++) {
      if (j > i) {
        const previousEnd = tokens[j - 1].index + tokens[j - 1][0].length;
        if (!/^\s+$/.test(text.slice(previousEnd, tokens[j].index))) break;
      }
      phrase = (phrase ? phrase + " " : "") + foldLatin(tokens[j][0]);
      if (index.byForm.has(phrase)) longest = { key: phrase, last: j };
    }
    if (longest) {
      const lastToken = tokens[longest.last];
      matches.push({ start: tokens[i].index, end: lastToken.index + lastToken[0].length, key: longest.key });
      i = longest.last;
    }
  }
  return matches;
}

function addButtons(cell, index) {
  const walker = document.createTreeWalker(cell, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) {
    const text = walker.currentNode;
    if (!text.parentElement.closest("button, a, summary, .muted, code, script, style")) nodes.push(text);
  }
  for (const original of nodes) {
    const text = original.nodeValue;
    const matches = glossaryMatches(text, index);
    if (!matches.length) continue;
    const fragment = document.createDocumentFragment();
    let cursor = 0;
    for (const match of matches) {
      fragment.append(text.slice(cursor, match.start));
      const button = document.createElement("button");
      button.type = "button";
      button.className = "lex";
      button.dataset.term = match.key;
      button.textContent = text.slice(match.start, match.end);
      fragment.append(button);
      cursor = match.end;
    }
    fragment.append(text.slice(cursor));
    original.replaceWith(fragment);
  }
}

function bindGlossary(grid, entries) {
  const index = glossaryFor(entries, grid.dataset.genre);
  const tip = document.createElement("div");
  tip.className = "tc-popover tc-lex-popover";
  tip.id = "reader-glossary-definition";
  tip.setAttribute("role", "tooltip");
  tip.hidden = true;
  document.body.append(tip);
  let active;

  function close() {
    if (active) active.removeAttribute("aria-describedby");
    active = null;
    tip.hidden = true;
  }

  function place() {
    if (!active) return;
    const bounds = active.getBoundingClientRect();
    tip.style.left = Math.max(8, Math.min(bounds.left, innerWidth - tip.offsetWidth - 8)) + "px";
    const below = bounds.bottom + 6;
    const top = below + tip.offsetHeight <= innerHeight - 8 ? below : Math.max(8, bounds.top - tip.offsetHeight - 6);
    tip.style.top = top + "px";
  }

  function show(button) {
    if (active === button) return;
    close();
    active = button;
    tip.replaceChildren();
    for (const sense of index.byForm.get(button.dataset.term)) {
      const heading = document.createElement("strong");
      heading.textContent = sense.lemma;
      const label = document.createElement("small");
      label.textContent = sense.source === "technical" ? "Cipher glossary" :
        sense.clusters === "all" ? "Editorial glossary" : sense.clusters.join(" · ").replaceAll("-", " ");
      const gloss = document.createElement("div");
      gloss.className = "lex-en";
      gloss.textContent = sense.en;
      tip.append(heading, label, gloss);
      if (sense.note) {
        const note = document.createElement("div");
        note.className = "lex-note";
        note.textContent = sense.note;
        tip.append(note);
      }
    }
    tip.hidden = false;
    button.setAttribute("aria-describedby", tip.id);
    place();
  }

  const buttonAt = event => event.target.closest?.("button.lex");
  for (const type of ["pointerover", "focusin", "click"]) {
    grid.addEventListener(type, event => { const button = buttonAt(event); if (button) show(button); });
  }
  grid.addEventListener("focusout", event => {
    if (active === event.target && !tip.contains(event.relatedTarget)) close();
  });
  grid.addEventListener("pointerout", event => {
    if (active === event.target && document.activeElement !== active && !tip.contains(event.relatedTarget)) close();
  });
  tip.addEventListener("pointerleave", () => { if (document.activeElement !== active) close(); });
  document.addEventListener("click", event => { if (!buttonAt(event) && !tip.contains(event.target)) close(); });
  document.addEventListener("keydown", event => { if (event.key === "Escape") close(); });
  window.addEventListener("resize", place);
  window.addEventListener("scroll", close, { passive: true });

  const latin = grid.querySelectorAll(".pp-latin");
  if ("IntersectionObserver" in window) {
    // Large folio witnesses contain hundreds of segments. Hydrate nearby rows
    // so opening a reader never waits for every occurrence in the volume.
    const observer = new IntersectionObserver(rows => {
      for (const row of rows) if (row.isIntersecting) {
        observer.unobserve(row.target);
        addButtons(row.target, index);
      }
    }, { rootMargin: "750px" });
    latin.forEach(cell => observer.observe(cell));
  } else {
    latin.forEach(cell => addButtons(cell, index));
  }
}

if (typeof document !== "undefined") {
  const grid = document.querySelector(".pp-grid[data-glossary]");
  if (grid) fetch(grid.dataset.glossary)
    .then(response => {
      if (!response.ok) throw new Error("Glossary unavailable");
      return response.json();
    })
    .then(data => bindGlossary(grid, data.entries))
    .catch(() => {
      const note = document.createElement("p");
      note.className = "muted";
      note.textContent = "Glossary definitions could not be loaded.";
      grid.before(note);
    });
}
