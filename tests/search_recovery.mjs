import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { runInNewContext } from "node:vm";

// Run the packaged Pagefind WASM and its real search / getData worker messages.
// Only the network, DOM nodes and worker's message channel are simulated.
const [runtime, bundle, mode] = process.argv.slice(2);
const indexURL = pathToFileURL(join(runtime, "pagefind.js")).href;
const workerScript = await readFile(join(runtime, "pagefind-worker.js"), "utf8");
globalThis.location = new URL("https://reader.test/corpus/search.html");
globalThis.history = { replaceState() {} };
globalThis.window = globalThis;
globalThis.addEventListener = () => {};
let network;
let workers = 0;
globalThis.fetch = async input => {
  const path = decodeURIComponent(new URL(input, location).pathname);
  const file = path.split("/").slice(path.includes("/fragment/") || path.includes("/index/") || path.includes("/filter/") ? -2 : -1).join("/");
  if (network) network.counts.set(file, (network.counts.get(file) || 0) + 1);
  if (network?.fail && file.startsWith(network.fail) && (!network.failedFile || file === network.failedFile)) {
    network.failedFile = file;
    if (file.startsWith("filter/")) throw new Error("temporary disconnection");
    return new Response("Temporarily unavailable", { status: 503 });
  }
  return new Response(await readFile(join(bundle, file)));
};
if (mode === "worker") {
  globalThis.Worker = class {
    constructor() {
      workers++;
      this.listeners = {};
      const self = {
        addEventListener: (type, listener) => { this.receive = listener; },
        postMessage: data => queueMicrotask(() => this.listeners.message({ data: structuredClone(data) })),
      };
      runInNewContext(workerScript, { self, fetch, TextDecoder, TextEncoder, URL, Request, Response, setTimeout, console });
    }
    addEventListener(type, listener) { this.listeners[type] = listener; }
    postMessage(data) { queueMicrotask(() => this.receive({ data: structuredClone(data) })); }
    terminate() {}
  };
}

class Element {
  constructor() { this.children = []; this.listeners = {}; this.hidden = false; this.textContent = ""; }
  addEventListener(type, fn) { this.listeners[type] = fn; }
  append(...children) { this.children.push(...children); }
  replaceChildren() { this.children = []; }
  emit(type) { return this.listeners[type]({ preventDefault() {} }); }
}

async function page(test) {
  const elements = Object.fromEntries(["corpus-search-form", "corpus-search-status", "corpus-results", "corpus-more", "corpus-retry"]
    .map(id => [id, new Element()]));
  const form = elements["corpus-search-form"];
  const input = new Element();
  form.elements = { q: input };
  form.dataset = { index: indexURL };
  const status = elements["corpus-search-status"];
  const retry = elements["corpus-retry"];
  retry.hidden = elements["corpus-more"].hidden = true;
  globalThis.document = {
    currentScript: null, baseURI: location.href, createElement: () => new Element(),
    querySelector: () => ({ getAttribute: () => "en" }), getElementById: id => elements[id] || null,
  };
  await import("../site/static/corpus-search.mjs?test=" + test);
  return {
    status, retry, results: elements["corpus-results"],
    async search(query) { input.value = query; await form.emit("submit"); },
  };
}

const normal = await page("normal");
await normal.search("scribes");
const baseline = normal.status.textContent.match(/8 of (\d+) matching pages loaded/);
assert(baseline && Number(baseline[1]) > 8);
await normal.search('"saffron zebras orbit Neptune together"');
assert.equal(normal.status.textContent, "No matching passages.");
assert(normal.retry.hidden);

for (const kind of ["index/", "filter/", "fragment/"]) {
  network = { fail: kind, counts: new Map() };
  const ui = await page(kind);
  await ui.search("scribes");
  assert.match(ui.status.textContent, /Search incomplete/);
  assert(!ui.status.textContent.includes("No matching passages"));
  assert.equal(ui.retry.hidden, false);
  const attempts = network.counts.get(network.failedFile);
  assert(attempts >= 1);
  network.fail = "";
  const retained = [...ui.results.children];
  if (kind === "fragment/") {
    assert(ui.status.textContent.includes("7 of " + baseline[1] + " matching pages loaded"));
    assert(retained.length > 0);
  }
  if (kind === "filter/") await ui.search("scribes"); // Enter also retries a pending search.
  else await ui.retry.emit("click");
  assert(network.counts.get(network.failedFile) > attempts);
  assert.equal(ui.retry.hidden, true);
  assert(ui.status.textContent.includes("8 of " + baseline[1] + " matching pages loaded"));
  assert(retained.every(section => ui.results.children.includes(section)));
}
assert.equal(workers > 0, mode === "worker");
console.log("Search recovery passed using the Pagefind " + mode + " runtime.");
