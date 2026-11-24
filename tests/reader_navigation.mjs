import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { runInNewContext } from "node:vm";

const { catalog, earlier, alternate, alias } = JSON.parse(await readFile(process.argv[2], "utf8"));
const script = await readFile(new URL("../site/static/reader.js", import.meta.url), "utf8");
const css = await readFile(new URL("../site/static/style.css", import.meta.url), "utf8");
assert.match(css, /\.study-shell\[data-text-layer="diplomatic"\] \.english-body\s*{\s*display: none/);
assert.match(css, /@media \(max-width: 850px\)/);

class Element extends EventTarget {
  constructor(attrs = {}) {
    super();
    this.attrs = { ...attrs };
    this.id = attrs.id;
    const classes = new Set();
    this.classList = { contains: name => classes.has(name), add: name => classes.add(name), remove: name => classes.delete(name) };
  }
  getAttribute(key) { return this.attrs[key] ?? null; }
  hasAttribute(key) { return Object.hasOwn(this.attrs, key); }
  setAttribute(key, value) { this.attrs[key] = value; }
  removeAttribute(key) { delete this.attrs[key]; }
  click() { this.dispatchEvent(new Event("click", { cancelable: true })); }
}
const storage = new Map();
const localStorage = { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value) };

function openPage(page, { width = 1280, hash = "" } = {}) {
  const config = page?.config;
  const window = new EventTarget();
  const location = new URL(config?.readingPath || "index.html", "https://reader.test/corpus/");
  location.hash = hash;
  window.location = location;
  window.innerWidth = width;
  window.innerHeight = width < 500 ? 844 : 800;
  window.TC_WORK = config && { ...config };
  window.history = { replaceState: (_, __, url) => { location.href = url; } };
  const frames = [];
  window.requestAnimationFrame = callback => frames.push(callback);
  const flush = () => { while (frames.length) frames.shift()(); };
  const document = new EventTarget();
  const shell = new Element();
  const modes = (page?.modes || []).map(mode => new Element({ "data-reader-mode": mode }));
  const layers = (page?.layers || []).map(layer => new Element({ "data-text-layer": layer }));
  let centered;
  const passages = (page?.passages || []).map((id, i) => {
    const element = new Element(config.track === "earlier" ? { id, "data-passage-id": id, "data-segment": "1" } : { id });
    Object.defineProperty(element, "offsetParent", { get: () => shell.getAttribute("data-text-layer") === "diplomatic" ? null : shell });
    element.getBoundingClientRect = () => ({ top: (i - 1) * 450, height: 200 });
    element.scrollIntoView = () => { centered = id; };
    return element;
  });
  const latin = new Element();
  const host = new Element();
  host.hidden = true;
  const selectors = config ? {
    "#study-reader": shell, "[data-study-pane='latin']": latin,
    "#rt-copy-link": new Element(), "#rt-copy-cite": new Element(),
  } : { "#continue-reading": host, "#resume-editions": { textContent: JSON.stringify(catalog) } };
  document.documentElement = { scrollHeight: 2200, clientHeight: window.innerHeight, scrollTop: 700 };
  document.querySelector = selector => selectors[selector] || null;
  document.querySelectorAll = selector => {
    if (selector === "[data-reader-mode]") return modes;
    if (selector === "button[data-text-layer]") return layers;
    if (selector === ".english-body [data-passage-id]") return config?.track === "earlier" ? passages : [];
    if (selector === ".english-body [id^='p-t4b-']") return config?.track === "trithemius-4b" ? passages : [];
    return [];
  };
  document.getElementById = id => passages.find(element => element.id === id) || null;
  runInNewContext(script, { document, window, localStorage, URL, CustomEvent, setTimeout: () => {} });
  window.dispatchEvent(new Event("load"));
  flush();
  return {
    shell, latin, host,
    mode: name => { modes.find(el => el.getAttribute("data-reader-mode") === name).click(); flush(); },
    layer: name => layers.find(el => el.getAttribute("data-text-layer") === name),
    scrollLatin() { window.dispatchEvent(new Event("wheel")); window.dispatchEvent(new Event("scroll")); flush(); },
    centered: () => centered, location,
  };
}

for (const width of [390, 1280]) {
  storage.clear();
  const target = earlier.passages[1];
  const reader = openPage(earlier, { width, hash: target });
  reader.mode("study");
  reader.layer("diplomatic").click();
  assert.equal(reader.latin.hidden, false);
  reader.scrollLatin();
  reader.mode("read");
  assert.equal(reader.shell.getAttribute("data-text-layer"), "normalized");
  assert.equal(reader.layer("normalized").getAttribute("aria-pressed"), "true");
  assert.equal(reader.latin.hidden, true);
  assert.equal(reader.centered(), target);
  assert.equal(reader.location.hash, "#" + target);
  reader.mode("study");
  reader.layer("diplomatic").click();
  assert.equal(reader.shell.getAttribute("data-text-layer"), "diplomatic");
}

storage.clear();
for (const page of [earlier, alternate, alias]) {
  openPage(page);
  const entry = JSON.parse(storage.get("tc-progress-" + page.config.readingPath));
  assert.equal(entry.track, page.config.track);
  assert.equal(entry.id, page.config.id);
  assert.equal(entry.path, page.config.readingPath);
  assert.equal(entry.passage, page.passages[1]);
  const card = openPage().host.innerHTML;
  assert(card.includes('href="' + page.config.readingPath + "?view=read"));
  assert(card.includes("#" + entry.passage + '"'));
}
assert.deepEqual(JSON.parse(storage.get("tc-progress-idx")), [alias, alternate, earlier].map(p => p.config.readingPath));

// An explicit alternate citation can lie above the viewport's inferred reading
// position. Keep it until the reader deliberately scrolls.
for (const page of [alternate, alias]) {
  const target = page.passages[0];
  const reader = openPage(page, { hash: target });
  const saved = () => JSON.parse(storage.get("tc-progress-" + page.config.readingPath)).passage;
  assert.equal(saved(), target);
  reader.scrollLatin();
  assert.equal(saved(), page.passages[1]);
}

function legacy(entry) {
  storage.clear();
  storage.set("tc-progress-idx", JSON.stringify([entry.id]));
  storage.set("tc-progress-" + entry.id, JSON.stringify({ v: 2, frac: 0.4, t: Date.now(), ...entry }));
  return openPage().host.innerHTML;
}
const oldStandard = legacy({ id: earlier.config.id, passage: earlier.passages[1] });
assert(oldStandard.includes(earlier.config.readingPath));
assert(!oldStandard.includes(alternate.config.readingPath));
assert(legacy({ id: alias.config.id }).includes(alias.config.readingPath + "?resume=0.4"));
const ambiguous = legacy({ id: earlier.config.id });
assert(ambiguous.includes("Choose a translation"));
assert([earlier, alternate].every(page => ambiguous.includes(page.config.readingPath + "?resume=0.4")));
console.log("Reader mode, independent edition positions, alias and legacy bookmarks passed.");
