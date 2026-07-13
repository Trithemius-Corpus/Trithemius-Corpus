"""Render the public-facing static site from manifest.json + per-work artifacts.

Output goes to `site/dist/` (open `site/dist/index.html` directly to preview, or
deploy the directory to GitHub Pages).

Pages produced:
  - index.html              landing page (hero + tier summary + suggestions)
  - scoreboard.html         sortable per-work table
  - methodology.html        rendered METHODOLOGY.md
  - LICENSE.html            rendered LICENSE (plain-text wrapped in <pre>)
  - works/<id>.html         per-work page: intro + stitched English + links
  - works/<id>_parallel.html  side-by-side Latin / English viewer

Phase 3 additions:
  - Stitched English is generated on the fly from the shipping `public`
    backend chunks (no committed english.md needed).
  - The parallel viewer re-chunks the Latin `full.txt` with the *same*
    harness chunker that produced the translations (max_chars=4500,
    ocr_cleanup=True), so Latin chunk i aligns with full_chunk_{i:04d}.md.
  - Every work/parallel page carries a print stylesheet and a "Save as
    PDF" button (window.print()). WeasyPrint is not used — it is broken on
    the Windows build box and a browser print is zero-dependency and works
    for every visitor and on GitHub Pages.

Inputs read from the repo root:
  manifest.json
  README.md, METHODOLOGY.md, LICENSE
  works/<id>/intro.md           per-work intro essay (optional)

Working corpus (read-only, for source Latin + translations):
  TRITHEMIUS_WORKING env or E:\\trithemius

Usage:
    python scripts/build_site.py
"""
from __future__ import annotations

import html as html_lib
import csv
import json
import os
import re
import shutil
import sys
from pathlib import Path

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape

sys.path.insert(0, str(Path(__file__).resolve().parent))
import facsimile_map  # noqa: E402  (shared chunk -> source-page mapping)

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "site" / "templates"
STATIC = ROOT / "site" / "static"
OUT = ROOT / "site" / "dist"

MANIFEST = ROOT / "manifest.json"
QUALITY_CSV = ROOT / "data" / "_quality" / "scoreboard_gpt_v3.csv"

WORKING = Path(os.environ.get("TRITHEMIUS_WORKING", r"E:\trithemius"))
CORPUS = WORKING / "data" / "corpus"
HARNESS_SCRIPTS = WORKING / "scripts"
GITHUB_ROOT = "https://github.com/Trithemius-Corpus/Trithemius-Corpus/blob/main"
SITE_BASE = "https://trithemius-corpus.github.io/Trithemius-Corpus/"
CLUSTER_MAPPING = ROOT / "cluster_mapping.json"
FIRST_ENGLISH = ROOT / "data" / "first_english.json"
CIPHERS_MD = ROOT / "docs" / "CIPHERS.md"

SITE_DESCRIPTION = (
    "Open English translations of the Latin works of Johannes Trithemius "
    "(1462–1516): 29 texts across 47 printed editions, each beside its "
    "Latin source, with cipher tables shown against the original page scans."
)

# Human-facing genre labels for the pipeline's genre_cluster slugs, in the
# order the browse index presents them.
GENRE_LABELS = {
    "crypto-occult": "Cryptography & the Occult",
    "monastic-reform": "Monastic Reform",
    "marian-hagiographic": "Marian & Hagiographic",
    "bibliographic": "Bibliography & History",
    "sacerdotal": "The Priestly Life",
    "devotional": "Devotional",
    "apologetic": "Apologetic",
    "verse": "Verse",
}
GENRE_ORDER = list(GENRE_LABELS)

# Browse-time genre corrections. cluster_mapping.json records which anchor set
# a work was TRANSLATED with (a pipeline fact, kept intact); these overrides
# fix the reader-facing shelving where the pipeline assignment mislabels the
# content. prdl-24380's own intro: "the texts themselves are the
# monastic-reform addresses of his abbacy".
DISPLAY_GENRE_OVERRIDES = {
    "prdl-24380_admonitiones-exhortationes-monachos": "monastic-reform",
    # The two 1515 Liber Octo Quaestionum witnesses were pipeline-clustered as
    # bibliographic; the text is the witchcraft/demonology response to
    # Maximilian, which cluster_mapping's own crypto-occult description names.
    "prdl-24381_octo-quaestionum-maximilianum-caesarem": "crypto-occult",
    "prdl-24382_octo-quaestionum-maximilianum-caesarem": "crypto-occult",
}

# Hand-curated landing-page entry points. Title and pitch are authored
# together (the old pick_suggestions() auto-selection once paired a work with
# another work's description). Facts are taken from each work's intro.md.
FEATURED = [
    {"id": "prdl-24390_polygraphiae-libri-vi",
     "pitch": "The first printed book on cryptography in the West (1518). Its "
              "“Ave Maria” cipher hides messages inside pious Latin prayers; "
              "this corpus gives the first continuous English of the body text, "
              "with every cipher table shown beside the original page scan."},
    {"id": "prdl-32287_e-rara_trithemius-sui-ipsius-vindex-sive",
     "pitch": "Trithemius defends himself against the charge of necromancy "
              "after his Steganographia leaked — a point-by-point rebuttal, in "
              "his own voice, of readers who took the cipher’s demonic disguise "
              "at face value."},
    {"id": "prdl-24373_de-statu-et-ruina-monastici-ordinis",
     "pitch": "His diagnosis of what had gone wrong with fifteenth-century "
              "Benedictine life, written at the height of the Sponheim reform "
              "program — a polemic that helped get him forced out a decade later."},
    {"id": "prdl-70280_e-rara_de-scriptoribus-ecclesiasticis-johannes-trithemius",
     "pitch": "A bio-bibliography of roughly a thousand Christian authors from "
              "the apostles to his own day (Basel, 1494) — a foundational "
              "document in the history of bibliography itself."},
]

# Populated in main(); the list of work IDs baked into each work page for the
# random-work button (see base.html.j2). Defaults to empty until build runs.
ALL_WORK_IDS: list[str] = []

# Same parameters the v2 / sweep runs used; alignment depends on this.
CHUNK_MAX_CHARS = 4500
CHUNK_OCR_CLEANUP = True

# Works whose ciphers are decoded on cipher-solutions.html, used to weave
# "solved" links into the relevant work pages. The solve key maps each work
# to a short list of (modus_label, facsimile_page) for the callout summary.
# The Clavis Generalis Triplex is the work that actually carries the solved
# modi (the Steganographia's own key).
CIPHER_SOLVE_LINKS = {
    "prdl-70281_clavis-generalis-triplex-in-libros-steganographicos": {
        "title": "Solved: the Clavis ciphers decoded",
        "blurb": ("Eleven of this work's cipher <em>modi</em> &mdash; the simple modi "
                  "(II&ndash;XI) and the high modi (XXXII&ndash;XXXIX) &mdash; decode "
                  "letter-for-letter through their printed alphabets into ordinary "
                  "early-modern German plaintext. The char-aligned decodes, with "
                  "facsimile crops and honest match scores, are on the solved-ciphers page."),
        "modi": ["II", "V", "VI", "X", "XI", "XXXII", "XXXIII", "XXXV",
                 "XXXVII", "XXXVIII", "XXXIX"],
    },
}

PLACEHOLDER_RE = re.compile(r"<!--\s*skipped:", re.I)
PARALLEL_SOURCE_PLACEHOLDERS = {"", "[illegible]", "[blank]"}
PARALLEL_EVIDENCE_MIN_ENGLISH = 500
REMOVED_BOILERPLATE_RE = re.compile(r"<!--\s*removed:\s*source digitization boilerplate\s*-->", re.I)
# Any chunk whose entire content is a single HTML comment (removal marker,
# missing-translation note, etc.) must never reach the page as invisible
# HTML — treat it as a non-content chunk.
REMOVED_ANY_RE = re.compile(r"<!--.*?-->", re.S)
# Double-scan duplicate markers carry a cross-reference to the retained chunk.
DUP_MARKER_RE = re.compile(r"<!--\s*removed:\s*OCR double-scan duplicate.*?chunk\s*0*(\d+)", re.I | re.S)


def _marker_only(raw: str) -> bool:
    return bool(REMOVED_ANY_RE.fullmatch(raw.strip()))


def _dup_of(raw: str) -> int | None:
    if not _marker_only(raw):
        return None
    m = DUP_MARKER_RE.search(raw)
    return int(m.group(1)) if m else None

# Style C content types from Phase 1 of the c-o-c cluster rendering. Each
# lives under `data/corpus/<work>/translations/style-c-<type>/` in the
# working repo with `_intro.md` plus `full/full_chunk_NNNN.md` files.
STYLE_C_TYPES = [
    {"key": "cipher-key", "label": "Cipher-key tables",
     "blurb": "Substitution-table chunks: each plaintext letter maps to a Latin "
              "cipher-word, rendered as an alphabet-down / columns-across "
              "markdown table with positional OCR repair."},
    {"key": "cipher-grid", "label": "Cipher-grid matrices",
     "blurb": "Bigram-pair tables, alphabet-rotation grids, and the "
              "numerical Orchema, rendered as markdown matrices with "
              "OCR-illegible cells marked."},
    {"key": "untranslated", "label": "Recovered untranslated passages",
     "blurb": "Latin passages the initial prose pipeline never tackled, "
              "translated with scholarly notes and explicit uncertainty "
              "markers where the OCR is damaged."},
    {"key": "prose-damaged", "label": "Damage-preserving review renderings",
     "blurb": "Difficult prose chunks rendered conservatively so OCR damage, "
              "embedded tenors, and uncertainty remain visible for review."},
]
INLINE_STYLE_C_TYPES = ("cipher-key", "cipher-grid")

PROSE_DAMAGED_PUBLIC_INTRO = """\
### About These Review Renderings

These passages preserve damaged prose rather than smoothing it into false
certainty. They keep OCR loss, embedded cipher tenors, and conjectural readings
visible so readers can compare them against the Latin and source scan.

They should be treated as review renderings, not certified final editions.
"""

UNTRANSLATED_PUBLIC_INTRO = """\
### About These Recovered Passages

These are Latin passages that were absent from the standard prose translation
path and were recovered as separate scholarly renderings. They preserve
uncertainty markers where the OCR is damaged and should be checked against the
Latin before quotation.
"""

TIER_META = [
    {"id": "S", "range": "faith >= 4.0; hall <= 5%", "action": "Publish as-is"},
    {"id": "A", "range": "faith >= 3.5; hall <= 15%", "action": "Surgical fixes welcome"},
    {"id": "B", "range": "faith >= 3.0; hall <= 30%", "action": "Needs targeted re-translation"},
    {"id": "C", "range": "faith >= 2.5", "action": "Special-case review"},
    {"id": "F", "range": "< 2.5", "action": "Broken; re-translate"},
]

_chunker = None


def get_chunker():
    """Lazily import the harness chunker; None if unavailable (degrade)."""
    global _chunker
    if _chunker is None:
        if str(HARNESS_SCRIPTS) not in sys.path:
            sys.path.insert(0, str(HARNESS_SCRIPTS))
        try:
            from latin_translation_harness import records_from_file
            _chunker = records_from_file
        except Exception as e:  # noqa: BLE001
            print(f"  [warn] harness chunker unavailable ({e}); "
                  f"parallel viewer will be skipped")
            _chunker = False
    return _chunker or None


