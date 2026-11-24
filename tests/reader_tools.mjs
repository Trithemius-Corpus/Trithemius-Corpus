import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { passageMatches } from "../site/static/corpus-search.mjs";

const script = await readFile(new URL("../site/static/glossary.js", import.meta.url));
const { glossaryFor, glossaryMatches } = await import("data:text/javascript;base64," + script.toString("base64"));
const { entries } = JSON.parse(await readFile(process.argv[2], "utf8"));
const monastic = glossaryFor(entries, "monastic-reform");
const crypto = glossaryFor(entries, "crypto-occult");

function terms(sentence, dictionary) {
  return glossaryMatches(sentence, dictionary).map(hit => sentence.slice(hit.start, hit.end));
}
assert.deepEqual(terms("(religiónem), diſciplinam regularem! religiosamente", monastic),
  ["religiónem", "diſciplinam regularem"]);
assert.deepEqual(terms("CLAVEM et figuras; figurativus", crypto), ["CLAVEM", "figuras"]);
assert(crypto.byForm.get("clauem").size > 1);
assert(!monastic.byForm.has("orchema"));

const fragment = {
  content: "Editorial note medieval ink pen two words now another passage",
  locations: [7, 1, 4],
  anchors: [
    { id: "note-intro-abc", location: 0 }, { id: "p-en-0002-0003", location: 2 },
    { id: "a-en-0002-0003-001", location: 3 }, { id: "p-en-0003-0001", location: 7 },
  ],
  meta: { view: "translation", workGroup: "in praise of scribes" },
};
const matches = passageMatches(fragment);
assert.deepEqual(matches.map(m => m.id), ["note-intro-abc", "p-en-0002-0003", "p-en-0003-0001"]);
assert.equal(matches[0].label, "English · Editorial introduction");
assert.equal(matches[1].label, "English · Passage 2.3");
assert.deepEqual(matches[1].excerpt.filter(token => token.hit).map(token => token.word), ["pen"]);
assert(!matches[1].excerpt.some(token => token.word === "now"));

for (const [view, id, target] of [
  ["latin", "latin-seg-1", "seg-1"],
  ["translation", "p-t4b-abc", "p-t4b-abc"],
  ["apparatus", "rendering-full_chunk_0018", "full_chunk_0018"],
]) {
  assert.equal(passageMatches({ ...fragment, meta: { view, workGroup: "w" },
    locations: [0], anchors: [{ id, location: 0 }] })[0].id, target);
}
const guide = passageMatches({ ...fragment, meta: { title: "Methodology" }, locations: [0], anchors: [] });
assert.equal(guide[0].id, "main");
console.log("Genre-sensitive glossary forms, bilingual offsets and edition targets passed.");
