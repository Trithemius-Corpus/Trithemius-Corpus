"""Regressions for the first scan-checked Frankfurt cipher trace."""
import csv
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from lxml import html

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_cipher_trace
import scan_evidence


CLAVIS = "prdl-70281_clavis-generalis-triplex-in-libros-steganographicos"


def cipher_chunk(work, chunk):
    path = ROOT / "data/publication/apparatus" / f"{work}.json"
    chunks = json.loads(path.read_text(encoding="utf-8"))["cipher-key"]["chunks"]
    return html.fromstring(next(c["html"] for c in chunks if c["name"] == chunk))


class PrintedCipherTests(unittest.TestCase):
    def test_modus_ii_printed_pairs_and_retained_transcription(self):
        trace = build_cipher_trace.load_and_compute()
        pairs = "ax bz ca db ec fd ge hf ig kh li mk nl om pn qo rp sq tr vs xt zv".split()
        self.assertEqual(pairs, trace["printed_substitution_pairs"])
        table = cipher_chunk(CLAVIS, "full_chunk_0113").xpath(".//table")[0]
        self.assertEqual(pairs, ["".join(row.xpath("td/code/text()")).lower()
                                 for row in table.xpath("tbody/tr")])
        self.assertEqual(trace["facsimile"]["printed_page"], 57)
        self.assertEqual(trace["facsimile"]["provider_image"], 249)
        self.assertEqual(trace["facsimile"]["corpus_page"], 251)
        computed = trace["computed"]
        self.assertEqual(computed["cover_sample_initials"], "gafzgbc")
        self.assertEqual(computed["extracted"], "gafzgbcpgafhmksmlqrsibxlvsskgrgqbseqetpmgr")
        self.assertEqual(computed["decoded"], "ichbiderichkomvonstvldanzvvmitisdvgsgxroit")
        expected = trace["intentio"]["normalized_letters"]
        self.assertEqual((len(computed["decoded"]), len(expected)), (42, 45))
        self.assertEqual(next(i for i, (a, b) in enumerate(zip(computed["decoded"], expected), 1) if a != b), 6)
        with TemporaryDirectory() as directory:
            build_cipher_trace.publish(trace, Path(directory))
            with (Path(directory) / "modus-ii.tsv").open(encoding="utf-8", newline="") as data:
                rows = list(csv.DictReader(data, delimiter="\t"))
            self.assertEqual("".join(row["cipher"] for row in rows), computed["extracted"])
            self.assertEqual("".join(row["decoded"] for row in rows), computed["decoded"])

    def test_full_witness_pages_publish_without_a_previous_site(self):
        with TemporaryDirectory() as directory:
            out = Path(directory)
            scan_evidence.publish_cited_pages(ROOT, out)
            for work, canvas, corpus_page in ((CLAVIS, 248, 250), (CLAVIS, 249, 251)):
                source = ROOT / "data/translation_disagreements" / work / "facsimiles" / f"canvas-{canvas:03d}.webp"
                published = out / work / f"page_{corpus_page:03d}.webp"
                self.assertEqual(published.read_bytes(), source.read_bytes())
