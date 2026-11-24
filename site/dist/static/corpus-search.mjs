/* Pagefind returns document scores and matched word offsets. The generated
   edition anchors give each offset its actual translation, Latin or note URL. */
function describe(view, id) {
  if (view === "latin") {
    const segment = /^latin-seg-(\d+)$/.exec(id);
    if (segment) return { id: "seg-" + segment[1], label: "Latin · Source OCR · Segment " + segment[1] };
  }
  if (view === "apparatus") {
    if (id === "apparatus-introduction") return { id, label: "Latin / English apparatus · Introduction" };
    const chunk = /^rendering-(full_chunk_(\d+))$/.exec(id);
    if (chunk) return { id: chunk[1], label: "Latin / English apparatus · Source segment " + Number(chunk[2]) };
  }
  if (view === "translation") {
    if (id === "intro-heading" || id.startsWith("note-intro-")) return { id, label: "English · Editorial introduction" };
    if (id === "errata-heading" || id.startsWith("note-errata-")) return { id, label: "English · Editorial corrections" };
    const earlier = /^p-en-(\d+)-(\d+)$/.exec(id);
    if (earlier) return { id, label: "English · Passage " + Number(earlier[1]) + "." + Number(earlier[2]) };
    if (id.startsWith("p-t4b-")) return { id, label: "English · Translation passage" };
    if (id === "translation-start") return { id, label: "English · Translation" };
  }
  return null;
}

export function passageMatches(fragment) {
  const words = fragment.content.split(" ");
  const guide = !fragment.meta.workGroup;
  const anchors = guide ? [{ id: "main", location: 0, text: "", element: "main" }, ...fragment.anchors] : fragment.anchors;
  const boundaries = anchors.map(anchor => {
    const target = guide && (anchor.id === "main" || /^h[1-6]$/.test(anchor.element)) ?
      { id: anchor.id, label: "English · " + (anchor.text || "Page") } : describe(fragment.meta.view, anchor.id);
    return target && { ...target, start: anchor.location, hits: [] };
  }).filter(Boolean).sort((a, b) => a.start - b.start);
  const hits = [...fragment.locations].sort((a, b) => a - b);
  let i = 0;
  while (i < hits.length && boundaries.length && hits[i] < boundaries[0].start) i++;
  for (const [index, section] of boundaries.entries()) {
    section.end = boundaries[index + 1]?.start ?? words.length;
    while (i < hits.length && hits[i] < section.end) section.hits.push(hits[i++]);
  }
  return boundaries.filter(section => section.hits.length).map(section => {
    // Avoid cutting across the next passage when producing an excerpt.
    const start = Math.max(section.start, section.hits[0] - 8);
    const end = Math.min(section.end, start + 30);
    const selected = new Set(section.hits);
    return {
      id: section.id, label: section.label, count: section.hits.length,
      excerpt: words.slice(start, end).map((word, j) => ({ word, hit: selected.has(start + j) })),
      leading: start > section.start, trailing: end < section.end,
    };
  }).sort((a, b) => b.count - a.count);
}

function node(tag, value) {
  const result = document.createElement(tag);
  if (value) result.textContent = value;
  return result;
}

function resultLink(url, match) {
  const li = node("li");
  const a = node("a", match.label);
  const target = new URL(url, document.baseURI);
  target.hash = match.id;
  a.href = target.href;
  const quote = node("p");
  if (match.leading) quote.append("… ");
  for (const [i, token] of match.excerpt.entries()) {
    if (i) quote.append(" ");
    quote.append(token.hit ? node("mark", token.word) : token.word);
  }
  if (match.trailing) quote.append(" …");
  li.append(a, quote);
  return li;
}

function editionResults(fragment, matches) {
  const section = node("section");
  const viewLabels = { latin: "Earlier edition · Latin source", translation: fragment.meta.track, apparatus: "Earlier edition · Scholarly rendering" };
  section.append(node("h3", fragment.meta.workGroup ?
    [fragment.meta.witness, viewLabels[fragment.meta.view]].filter(Boolean).join(" · ") : fragment.meta.title));
  const list = node("ul");
  const more = node("button");
  more.type = "button";
  let shown = 0;
  function appendMatches() {
    const batch = matches.slice(shown, shown + 4);
    list.append(...batch.map(match => resultLink(fragment.url, match)));
    shown += batch.length;
    more.hidden = shown >= matches.length;
    more.textContent = "Show more passages (" + (matches.length - shown) + " remaining)";
  }
  more.addEventListener("click", appendMatches);
  appendMatches();
  section.append(list);
  if (!more.hidden) section.append(more);
  return section;
}