def make_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    # Default globals are for root-depth pages (index, scoreboard, etc.).
    # For pages emitted into works/, render() should override url + asset
    # with `make_url(1)` / `make_asset(1)` so cross-section links and the
    # CSS reference resolve correctly under file:// and GitHub Pages alike.
    env.globals["url"] = make_url(0)
    env.globals["asset"] = make_asset(0)
    return env


def make_url(depth: int, cur_dir: str = "works"):
    """Returns a url(path) helper for a page at `depth` directories below
    the site root. depth=0 means the page sits at site/dist/<page>.html;
    depth=1 means it sits at site/dist/<cur_dir>/<page>.html — links into the
    page's own directory drop the prefix (sibling files), everything else gets
    a ../ hop. Works under file:// and GitHub Pages alike."""
    if depth == 0:
        return lambda path: path
    prefix = "../" * depth
    own = cur_dir.rstrip("/") + "/"
    def _url(path: str) -> str:
        if path.startswith(own):
            return path[len(own):]
        return prefix + path
    return _url


def make_asset(depth: int):
    prefix = "../" * depth
    return lambda path: f"{prefix}static/{path}"


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def load_corpus_quality() -> dict:
    """Current published corpus quality, computed from manifest.json (the
    canonical per-work state). The detailed release evidence is mirrored in
    data/_quality/public_release_chunks.jsonl and per-work chunks/grades.csv;
    this headline stays tied to the manifest so the landing-page summary and
    work table cannot drift."""
    mf = load_manifest()
    works = [w for w in mf.get("works", []) if not w.get("skip")]
    if not works:
        return {"chunks": None, "faithful": None, "hallucinated_pct": None, "ge4_clean_pct": None}
    chunks = sum(int(w.get("chunks_graded") or 0) for w in works)
    # Chunk-weighted corpus mean (matches METHODOLOGY §6), not a flat
    # mean of per-work scores — the latter drifts because works have very different
    # chunk counts.
    faithful = (sum((w.get("faithful_adj") or 0) * int(w.get("chunks_graded") or 0) for w in works) / chunks) if chunks else 0.0
    hall_vals = [w.get("hallucinated_pct") for w in works if w.get("hallucinated_pct") is not None]
    halluc = sum(hall_vals) / len(hall_vals) if hall_vals else 0.0
    # ge4_clean_pct: share of works with faithful>=4 and 0% hallucination (all-S proxy)
    ge4_clean = 100.0 * sum(1 for w in works if (w.get("faithful_adj") or 0) >= 4.0 and (w.get("hallucinated_pct") or 0) == 0) / len(works)
    return {
        "chunks": chunks,
        "faithful": faithful,
        "hallucinated_pct": halluc,
        "ge4_clean_pct": ge4_clean,
    }


def humanize_title(raw: str) -> str:
    if not raw:
        return ""
    cleaned = re.sub(r"^E Rara_", "", raw)
    cleaned = re.sub(r"^Dilibri_", "", cleaned)
    cleaned = re.sub(r"^Joh Tritthemii", "Iohannes Trithemius", cleaned)
    cleaned = re.sub(r"^Joannis Tritenhemii", "Iohannes Trithemius", cleaned)
    cleaned = re.sub(r"^Iohannis Trittenhemii", "Iohannes Trithemius", cleaned)
    cleaned = re.sub(r"^Johannis Trithemii", "Iohannes Trithemius", cleaned)
    return cleaned.strip()


_first_english_cache: dict | None = None


def load_first_english() -> dict:
    """Curated 'first published English translation' flags (data/first_english.json)."""
    global _first_english_cache
    if _first_english_cache is None:
        if FIRST_ENGLISH.exists():
            _first_english_cache = json.loads(
                FIRST_ENGLISH.read_text(encoding="utf-8")).get("works", {})
        else:
            _first_english_cache = {}
    return _first_english_cache


def load_clusters() -> dict:
    """Curated cluster descriptions + register notes from cluster_mapping.json."""
    if not CLUSTER_MAPPING.exists():
        return {}
    return json.loads(CLUSTER_MAPPING.read_text(encoding="utf-8")).get("clusters", {})


def enrich_work(w: dict) -> dict:
    w = dict(w)
    # manifest.json now carries the curated Latin title (+ title_en) from
    # work_titles.json. Only fall back to the shelfmark de-mangler if a work
    # somehow lacks a curated title.
    if not w.get("title_en"):
        w["title"] = humanize_title(w.get("title", w["id"]))
    # Reader-facing genre: pipeline cluster, corrected by the display override.
    w["genre"] = DISPLAY_GENRE_OVERRIDES.get(w["id"], w.get("genre_cluster"))
    w["genre_label"] = GENRE_LABELS.get(w["genre"], w["genre"] or "")
    fe = load_first_english().get(w["id"], {})
    w["first_english"] = bool(fe.get("first_english"))
    w["first_english_note"] = fe.get("note", "")
    return w


_EDITION_PLACE_RE = re.compile(r"^\s*\[?\s*([^,\]:(]+?)\s*[\],:(]")

TEXT_GROUP_ALIASES = {
    "prdl-24390_polygraphiae-libri-vi": "six books of polygraphy",
    "prdl-24378_institutio-vitae-sacerdotalis": "on the institution of the priestly life",
    "prdl-24379_institutio-vitae-sacerdotalis": "on the institution of the priestly life",
    "prdl-24369_de-purissima-et-immaculata-conceptione-virginis": "on the most pure and immaculate conception of the virgin",
    "prdl-24370_de-purissima-et-immaculata-conceptione-virginis": "on the most pure and immaculate conception of the virgin",
    "prdl-70291_dilibri_veterum-sophorum-sigilla-et-imagines-magicae": "seals and magical images of the ancient sages",
    "prdl-70292_e-rara_veterum-sophorum-sigilla-et-imagines": "seals and magical images of the ancient sages",
}


def text_group_key(w: dict) -> str:
    if w["id"] in TEXT_GROUP_ALIASES:
        return TEXT_GROUP_ALIASES[w["id"]]
    raw = (w.get("title_en") or w.get("title") or w["id"]).strip().lower()
    return re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", raw).strip()


def edition_tag(w: dict) -> str:
    """Short 'Place, Year' disambiguator parsed from the curated edition_info
    (falls back to the holding provider when no place is given)."""
    info = w.get("edition_info") or ""
    year = w.get("source_year") or w.get("year") or ""
    m = _EDITION_PLACE_RE.match(info)
    place = m.group(1).strip() if m else ""
    # "s. n." / "s. l." (sine nomine / sine loco) mean the print names no
    # publisher/place — meaningless as a disambiguator; use the provider.
    if re.fullmatch(r"s\.\s*[nl]\.?", place, re.I):
        place = ""
    if not place:
        place = (w.get("source") or {}).get("provider") or ""
    return ", ".join(p for p in (place, str(year)) if p)


def attach_editions(works: list[dict]) -> None:
    """Several works are different printed editions of the SAME text (e.g. the
    Polygraphia has three, the Liber Octo four). Group them by translated title
    and annotate each with a disambiguating edition label plus links to its
    sibling editions, so the site does not read as accidental duplicates.

    For each multi-edition family the witness with the cleanest Latin source
    (fewest [unclear] markers; tiebreak faithfulness desc, then earliest year)
    is flagged `is_primary` — the recommended reading edition — and sorts first
    so readers hit the most complete witness."""
    groups: dict[str, list[dict]] = {}
    for w in works:
        key = text_group_key(w)
        groups.setdefault(key, []).append(w)
    for group in groups.values():
        if len(group) < 2:
            continue
        # score each witness by Latin cleanliness to pick the primary
        scored = []
        for w in group:
            hits = list((ROOT / "works").glob(w["id"][:18] + "*"))
            f = hits[0] / "latin-ocr.txt" if hits else None
            gaps = 999999
            if f and f.exists():
                gaps = len(re.findall(r"\[unclear\](?! →)",
                            f.read_text(encoding="utf-8", errors="replace")))
            w["_latin_gaps"] = gaps
            scored.append(((gaps, -(w.get("faithful_adj") or 0),
                            w.get("source_year") or w.get("year") or 9999), w))
        scored.sort(key=lambda x: x[0])
        primary_id = scored[0][1]["id"]
        # primary sorts first, then by year
        ordered = sorted(
            group,
            key=lambda x: (0 if x["id"] == primary_id else 1,
                           str(x.get("source_year") or x.get("year") or ""), x["id"]),
        )
        for idx, w in enumerate(ordered, 1):
            w["edition_label"] = edition_tag(w)
            w["edition_count"] = len(ordered)
            w["edition_index"] = idx
            w["is_primary"] = (w["id"] == primary_id)
            w["edition_siblings"] = [
                {"id": s["id"], "label": edition_tag(s),
                 "is_primary": s["id"] == primary_id}
                for s in ordered if s["id"] != w["id"]
            ]


