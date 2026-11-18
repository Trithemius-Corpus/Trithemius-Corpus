import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_t4b_editions as assembler
from edition_corrections import history
from edition_metadata import editorial_record
from publication_guard import staged_directory, undo_migrations
from publication_inventory import canonical_inventory

SCRIBES = "prdl-24362_de-laude-scriptorum-manualium"


class PublicationContracts(unittest.TestCase):
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

    def test_reassembly_from_original_chunks_replays_all_scribes_edits(self):
        original = ROOT / "works-t4b" / SCRIBES
        with TemporaryDirectory() as directory:
            scratch = Path(directory)
            work = scratch / "corpus" / SCRIBES / "translations"
            chunks = work / assembler.LANE / "full"
            shutil.copytree(original / "chunks", chunks)
            first_snapshot = {}
            for ledger in history(ROOT, SCRIBES):
                for file in ledger["files"]:
                    if file["path"].startswith(f"works-t4b/{SCRIBES}/chunks/"):
                        first_snapshot.setdefault(Path(file["path"]).name, ROOT / file["before_path"])
            for name, source in first_snapshot.items():
                shutil.copyfile(source, chunks / name)
            ocr = work / "_reocr" / assembler.OCR_ENGINE
            ocr.mkdir(parents=True)
            shutil.copyfile(original / "latin-ocr.txt", ocr / "full.txt")
            with patch.object(assembler, "CORPUS", scratch / "corpus"), patch.object(assembler, "OUT_ROOT", scratch / "editions"):
                self.assertTrue(assembler.assemble_work("prdl-24362", {}, None))
                built = assembler.OUT_ROOT / SCRIBES
                for p in [original / "english.md", original / "ERRATA.md", *original.glob("chunks/full_chunk_*.md")]:
                    self.assertEqual(p.read_text(encoding="utf-8"), (built / p.relative_to(original)).read_text(encoding="utf-8"))
                meta = json.loads((built / "metadata.json").read_text(encoding="utf-8"))
                self.assertEqual(meta["ai_corrections"], json.loads((original / "metadata.json").read_text(encoding="utf-8"))["ai_corrections"])
                bad = chunks / next(iter(first_snapshot))
                bad.write_text("Unknown edited source", encoding="utf-8")
                with self.assertRaises(ValueError):
                    assembler.assemble_work("prdl-24362", {}, None)
                self.assertEqual((built / "english.md").read_bytes(), (original / "english.md").read_bytes())


if __name__ == "__main__":
    unittest.main()
