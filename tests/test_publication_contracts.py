import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from lxml import html

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_t4b_editions as assembler
import build_site
import build_work_artifacts as standard
from edition_corrections import history
from edition_metadata import editorial_record
from publication_guard import staged_directory, undo_migrations
from publication_inventory import canonical_inventory
from validate_edition_contracts import restored_passages

class PublicationContracts(unittest.TestCase):
    def test_same_day_revisions_require_contiguous_explicit_sequence(self):
        from tempfile import TemporaryDirectory
        from edition_corrections import recorded_ledgers

        with TemporaryDirectory() as folder:
            root = Path(folder)
            base = root / "data/translation_disagreements/sample"
            (base / "revisions").mkdir(parents=True)
            data = {"date": "2026-11-23", "human_review": "none_documented"}
            (base / "corrections.json").write_text(json.dumps(data))
            second = base / "revisions/2026-11-23_02.json"
            for number in (None, 3, True):
                second.write_text(json.dumps({**data, **({"sequence": number} if number is not None else {})}))
                with self.assertRaisesRegex(ValueError, "out of order"):
                    recorded_ledgers(root, "sample", "corrections")
            second.write_text(json.dumps({**data, "sequence": 2}))
            self.assertEqual(len(recorded_ledgers(root, "sample", "corrections")), 2)

    def test_retiring_an_early_note_preserves_a_later_annotation_bookmark(self):
        from passage_model import identify_passages

        block = '<!--PASSAGE-SEG:24--><p><span class="anno anno-unclear">[unclear]</span> letters</p>'
        retired = frozenset(("a-en-0024-0001-001", "a-en-0024-0001-002"))
        markup, _, annotations = identify_passages(block, "sample", retired_annotations=retired)
        self.assertEqual([a["html_id"] for a in annotations], ["a-en-0024-0001-003"])
        self.assertIn('id="a-en-0024-0001-003"', markup)

    def test_restored_paragraphs_precede_the_original_following_heading(self):
        body = html.fromstring('<section><p id="p-t4b-a">One.</p><p id="p-t4b-b">Two.</p>'
                               '<h3 id="p-t4b-c">Original heading</h3></section>')
        change = {"item_id": "omission", "before": "Original heading",
                  "after": "One.\n\nTwo.\n\nOriginal heading", "insert_before": "p-t4b-c",
                  "added_passages": ["p-t4b-a", "p-t4b-b"]}
        self.assertEqual(restored_passages(body, change), {"p-t4b-a": "One.", "p-t4b-b": "Two."})
        change["added_passages"].reverse()
        with self.assertRaisesRegex(ValueError, "out of position"):
            restored_passages(body, change)

    def test_failed_render_keeps_readable_edition_and_retry_can_finish(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / "dist"
            target.mkdir()
            page = target / "work.html"
            page.write_text("original")
            with self.assertRaisesRegex(ValueError, "bad render"):
                with staged_directory(target, seed=True) as stage:
                    (stage / page.name).write_text("incomplete")
                    raise ValueError("bad render")
            self.assertEqual(page.read_text(), "original")
            with staged_directory(target, seed=True) as stage:
                (stage / page.name).write_text("verified")
            self.assertEqual(page.read_text(), "verified")

    def test_other_writer_cannot_replace_active_publication(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / "dist"
            target.mkdir()
            with staged_directory(target, seed=True):
                with self.assertRaises(OSError):
                    with staged_directory(target / "editions", seed=False, lock_target=target):
                        self.fail("competing writer acquired the site lock")

    def test_migration_only_accepts_recorded_new_wording(self):
        entry = {"id": "paragraph", "before": "old", "after": "new", "reason": "scan correction"}
        self.assertEqual(undo_migrations({"paragraph": "new"}, [entry], ""), {"paragraph": "old"})
        with self.assertRaises(ValueError):
            undo_migrations({"paragraph": "different"}, [entry], "")

    def test_partial_machine_audit_never_displays_as_complete(self):
        for graded, total in ((38, 40), (262, 268)):
            meta = {"id": "sample", "chunks_total": total, "chunks_graded": graded}
            self.assertEqual(editorial_record(meta, "earlier", {})["automated_qa"], "sampled-machine-audit")
            meta["chunks_graded"] = total
            self.assertEqual(editorial_record(meta, "earlier", {})["automated_qa"], "full-machine-audit")

    def test_both_tracks_in_sitemap_and_stale_canonical_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            base = "https://example.org/corpus/"
            (root / "works").mkdir()
            paths = ("works/w.html", "works/w-trithemius-4b.html", "search.html")
            for path in paths:
                robots = '<meta name="robots" content="noindex,follow">' if path == "search.html" else ""
                (root / path).write_text(f'<head><link rel="canonical" href="{base}{path}">{robots}</head>')
            self.assertEqual(canonical_inventory(root, base), sorted(base + p for p in paths[:2]))
            (root / paths[1]).write_text((root / paths[0]).read_text())
            with self.assertRaisesRegex(ValueError, "canonical"):
                canonical_inventory(root, base)

    def test_reassembly_from_original_chunks_replays_all_corrected_t4b_editions(self):
        for meta in sorted((ROOT / "works-t4b").glob("*/metadata.json")):
            if json.loads(meta.read_text(encoding="utf-8")).get("ai_corrections"):
                with self.subTest(work=meta.parent.name):
                    self.check_reassembly(meta.parent)

    def test_standard_reassembly_preserves_page_turn_and_archived_title_page(self):
        works = build_site.load_manifest()["works"]
        for prefix in ("prdl-24383_", "prdl-70292_"):
            work = next(w for w in works if w["id"].startswith(prefix))
            with self.subTest(work=work["id"]):
                self.check_standard_reassembly(work)

    def check_standard_reassembly(self, work):
        wid = work["id"]
        original = ROOT / "works" / wid
        with TemporaryDirectory() as directory:
            scratch = Path(directory)
            destination = scratch / "works" / wid
            shutil.copytree(original, destination)
            corpus = scratch / "corpus" / wid
            raw_chunks = corpus / "translations/public/full"
            shutil.copytree(original / "chunks", raw_chunks)
            for record in history(ROOT, wid)[0]["files"]:
                if record["path"].startswith(f"works/{wid}/chunks/"):
                    shutil.copyfile(ROOT / record["before_path"], raw_chunks / Path(record["path"]).name)
            source = corpus / "full.txt"
            blocks = [{"text": s["latin"]} for s in build_site._parse_latin_artifact(original / "latin-ocr.txt")]
            with (patch.object(standard, "CORPUS", scratch / "corpus"),
                  patch.object(standard, "WORKS", scratch / "works"),
                  patch.object(standard, "choose_source_records", return_value=(source, blocks, [(source, blocks)]))):
                standard.build_one(work)
                for p in [original / "english.md", original / "ERRATA.md", *original.glob("chunks/full_chunk_*.md")]:
                    self.assertEqual(p.read_text(encoding="utf-8"), (destination / p.relative_to(original)).read_text(encoding="utf-8"))
                # An unrelated substantive edit invalidates the separately edited master.
                (raw_chunks / "full_chunk_0004.md").write_text("Unrecorded new text", encoding="utf-8")
                with self.assertRaises(ValueError):
                    standard.build_one(work)
                self.assertEqual((destination / "english.md").read_text(encoding="utf-8"),
                                 (original / "english.md").read_text(encoding="utf-8"))

    def check_reassembly(self, original):
        wid = original.name
        prdl = wid.split("_", 1)[0]
        with TemporaryDirectory() as directory:
            scratch = Path(directory)
            work = scratch / "corpus" / wid / "translations"
            chunks = work / assembler.LANE / "full"
            shutil.copytree(original / "chunks", chunks)
            first_snapshot = {}
            for ledger in history(ROOT, wid):
                for file in ledger["files"]:
                    if file["path"].startswith(f"works-t4b/{wid}/chunks/"):
                        first_snapshot.setdefault(Path(file["path"]).name, ROOT / file["before_path"])
            for name, source in first_snapshot.items():
                shutil.copyfile(source, chunks / name)
            ocr = work / "_reocr" / assembler.OCR_ENGINE
            ocr.mkdir(parents=True)
            shutil.copyfile(original / "latin-ocr.txt", ocr / "full.txt")
            with patch.object(assembler, "CORPUS", scratch / "corpus"), patch.object(assembler, "OUT_ROOT", scratch / "editions"):
                self.assertTrue(assembler.assemble_work(prdl, {}, None))
                built = assembler.OUT_ROOT / wid
                for p in [original / "english.md", original / "ERRATA.md", *original.glob("chunks/full_chunk_*.md")]:
                    self.assertEqual(p.read_text(encoding="utf-8"), (built / p.relative_to(original)).read_text(encoding="utf-8"))
                meta = json.loads((built / "metadata.json").read_text(encoding="utf-8"))
                self.assertEqual(meta["ai_corrections"], json.loads((original / "metadata.json").read_text(encoding="utf-8"))["ai_corrections"])
                corrected = chunks / next(iter(first_snapshot))
                neighbours = [p for p in sorted(chunks.glob("full_chunk_*.md")) if p.name not in first_snapshot]
                for bad in [corrected, *neighbours[:1]]:
                    with self.subTest(changed_chunk=bad.name):
                        saved = bad.read_bytes()
                        bad.write_text("Unknown edited source", encoding="utf-8")
                        with self.assertRaises(ValueError):
                            assembler.assemble_work(prdl, {}, None)
                        self.assertEqual((built / "english.md").read_bytes(), (original / "english.md").read_bytes())
                        bad.write_bytes(saved)


if __name__ == "__main__":
    unittest.main()