_MD_INLINE_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)|[*_`]")


def intro_excerpt(work_id: str) -> str:
    """First paragraph of the work's researched intro.md as plain text, for
    the browse cards (display is line-clamped in CSS, so no text surgery)."""
    p = ROOT / "works" / work_id / "intro.md"
    if not p.exists():
        return ""
    for para in p.read_text(encoding="utf-8").split("\n\n"):
        para = para.strip()
        if not para or para.startswith("#"):
            continue
        return _MD_INLINE_RE.sub(lambda m: m.group(1) or "", " ".join(para.split()))
    return ""


def build_texts(works: list[dict]) -> list[dict]:
    """Collapse the 47 edition entries into the 29 distinct texts for the
    browse index. Each text: the earliest edition is the representative (its
    title, intro excerpt, and link), with all editions listed beneath it."""
    groups: dict[str, list[dict]] = {}
    order: list[str] = []
    for w in works:
        key = text_group_key(w)
        if key not in groups:
            order.append(key)
        groups.setdefault(key, []).append(w)
    texts: list[dict] = []
    for key in order:
        group = sorted(
            groups[key],
            key=lambda x: (str(x.get("source_year") or x.get("year") or ""), x["id"]),
        )
        rep = group[0]
        year = min((str(w.get("year")) for w in group if w.get("year")), default="")
        texts.append({
            "key": key,
            "rep": rep,
            "title": rep.get("title"),
            "title_en": rep.get("title_en"),
            "genre": rep.get("genre"),
            "genre_label": rep.get("genre_label"),
            "year": year,
            "first_english": rep.get("first_english", False),
            "excerpt": intro_excerpt(rep["id"]),
            "editions": [
                {"id": w["id"], "label": edition_tag(w), "tier": w.get("tier")}
                for w in group
            ],
        })
    return texts


def resolve_featured(works: list[dict]) -> list[dict]:
    """Attach the hand-curated landing-page picks to their live work entries,
    so title and pitch can never drift apart again. Each pick carries its
    designed SVG cover for the landing thumbnail."""
    byid = {w["id"]: w for w in works}
    out = []
    for f in FEATURED:
        w = byid.get(f["id"])
        if w:
            cover = None
            if _build_cover_svg:
                try:
                    cover = _build_cover_svg(w, width=300)
                except Exception:
                    cover = None
            out.append({"work": w, "pitch": f["pitch"], "cover": cover})
    return out


def resolve_first_english_starters(texts: list[dict], limit: int = 12) -> list[dict]:
    """Build a concise landing-page list of distinct first-English texts."""
    out = []
    for text in texts:
        if not text.get("first_english"):
            continue
        work = text["rep"]
        cover = None
        if _build_cover_svg:
            try:
                cover = _build_cover_svg(work, width=300)
            except Exception:
                cover = None
        out.append({
            "work": work,
            "pitch": text.get("excerpt") or work.get("first_english_note", ""),
            "cover": cover,
        })
        if len(out) == limit:
            break
    return out


# Library-scan boilerplate that the OCR carried into the source Latin. It is
# not Trithemius; strip it from the *displayed* Latin (alignment is by chunk
# index and is unaffected).
_SCAN_JUNK = re.compile(
    r"""^\s*(?:
        -{2,}\s*Page\s*\d+\s*-{2,} |
        \#+\s*Translation |
        ©\s*(?:Herzog\ August|HAB|\[Autor|\[Author).* |
        Graph\..* |
        .*Persistent\s+URL.* |
        .*Persitent\s+URL.* |
        .*\[Signatur\].* |
        \[?\s*(?:BSB|Bayerische|Bayerische\ Staatsbibliothek|StaatsBibliothek|
            M[üu]nchener|Digitalisierungs\w*|Digitale?\s+Biblioth\w+|
            Digital\s+Library|Herzog\ August\ Biblioth\w+|
            Dominus\ Augustus\ Bibliotheca|
            Terms\ of\ Use|Wolfenb[üu]ttel|dilibri|urn:nbn|VD\d{2}\s|
            Res/|Graph\.|Inc\.[a-z]|BSB-Ink|GW\ M\d|Creative\ Commons|
            Trithemius,\ Johannes)\b.*
    )\s*$""",
    re.I | re.X,
)

_EN_SCAN_JUNK = re.compile(
    r"""^\s*(?:
        BSB.*(?:Bayerische|Bavarian|Staatsbibliothek|Digitization|Digitalisierungszentrum).* |
        Herzog\ August\ (?:Bibliothek|Library).* |
        Dominus\ Augustus\ Bibliotheca.* |
        ©\s*(?:Herzog\ August|HAB|\[Author|\[author).* |
        .*Persistent\s+URL.* |
        .*\[Call\ number\].* |
        .*\[Shelfmark\].* |
        Bavarian\ State\ Library.* |
        Bayerische\ Staatsbibliothek.* |
        M[Ã¼üu]nchener\ Digitalisierungs\w+.* |
        Munich\ Digitization\ Cent(?:er|re).* |
        Digitale?\s+Biblioth\w+.* |
        Digital\ Library.* |
        Trithemius,\ Johannes.* |
        urn:nbn:.* |
        VD16\b.* |
        BSB-Ink\b.* |
        GW\s+M\d+.* |
        Res/.* |
        Graph\.(?:\s*\d+.*)? |
        College\ of\ the\ Society.* |
        \[?(?:Library|The\ remaining\ pages\ are\ blank).*Bavarian\ State\ Library.*\]?
    )\s*$""",
    re.I | re.X,
)

_HAB_NOTICE_HEAD = re.compile(
    r"(Herzog\ August|HAB|Wolfenb|Persistent\s+URL|diglib\.hab)",
    re.I,
)
_HAB_NOTICE_END = re.compile(r"(?:Der|The)\s+Dire(?:ktor|ctor)\s+\(2013-03-01\)", re.I)
_HAB_TRAILING_JUNK = re.compile(
    r"""^\s*(?:
        ```(?:plaintext)? |
        Herzog\ August\ (?:Bibliothek|Library) |
        Wolfenb.* |
        Wolffenb.* |
        Wolfsb.* |
        Yg|51|HELMST|8[Â°°]?
    )\s*$""",
    re.I | re.X,
)


def strip_leading_hab_notice(text: str) -> str:
    """Remove HAB usage/citation boilerplate that was OCRed as content."""
    lines = text.splitlines()
    if not _HAB_NOTICE_HEAD.search("\n".join(lines[:80])):
        return text

    end = None
    for idx, line in enumerate(lines[:120]):
        if _HAB_NOTICE_END.search(line):
            end = idx + 1
            break
    if end is None:
        return text

    while end < len(lines):
        line = lines[end].strip()
        if not line or _HAB_TRAILING_JUNK.match(line):
            end += 1
            continue
        break
    return "\n".join(lines[end:])


def strip_scan_boilerplate(text: str) -> str:
    """Drop library/scan header lines; keep the Latin body."""
    text = strip_leading_hab_notice(text)
    kept = [
        ln for ln in text.splitlines()
        if not _SCAN_JUNK.match(ln) and not _HAB_TRAILING_JUNK.match(ln)
    ]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()


def strip_english_scan_boilerplate(text: str) -> str:
    text = strip_leading_hab_notice(text)
    kept = [ln for ln in text.splitlines() if not _EN_SCAN_JUNK.match(ln)]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()


def tier_counts(works: list[dict]) -> list[dict]:
    counts = {t["id"]: 0 for t in TIER_META}
    for w in works:
        t = w.get("tier")
        if t in counts:
            counts[t] += 1
    return [{**meta, "count": counts[meta["id"]]} for meta in TIER_META]


HERO_IMAGE_REL = "images/hero-steganographia-wheel.webp"  # relative to static/
HERO_IMAGE = "static/" + HERO_IMAGE_REL  # full path for absolute URLs

# Designed typographic SVG covers for every work, generated at build time.
# (See scripts/make_cover.py.) The cover is rendered inline on each work page.
try:
    import sys as _sys
    _sys.path.insert(0, str(ROOT / "scripts"))
    from make_cover import build_cover_svg as _build_cover_svg
except Exception:  # pragma: no cover
    _build_cover_svg = None

# Curated facsimile photos for the crypto-occult works, used as the social-card
# (og:image) thumbnail where one exists — the best available image for sharing.
# Values are paths RELATIVE TO static/.
WORK_OG_IMAGES = {
    "prdl-70281_clavis-generalis-triplex-in-libros-steganographicos": "images/works/prdl-70281_clavis-generalis-triplex-in-libros-steganographicos-1.webp",
    "prdl-70282_clavis-polygraphiae-ioannis-trithemii-abbatis-diui": "images/works/prdl-70282_clavis-polygraphiae-ioannis-trithemii-abbatis-diui-1.webp",
    "prdl-24390_polygraphiae-libri-vi": "images/works/prdl-24390_polygraphiae-libri-vi-image2A.webp",
    "prdl-70291_dilibri_veterum-sophorum-sigilla-et-imagines-magicae": "images/works/prdl-70291_dilibri_veterum-sophorum-sigilla-et-imagines-magicae-1.webp",
    "prdl-24395_steganographia-hoc-est-ars-per-occultam-scripturam": "images/works/prdl-24395_steganographia-hoc-est-ars-per-occultam-scripturam-1.webp",
}


def page_meta(path: str, description: str = "", nav: str | None = None,
              jsonld: dict | None = None, image: str | None = None) -> dict:
    """Per-page head metadata: description, canonical URL, Open Graph, JSON-LD,
    and the active top-nav section. Consumed by base.html.j2.

    `image` is a path relative to static/ (matches WORK_IMAGES); falls back to
    HERO_IMAGE when None."""
    desc = " ".join((description or SITE_DESCRIPTION).split())
    if len(desc) > 280:
        desc = desc[:277].rsplit(" ", 1)[0] + "…"
    return {
        "page_path": path,
        "meta_description": desc,
        "canonical": SITE_BASE + path,
        "og_image": SITE_BASE + "static/" + (image or HERO_IMAGE_REL),
        "jsonld": json.dumps(jsonld, ensure_ascii=False) if jsonld else None,
        "nav_active": nav,
    }


def work_jsonld(work: dict) -> dict:
    """Schema.org record for a per-work page."""
    out = {
        "@context": "https://schema.org",
        "@type": "Book",
        "name": work.get("title_en") or work.get("title"),
        "alternateName": work.get("title"),
        "author": {"@type": "Person", "name": "Johannes Trithemius",
                   "birthDate": "1462", "deathDate": "1516"},
        "inLanguage": "en",
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "isPartOf": {"@type": "Dataset", "name": "Trithemius Corpus", "url": SITE_BASE},
        "url": f"{SITE_BASE}works/{work['id']}.html",
    }
    if work.get("year"):
        out["dateCreated"] = str(work["year"])
    src = work.get("source") or {}
    if src.get("url"):
        out["isBasedOn"] = src["url"]
    return out


def site_jsonld(texts_count: int, works_count: int) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": "Trithemius Corpus",
        "description": SITE_DESCRIPTION,
        "url": SITE_BASE,
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "creator": {"@type": "Person", "name": "Ian Carlos Fabin",
                    "url": "https://github.com/agentcarlosian"},
        "about": {"@type": "Person", "name": "Johannes Trithemius",
                  "birthDate": "1462", "deathDate": "1516"},
        "distribution": {"@type": "DataDownload",
                         "contentUrl": "https://github.com/Trithemius-Corpus/Trithemius-Corpus"},
    }


def citation_text(work: dict) -> str:
    """Plain-text suggested citation for one work page."""
    title_en = work.get("title_en") or ""
    title = work.get("title") or work["id"]
    ed = work.get("edition_info") or ""
    bits = [f"Fabin, Ian Carlos (2026). “{title_en}” [{title}]."]
    bits.append("Machine-assisted English translation"
                + (f" of the {ed} edition." if ed else "."))
    bits.append(f"In Trithemius Corpus. {SITE_BASE}works/{work['id']}.html")
    return " ".join(bits)


def render_markdown_file(src: Path) -> str:
    if not src.exists():
        return ""
    text = src.read_text(encoding="utf-8")
    html = markdown.markdown(text, extensions=["extra", "toc", "tables", "fenced_code", "sane_lists"])
    html = _strip_spurious_autolinks(html)
    return rewrite_rendered_links(html)


# Editorial markers like `[unclear]` get mis-parsed by the `extra` extension as
# collapsed reference links, rendering as e.g. `<a href="charity">unclear</a>`.
# `charity` is never a real link target — unwrap these back to plain text.
_SPURIOUS_AUTOLINK_RE = re.compile(r'<a href="charity">(.*?)</a>', re.S)

# The `extra` extension also ships the `abbr` feature, which treats a source
# line of the form `*[unclear]: <caption>.*` as an abbreviation definition.
# Once such a line appears anywhere in a work, EVERY later `[unclear]` renders
# as `<abbr title="<caption>">unclear</abbr>` — one stray marginal rubric thus
# stamps thousands of identical wrong tooltips across the page (2,760 on
# prdl-70290, 332 on prdl-24394). Unwrap any such abbr back to [unclear].
_SPURIOUS_ABBR_RE = re.compile(
    r'<abbr title="[^"]*">unclear</abbr>', re.S)


def _strip_spurious_autolinks(html: str) -> str:
    html = _SPURIOUS_AUTOLINK_RE.sub(r"\1", html)
    html = _SPURIOUS_ABBR_RE.sub("[unclear]", html)
    return html



def rewrite_rendered_links(html: str) -> str:
    """Make GitHub-flavored repo links work inside site/dist pages."""
    site_pages = {
        "METHODOLOGY.md": "methodology.html",
        # PIPELINE.md and LIMITATIONS.md were merged into METHODOLOGY.md;
        # any surviving in-body links to them resolve to the unified page.
        "PIPELINE.md": "methodology.html",
        "LIMITATIONS.md": "methodology.html",
        "LICENSE": "LICENSE.html",
    }
    repo_prefixes = ("data/", "scripts/", "docs/", "works/")
    repo_files = {
        "README.md", "CITATION.cff", "CONTRIBUTING.md", "manifest.json",
        "cluster_mapping.json", "work_titles.json", ".zenodo.json",
    }

    def repl(match: re.Match) -> str:
        quote = match.group(1)
        href = match.group(2)
        if href.startswith(("#", "http://", "https://", "mailto:")):
            return match.group(0)
        path, sep, frag = href.partition("#")
        if path in site_pages:
            new_href = site_pages[path] + (sep + frag if sep else "")
        elif path.endswith(".html"):
            # Already a rendered site page (e.g. works/<id>_style-c-*.html in
            # docs/CIPHERS.md) — leave the relative link untouched.
            return match.group(0)
        elif path in repo_files or path.startswith(repo_prefixes) or path.endswith((".jsonl", ".csv", ".py", ".cff")):
            new_href = f"{GITHUB_ROOT}/{path}" + (sep + frag if sep else "")
        else:
            return match.group(0)
        return f"href={quote}{new_href}{quote}"

    return re.sub(r"href=(['\"])([^'\"]+)\1", repl, html)


def render_simple_page(env: Environment, title: str, body_html: str, slug: str,
                       description: str = "", nav: str | None = None) -> str:
    page_tmpl = env.from_string("""{% extends "base.html.j2" %}
{% block title %}{{ title }} &mdash; Trithemius Corpus{% endblock %}
{% block body %}
<article class="prose">
{{ body_html|safe }}
</article>
{% endblock %}
""")
    return page_tmpl.render(title=title, body_html=body_html,
                            **page_meta(slug, description, nav=nav))


def _clean_chunk_text(raw: str) -> str:
    """Strip the leading '# Translation' / page-marker scaffolding the
    translation files sometimes carry, leaving readable prose."""
    txt = raw.strip()
    if REMOVED_ANY_RE.fullmatch(txt):
        return ""
    txt = re.sub(r"^#+\s*Translation\s*", "", txt)
    txt = re.sub(r"^\*{0,2}-{0,3}\s*Page\s*\d+\s*-{0,3}\*{0,2}\s*$", "", txt, flags=re.M | re.I)
    txt = re.sub(r"^\s*-{2,}\s*Page\s*\d+\s*-{2,}\s*$", "", txt, flags=re.M | re.I)
    return strip_english_scan_boilerplate(txt)


# ---- Pipe-delimited cipher alphabets -> markdown tables ---------------------
# Several Polygraphia / Clavis witnesses render Trithemius's parallel-alphabet
# substitution lists with literal `|` separators, e.g.
#     a of the mother | a coequal
#     b of the nurse   | b coessential
# These are not valid markdown tables, so they rendered as ugly bare bars in a
# <p>. The clean witnesses (prdl-24390) used `;` and read fine; this transform
# rebuilds the rest into real markdown tables before rendering. Detection is
# deliberately conservative: a run of >=4 consecutive lines that each look like
# `<letter-token> <text> | <letter-token> <text> [| ...]` is converted; any
# isolated pipe in ordinary prose is left untouched.
_PIPE_ALPHA_TOK = r"(?:2v|ꝛv|\[unclear\]|[A-Za-z])"
_PIPE_ALPHA_SEG = re.compile(rf"^({_PIPE_ALPHA_TOK})(?:\s+(.+))?$")
_PIPE_ALPHA_LINEHEAD = re.compile(rf"^{_PIPE_ALPHA_TOK}(?:\s|\|)")
_PIPE_ALPHA_PAGENUM = re.compile(r"\d+[a-z]*")


def _pipe_alpha_parse_seg(seg: str) -> tuple[str | None, str]:
    m = _PIPE_ALPHA_SEG.match(seg.strip())
    if m:
        return m.group(1), (m.group(2) or "").strip()
    return None, seg.strip()


def _is_pipe_alpha_line(line: str) -> bool:
    line = line.rstrip()
    if "|" not in line or line.lstrip().startswith("|"):
        return False  # `|a| ... |` is the tabula-recta grid shape, not this one
    if not _PIPE_ALPHA_LINEHEAD.match(line):
        return False
    parts = [p.strip() for p in line.split("|")]
    if len(parts) < 2:
        return False
    good = sum(1 for p in parts if _PIPE_ALPHA_SEG.match(p))
    return good >= 2


def _pipe_alpha_line_cells(line: str) -> list[tuple[str, str]] | None:
    """Split one pipe-alpha line into (token, value) segments, dropping the
    trailing bare page/folio number. None if a non-conforming segment appears."""
    cells: list[tuple[str, str]] = []
    for p in line.split("|"):
        p = p.strip()
        if not p:
            continue
        if _PIPE_ALPHA_PAGENUM.fullmatch(p) and cells:
            continue  # trailing '721' folio marker — not a substitution column
        tok, txt = _pipe_alpha_parse_seg(p)
        if tok is None:
            return None
        cells.append((tok, txt))
    return cells if len(cells) >= 2 else None


def _pipe_alpha_block_to_table(block: list[str]) -> str | None:
    """Render a run of pipe-alpha lines as one markdown table."""
    parsed = [_pipe_alpha_line_cells(ln) for ln in block]
    if any(c is None for c in parsed):
        return None
    n_cols = max(len(c) for c in parsed)  # value columns (excludes the key)
    headers = ["letter"] + [f"col {chr(64 + i)}" for i in range(1, n_cols + 1)]
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"] * (n_cols + 1)) + "|"]
    for cells in parsed:
        key = cells[0][0]
        vals = [txt for _, txt in cells]
        vals += [""] * (n_cols - len(vals))
        def esc(s: str) -> str:
            return s.replace("|", "\\|").replace("\n", " ")
        out.append("| " + esc(key) + " | " + " | ".join(esc(v) for v in vals) + " |")
    return "\n".join(out)


def _pipe_alpha_single_line_to_table(line: str, min_segs: int = 8) -> str | None:
    """A single long line of `<tok> <val> | <tok> <val> | …` (multiple
    concatenated alphabet columns flattened into one paragraph) becomes a
    two-column `letter | word` table. Returns None if the line is not such a
    run (too few segments). Lenient about token shape: Trithemius's flattened
    lists mix single letters, compound codes (qz, qzn, 2v), and bare trailing
    markers, so any leading short token is accepted."""
    if not _is_pipe_alpha_line(line):
        return None
    parts = [p.strip() for p in line.split("|")]
    cells: list[tuple[str, str]] = []
    for p in parts:
        if not p:
            continue
        if _PIPE_ALPHA_PAGENUM.fullmatch(p) and cells:
            continue
        tok, txt = _pipe_alpha_parse_seg(p)
        if tok is None:
            # not a clean <tok> <val>; accept a leading short code + rest
            m = re.match(r"^(\S{1,4})(?:\s+(.+))?$", p)
            if not m:
                return None
            tok, txt = m.group(1), (m.group(2) or "").strip()
        cells.append((tok, txt))
    if len(cells) < min_segs:
        return None
    def esc(s: str) -> str:
        return s.replace("|", "\\|").replace("\n", " ")
    out = ["| letter | word |", "|---|---|"]
    for tok, txt in cells:
        out.append(f"| {esc(tok)} | {esc(txt)} |")
    return "\n".join(out)


def _convert_pipe_alphabets(text: str, min_block: int = 4) -> str:
    """Rewrite pipe-delimited cipher alphabets into markdown tables.

    Two shapes are handled, both rendered before markdown so they become real
    <table> elements instead of literal `|` bars:
      * a contiguous run (>=`min_block` lines) where each line is
        `<tok> <val> | <tok> <val> [| …]` — one multi-column table;
      * a single long line of >=8 `<tok> <val>` segments — a two-column
        `letter | word` table.
    Isolated pipes in ordinary prose are left untouched."""
    if "|" not in text:
        return text
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        if _is_pipe_alpha_line(lines[i]):
            j = i
            while j < len(lines) and _is_pipe_alpha_line(lines[j]):
                j += 1
            block = lines[i:j]
            if len(block) >= min_block:
                table = _pipe_alpha_block_to_table(block)
                if table:
                    out += ["", table, ""]
                    i = j
                    continue
            # a lone long line (a flattened alphabet list) -> two-col table
            if len(block) == 1:
                single = _pipe_alpha_single_line_to_table(block[0])
                if single:
                    out += ["", single, ""]
                    i = j
                    continue
            out += block
            i = j
        else:
            out.append(lines[i])
            i += 1
    return "\n".join(out)


# ---- Numeric / tabular line-runs -> markdown tables -------------------------
# A second family of malformed tables in the Polygraphia: the "order of
# numerical letters" runs. These come in three shapes the markdown `tables`
# extension does not parse:
#   1. space-separated <token> <number> pairs, several per line
#      ("a 1 ma 31 oa 61 ra 91 wd 1004") -> a letter/value table;
#   2. leading-`|` rows with NO separator row (markdown needs one to treat a
#      run as a table) -> a separator is inserted after the first row, with
#      ragged rows padded to the max column count;
#   3. tables that DO have a separator but are OCR-garbled (empty `||` cells,
#      or several separator rows interspersed) -> wrapped in a fenced code
#      block so the raw OCR stays readable as monospace rather than collapsing
#      into run-on prose. (Reconstructing their column structure would invent
#      data, so the honest rendering is verbatim.)
_PIPE_SEP_RE = re.compile(r"[\s|:\-]+")


def _pipe_is_leading(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.count("|") >= 2


def _pipe_is_separator(line: str) -> bool:
    s = line.strip()
    return bool(s) and "-" in s and "|" in s and _PIPE_SEP_RE.fullmatch(s)


def _pipe_row_cells(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _pair_is_numline(line: str) -> bool:
    """`a 1 ma 31 oa 61 ra 91 wd 1004` — >=2 token/number pairs, numbers at
    every odd position. A single trailing non-number token (a folio marker
    like 'p ij') is tolerated and dropped."""
    line = line.strip()
    if not line or "|" in line:
        return False
    toks = line.split()
    if len(toks) < 4:
        return False
    if len(toks) % 2 != 0:
        if not re.fullmatch(r"\d+", toks[-2]):
            return False
        toks = toks[:-1]
    if len(toks) < 4 or len(toks) % 2 != 0:
        return False
    return all(re.fullmatch(r"\d+", toks[i]) for i in range(1, len(toks), 2))


def _pair_cells(line: str) -> list[tuple[str, str]]:
    toks = line.split()
    if len(toks) % 2 != 0:
        toks = toks[:-1]
    return [(toks[i], toks[i + 1]) for i in range(0, len(toks), 2)]


def _convert_number_pairs(text: str, min_rows: int = 4) -> str:
    """Shape 1: runs of `<tok> <num> <tok> <num> ...` lines -> a letter/value
    table with as many column-pairs as the widest line."""
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        if _pair_is_numline(lines[i]):
            j = i
            while j < len(lines) and _pair_is_numline(lines[j]):
                j += 1
            block = lines[i:j]
            if len(block) >= min_rows:
                rows = [_pair_cells(ln) for ln in block]
                ncols = max(len(r) for r in rows)

                def esc(s: str) -> str:
                    return s.replace("|", "\\|")
                headers: list[str] = []
                for _ in range(ncols):
                    headers += ["letter", "value"]
                # blank-line guards so the table is not glued to preceding or
                # following prose (markdown needs a blank line to start a table)
                out.append("")
                out.append("| " + " | ".join(headers) + " |")
                out.append("|" + "|".join(["---"] * (2 * ncols)) + "|")
                for r in rows:
                    cells: list[str] = []
                    for t, v in r:
                        cells += [t, v]
                    cells += ["", ""] * (ncols - len(r))
                    out.append("| " + " | ".join(esc(c) for c in cells[:2 * ncols]) + " |")
                out.append("")
                i = j
                continue
            out += block
            i = j
        else:
            out.append(lines[i])
            i += 1
    return "\n".join(out)


def _pipe_is_row(line: str) -> bool:
    """Any table-ish pipe row: leading-`|` rows, or interior-pipe rows with
    >=3 columns (e.g. the Greek-alphabet cipher `A α | 1 | i | ...`)."""
    s = line.strip()
    if "|" not in s:
        return False
    if _pipe_is_separator(s):
        return False
    if s.startswith("|"):
        return s.count("|") >= 2
    # interior pipes: split and count non-empty columns
    cols = [c.strip() for c in s.split("|")]
    return len([c for c in cols if c]) >= 3


def _pipe_row_normalize(line: str) -> list[str]:
    """Cell list for either a leading-`|` or interior-pipe row."""
    s = line.strip()
    if s.startswith("|"):
        return _pipe_row_cells(line)
    return [c.strip() for c in s.split("|")]


def _fix_pipe_table_runs(text: str, min_rows: int = 3) -> str:
    """Shape 2: a run of >=min_rows pipe rows (leading-`|` or interior-pipe)
    without a separator row is turned into a table by padding to the max width
    and inserting a `---` separator after the first (header) row. Runs already
    carrying a separator are left to markdown (or the malformed-pre pass).

    This also catches interior-pipe cipher alphabets that the dedicated
    `_convert_pipe_alphabets` letter-substitution pass did not match (mixed
    letter/Greek/number cells), so they render as tables instead of bare bars."""
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        if _pipe_is_row(lines[i]):
            j = i
            # Gather the whole contiguous table: pipe rows AND separator rows
            # belong to the same table, so a separator inside the run does not
            # split it (otherwise the body rows after a separator would look
            # like a separator-less run and get a second separator injected).
            while j < len(lines) and (_pipe_is_row(lines[j]) or _pipe_is_separator(lines[j])):
                j += 1
            block = lines[i:j]
            has_sep = any(_pipe_is_separator(b) for b in block)
            if not has_sep and len(block) >= min_rows:
                rows = [_pipe_row_normalize(b) for b in block]
                w = max(len(r) for r in rows)
                for r in rows:
                    while len(r) < w:
                        r.append("")

                def esc(s: str) -> str:
                    return s.replace("|", "\\|")
                # blank-line guards so the table is not glued to surrounding prose
                out.append("")
                out.append("| " + " | ".join(esc(c) for c in rows[0]) + " |")
                out.append("|" + "|".join(["---"] * w) + "|")
                for r in rows[1:]:
                    out.append("| " + " | ".join(esc(c) for c in r) + " |")
                out.append("")
                i = j
                continue
            out += block
            i = j
        else:
            out.append(lines[i])
            i += 1
    return "\n".join(out)


def _wrap_malformed_pipe_tables(text: str) -> str:
    """Shape 3: a leading-`|` block that already has a separator but is
    OCR-garbled (empty `||` / `| |` cells, or several separator rows) is
    wrapped in a fenced code block. Reconstructing its columns would invent
    data, so the honest rendering is the raw OCR as monospace."""
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        if _pipe_is_leading(lines[i]):
            j = i
            while j < len(lines) and _pipe_is_leading(lines[j]):
                j += 1
            block = lines[i:j]
            seps = sum(1 for b in block if _pipe_is_separator(b))
            empties = sum(1 for b in block if "||" in b or re.search(r"\|\s+\|", b))
            malformed = seps >= 1 and (seps > 1 or empties >= 2)
            if malformed:
                out += ["", "```"] + block + ["```", ""]
                i = j
                continue
            out += block
            i = j
        else:
            out.append(lines[i])
            i += 1
    return "\n".join(out)


def _convert_numeric_tables(text: str) -> str:
    """Apply the three numeric/tabular transforms in order: pair-lines, then
    pipe-table runs, then wrap any remaining garbled tables as code."""
    text = _convert_number_pairs(text)
    text = _fix_pipe_table_runs(text)
    text = _wrap_malformed_pipe_tables(text)
    return text


def _chunk_markdown_to_html(text: str) -> str:
    if not text:
        return ""
    text = _convert_pipe_alphabets(text)
    text = _convert_numeric_tables(text)
    html = _strip_spurious_autolinks(markdown.markdown(text, extensions=["extra", "sane_lists"]))
    return _wrap_style_c_wide_blocks(html)


def _parse_latin_artifact(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    marker_re = re.compile(r"(?m)^\[segment\s+(\d+)\]\s*$")
    matches = list(marker_re.finditer(text))
    if not matches:
        stripped = text.strip()
        return [{"n": 1, "latin": stripped}] if stripped else []
    segments: list[dict] = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        latin = strip_scan_boilerplate(text[start:end])
        segments.append({"n": int(match.group(1)), "latin": latin})
    return segments


def _lacks_parallel_source_evidence(latin: str, english: str) -> bool:
    """Avoid presenting long English chunks against blank/placeholder Latin."""
    latin_norm = re.sub(r"\s+", " ", (latin or "")).strip()
    english_norm = re.sub(r"\s+", " ", (english or "")).strip()
    return (
        latin_norm in PARALLEL_SOURCE_PLACEHOLDERS
        and len(english_norm) > PARALLEL_EVIDENCE_MIN_ENGLISH
    )


def _load_pairs_from_release_artifacts(work_id: str) -> tuple[list[dict], dict] | None:
    """Prefer the committed release artifacts for standard site pages.

    The working corpus is still needed for Style C pages, but the normal
    Latin/English reader should rebuild from the public dataset committed in
    this repository whenever possible.
    """
    work_dir = ROOT / "works" / work_id
    latin_path = work_dir / "latin-ocr.txt"
    chunks_dir = work_dir / "chunks"
    if not latin_path.exists() or not chunks_dir.is_dir():
        return None

    latin_segments = _parse_latin_artifact(latin_path)
    if not latin_segments:
        return None

    chunk_files = sorted(chunks_dir.glob("full_chunk_*.md"))
    english_by_n: dict[int, Path] = {}
    for f in chunk_files:
        m = re.search(r"full_chunk_(\d+)$", f.stem)
        if m:
            english_by_n[int(m.group(1))] = f

    latin_by_n = {seg["n"]: seg["latin"] for seg in latin_segments}
    max_n = max([*latin_by_n.keys(), *english_by_n.keys()], default=0)

    pairs: list[dict] = []
    for n in range(1, max_n + 1):
        ef = english_by_n.get(n)
        if ef:
            raw = ef.read_text(encoding="utf-8", errors="replace")
            dup_of = _dup_of(raw)
            if PLACEHOLDER_RE.search(raw[:200]):
                english, missing = "", True
            else:
                english = _clean_chunk_text(raw)
                missing = not bool(english)
        else:
            english, missing, dup_of = "", True, None
        latin = latin_by_n.get(n, "")
        if not missing and _lacks_parallel_source_evidence(latin, english):
            english, missing = "", True
        pairs.append({
            "n": n,
            "latin": latin,
            "english": english,
            "english_html": _chunk_markdown_to_html(english),
            "missing": missing,
            "dup_of": dup_of,
        })

    stats = {
        "aligned": True,
        "source": "release-artifacts",
        "n_latin": max_n,
        "n_english": len(chunk_files),
        "n_missing": sum(1 for p in pairs if p["missing"] and not p.get("dup_of")),
        "n_dup": sum(1 for p in pairs if p.get("dup_of")),
        "n_extra_english": 0,
    }
    return pairs, stats


def load_pairs(work_id: str) -> tuple[list[dict], dict]:
    """Return (pairs, stats). Each pair: {n, latin, english, missing}.

    Latin is re-chunked from full.txt with the harness chunker so chunk i
    lines up with translations/public/full/full_chunk_{i:04d}.md.
    """
    from_artifacts = _load_pairs_from_release_artifacts(work_id)
    if from_artifacts is not None:
        return from_artifacts

    chunker = get_chunker()
    full_txt = CORPUS / work_id / "full.txt"
    pub = CORPUS / work_id / "translations" / "public" / "full"
    if chunker is None or not full_txt.exists() or not pub.is_dir():
        return [], {"aligned": False, "n_latin": 0, "n_english": 0}

    recs = chunker(full_txt, None, CHUNK_MAX_CHARS, 0, CHUNK_OCR_CLEANUP)
    eng_files = sorted(pub.glob("full_chunk_*.md"))
    n_eng = len(eng_files)
    pairs: list[dict] = []
    for i, rec in enumerate(recs, 1):
        ef = pub / f"full_chunk_{i:04d}.md"
        if ef.exists():
            raw = ef.read_text(encoding="utf-8", errors="replace")
            dup_of = _dup_of(raw)
            if PLACEHOLDER_RE.search(raw[:200]):
                english, missing = "", True
            else:
                english = _clean_chunk_text(raw)
                missing = not bool(english)
        else:
            english, missing, dup_of = "", True, None
        latin = strip_scan_boilerplate(rec["text"])
        if not missing and _lacks_parallel_source_evidence(latin, english):
            english, missing = "", True
        pairs.append({
            "n": i,
            "latin": latin,
            "english": english,
            "english_html": _chunk_markdown_to_html(english),
            "missing": missing,
            "dup_of": dup_of,
        })
    stats = {
        "aligned": len(recs) == n_eng,
        "source": "working-corpus",
        "n_latin": len(recs),
        "n_english": n_eng,
        "n_missing": sum(1 for p in pairs if p["missing"] and not p.get("dup_of")),
        "n_dup": sum(1 for p in pairs if p.get("dup_of")),
        "n_extra_english": max(0, n_eng - len(recs)),
    }
    return pairs, stats


def _md_to_html(md_text: str) -> str:
    return _strip_spurious_autolinks(markdown.markdown(
        md_text,
        extensions=["extra", "tables", "fenced_code", "sane_lists"],
    ))


CIPHER_GRID_ARTIFACT_NOTE = (
    "> *OCR/grid artefact omitted. The printed figure should be read from the "
    "source facsimile: OCR collapsed its columns into repeated alphabet "
    "strings, so no transcribed grid is shown here.*"
)


def _normalise_cipher_grid_row(line: str) -> str:
    return re.sub(r"[^a-z0-9]", "", line.lower())


def _looks_like_collapsed_cipher_grid(block: str) -> bool:
    """Detect OCR-linearized alphabet tables that render as repeated rows."""
    rows = [
        _normalise_cipher_grid_row(line)
        for line in block.splitlines()
        if _normalise_cipher_grid_row(line)
    ]
    if len(rows) < 8:
        return False

    alphabetish: list[str] = []
    for row in rows:
        if len(row) < 12 or len(set(row)) < 10:
            continue
        if "fedcba" in row or "yxutsrqpon" in row or "abcdef" in row:
            alphabetish.append(row)

    if len(alphabetish) < 8:
        return False

    counts: dict[str, int] = {}
    for row in alphabetish:
        counts[row] = counts.get(row, 0) + 1
    max_repeat = max(counts.values(), default=0)
    unique_ratio = len(counts) / len(alphabetish)
    return max_repeat >= 6 or unique_ratio <= 0.35


def _suppress_cipher_grid_artifacts(text: str) -> str:
    def replace_block(match: re.Match[str]) -> str:
        block = match.group(1)
        if _looks_like_collapsed_cipher_grid(block):
            return CIPHER_GRID_ARTIFACT_NOTE
        return match.group(0)

    return re.sub(r"```[^\n`]*\n(.*?)```", replace_block, text, flags=re.S)


def _clean_style_c_markdown(md_text: str, content_key: str) -> str:
    """Remove review-packet scaffolding from public Style C pages."""
    text = md_text.replace("Prose-damaged drafts (Style C)", "Damage-preserving review renderings")
    text = text.replace("prose-damaged draft, chunk", "damage-preserving rendering,")
    text = text.replace(
        "Style C draft for human review. GPT-5.5 damage-preserving re-translation "
        "with tenor detection and footnoting.",
        "Damage-preserving review rendering with tenor detection and footnoting.",
    )
    text = text.replace("*(to seed reviewer)*", "")
    text = re.sub(r"\*\*v1\.0 critique\*\*", "**Audit note**", text, flags=re.I)
    text = re.sub(r"\s+\(urn:nbn:[^)]+\)", "", text)
    text = re.sub(
        r" \*\*Read the source facsimile alongside[^\n]*?"
        r"it is authoritative for this figure\.\*\*\*",
        " Read the source facsimile alongside - it is authoritative for this figure.*",
        text,
    )

    cleaned: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if _EN_SCAN_JUNK.match(stripped):
            continue
        if re.match(r"^\d+\s+P\.lat\b", stripped, re.I):
            continue
        if re.match(r"^Johannes\s+Trithemius\^\d+\.?$", stripped, re.I):
            continue
        if re.match(r"^\^\d+\.\s+(?:Modern repository metadata|VD16 is)\b", stripped, re.I):
            continue
        cleaned.append(line)

    text = "\n".join(cleaned)
    if content_key == "prose-damaged":
        text = re.sub(r"\b[Dd]rafts?\b", "review renderings", text)
        text = text.replace("human reviewer", "reader")
        text = text.replace("human review", "source review")
    if content_key == "cipher-grid":
        text = _suppress_cipher_grid_artifacts(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _wrap_style_c_wide_blocks(html: str) -> str:
    """Give wide Style C tables and pre blocks their own scroll viewport.
    Idempotent: a table/pre already inside a .table-scroll wrapper is left
    alone, so re-running this on HTML that already wraps its tables does not
    double-nest."""
    def _wrap(m: re.Match[str]) -> str:
        start = m.start()
        preceding = html[max(0, start - 40):start]
        if 'class="table-scroll"' in preceding and ">" in preceding:
            return m.group(0)  # already wrapped
        return f'<div class="table-scroll">{m.group(0)}</div>'

    html = re.sub(r"<table\b.*?</table>", _wrap, html, flags=re.S)
    html = re.sub(r"<pre\b.*?</pre>", _wrap, html, flags=re.S)
    return html


def _style_c_inline_lookup(work: dict, style_c: dict | None) -> dict[str, list[dict]]:
    """Map full_chunk_NNNN to structured table renderings that can replace
    linear prose/table-salad chunks in the main work page."""
    if not style_c:
        return {}
    out: dict[str, list[dict]] = {}
    for key in INLINE_STYLE_C_TYPES:
        content_type = style_c.get(key)
        if not content_type:
            continue
        for chunk in content_type.get("chunks") or []:
            name = chunk.get("name")
            if not name:
                continue
            out.setdefault(name, []).append({
                "key": key,
                "label": content_type["label"],
                "href": f"{work['id']}_style-c-{key}.html#{name}",
                "html": chunk["html"],
                "pages": chunk.get("pages") or [],
            })
    return out


def _render_inline_style_c(chunk_name: str, renderings: list[dict], original_md: str) -> str:
    labels = ", ".join(html_lib.escape(r["label"]) for r in renderings)
    links = " ".join(
        f'<a class="badge badge-link" href="{html_lib.escape(r["href"])}">'
        f'{html_lib.escape(r["label"])}</a>'
        for r in renderings
    )
    pages = sorted({
        int(pg["n"])
        for rendering in renderings
        for pg in rendering.get("pages", [])
        if pg.get("n")
    })
    page_label = ""
    if pages:
        page_label = " &middot; source " + ("page " if len(pages) == 1 else "pages ")
        page_label += ", ".join(str(n) for n in pages[:8])
        if len(pages) > 8:
            page_label += f", +{len(pages) - 8} more"
    original_html = _chunk_markdown_to_html(original_md) if original_md else ""

    parts = [
        f'<aside class="inline-apparatus" id="apparatus-{html_lib.escape(chunk_name)}">',
        '<div class="inline-apparatus-head">',
        '<p class="eyebrow">Structured cipher apparatus</p>',
        f'<h4>{html_lib.escape(chunk_name)} &middot; {labels}</h4>',
        (
            '<p class="muted">This table-heavy segment is displayed as a '
            f'structured rendering instead of a linear prose chunk{page_label}.</p>'
        ),
        f'<div class="inline-apparatus-links">{links}</div>',
        '</div>',
    ]
    for rendering in renderings:
        parts.extend([
            f'<section class="style-c-rendering inline-apparatus-rendering" data-style-c="{html_lib.escape(rendering["key"])}">',
            rendering["html"],
            '</section>',
        ])
    if original_html:
        parts.extend([
            '<details class="inline-apparatus-original">',
            '<summary>Original linear rendering</summary>',
            f'<div class="prose">{original_html}</div>',
            '</details>',
        ])
    parts.append('</aside>')
    return "\n".join(parts)


def _facsimile_pages_for(work_id: str, chunk_name: str,
                         rec_pages: dict[int, list[int]]) -> list[dict]:
    """Source-page facsimiles for one Style C chunk, gated on the WebP having
    actually been encoded (`build_facsimiles.py`). Returns [] when the chunker
    is unavailable or no image exists, so a partial/absent image set never
    yields a broken <img>. `src`/`thumb` are paths relative to static/ for the
    template's asset() helper."""
    m = facsimile_map.CHUNK_INDEX_RE.search(chunk_name)
    if not m:
        return []
    pages, approx = facsimile_map.pages_for_chunk(work_id, int(m.group(1)), rec_pages)
    out: list[dict] = []
    for n in pages:
        rel = f"images/{work_id}/page_{n:03d}.webp"
        if not (STATIC / rel).exists():
            continue
        out.append({
            "n": n,
            "src": rel,
            "thumb": f"images/{work_id}/page_{n:03d}_thumb.webp",
            "approx": approx,
        })
    return out


