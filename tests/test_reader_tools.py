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
import build_search
import build_t4b_pages
import reader_tools
import validate_reader_tools
import passage_model
from lxml import html


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

    def test_corrected_t4b_text_keeps_the_cited_anchor(self):
        def anchor(body):
            return html.fromstring(reader_tools.search_anchors(body, "p-t4b")).get("id")
        before = "<p>Previously cited wording.</p>"
        after = "<p>Revised wording.</p>"
        ids = {anchor(after): anchor(before)}
        self.assertEqual(html.fromstring(reader_tools.search_anchors(after, "p-t4b", ids)).get("id"), anchor(before))
        with self.assertRaisesRegex(ValueError, "no longer renders"):
            reader_tools.search_anchors(before, "p-t4b", ids)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            reader_tools.search_anchors(before + after, "p-t4b", ids)

    def test_reviewed_latin_target_changes_one_passage_and_survives_without_javascript(self):
        pairs = [{"n": 1, "latin": "prima", "english_html": "<p>One</p><p>Two</p>"},
                 {"n": 2, "latin": "secunda", "english_html": "<p>Three</p>"}]
        rule = {"p-en-0001-0002": {"latin_segment": 2, "english_quote": "Two", "latin_quote": "secunda"}}
        marked = "<!--PASSAGE-SEG:1-->" + pairs[0]["english_html"]
        rendered, passages, _ = passage_model.identify_passages(marked, "sample", alignments=rule)
        doc = html.fragment_fromstring(rendered, create_parent=True)
        self.assertEqual([p["text"] for p in passages], ["One", "Two"])
        self.assertEqual([p["segment"] for p in passages], [1, 1])
        self.assertEqual([p["targets"]["parallel"] for p in passages],
                         ["works/sample_parallel.html#seg-1", "works/sample_parallel.html#seg-2"])
        changed = doc.get_element_by_id("p-en-0001-0002")
        self.assertEqual(changed.get("data-latin-segment"), "2")
        self.assertEqual(changed.getnext().xpath("./a/@href"), ["sample_parallel.html#seg-2"])
        parallel = html.fragment_fromstring(passage_model.parallel_source_links(pairs, rule)[0]["english_html"], create_parent=True)
        self.assertEqual(parallel.xpath("./p[@data-segment='2']/text()"), ["Two"])
        self.assertEqual(parallel.xpath("./small/a/@href"), ["#seg-2"])
        pairs[1]["latin"] = "different source"
        with self.assertRaisesRegex(ValueError, "Latin quotation"):
            passage_model.parallel_source_links(pairs, rule)

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
    def test_reader_modes_and_edition_bookmarks(self):
        env = build_site.make_env()
        manifest = build_site.load_manifest()
        works = [w for w in manifest["works"] if not w["skip"]]
        homepage = html.fromstring(build_site.build_index(env, manifest, works, [], []))
        catalog = json.loads(homepage.get_element_by_id("resume-editions").text)
        alternate = build_t4b_pages.load_t4b_works()
        self.assertEqual(len(works), 47)
        self.assertEqual(len(alternate), 27)
        for editions, track in ((works, "earlier"), (alternate, "trithemius-4b")):
            for work in editions:
                path = catalog[work["id"]][track]
                self.assertEqual(path, build_site.reading_path(work))
                self.assertTrue((ROOT / "site/dist" / path).is_file(), path)

        def fixture(markup):
            doc = html.fromstring(markup)
            script = doc.xpath('//script[starts-with(text(),"window.TC_WORK=")]/text()')[0]
            config = json.loads(script.split("=", 1)[1][:-1])
            self.assertEqual(config["readingPath"], catalog[config["id"]][config["track"]])
            ids = doc.xpath('//*[@data-passage-id]/@data-passage-id') or doc.xpath('//*[starts-with(@id,"p-t4b-")]/@id')
            return {"config": config, "passages": ids[:2], "modes": doc.xpath('//*[@data-reader-mode]/@data-reader-mode'),
                    "layers": doc.xpath('//button[@data-text-layer]/@data-text-layer')}

        scribes = next(w for w in works if w["id"].startswith("prdl-24362_"))
        build_site.attach_public_status(scribes)
        build_site.attach_translation_survey(scribes)
        published = html.parse(str(ROOT / "site/dist" / catalog[scribes["id"]]["earlier"]))
        passages = published.xpath('//*[@data-passage-id]')[:2]
        english = "".join(html.tostring(el, encoding="unicode") for el in passages)
        sample = {"catalog": catalog, "earlier": fixture(build_site.build_work(
            env, scribes, english, True, None, passage_count=len(passages)))}
        for key, prefix in (("alternate", "prdl-24362_"), ("alias", "prdl-70283_")):
            work = next(w for w in alternate if w["id"].startswith(prefix))
            sample[key] = fixture(build_t4b_pages.build_t4b_work_page(env, work))
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "navigation.json"
            data.write_text(json.dumps(sample), encoding="utf-8")
            subprocess.run(["node", str(ROOT / "tests/reader_navigation.mjs"), str(data)], check=True)

    @unittest.skipUnless(shutil.which("node"), "Node is needed to exercise the reader JavaScript")
    def test_real_pagefind_failure_recovery(self):
        bundle = ROOT / "site/dist/pagefind"
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            (runtime / "package.json").write_text('{"type":"module"}', encoding="utf-8")
            for name in ("pagefind.js", "pagefind-worker.js"):
                shutil.copyfile(bundle / name, runtime / name)
            validate_reader_tools.check_runtime(runtime)
            for mode in ("main", "worker"):
                with self.subTest(mode=mode):
                    subprocess.run(["node", str(ROOT / "tests/search_recovery.mjs"),
                                    str(runtime), str(bundle), mode], check=True, timeout=60)
            worker = runtime / "pagefind-worker.js"
            build_search.enable_search_recovery(runtime)
            validate_reader_tools.check_runtime(runtime)
            worker.write_text("unexpected runtime", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "pagefind-worker.js"):
                validate_reader_tools.check_runtime(runtime)
            with self.assertRaisesRegex(ValueError, "Pagefind version"):
                build_search.enable_search_recovery(runtime)

    @unittest.skipUnless(shutil.which("node"), "Node is needed to exercise the reader JavaScript")
    def test_javascript_matching_and_destinations(self):
        with tempfile.TemporaryDirectory() as directory:
            reader_tools.publish_glossary(ROOT, Path(directory))
            subprocess.run(["node", str(ROOT / "tests/reader_tools.mjs"),
                            str(Path(directory) / "static/reader-glossary.json")], check=True)


if __name__ == "__main__":
    unittest.main()
