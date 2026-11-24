"""Catalogue alias, shared-scan correction and offline citation regressions."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml
from lxml import html

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_editorial_ledger
import build_site
import validate_release


class CatalogueProvenance(unittest.TestCase):
    def test_catalogue_groups_aliases_and_retains_every_record_link(self):
        works = [work for work in build_site.load_manifest()["works"] if not work["skip"]]
        texts = build_site.build_texts(works)
        sources = [source for text in texts for source in text["sources"]]
        records = [record["id"] for source in sources for record in source["records"]]
        self.assertEqual((len(texts), len(sources), len(records)), (29, 45, 47))
        self.assertCountEqual(records, [work["id"] for work in works])
        groups = {tuple(sorted(record["prdl"] for record in source["records"]))
                  for source in sources if len(source["records"]) > 1}
        self.assertEqual(groups, {("24364", "70284"), ("24371", "24372")})
        self.assertIn("23 texts (41 records from 39 sources)", build_editorial_ledger.summary())
        enriched = [build_site.enrich_work(work) for work in works]
        texts = build_site.build_texts(enriched)
        sections = build_site.genre_sections(texts, build_site.load_clusters())
        catalogue = html.fromstring(build_site.build_works_page(build_site.make_env(), enriched, texts, sections))
        self.assertIn("41 records from 39 sources", " ".join(catalogue.xpath("string(//section[1]/p[1])").split()))
        for record in ("24364", "70284", "24371", "24372"):
            self.assertTrue(catalogue.xpath('//a[text()=$label and starts-with(@href,$prefix)]',
                                            label="PRDL " + record, prefix="works/prdl-" + record + "_"))

    def test_revised_headnotes_keep_their_published_fragment(self):
        aliases = build_site.publication_guard.read_input("headnote-anchors.json")
        self.assertTrue(aliases)
        for source, changes in aliases.items():
            with self.subTest(source=source):
                rendered = html.fragment_fromstring(build_site.render_headnote(ROOT / source), create_parent=True)
                for published in changes.values():
                    self.assertEqual(len(rendered.xpath("//*[@id=$anchor]", anchor=published)), 1)

    def test_offline_schema_rejects_old_book_location(self):
        valid = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
        result = validate_release.Result([], [])
        with patch("socket.socket.connect", side_effect=AssertionError("unexpected network access")):
            validate_release.validate_yaml_cff(result)
            self.assertEqual(result.errors, [])
            with tempfile.TemporaryDirectory() as scratch:
                path = Path(scratch) / "CITATION.cff"
                record = yaml.safe_load(valid)
                record["references"][0]["location"] = "Lawrence, Kansas"
                path.write_text(yaml.safe_dump(record, allow_unicode=True), encoding="utf-8")
                validate_release.validate_yaml_cff(result, path)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("references[0].location", result.errors[0])

    def test_archive_citation_and_institutional_rights(self):
        cff = yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8"))
        archive = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))
        creator = cff["authors"][0]
        self.assertEqual(archive["creators"][0]["name"], f"{creator['family-names']}, {creator['given-names']}")
        self.assertEqual(archive["title"], cff["title"])
        self.assertEqual(archive["description"], cff["abstract"].strip())
        urls = {item["relation"]: item["identifier"] for item in archive["related_identifiers"]}
        self.assertEqual(urls["isSupplementTo"], cff["repository-code"])
        self.assertEqual(urls["isDocumentedBy"], cff["url"])
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        for prefix, canvas in (("prdl-70291_", "5"), ("prdl-24373_", "9")):
            folder = next((ROOT / "data/translation_disagreements").glob(prefix + "*"))
            register = json.loads((folder / "facsimiles/images.json").read_text(encoding="utf-8"))
            for rights_url in register[canvas]["rights"]:
                self.assertIn(rights_url, archive["notes"])
                self.assertIn(rights_url, license_text)
                evidence_credit = (folder / "facsimiles/README.md").read_text(encoding="utf-8")
                self.assertIn(rights_url, evidence_credit)
                if prefix == "prdl-70291_":
                    web_credit = ROOT / "site/static/images" / folder.name / "RIGHTS.txt"
                    self.assertIn(rights_url, web_credit.read_text(encoding="utf-8"))