def load_style_c(work: dict) -> dict:
    """Read Style C content from the working corpus. Returns a dict keyed by
    content-type with intro_html, source (provider attribution), and
    chunks=[{name, html, pages}, ...]. Empty dict if the work has no Style C
    content."""
    work_id = work["id"]
    source = work.get("source") or {}
    rec_pages = facsimile_map.rec_pages_for_work(work_id)
    out: dict[str, dict] = {}
    for ct in STYLE_C_TYPES:
        type_dir = CORPUS / work_id / "translations" / f"style-c-{ct['key']}"
        if not type_dir.is_dir():
            continue
        full_dir = type_dir / "full"
        chunk_files = sorted(full_dir.glob("full_chunk_*.md")) if full_dir.is_dir() else []
        if not chunk_files:
            continue
        intro_path = type_dir / "_intro.md"
        if ct["key"] == "prose-damaged":
            intro_html = _wrap_style_c_wide_blocks(_md_to_html(PROSE_DAMAGED_PUBLIC_INTRO))
        elif ct["key"] == "untranslated":
            intro_html = _wrap_style_c_wide_blocks(_md_to_html(UNTRANSLATED_PUBLIC_INTRO))
        else:
            intro_html = (
                _wrap_style_c_wide_blocks(
                    _md_to_html(_clean_style_c_markdown(intro_path.read_text(encoding="utf-8"), ct["key"]))
                )
                if intro_path.exists() else ""
            )
        chunks: list[dict] = []
        for f in chunk_files:
            chunk_md = _clean_style_c_markdown(f.read_text(encoding="utf-8"), ct["key"])
            chunks.append({
                "name": f.stem,
                "html": _wrap_style_c_wide_blocks(_md_to_html(chunk_md)),
                "pages": _facsimile_pages_for(work_id, f.stem, rec_pages),
            })
        out[ct["key"]] = {
            "key": ct["key"],
            "label": ct["label"],
            "blurb": ct["blurb"],
            "intro_html": intro_html,
            "chunks": chunks,
            "n": len(chunks),
            "n_facsimiles": sum(1 for c in chunks if c["pages"]),
            "source": {
                "provider": source.get("provider"),
                "url": source.get("url"),
            },
        }
    return out