function bindSearch(form) {
  const input = form.elements.q;
  const results = document.getElementById("corpus-results");
  const status = document.getElementById("corpus-search-status");
  const loadMore = document.getElementById("corpus-more");
  const retry = document.getElementById("corpus-retry");
  let clientPromise;
  let importFailures = 0;
  let timer;
  let revision = 0;
  let query = "";
  let missingCollections = [];
  let pending = [];
  let failed = [];
  let loaded = 0;
  let matchesShown = 0;
  const groups = new Map();

  function showEdition(fragment, matches) {
    if (!matches.length) return;
    const group = fragment.meta.workGroup || "site-guides";
    if (!groups.has(group)) {
      const section = node("section");
      section.className = "corpus-work-results";
      // The edition line identifies the particular printed witness.
      const title = fragment.meta.workTitle?.replace(/\s*[\[(][^\])]*[\])]/g, "").trim();
      section.append(node("h2", title || "Site guides and catalogues"));
      results.append(section);
      groups.set(group, section);
    }
    groups.get(group).append(editionResults(fragment, matches));
    matchesShown += matches.length;
  }

  async function collectPages(version) {
    if (!clientPromise) {
      const url = new URL(form.dataset.index, document.baseURI);
      if (importFailures) url.searchParams.set("retry", importFailures);
      clientPromise = import(url.href).then(module => module.createInstance()).catch(error => {
        importFailures++;
        clientPromise = null;
        throw error;
      });
    }
    const collections = missingCollections.slice();
    let client;
    try { client = await clientPromise; }
    catch { return; } // All requested collections are still missing.
    if (version !== revision) return;
    const searches = await Promise.allSettled(collections.map(collection => client.search(query, { filters: { collection } })));
    if (version !== revision) return;
    missingCollections = [];
    searches.forEach((outcome, i) => {
      if (outcome.status === "fulfilled") pending.push(...outcome.value.results);
      else missingCollections.push(collections[i]);
    });
    if (missingCollections.length === collections.length && !loaded && !failed.length && !pending.length) {
      // A failed initialization is terminal for this Pagefind instance.
      clientPromise = null;
      await client.destroy();
    }
  }

  function report() {
    const incomplete = missingCollections.length > 0 || failed.length > 0;
    retry.hidden = !incomplete;
    loadMore.hidden = !pending.length;
    const total = loaded + failed.length + pending.length;
    const workCount = groups.size - (groups.has("site-guides") ? 1 : 0);
    const works = workCount ? " in " + workCount + (workCount === 1 ? " work" : " works") : "";
    const guides = groups.has("site-guides") ? (workCount ? " and site guides" : " in site guides") : "";
    const count = total ? matchesShown.toLocaleString() + " matching sections" + works + guides +
      ". " + loaded + " of " + total + " matching pages loaded." : "";
    status.textContent = incomplete ? "Search incomplete. " + count + (count ? " " : "") +
      "Some search data could not be loaded. Retry to finish." : count || "No matching passages.";
  }

  async function load(version, recover) {
    if (!query || version !== revision) return;
    loadMore.disabled = retry.disabled = true;
    try {
      if (recover && missingCollections.length) await collectPages(version);
      if (version !== revision) return;
      const batch = recover && failed.length ? failed.splice(0, 8) : pending.splice(0, 8);
      const fragments = await Promise.allSettled(batch.map(async hit => {
        const fragment = await hit.data();
        return { fragment, matches: passageMatches(fragment) };
      }));
      if (version !== revision) return;
      fragments.forEach((outcome, i) => {
        if (outcome.status === "fulfilled") {
          showEdition(outcome.value.fragment, outcome.value.matches);
          loaded++;
        } else failed.push(batch[i]);
      });
    } finally {
      if (version === revision) {
        report();
        loadMore.disabled = retry.disabled = false;
      }
    }
  }

  function schedule(immediate) {
    clearTimeout(timer);
    const nextQuery = input.value.trim();
    if (immediate && query === nextQuery && !retry.hidden) {
      if (!retry.disabled) return load(revision, true);
      return;
    }
    query = nextQuery;
    const version = ++revision;
    results.replaceChildren();
    groups.clear();
    missingCollections = ["editions", "guides"];
    failed = [];
    pending = [];
    loaded = 0;
    matchesShown = 0;
    loadMore.hidden = retry.hidden = true;
    status.textContent = query ? "Searching…" : "";
    const url = new URL(location.href);
    if (query) url.searchParams.set("q", query);
    else url.searchParams.delete("q");
    history.replaceState(null, "", url);
    if (immediate) return load(version, true);
    else timer = setTimeout(() => load(version, true), 300);
  }

  if (location.protocol === "file:") {
    input.disabled = true;
    form.querySelector("button").disabled = true;
    status.textContent = "Open the corpus through a local HTTP server or the published site to search.";
    return;
  }
  form.addEventListener("submit", event => { event.preventDefault(); return schedule(true); });
  input.addEventListener("input", () => schedule(false));
  retry.addEventListener("click", () => load(revision, true));
  loadMore.addEventListener("click", () => load(revision, false));
  input.value = new URLSearchParams(location.search).get("q") || "";
  if (input.value) schedule(true);
}

if (typeof document !== "undefined") {
  const form = document.getElementById("corpus-search-form");
  if (form) bindSearch(form);
}
