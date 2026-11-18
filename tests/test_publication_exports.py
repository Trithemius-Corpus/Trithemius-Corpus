"""Regression checks for complete and single-work edition publication."""
from __future__ import annotations

import json
import hashlib
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_publication_exports as exports
from validate_publication_exports import validate_exports


class EditionRevisions(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        self.out = self.root / "editions"
        source = Path(exports.__file__).resolve().parents[1]
        for name in ("site/static/publication.css", "site/static/publication-epub.css", "data/publication/export-history.json"):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((source / name).read_bytes())
        self.works = ("poem", "sigilla")
        attribution = ({"author": "Hucbald of Saint-Amand", "transmitted_by": "Johannes Trithemius"},
                       {"author": None, "attributed_to": "Johannes Trithemius"})
        (self.root / "manifest.json").write_text(json.dumps({"works": [{"id": w} for w in self.works]}))
        for work, authors in zip(self.works, attribution):
            work_dir = self.root / "works" / work
            work_dir.mkdir(parents=True)
            meta = {"id": work, "title": work, "attribution": authors, "source": {"url": "https://example.org/book"}}
            (work_dir / "metadata.json").write_text(json.dumps(meta))
            (work_dir / "intro.md").write_text("Preface.\n")
            (work_dir / "english.md").write_text("Reading text.\n")
        env = patch.dict(os.environ, {"SOURCE_DATE_EPOCH": "", "TRITHEMIUS_EDITION_VERSION": ""})
        env.start()
        self.addCleanup(env.stop)

    def build(self, selected=None):
        return exports.build_editions(selected, root=self.root, out=self.out)

    def index(self):
        return json.loads((self.out / "index.json").read_text(encoding="utf-8"))

    def test_single_revision_updates_index_and_keeps_other_rows_and_files(self):
        original, unrelated = self.build()
        self.assertEqual(validate_exports(self.root, self.out), [])
        target = self.root / "works" / self.works[0]
        (target / "english.md").write_text("Corrected reading text.\n")
        (target / "ERRATA.md").write_text("## 2027-01-02 — Corrected reading\n", encoding="utf-8")
        self.assertTrue(any("canonical source" in e for e in validate_exports(self.root, self.out)))
        with patch.dict(os.environ, {"TRITHEMIUS_EDITION_VERSION": "v2"}):
            revised, = self.build([self.works[0]])
        self.assertNotEqual(revised["epub_sha256"], original["epub_sha256"])
        self.assertNotEqual(revised["edition_version"], original["edition_version"])
        self.assertEqual(revised["modified"], "2027-01-02T00:00:00Z")
        self.assertTrue(revised["edition_version"].startswith("v2-2027-01-02."))
        self.assertEqual(self.index()["works"], [revised, unrelated])
        self.assertEqual(validate_exports(self.root, self.out), [])
        with patch.dict(os.environ, {"TRITHEMIUS_EDITION_VERSION": "v2"}):
            self.assertEqual(self.build([self.works[0]]), [revised])

    def test_corrupt_or_unindexed_files_rollback_a_partial_build(self):
        old, unrelated = self.build()
        epub = self.out / unrelated["epub"]
        epub.write_bytes(epub.read_bytes() + b"changed")
        original_index = (self.out / "index.json").read_bytes()
        with patch.dict(os.environ, {"TRITHEMIUS_EDITION_VERSION": "different"}):
            with self.assertRaisesRegex(ValueError, "epub_sha256"):
                self.build([old["id"]])
        self.assertEqual((self.out / "index.json").read_bytes(), original_index)
        self.assertEqual(exports.artifact_errors(self.out, old), [])
        self.assertTrue(any("epub_sha256" in e for e in validate_exports(self.root, self.out, [unrelated["id"]])))
        self.build([unrelated["id"]])
        (self.out / "epub/unlisted.epub").write_bytes(b"unlisted")
        self.assertTrue(any("Unindexed" in e for e in validate_exports(self.root, self.out)))

    def test_stale_digests_and_missing_index_rows_fail_single_validation(self):
        row, = self.build([self.works[0]])
        self.assertEqual(validate_exports(self.root, self.out, [row["id"]]), [])
        self.assertTrue(any("missing from" in e for e in validate_exports(self.root, self.out, [self.works[1]])))
        index = self.index()
        index["works"][0]["epub_sha256"] = "0" * 64
        (self.out / "index.json").write_text(json.dumps(index))
        self.assertTrue(any("epub_sha256" in e for e in validate_exports(self.root, self.out, [row["id"]])))

    def test_known_history_cannot_be_backdated(self):
        with patch.dict(os.environ, {"SOURCE_DATE_EPOCH": "1"}):
            with self.assertRaisesRegex(ValueError, "predates"):
                self.build()
        self.assertFalse(self.out.exists())

    def test_partial_build_from_legacy_index_preserves_unselected_file_bytes(self):
        first, second = self.build()
        fields = ("id", "title", "epub", "print", "epub_sha256", "source")
        old_index = {"schema_version": "1.0", "edition_version": "2026-07-12",
                     "modified": "2026-07-12T00:00:00Z",
                     "works": [{k: record[k] for k in fields} for record in (first, second)]}
        (self.out / "index.json").write_text(json.dumps(old_index))
        with patch.dict(os.environ, {"TRITHEMIUS_EDITION_VERSION": "revised"}):
            revised, = self.build([first["id"]])
        self.assertEqual(self.index()["works"][0], revised)
        legacy = self.index()["works"][1]
        self.assertTrue(legacy["legacy"])
        self.assertEqual(legacy["epub_sha256"], second["epub_sha256"])
        self.assertEqual(legacy["print_sha256"], second["print_sha256"])
        self.assertEqual(validate_exports(self.root, self.out, [first["id"]]), [])
        self.assertTrue(any("legacy edition" in e for e in validate_exports(self.root, self.out)))
        self.build([second["id"]])
        self.assertEqual(validate_exports(self.root, self.out), [])

    def test_rehashed_file_with_wrong_package_role_and_identifier_fails(self):
        row, = self.build([self.works[0]])
        path = self.out / row["epub"]
        with zipfile.ZipFile(path) as archive:
            files = {name: archive.read(name).decode("utf-8") for name in archive.namelist() if name != "mimetype"}
        opf = files["EPUB/package.opf"].replace(">oth</meta>", ">trc</meta>")
        files["EPUB/package.opf"] = opf.replace(row["identifier"], row["identifier"] + "-stale")
        exports.write_epub(path, files)
        index = self.index()
        index["works"][0]["epub_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        (self.out / "index.json").write_text(json.dumps(index))
        errors = validate_exports(self.root, self.out, [row["id"]])
        for reason in ("package identifier", "source role", "revision fingerprint"):
            self.assertTrue(any(reason in err for err in errors), errors)


if __name__ == "__main__":
    unittest.main()