def load_chapters(work_id: str) -> dict | None:
    """Load works/<id>/chapters.json, or None if absent."""
    p = ROOT / "works" / work_id / "chapters.json"
    if not p.exists():
        return None
    try:
        import json
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def stitch_english(
    pairs: list[dict],
    chapters: dict | None = None,
    inline_style_c: dict[str, list[dict]] | None = None,
) -> str:
    """Concatenate the non-missing English chunks into one readable HTML body.

    If `chapters` (a chapters.json dict) is supplied, wrap each chapter boundary
    segment in `<section class="chapter" id="ch-N" data-seg="N">` so the
    chapter-nav dropdown can anchor to it."""
    chapter_segs = set()
    if chapters and chapters.get("entries"):
        chapter_segs = {e["n"] for e in chapters["entries"]}
    # Build the joined markdown body. Chapter-boundary segments are marked with
    # a unique HTML comment placeholder rather than wrapped in <section> tags,
    # because the `extra` extension's md_in_html would treat a <section> as a
    # raw HTML block and skip parsing tables/lists inside it (breaking every
    # table that falls in a chapter-boundary segment). The placeholders survive
    # markdown and are swapped for <section> wrappers after rendering.
    blocks: list[str] = []
    for p in pairs:
        if p["missing"] or not p["english"]:
            continue
        seg = p.get("n")
        chunk_name = f"full_chunk_{seg:04d}" if isinstance(seg, int) else ""
        inline_renderings = (inline_style_c or {}).get(chunk_name)
        if inline_renderings:
            content = _render_inline_style_c(chunk_name, inline_renderings, p["english"])
        else:
            content = p["english"]
        if seg in chapter_segs:
            blocks.append(f"<!--CHAPTER-ANCHOR:{seg}-->")
        blocks.append(content)
    if not blocks:
        return ""
    joined = "\n\n".join(blocks)
    joined = _convert_pipe_alphabets(joined)
    joined = _convert_numeric_tables(joined)
    html = _strip_spurious_autolinks(markdown.markdown(joined, extensions=["extra", "sane_lists"]))
    # Wrap [bracketed] OCR/translator annotations (e.g. [unclear]) in spans so
    # the scholarly-view toggle can reveal or hide them.
    html = _wrap_annotations(html)
    # Swap the chapter placeholders for <section> wrappers. Each placeholder
    # opens a section that runs until the next placeholder (or end of body).
    if chapter_segs:
        html = _apply_chapter_anchors(html)
    return _wrap_style_c_wide_blocks(html)


