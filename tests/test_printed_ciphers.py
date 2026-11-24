"""Regressions for the cipher readings collated against their printed witnesses."""
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
import build_site
import scan_evidence


CAMUEL = "prdl-24395_steganographia-hoc-est-ars-per-occultam-scripturam"
BASEL = "prdl-24390_polygraphiae-libri-vi"
CLAVIS = "prdl-70281_clavis-generalis-triplex-in-libros-steganographicos"


def cipher_chunk(work, chunk):
    path = ROOT / "data/publication/apparatus" / f"{work}.json"
    chunks = json.loads(path.read_text(encoding="utf-8"))["cipher-key"]["chunks"]
    return html.fromstring(next(c["html"] for c in chunks if c["name"] == chunk))


class PrintedCipherTests(unittest.TestCase):
    def test_modus_ii_printed_pairs_letter_line_and_independent_prayer(self):
        trace = build_cipher_trace.load_and_compute()
        earlier = scan_evidence.load(ROOT, CLAVIS, as_of="2026-11-23", sequence=1)
        self.assertIn("clavis-modus-ii-alphabet", earlier)
        self.assertNotIn("clavis-modus-ii-significant-line", earlier)
        self.assertIn("clavis-modus-ii-significant-line",
                      scan_evidence.load(ROOT, CLAVIS, as_of="2026-11-23", sequence=2))
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
        self.assertEqual(computed["extracted"], "gafzgbcpgafhmksmlqrsibxlvskgrgqbseqetpmgr")
        self.assertEqual(computed["decoded"], "ichbiderichkomvonstvldanzvmitisdvgsgxroit")
        self.assertEqual([len(line.split()) for line in trace["cipher_stream"]["printed_lines"]], [35, 6])
        # Ordinary word breaks keep all printed letters visible in reflowable books.
        spaced = " ".join(trace["cipher_stream"]["printed_lines"]).replace("ſ", "s")
        self.assertIn(spaced, (ROOT / "works" / CLAVIS / "english.md").read_text(encoding="utf-8"))
        self.assertEqual(len(trace["cover"]["tokens"]), 85)
        self.assertEqual(computed["cover_initials"], "gafzgbcgafhmcsmlqrslbclvscgpgqbscrqgstnpqn")
        self.assertEqual(computed["comparison"][5], {
            "position": 6, "printed": "b", "decoded": "d", "intended": "t",
            "required_cipher": "r", "cover_word": "bene", "cover_initial": "b",
        })
        eighth = computed["comparison"][7]
        self.assertEqual((eighth["printed"], eighth["cover_word"], eighth["cover_initial"]), ("p", "gaudium", "g"))
        self.assertEqual(len(computed["comparison"]), 45)
        self.assertIsNone(computed["comparison"][41]["printed"])
        self.assertEqual(computed["comparison"][41]["cover_word"], "nos")
        expected = trace["intentio"]["normalized_letters"]
        self.assertEqual((len(computed["decoded"]), len(expected)), (41, 45))
        self.assertEqual(next(i for i, (a, b) in enumerate(zip(computed["decoded"], expected), 1) if a != b), 6)
        with TemporaryDirectory() as directory:
            build_cipher_trace.publish(trace, Path(directory))
            with (Path(directory) / "modus-ii.tsv").open(encoding="utf-8", newline="") as data:
                rows = list(csv.DictReader(data, delimiter="\t"))
            self.assertEqual("".join(row["cipher"] for row in rows), computed["extracted"])
            self.assertEqual("".join(row["decoded"] for row in rows), computed["decoded"])

    def test_numeral_cipher_retains_the_reading_of_each_printed_copy(self):
        for prefix, groups in (
            ("70282", ("cakeihid", "i&kahk", "&kif", "icei&kaib")),
            ("24390", ("cakeihid", "i&kahk", "&kif", "icei&kaib")),
            ("24389", ("a[k?]eihid", "i&kahk", "&[k?]if", "icei&kaib")),
            ("24391", ("cakeibid", "i&kabk", "& kif", "icei&kaib")),
        ):
            for source in [*ROOT.glob(f"works/prdl-{prefix}_*/english.md"),
                           *ROOT.glob(f"works-t4b/prdl-{prefix}_*/english.md")]:
                with self.subTest(source=source):
                    text = source.read_text(encoding="utf-8")
                    self.assertTrue(all(token in text for token in groups))
                    self.assertNotIn("amp;kahk", text)

    def test_camuel_twenty_entries_and_complete_formula(self):
        table = cipher_chunk(CAMUEL, "full_chunk_0010").xpath(".//table")[0]
        expected = [
            ["Orpeniel 10", "Citgara 100", "Daniel 10", "Dobiel 100", "Azimo 10"],
            ["Camyel 100", "Pariel 10", "Omyel 10", "*Nodar 10", "Tediel 0"],
            ["Budiel 10", "Cariel 10", "Asiniel 100", "Phaniel 10", "Moriel 0"],
            ["Elcar 10", "Neriel 10", "Calym 100", "Meras 100", "Tugaros 0"],
        ]
        self.assertEqual([row.xpath("td/text()") for row in table.xpath("tbody/tr")], expected)
        formula = ("Camuel aperoys, melym meuomanial, casmoyn cralti busaco aeli lumar "
                   "photytion theor besamys, aneal Cabelonyr thiamo vesonthy.")
        for track in ("works", "works-t4b"):
            for file in ("english.md", "chunks/full_chunk_0010.md"):
                text = (ROOT / track / CAMUEL / file).read_text(encoding="utf-8")
                self.assertIn(formula, text)
                for row in expected:
                    for cell in row:
                        self.assertIn(cell.removeprefix("*"), text)

    def test_basel_geography_rows_and_reviewed_canvas(self):
        pairs, _ = build_site.load_pairs(BASEL)
        block = next(pair["english"] for pair in pairs if pair["n"] == 44)
        doc = html.fromstring(build_site._chunk_markdown_to_html(block))
        table = next(t for t in doc.xpath(".//table") if "Helvetia" in t.text_content())
        rows = [[cell.text_content() for cell in row.xpath("td")] for row in table.xpath("tbody/tr")]
        q = rows.index(["q", "Galicia", "q", "Belgica"])
        self.assertEqual(rows[q + 1:q + 4], [
            ["r", "Gascony", "r", "Navarre"],
            ["s", "Austrasia", "s", "Luxembourg"],
            ["t", "Gaul", "t", "Majorca"],
        ])
        registry = json.loads((ROOT / "data/publication/reviewed-canvases.json").read_text(encoding="utf-8"))
        self.assertEqual(registry[BASEL]["p-en-0044-0011"],
                         "https://api.digitale-sammlungen.de/iiif/presentation/v2/bsb00029406/canvas/186")

    def test_full_witness_pages_publish_without_a_previous_site(self):
        with TemporaryDirectory() as directory:
            out = Path(directory)
            scan_evidence.publish_cited_pages(ROOT, out)
            for work, canvas, corpus_page in ((CAMUEL, 21, 21), (CLAVIS, 248, 250), (CLAVIS, 249, 251)):
                source = ROOT / "data/translation_disagreements" / work / "facsimiles" / f"canvas-{canvas:03d}.webp"
                published = out / work / f"page_{corpus_page:03d}.webp"
                self.assertEqual(published.read_bytes(), source.read_bytes())
