"""Check that a partial or stale editorial package cannot pass as a complete review."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_translation_disagreements as b
import context_review
from edition_corrections import history, validate_history
from validate_translation_disagreements import validate_context


class ContextIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = b.DEFAULT_WORK
        cls.inputs = b.ROOT / "data/translation_disagreements" / cls.work
        cls.outputs = b.ROOT / "review/translation-disagreements" / cls.work
        cls.spec = json.loads(b.read(cls.inputs / "review.json"))
        cls.inventory = json.loads(b.read(cls.outputs / "candidates.json"))
        cls.queue = json.loads(b.read(cls.outputs / "queue.json"))

    def test_missing_middle_or_all_declared_context_ledgers_fails_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            parts = root / "data/translation_disagreements" / self.work
            parts.mkdir(parents=True)
            for names in ([], ["context-review-a.json", "context-review-c.json"]):
                with self.subTest(present=names):
                    for name in names:
                        (parts / name).touch()
                    with self.assertRaisesRegex(ValueError, "missing or unexpected"):
                        context_review.assemble(root, self.work, self.spec, self.inventory)

    def test_latest_resolution_preserves_both_sides_of_a_page_turn(self):
        batches = history(b.ROOT, self.work)
        changes = b.current_resolutions(batches)["B-F03"]["changes"]
        self.assertEqual([change["passage"] for change in changes],
                         ["p-en-0009-0005", "p-en-0010-0001"])

    def test_rehashed_candidate_text_is_outside_the_frozen_context_inventory(self):
        inventory = copy.deepcopy(self.inventory)
        inventory["candidates"][0]["earlier_text"] += " altered"
        with self.assertRaisesRegex(ValueError, "different candidate snapshot"):
            context_review.assemble(b.ROOT, self.work, self.spec, inventory)

    def test_contextual_disposition_must_reach_each_candidate(self):
        inventory = copy.deepcopy(self.inventory)
        inventory["candidates"][0]["status"] = "untriaged_lexical_difference"
        with self.assertRaisesRegex(ValueError, "missing or stale contextual coverage"):
            validate_context(self.queue, inventory, self.outputs, self.spec)

    def test_stale_context_html_or_surplus_report_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "context-review.json").write_bytes((self.outputs / "context-review.json").read_bytes())
            (folder / "context-review.html").write_text("<main></main>", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "HTML belongs to a different review snapshot"):
                validate_context(self.queue, self.inventory, folder, self.spec)
            with self.assertRaisesRegex(ValueError, "Unexpected review artifacts"):
                b.reject_stale_outputs(folder, {})

    def test_lost_declared_correction_batch_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / "data/translation_disagreements" / self.work
            base.mkdir(parents=True)
            (base / "review.json").write_bytes((self.inputs / "review.json").read_bytes())
            (base / "corrections.json").write_bytes((self.inputs / "corrections.json").read_bytes())
            with self.assertRaisesRegex(ValueError, "incomplete or unexpected corrections history"):
                history(root, self.work)

    def test_all_recorded_replacements_replay_through_the_dated_batches(self):
        batches = history(b.ROOT, self.work)
        self.assertGreaterEqual(len(batches), 3)
        validate_history(b.ROOT, self.work, batches)
        latest = b.current_resolutions(batches)["scribes-003"]
        self.assertEqual({e["track"] for e in latest["changes"]}, {"earlier", "t4b"})
        self.assertEqual({e["after"] for e in latest["changes"]}, {"my [dipped?] pen trembles again"})
        seed = json.loads(b.read(self.inputs / "benchmark-seed.json"))
        self.assertNotIn("scribes-003", {f["id"] for f in seed["fixtures"]})
        self.assertIn("scribes-003", {f["id"] for f in seed["withheld"]})


if __name__ == "__main__":
    unittest.main()