_ANNOT_RE = re.compile(r"\[(unclear|sic|ed\.?|lit\.?|tn\.?|note|trans\.?|ocr)\]",
                       re.IGNORECASE)


def _wrap_annotations(html: str) -> str:
    """Wrap OCR/translator annotation markers like ``[unclear]`` in
    ``<span class="anno anno-unclear">[unclear]</span>`` so the reader's
    scholarly-view toggle can reveal or hide them. Only acts inside text nodes
    (skips tag attributes) by operating on text between ``>`` and ``<``."""
    def repl(m: re.Match[str]) -> str:
        tag = m.group(1).lower().rstrip(".")
        cls = "anno anno-" + tag
        return f'<span class="{cls}">{m.group(0)}</span>'

    out: list[str] = []
    for chunk in re.split(r"(<[^>]+>)", html):
        if chunk.startswith("<") and chunk.endswith(">"):
            out.append(chunk)  # a tag — leave alone (don't touch attributes)
        else:
            out.append(_ANNOT_RE.sub(repl, chunk))
    return "".join(out)


_CHAPTER_ANCHOR_RE = re.compile(r"<!--CHAPTER-ANCHOR:(\d+)-->")


def _apply_chapter_anchors(html: str) -> str:
    """Replace the CHAPTER-ANCHOR placeholders left in the rendered HTML with
    flat (non-nested) <section class="chapter"> wrappers. Each placeholder opens
    a section and closes the previous one, so the body is a flat sequence of
    sibling chapter sections, each carrying the id the chapter-nav links to."""
    pieces: list[str] = []
    open = False
    pos = 0
    for m in _CHAPTER_ANCHOR_RE.finditer(html):
        pieces.append(html[pos:m.start()])
        if open:
            pieces.append("</section>")
        seg = m.group(1)
        pieces.append(f'<section class="chapter" id="ch-{seg}" data-seg="{seg}">')
        open = True
        pos = m.end()
    pieces.append(html[pos:])
    if open:
        pieces.append("</section>")
    return "".join(pieces)


