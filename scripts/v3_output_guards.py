"""V3 translation-output guardrails.

The corpus rerun needs mechanical checks that fail before a bad translation is
cached as complete. These guards are intentionally conservative: marker drift,
assistant preambles, and repeated-line loops are always structural issues;
source-anchor checks are available as a stricter production gate.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any


OUTPUT_PAGE_RE = re.compile(r"^---\s*Page\s+0*(\d+)\s*---\s*$", re.M)
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9'._-]{2,}|\d{2,}")

COMMON_LATIN_CAPS = {
    "AD",
    "ANNO",
    "CAP",
    "CAPUT",
    "DE",
    "DOMINI",
    "EGO",
    "ET",
    "IN",
    "IOANNES",
    "LIBER",
    "NON",
    "PAGE",
    "PROLOGUS",
    "QUI",
    "QUOD",
    "REVERENDO",
    "SANCTI",
}

PREAMBLE_PREFIXES = (
    "here is",
    "here's",
    "certainly",
    "sure,",
    "the translation is",
    "translation:",
    "```",
)


def output_pages(text: str) -> list[int]:
    return [int(match.group(1)) for match in OUTPUT_PAGE_RE.finditer(text or "")]


def normalize_token(token: str) -> str:
    return re.sub(r"[^a-z0-9]", "", token.lower())


def _first_text_line(text: str) -> str:
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _has_preamble(text: str) -> bool:
    first = _first_text_line(text).lower()
    return any(first.startswith(prefix) for prefix in PREAMBLE_PREFIXES)


def _has_repetition_loop(text: str) -> bool:
    lines = [
        re.sub(r"\s+", " ", line.strip()).lower()
        for line in (text or "").splitlines()
        if len(line.strip()) >= 16 and not OUTPUT_PAGE_RE.match(line.strip())
    ]
    if any(count >= 3 for count in Counter(lines).values()):
        return True

    compact = re.sub(r"\s+", " ", (text or "").lower())
    if len(compact) < 240:
        return False
    windows = [compact[i : i + 48] for i in range(0, max(0, len(compact) - 48), 16)]
    return any(count >= 6 for count in Counter(windows).values())


def source_anchor_tokens(source_text: str, limit: int = 12) -> list[str]:
    """Return source tokens that should usually survive translation.

    We focus on numbers and proper-name-like tokens because ordinary Latin
    vocabulary should not be copied into English.
    """

    anchors: list[str] = []
    seen: set[str] = set()
    for raw in TOKEN_RE.findall(source_text or ""):
        norm = normalize_token(raw)
        if len(norm) < 3 or norm in seen:
            continue
        is_number = any(char.isdigit() for char in raw)
        is_name = raw[:1].isupper() and raw.upper() not in COMMON_LATIN_CAPS
        is_roman_year = bool(re.fullmatch(r"[MDCLXVI]{3,}", raw.upper()))
        if not (is_number or is_name or is_roman_year):
            continue
        anchors.append(raw)
        seen.add(norm)
        if len(anchors) >= limit:
            break
    return anchors


def _anchor_hits(source_text: str, output_text: str) -> tuple[list[str], list[str]]:
    anchors = source_anchor_tokens(source_text)
    output_norm = " ".join(normalize_token(token) for token in TOKEN_RE.findall(output_text or ""))
    hits = [anchor for anchor in anchors if normalize_token(anchor) in output_norm]
    misses = [anchor for anchor in anchors if anchor not in hits]
    return hits, misses


# Thresholds for the strengthened fidelity checks. A chunk is flagged when
# BOTH the source has enough signal to judge AND overlap falls below the floor.
# Calibrated on the v2 dual-context lane: faithful chunks (S/A grade) clear
# these comfortably; drifted chunks (translating a different page/sermon) do not.
ANCHOR_HIT_RATIO_FLOOR = 0.15  # <15% of name/year anchors surviving => drift
CONTENT_OVERLAP_RATIO_FLOOR = 0.15  # <15% of Latin content-word stems in English
CONTENT_OVERLAP_MIN_SOURCE_WORDS = 8  # don't judge chunks with too little Latin

# Common Latin stopwords to exclude from the overlap signal. These translate to
# short English function words or unrelated cognates, so they produce noise.
_LATIN_STOPWORDS = {
    "que", "neque", "nec", "autem", "enim", "igitur", "nam", "quia", "quoniam",
    "cum", "dum", "quam", "qui", "quae", "quod", "cuius", "cui", "quo",
    "eius", "eum", "eam", "eo", "ea", "huius", "hic", "ille", "iste",
    "est", "sunt", "erat", "fuit", "esse", "fuisse", "huiusmodi", "eiusmodi",
    "tamen", "sed", "at", "vero", "etiam", "item", "quidem", "scilicet",
    "videlicet", "nempe", "ut", "sic", "sicut", "ita", "tam", "tunc", "nunc",
    "deinde", "inde", "hinc", "ex", "ab", "ad", "in", "per", "pro", "sub",
    "super", "inter", "contra", "ante", "post", "circa", "versus",
    "suo", "sua", "suos", "suas", "eiusdem", "eidem", "codem", "eadem",
    "quibus", "quarum", "quorum", "quos", "quas", "quibusdam",
    "omnibus", "omnium", "multa", "multae", "multorum",
    "necnon", "scilicet", "videlicet", "utinam", "ecce", "en", "heu",
}


def _denoise_long_s(word: str) -> str:
    """Recover 's' from early-modern long-s set as 'f'.

    The OCR cleanup in the translation harness already maps the Unicode long-s
    (ſ) to 's', but blackletter 'f' between vowels is often a long-s in the
    source (e.g. ``iuftitiae`` -> ``iustitiae``). This heuristic converts
    word-internal 'f' to 's' only after vowels/i/u, where it is almost always
    the long-s, leaving genuine initial 'f' (``fides``, ``frater``) intact.
    """
    out = re.sub(r"(?<=[aeiouy])f", "s", word)
    out = re.sub(r"(?<=[iu])f", "s", out)
    return out


def _source_content_overlap(source_text: str, output_text: str) -> dict[str, Any]:
    """Measure how much Latin source vocabulary is reflected in the English.

    Catches page drift where the translation keeps the correct page markers but
    renders content from a different page. Proper-name anchors (above) catch
    catalogue/chronicle drift; this catches prose drift (sermons, treatises)
    where names are sparse but the theological register is dense with shared
    Latin/English cognates (iustitia->justice, scriptura->scripture,
    fides->faith, monachus->monk).

    Returns a ratio of Latin content-word stems that appear (as a 4-char
    prefix) in any English word, plus raw counts for the audit log.
    """
    latin_words = [
        _denoise_long_s(w.lower())
        for w in re.findall(r"[A-Za-z]{5,}", source_text or "")
    ]
    latin_words = [w for w in latin_words if w not in _LATIN_STOPWORDS]
    if not latin_words:
        return {"ratio": 1.0, "hits": 0, "source_words": 0}

    english_words = re.findall(r"[a-z]{5,}", (output_text or "").lower())
    english_blob = " ".join(english_words)

    hits = 0
    for lw in latin_words:
        stem = lw[:4]
        if stem in english_blob:
            hits += 1
    ratio = hits / len(latin_words)
    return {"ratio": ratio, "hits": hits, "source_words": len(latin_words)}


def validate_translation_output(
    *,
    output_text: str | None,
    expected_pages: list[int],
    source_text: str,
    require_source_anchor: bool = False,
) -> dict[str, Any]:
    """Validate page markers and basic structural fidelity.

    Returns a record with all issues and the subset that should block caching.
    """

    text = output_text or ""
    issues: list[str] = []
    blocking: list[str] = []
    expected = list(expected_pages or [])
    actual = output_pages(text)

    # Compute content overlap early so marker checks can use it: a faithful
    # translation that merely omits page markers (common with prose) should
    # not be blocked as drift. Markers + low overlap together signal drift.
    anchor_hits, anchor_misses = _anchor_hits(source_text, text)
    overlap = _source_content_overlap(source_text, text)
    overlap_low = (
        require_source_anchor
        and overlap["source_words"] >= CONTENT_OVERLAP_MIN_SOURCE_WORDS
        and overlap["ratio"] < CONTENT_OVERLAP_RATIO_FLOOR
    )

    if expected and actual != expected:
        issues.append("marker_set_mismatch")
        # Block on marker mismatch only when it indicates real drift: either the
        # output has DIFFERENT page numbers (translating the wrong page) or the
        # content overlap is also low. A faithful chunk that dropped its markers
        # (actual == []) with healthy overlap is a formatting gap, not drift.
        if actual and set(actual) != set(expected):
            blocking.append("marker_set_mismatch")
        elif overlap_low:
            blocking.append("marker_set_mismatch")
    if expected and not actual:
        issues.append("marker_drop")
        if overlap_low:
            blocking.append("marker_drop")
    if actual and len(actual) != len(set(actual)):
        issues.append("marker_duplicate")
        blocking.append("marker_duplicate")

    if _has_preamble(text):
        issues.append("preamble_leak")
        blocking.append("preamble_leak")
    if _has_repetition_loop(text):
        issues.append("repetition_loop")
        blocking.append("repetition_loop")

    if require_source_anchor:
        # Content-overlap is the primary drift signal: it measures how much
        # Latin source vocabulary is reflected in the English. Calibrated on
        # the v2 lane: faithful chunks median ~0.32, drifted chunks near 0.0.
        # Only judged when the source has enough content words to be reliable.
        if overlap_low:
            issues.append("source_content_overlap_low")
            blocking.append("source_content_overlap_low")

        # Name/number anchor check, gated on overlap so it does not over-fire
        # on faithful prose works (which have few extractable proper names).
        # Fires only when BOTH the name anchors largely missed AND the content
        # overlap is low — the conjunction is the real page-drift signature.
        anchor_total = len(anchor_hits) + len(anchor_misses)
        if anchor_total and len(anchor_hits) / anchor_total < ANCHOR_HIT_RATIO_FLOOR and overlap_low:
            issues.append("source_anchor_missing")
            blocking.append("source_anchor_missing")
        elif not anchor_total and overlap_low:
            issues.append("source_anchor_unavailable")

    return {
        "issues": issues,
        "blocking_issues": blocking,
        "expected_pages": expected,
        "output_pages": actual,
        "source_anchor_hits": anchor_hits,
        "source_anchor_misses": anchor_misses[:8],
        "source_content_overlap": overlap["ratio"],
        "source_overlap_hits": overlap["hits"],
        "source_overlap_words": overlap["source_words"],
        "require_source_anchor": require_source_anchor,
    }
