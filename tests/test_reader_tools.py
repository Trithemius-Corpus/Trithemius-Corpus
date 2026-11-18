import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_site
import reader_tools


class ReaderToolsTests(unittest.TestCase):
    def test_repeated_blocks_and_existing_links(self):
        original = '<h3 id="ancient-name">Preface</h3><p>A text</p><p>A text</p>'
        result = reader_tools.search_anchors(original, "p-t4b")
        anchors = re.findall(r'id="(p-t4b-[^"]+)"', result)
        self.assertEqual(len(set(anchors)), 3)
        self.assertIn('id="ancient-name"', result)
        self.assertEqual(anchors[-1], anchors[-2] + "-2")
        inserted = reader_tools.search_anchors("<p>Another text</p>" + original, "p-t4b")
        self.assertTrue(all(key in inserted for key in anchors))

    def test_search_stamp_detects_changed_word_and_survives_checkout(self):
        body = '<meta data-pagefind-filter="collection[content]" content="editions">\n<p>scribes</p>'
        stamped, revision = reader_tools.stamped_page(body)
        self.assertEqual((stamped, revision), reader_tools.stamped_page(stamped.replace("\n", "\r\n")))
        changed, new_revision = reader_tools.stamped_page(stamped.replace("scribes", "prelates"))
        self.assertNotEqual(revision, new_revision)
        self.assertNotIn(revision, changed)

    def test_catalogue_groups_shared_witnesses_across_tracks(self):
        search_witness = build_site.make_env().globals["search_witness"]
        earlier = [w for w in build_site.load_manifest()["works"] if not w["skip"]]
        self.assertEqual(len({search_witness(w)["group"] for w in earlier}), 29)
        saint = next((ROOT / "works-t4b").glob("prdl-70283_*/metadata.json"))
        t4b = json.loads(saint.read_text(encoding="utf-8"))
        earlier_saint = next(w for w in earlier if w["id"] == t4b["standard_witness"])
        self.assertEqual(search_witness(earlier_saint), search_witness(t4b))

    def test_curated_inputs_in_full(self):
        entries = reader_tools.reader_glossary(ROOT)["entries"]
        editorial = [json.loads(line) for line in
                     (ROOT / "data/lexicon/glossary.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        technical = json.loads((ROOT / "site/static/lexicon.json").read_text(encoding="utf-8"))["terms"]
        self.assertEqual([{**e, "source": "editorial"} for e in editorial],
                         [e for e in entries if e["source"] == "editorial"])
        terms = [e for e in entries if e["source"] == "technical"]
        self.assertEqual(len(terms), len(technical))
        self.assertTrue(set(technical) <= {form for e in terms for form in e["forms"]})

    @unittest.skipUnless(shutil.which("node"), "Node is needed to exercise the reader JavaScript")
    def test_javascript_matching_and_destinations(self):
        with tempfile.TemporaryDirectory() as directory:
            reader_tools.publish_glossary(ROOT, Path(directory))
            subprocess.run(["node", str(ROOT / "tests/reader_tools.mjs"),
                            str(Path(directory) / "static/reader-glossary.json")], check=True)


if __name__ == "__main__":
    unittest.main()