def genre_sections(texts: list[dict], clusters: dict) -> list[dict]:
    """Texts grouped by reader-facing genre, in GENRE_ORDER."""
    sections = []
    for slug in GENRE_ORDER:
        members = [t for t in texts if t["genre"] == slug]
        if not members:
            continue
        info = clusters.get(slug, {})
        sections.append({
            "slug": slug,
            "label": GENRE_LABELS[slug],
            "description": info.get("description", ""),
            "register_notes": info.get("register_notes", ""),
            "texts": sorted(members, key=lambda t: (t["year"] or "9999", t["key"])),
            "n_texts": len(members),
            "n_editions": sum(len(t["editions"]) for t in members),
        })
    return sections


def build_index(env: Environment, manifest: dict, works: list[dict],
                texts: list[dict], sections: list[dict]) -> str:
    n_first = sum(1 for t in texts if t["first_english"])
    return env.get_template("index.html.j2").render(
        stats={
            "texts": len(texts),
            "editions": len(works),
            "first_english": n_first,
        },
        featured=resolve_first_english_starters(texts, limit=12),
        sections=sections,
        **page_meta("index.html", SITE_DESCRIPTION, nav="home",
                    jsonld=site_jsonld(len(texts), len(works))),
    )


def build_works_page(env: Environment, works: list[dict], texts: list[dict],
                     sections: list[dict]) -> str:
    by_year = sorted(texts, key=lambda t: (t["year"] or "9999", t["key"]))
    return env.get_template("works.html.j2").render(
        sections=sections,
        texts_by_year=by_year,
        n_texts=len(texts),
        n_editions=len(works),
        n_first=sum(1 for t in texts if t["first_english"]),
        **page_meta("works.html",
                    "All 28 Latin texts of Johannes Trithemius in this corpus, "
                    "grouped by genre, with every printed edition and its "
                    "English translation.", nav="works"),
    )


def build_genre_page(env: Environment, section: dict) -> str:
    return env.get_template("genre.html.j2").render(
        section=section,
        url=make_url(1, "genres"), asset=make_asset(1),
        **page_meta(f"genres/{section['slug']}.html",
                    section["description"], nav="works"),
    )


def build_scoreboard(env: Environment, works: list[dict]) -> str:
    tier_rank = {"S": 0, "A": 1, "B": 2, "C": 3, "F": 4, None: 5}
    ordered = sorted(
        works,
        key=lambda w: (
            tier_rank.get(w.get("tier"), 5),
            w.get("priority", 99),
            -(w.get("faithful_adj") or 0),
        ),
    )
    return env.get_template("scoreboard.html.j2").render(
        works=ordered,
        tiers=tier_counts(works),
        quality=load_corpus_quality(),
        **page_meta("scoreboard.html",
                    "Quality tier table for every translated "
                    "edition in the Trithemius Corpus, graded chunk-by-chunk against the Latin.", nav="quality"),
    )


def _errata_markup(errata_path: Path) -> str:
    """Render ERRATA.md for embedding: drop the file's own top-level title
    (the section already carries an 'Editorial corrections' heading) and
    demote the remaining headings so the page keeps a single h1."""
    html_s = render_markdown_file(errata_path)
    html_s = re.sub(r"<h1[^>]*>.*?</h1>\s*", "", html_s, count=1, flags=re.S)
    def _demote(m):
        lvl = min(6, int(m.group(2)) + 2)
        return f"<{m.group(1)}h{lvl}"
    return re.sub(r"<(/?)h([1-6])", _demote, html_s)


def build_work(env: Environment, work: dict, english_html: str,
               has_parallel: bool, style_c: dict | None,
               chapters: dict | None = None,
               related: list[dict] | None = None,
               prev_work_id: str | None = None,
               next_work_id: str | None = None) -> str:
    work_dir = ROOT / "works" / work["id"]
    intro_html = render_markdown_file(work_dir / "intro.md")
    desc = intro_excerpt(work["id"]) or (
        f"English translation of {work.get('title')} ({work.get('year', '')}), "
        f"with the Latin source.")
    # Reading time estimate from english.md word count
    reading_time = None
    em = work_dir / "english.md"
    if em.exists():
        import re as _re
        wt = len(_re.findall(r"[A-Za-z']+", em.read_text(encoding="utf-8", errors="replace")))
        hrs = wt / 150 / 60
        if hrs >= 1:
            reading_time = f"{round(hrs)} hours"
        else:
            reading_time = f"{max(1, round(wt / 150))} minutes"
    # ERRATA
    errata_html = None
    has_errata = False
    errata_path = work_dir / "ERRATA.md"
    if errata_path.exists():
        et = errata_path.read_text(encoding="utf-8", errors="replace").strip()
        # only flag if there's real content beyond the stub
        if len(et) > 80 or "No corrections recorded" not in et:
            has_errata = True
            errata_html = _errata_markup(errata_path)
        elif "No corrections recorded" not in et:
            has_errata = True
            errata_html = _errata_markup(errata_path)
    return env.get_template("work.html.j2").render(
        work=work,
        intro=intro_html or None,
        english=english_html or None,
        has_parallel=has_parallel,
        style_c=style_c or None,
        chapters=chapters,
        chapter_anchor="ch",
        related=related or [],
        citation=citation_text(work),
        work_id=work["id"],
        work_title=work.get("title_en") or work.get("title") or work["id"],
        reading_time=reading_time,
        has_errata=has_errata,
        errata_html=errata_html,
        prev_work=prev_work_id,
        next_work=next_work_id,
        all_work_ids=ALL_WORK_IDS,
        solve=CIPHER_SOLVE_LINKS.get(work["id"]),
        work_cover=(_build_cover_svg(work) if _build_cover_svg else None),
        url=make_url(1), asset=make_asset(1),
        **page_meta(f"works/{work['id']}.html", desc, nav="works",
                    jsonld=work_jsonld(work),
                    image=WORK_OG_IMAGES.get(work["id"])),
    )


def build_parallel(env: Environment, work: dict, pairs: list[dict], stats: dict,
                   style_c: dict | None = None, chapters: dict | None = None) -> str:
    return env.get_template("parallel.html.j2").render(
        work=work, pairs=pairs, stats=stats, style_c=style_c or None,
        chapters=chapters, chapter_anchor="seg",
        url=make_url(1), asset=make_asset(1),
        **page_meta(f"works/{work['id']}_parallel.html",
                    f"{work.get('title_en') or work.get('title')}: Latin source "
                    f"and English translation, segment by segment.", nav="works"),
    )


def build_style_c_page(env: Environment, work: dict, content_type: dict,
                       style_c: dict | None = None) -> str:
    """Per-content-type Style C subpage: `works/<id>_style-c-<type>.html`.
    `style_c` is the full per-work dict, used for sibling content-type nav."""
    siblings = [
        {"key": k, "label": v["label"], "n": v["n"]}
        for k, v in (style_c or {}).items()
    ]
    return env.get_template("style_c.html.j2").render(
        work=work, content_type=content_type, siblings=siblings,
        url=make_url(1), asset=make_asset(1),
        **page_meta(f"works/{work['id']}_style-c-{content_type['key']}.html",
                    f"{work.get('title_en') or work.get('title')} — "
                    f"{content_type['label']}, shown beside the source "
                    f"facsimiles.", nav="works"),
    )


def copy_static() -> None:
    """Mirror site/static into dist incrementally. The facsimile tree is
    ~2,000 images; a delete-and-recopy on every build wastes minutes, so copy
    only missing/stale files instead. (Renamed/removed statics may linger in
    dist until a manual clean — acceptable for this repo.)"""
    static_out = OUT / "static"
    copied = 0
    for src in STATIC.rglob("*"):
        if not src.is_file():
            continue
        dst = static_out / src.relative_to(STATIC)
        if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied += 1
    if copied:
        print(f"  static: copied {copied} new/updated files")


def write_sitemap(paths: list[str]) -> None:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p in paths:
        lines.append(f"  <url><loc>{html_lib.escape(SITE_BASE + p)}</loc></url>")
    lines.append("</urlset>")
    (OUT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE}sitemap.xml\n",
        encoding="utf-8")


def _slim_cipher_data_for_tools(path: Path) -> dict:
    """Load cipher-data.json and return a slimmed copy for inlining into the
    tools page. The full Ave Maria column set (~450KB, 895 columns) is mostly
    redundant for the encoder/decoder, so we keep ~24 clean, diverse columns
    (one per source chunk) — enough for column-rotation variety and the
    monoalphabetic mode — plus all spirits, numerical letters, and alphabet.
    This keeps the inlined payload small while every tool still works."""
    import collections
    data = json.loads(path.read_text(encoding="utf-8"))
    full_cols = [c for c in data["ave_maria"]["columns"] if len(c["words"]) >= 24]
    # one clean column per chunk, taking the first (col A) where available
    by_chunk: dict[str, dict] = collections.OrderedDict()
    for c in full_cols:
        by_chunk.setdefault(c["chunk"], c)
    slim_cols = list(by_chunk.values())[:24]
    return {
        "source": data.get("source", ""),
        "alphabet_24": data["alphabet_24"],
        "ave_maria": {"alphabet": data["ave_maria"]["alphabet"],
                      "columns": slim_cols, "chunk_count": data["ave_maria"]["chunk_count"]},
        "tabula_recta": data["tabula_recta"],
        "numerical_letters": data["numerical_letters"],
        "spirits": data["spirits"],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    copy_static()
    (OUT / ".nojekyll").write_text("", encoding="utf-8")

    env = make_env()
    manifest = load_manifest()
    works = [enrich_work(w) for w in manifest["works"] if not w["skip"]]
    attach_editions(works)
    texts = build_texts(works)
    sections = genre_sections(texts, load_clusters())
    # Work IDs for the random-work button (baked into each work page so the
    # button needs no fetch() — works on file://, HTTP, and GitHub Pages).
    global ALL_WORK_IDS
    ALL_WORK_IDS = [w["id"] for w in works]
    sitemap_paths: list[str] = ["index.html", "works.html", "scoreboard.html",
                                "ciphers.html", "cipher-solutions.html", "methodology.html",
                                "LICENSE.html"]

    (OUT / "index.html").write_text(
        build_index(env, manifest, works, texts, sections), encoding="utf-8")
    (OUT / "works.html").write_text(
        build_works_page(env, works, texts, sections), encoding="utf-8")
    (OUT / "scoreboard.html").write_text(build_scoreboard(env, works), encoding="utf-8")

    genres_out = OUT / "genres"
    genres_out.mkdir(exist_ok=True)
    for section in sections:
        (genres_out / f"{section['slug']}.html").write_text(
            build_genre_page(env, section), encoding="utf-8")
        sitemap_paths.append(f"genres/{section['slug']}.html")

    if CIPHERS_MD.exists():
        (OUT / "ciphers.html").write_text(
            render_simple_page(
                env, "The Ciphers of Trithemius",
                render_markdown_file(CIPHERS_MD), "ciphers.html",
                description="The Ave Maria cipher, the tabula recta expansion "
                            "figures, and the Steganographia's letter-pair "
                            "claves — with the Clavis ciphers decoded.",
                nav="ciphers"),
            encoding="utf-8")

    # Methodology is the single authoritative docs page: pipeline + method +
    # limitations merged (PIPELINE.md and LIMITATIONS.md were folded in and
    # removed). See the §-anchors in METHODOLOGY.md for the structure.
    (OUT / "methodology.html").write_text(
        render_simple_page(env, "Methodology", render_markdown_file(ROOT / "METHODOLOGY.md"), "methodology.html",
                           description="How the Trithemius Corpus was made: the OCR, translation, and grading "
                                       "pipeline, per-work model provenance, and honest limitations.",
                           nav="methodology"),
        encoding="utf-8",
    )
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    license_html = f"<h2>License</h2>\n<pre>{html_lib.escape(license_text)}</pre>"
    (OUT / "LICENSE.html").write_text(
        render_simple_page(env, "License", license_html, "LICENSE.html"),
        encoding="utf-8",
    )

    # 404 page (sits at the site root, so depth 0)
    (OUT / "404.html").write_text(
        env.get_template("404.html.j2").render(
            url=make_url(0), asset=make_asset(0),
            **page_meta("404.html", "Page not found"),
        ),
        encoding="utf-8",
    )

    # Search page (sits at the site root, so depth 0 — no ../ prefix)
    (OUT / "search.html").write_text(
        env.get_template("search.html.j2").render(
            url=make_url(0), asset=make_asset(0),
            **page_meta("search.html", "Search the Trithemius Corpus — full-text search across all 47 works", nav="works"),
        ),
        encoding="utf-8",
    )

    # Cipher Lab — interactive encoder/decoder, tabula recta, spirit index.
    # Lives at the site root (depth 0) and is wired into the main nav. The cipher
    # data is INLINED into the page (as window.CIPHER_DATA) so the tools work
    # even when opened from file:// — a fetch() of a sibling JSON is blocked by
    # the browser under the file scheme. A slimmed subset is embedded: the full
    # ave_maria column set is ~450KB and mostly redundant for the tools, so we
    # keep a representative ~24 clean columns (enough for the encoder's
    # column-rotation) plus all spirits, numerical letters, and the alphabet.
    cipher_tools_data = _slim_cipher_data_for_tools(STATIC / "cipher-data.json")
    (OUT / "tools.html").write_text(
        env.get_template("tools.html.j2").render(
            url=make_url(0), asset=make_asset(0),
            cipher_data_json=json.dumps(cipher_tools_data, ensure_ascii=False),
            **page_meta("tools.html", "Interactive cipher tools — encode and decode with Trithemius's own tables, explore the tabula recta, and consult the Steganographia spirits.", nav="tools"),
        ),
        encoding="utf-8",
    )

    # Cipher solutions — rendered from the cryptanalysis pass as a themed partial
    # (inline card CSS + base64 facsimile crops) and wrapped through the site's
    # base template so it inherits the main index theme, header, nav, footer,
    # and theme switcher (see CIPHER_DECODE_FINDINGS.md).
    cipher_solutions_src = Path(r"E:\trithemius\cipher_solutions.html")
    if cipher_solutions_src.exists():
        partial = cipher_solutions_src.read_text(encoding="utf-8")
        partial = partial.replace('href="../works/', 'href="works/')
        (OUT / "cipher-solutions.html").write_text(
            render_simple_page(
                env, "Solved Ciphers", partial, "cipher-solutions.html",
                description="The Clavis Generalis Triplex ciphers, solved: eleven modi decoded "
                            "into their hidden German plaintexts.",
                nav="ciphers"),
            encoding="utf-8",
        )

    # Lateral nav: other texts shelved under the same genre (different text
    # group), shown at the bottom of each work page.
    text_key_by_id = {}
    for t in texts:
        for e in t["editions"]:
            text_key_by_id[e["id"]] = t["key"]
    related_by_id: dict[str, list[dict]] = {}
    for t in texts:
        same_genre = [o for o in texts if o["genre"] == t["genre"] and o["key"] != t["key"]]
        rel = [{"id": o["rep"]["id"], "title": o["title"], "title_en": o["title_en"],
                "year": o["year"]} for o in same_genre[:4]]
        for e in t["editions"]:
            related_by_id[e["id"]] = rel

    works_out = OUT / "works"
    works_out.mkdir(exist_ok=True)
    # Clean stale work files from previous builds (old slugs renamed since).
    # Keep only files whose prdl- prefix matches a current manifest work id.
    current_ids = {w["id"] for w in works}
    for f in works_out.glob("prdl-*.html"):
        # extract the prdl-NNNNN_slug from the filename (strip _parallel/_style-c-* suffixes)
        stem = f.name
        for suffix in ("_parallel.html", ".html"):
            if stem.endswith(suffix):
                stem = stem[:-len(suffix)]
                break
        for suffix in ("_style-c-cipher-key", "_style-c-cipher-grid",
                       "_style-c-prose-damaged", "_style-c-untranslated"):
            if stem.endswith(suffix):
                stem = stem[:-len(suffix)]
                break
        # check if this stem is one of the current ids, OR a style-c subfile of one
        matched = any(stem == cid or stem.startswith(cid + "_style-c") for cid in current_ids)
        if not matched:
            f.unlink()
    n_parallel = 0
    n_style_c_pages = 0
    n_untranslated_display = 0
    misaligned: list[str] = []
    for w in works:
        pairs, stats = load_pairs(w["id"])
        has_parallel = bool(pairs)
        style_c = load_style_c(w)
        chapters = load_chapters(w["id"])
        if has_parallel:
            (works_out / f"{w['id']}_parallel.html").write_text(
                build_parallel(env, w, pairs, stats, style_c, chapters), encoding="utf-8")
            n_parallel += 1
            sitemap_paths.append(f"works/{w['id']}_parallel.html")
            n_untranslated_display += stats.get("n_missing", 0)
            if not stats["aligned"]:
                misaligned.append(f"{w['id']} (L={stats['n_latin']} E={stats['n_english']})")
        for ct_key, ct_data in style_c.items():
            (works_out / f"{w['id']}_style-c-{ct_key}.html").write_text(
                build_style_c_page(env, w, ct_data, style_c), encoding="utf-8")
            sitemap_paths.append(f"works/{w['id']}_style-c-{ct_key}.html")
            n_style_c_pages += 1
        inline_style_c = _style_c_inline_lookup(w, style_c)
        english_html = stitch_english(pairs, chapters, inline_style_c=inline_style_c) if pairs else ""
        # prev/next work navigation (by manifest order)
        wi = works.index(w)
        prev_id = works[wi-1]["id"] if wi > 0 else None
        next_id = works[wi+1]["id"] if wi < len(works)-1 else None
        (works_out / f"{w['id']}.html").write_text(
            build_work(env, w, english_html, has_parallel, style_c, chapters,
                       related_by_id.get(w["id"]),
                       prev_work_id=prev_id, next_work_id=next_id),
            encoding="utf-8")
        sitemap_paths.append(f"works/{w['id']}.html")

    write_sitemap(sitemap_paths)

    print(f"wrote site to {OUT.relative_to(ROOT)}/")
    print(f"  index, works ({len(texts)} texts), scoreboard, "
          f"{len(sections)} genre pages, ciphers, methodology, limitations, LICENSE")
    print(f"  {len(works)} work pages; {n_parallel} parallel viewers; "
          f"{n_style_c_pages} Style C subpages")
    print(f"  sitemap.xml ({len(sitemap_paths)} urls) + robots.txt")
    if misaligned:
        print(f"  [warn] {len(misaligned)} works had Latin/English count mismatch:")
        for m in misaligned:
            print(f"         {m}")
    else:
        print(f"  all parallel viewers have stable segment numbering")
    if n_untranslated_display:
        print(f"  {n_untranslated_display} Latin display segments have no English artifact "
              f"(marked in the viewer)")


if __name__ == "__main__":
    main()
