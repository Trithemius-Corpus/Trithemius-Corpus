"""Display-only reading-text cleanup for the prose/history T4B volumes.

The files in ``works-t4b`` are archival witnesses and are deliberately never
rewritten.  This module removes scan and printing furniture while assembling a
continuous Markdown reading text for the site builder.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


HANDLED = {
    "prdl-24361", "prdl-24362", "prdl-24363", "prdl-24368",
    "prdl-24371", "prdl-24372", "prdl-24373", "prdl-24375",
    "prdl-24378", "prdl-24379", "prdl-24381", "prdl-24382",
    "prdl-32286", "prdl-70286",
}

_PAGE = re.compile(r"(?m)^--- Page (\d+) ---\s*$")
_SEGMENT = re.compile(r"(?m)^\[segment \d+\]\s*$")
_BRACKETED_DEBRIS = re.compile(
    r"^\[(?:Page\s+\d+|blank page|book cover; no translatable text\.?|no discernible text|"
    r"fragmentary text and digitization target|digitization (?:color-)?calibration target[^]]*|"
    r"OCR-(?:damaged|duplicate)[^]]*|OCR repetition:[^]]*|duplicate scan leaves[^]]*)\]$",
    re.I,
)
_SCAN_DEBRIS = re.compile(
    r"(?:urn:nbn:|digitalfoto-trainer\.de|Gray Scale|Bavarian State Library|"
    r"ROYAL LIBRARY(?: OF MUNICH)?|BIBLIOTHECA REGIA MONACENSIS|MUNICH CONVENT|"
    r"Herzog August (?:Library|Bibliothek)|Wolfenb[�Ã¼]ttel|"
    r"^<?\d{10,}|^\d(?:\s+\d){5,})",
    re.I,
)
_OCTO_HEAD = re.compile(
    r"^QUESTION(?:S)?\.?$|"
    r"^(?:(?:IO|JO)H?AN(?:NES|N)?\.?|JOH\.|IOH\.)[^\n]{0,60}(?:TRIT|TRITHEMIUS|TRITTEN)[^\n]{0,60}$|"
    r"^\*?To Maximilian Caesar\.\*?$",
    re.I,
)
_QUESTION_ORDINAL = re.compile(
    r"^(?:THE )?(?:(FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH) QUESTION|"
    r"QUESTION (ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT))\.?$", re.I,
)
_TERMINAL = re.compile(r"[.!?][\"'”’)]*$")
_HEADING = re.compile(
    r"^(?:Here (?:begins|ends)\b|(?:The )?(?:First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth) "
    r"Question\b|Question (?:One|Two|Three|Four|Five|Six|Seven|Eight)\b|"
    r"Chapter (?:\d+|[IVXLCDM]+)\b|Book (?:One|Two|Three|Four|[IVXLCDM]+)\b|"
    r"Conclusion\b|Preface\b|Prologue\b)", re.I,
)


@dataclass
class _PageText:
    number: int
    paragraphs: list[str]


def _one_line(paragraph: str) -> str:
    return " ".join(paragraph.split())


def _is_debris(paragraph: str) -> bool:
    p = _one_line(paragraph)
    if not p:
        return True
    if _BRACKETED_DEBRIS.fullmatch(p) or _SCAN_DEBRIS.search(p):
        return True
    if re.fullmatch(r"(?:\d+|[A-Z]|[IVXLCDM]{1,4})\.?", p):
        return True
    if re.fullmatch(r"(?:4�\s+)?(?:Inc\.|P\.\s*lat\.)[^\n]{0,85}", p, re.I):
        return True
    return False


def _pages(text: str, octo: bool) -> list[_PageText]:
    text = _SEGMENT.sub("", text)
    marks = list(_PAGE.finditer(text))
    if not marks:
        raw_pages = [(0, text)]
    else:
        raw_pages = [
            (int(mark.group(1)), text[mark.end(): marks[i + 1].start() if i + 1 < len(marks) else len(text)])
            for i, mark in enumerate(marks)
        ]
    pages: list[_PageText] = []
    for number, body in raw_pages:
        paragraphs = [_one_line(p) for p in re.split(r"\n\s*\n", body) if p.strip()]
        paragraphs = [p for p in paragraphs if not _is_debris(p)]
        if octo:
            paragraphs = [p for p in paragraphs if not _OCTO_HEAD.fullmatch(p)]
        pages.append(_PageText(number, paragraphs))
    return pages


def _catchword(last: str, first: str) -> bool:
    word = last.strip(" *.,:;—–")
    if not word or len(word) > 32 or len(word.split()) > 3:
        return False
    stem = word.rstrip("-").lower()
    following = first.lstrip("*# ").lower()
    return following == stem or following.startswith(stem + " ") or (
        word.endswith("-") and following.startswith(stem)
    )


def _join_turn(left: str, right: str) -> bool:
    """Join only page turns that visibly interrupt a sentence."""
    if not left or not right or _HEADING.match(right):
        return False
    first = right.lstrip("*# \"'“‘(")[:1]
    return not _TERMINAL.search(left.rstrip()) or (first and first.islower())


def _as_heading(paragraph: str) -> str:
    plain = paragraph.strip(" *")
    if _HEADING.match(plain) and len(plain) <= 180:
        return "## " + plain.rstrip(".")
    # Genuine question titles in these editions normally carry a subtitle;
    # bare QUESTION TWO forms have already been discarded as running heads.
    if re.match(r"^(?:THE )?(?:FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH) QUESTION[:,.]", plain, re.I):
        return "## " + plain.rstrip(".")
    if len(plain) <= 180 and re.search(r"\bChapter\s+(?:\d+|[IVXLCDM]+)\.?$", plain, re.I):
        return "## " + plain.strip("* ").rstrip(".")
    return paragraph


def _clean_octo_inline(paragraph: str) -> str:
    """Remove running heads absorbed into neighboring OCR paragraphs."""
    p = paragraph
    p = re.sub(r"(?:^|\s)\*?(?:To|TO (?:EMPEROR )?) Maximilian Caesar\.?\*?\s*\d*", " ", p, flags=re.I)
    p = re.sub(r"(?:^|\s)\d+\s+\*?(?:Johannes|IOA\.|IOH\.)\s+Trit(?:hemius|emii|emius)[^*\n.]{0,30}\*?\.?", " ", p, flags=re.I)
    p = re.sub(r"(?:^|\s)IOA\.\s+TRITEMII\s+OCTO\s+QVAEST\.?", " ", p, flags=re.I)
    p = re.sub(r"^\[Page\s+\d+\]\s*", "", p, flags=re.I)
    p = re.sub(r"^\*?Johannes Trithemius, Eight Questions\.?\*?$", "", p, flags=re.I)
    p = re.sub(r"^TO (?:EMPEROR )?MAXIMILIAN(?: CAESAR)?\.?\s*\d*$", "", p, flags=re.I)
    return re.sub(r"\s{2,}", " ", p).strip()


def _polish_de_cura(text: str) -> str:
    """Targeted reading-view repairs for the 1496 pastoral oration."""
    # The first scan leaves combine a modern catalogue card with the original
    # title page.  The bibliographic facts already appear in the page header.
    text = re.sub(
        r"^Trithemius, Johannes On pastoral care, Seligenstadt, 1 May 1496 "
        r"On pastoral care\. ",
        "On Pastoral Care. ",
        text,
    )
    text = re.sub(r"\n\nIV\.12\.\n\n", "\n\n", text)

    # Two scan boundaries repeat the end of the preceding line at the start
    # of the next leaf.  Keep the complete continuation in each case.
    text = text.replace(
        "This consideration of the first commission of the pastoral office commands you "
        "Consideration of the pastoral office enjoins this upon you:",
        "Consideration of the pastoral office enjoins this upon you:",
    )
    text = text.replace("can easily repel. easily drive away;", "can easily drive away;")

    # These are the oration's genuine structural divisions, not running heads.
    text = re.sub(r"(?m)^Feed by word\.?$", "## Feed by word", text)
    text = re.sub(
        r"(?m)^(Feed by example|Third: feed them with nourishment)\.\s+",
        lambda m: "## " + m.group(1) + "\n\n",
        text,
    )
    return text


def _polish_scriptorum(text: str) -> str:
    """Restore the sixteen-chapter structure of *De laude scriptorum*."""
    # Omit the OCR table of contents from the continuous reading stream.  Its
    # inconsistent medieval numerals were being mistaken for page headings.
    text = re.sub(
        r"\n\nThe chapters of the present work On the Praise of Scribes follow\..*?"
        r"Here end the chapters of this book On the Praise of Scribes\.\n\n",
        "\n\n",
        text,
        flags=re.S,
    )
    replacements = [
        (r"Begins the book of Dom Johannes Trithemius, abbot in Sponheim, On the Praise of Scribes, to Dom Gerlach, abbot of Deutz\.",
         "## Chapter I — In Praise of Scribes"),
        (r"(?:## )?The Commendation of the Usefulness of Sacred Scripture\.\s+(?:## )?Chapter 2\.?",
         "## Chapter II — The Usefulness of Sacred Scripture"),
        (r"\*?On the diligence and love of the ancients toward books\.\*?\n\n## Chapter 3",
         "## Chapter III — The Diligence and Love of the Ancients toward Books"),
        (r"On the diligence of the ancients in writing books\.\n\n## Chapter 4",
         "## Chapter IV — The Diligence of the Ancients in Writing Books"),
        (r"That copying the books of the ancients is, as it were, the proper and fitting craft of monks\.",
         "## Chapter V — Why Copying Books Is a Fitting Craft for Monks"),
        (r"How good and useful it is for monks to write\. Chapter VI\.",
         "## Chapter VI — How Good and Useful It Is for Monks to Write"),
        (r"\*?That one must not cease from writing volumes because of printing\. Chapter VII\.\*?",
         "## Chapter VII — Why Printing Is No Reason to Cease Copying Books"),
        (r"On Orthography and the Manner of Writing\. Chapter 8\.",
         "## Chapter VIII — Orthography and the Manner of Writing"),
        (r"(?:b iij 14 )?Concerning Those Who Cannot Write\. Chapter IX\.",
         "## Chapter IX — Those Who Cannot Write"),
        (r"Concerning the Material They Should Write\. Chapter X\.",
         "## Chapter X — What They Should Write"),
        (r"Whether Monks May Write on Feast Days\. Chapter 11\.",
         "## Chapter XI — Whether Monks May Write on Feast Days"),
        (r"Concerning the Difference between Scribes and the Names of Short Works\. Chapter XII\.",
         "## Chapter XII — Scribes and the Names of Short Works"),
        (r"On Instituting Scribes in Monasteries\. Chapter 14\.",
         "## Chapter XIII — Instituting Scribes in Monasteries"),
        (r"Whether it is commendable to have many books in monasteries\. Chapter XIV\.",
         "## Chapter XIV — Whether Monasteries Should Have Many Books"),
        (r"\*?On the Care and Cleanliness to Be Maintained for Books\.\*?\n\n## Chapter 15",
         "## Chapter XV — The Care and Cleanliness of Books"),
        (r"Exhortation to the Study and Love of the Scriptures\.\n\n## Chapter xvi",
         "## Chapter XVI — An Exhortation to Study and Love the Scriptures"),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.I)
    text = re.sub(r"(?m)^##\s*$\n?", "", text)
    # A page number was absorbed between the end of chapter VIII and IX.
    text = text.replace(" b iij 14 ## Chapter IX", "\n\n## Chapter IX")
    # Some title leaves were joined directly to the preceding paragraph at a
    # page turn. Markdown headings must start on their own block.
    text = re.sub(r"[ \t]+(## Chapter [IVXLCDM]+\b)", r"\n\n\1", text)
    return text


def _polish_carmelites(text: str) -> str:
    """Restore the two-book, twelve-chapter hierarchy of the Carmelite work."""
    text = re.sub(
        r"\n\n(?:## )?Here follows the table of chapters\..*?"
        r"(?:## )?On the saints and canonized persons from this order\. Chapter 12\.?\n\n",
        "\n\n",
        text,
        flags=re.S | re.I,
    )
    replacements = [
        (r"## Here begins the first book of lord Johannes Trithemius, abbot of Spanheim, On the Praises of the Order of the Carmelites",
         "## Book I — On the Praises of the Carmelite Order"),
        (r"On the beginning of the order\. Chapter 1\.",
         "## Chapter I — The Beginning of the Order"),
        (r"How Elijah the prophet of the Lord was the founder of the order of the Carmelites\. Chapter 2\.",
         "## Chapter II — Elijah as Founder of the Carmelite Order"),
        (r"## Chapter 3\s+On the manner of life of the sons of the prophets and of other hermits before the birth\. Chapter 3\.",
         "## Chapter III — The Sons of the Prophets and the Early Hermits"),
        (r"On when and in what manner the rule was given to the brothers dwelling on Mount Carmel\.\s+## Chapter 4",
         "## Chapter IV — When and How the Rule Was Given"),
        (r"\*?On the confirmation and approval of the order of Carmelites\. Chapter 5\.\*?",
         "## Chapter V — Confirmation and Approval of the Order"),
        (r"\*?On the change of the brothers[’'] outer habit\. Chapter 6\.\*?",
         "## Chapter VI — The Change in the Brothers’ Habit"),
        (r"Why the Carmelite Brothers Are Called Brothers of Blessed Mary Ever-Virgin of Mount Carmel\.\s+## Chapter 8",
         "## Chapter VII — Why They Are Called Brothers of the Virgin Mary"),
        (r"\*?On the Migration of the Brothers into Europe\. Chapter 8\.\*?",
         "## Chapter VIII — The Migration of the Brothers into Europe"),
        (r"On the manifold persecution of this most holy order, and its victory against its rivals\. Chapter IX\.",
         "## Chapter IX — The Order’s Persecution and Victory"),
        (r"On the first advance of the order of the brothers in Europe, and on the multiplication of its convents\. Chapter x\.",
         "## Chapter X — The Order’s Growth in Europe"),
        (r"How useful and fruitful the order of Carmelites is in the church\. Chapter xi\.",
         "## Chapter XI — The Usefulness of the Carmelite Order in the Church"),
        (r"On the saints and canonized persons from this order\.\s+## Chapter 12",
         "## Chapter XII — Saints and Canonized Members of the Order"),
        (r"## Here ends the first book\s+## Here begins the second book of Lord Johannes Trithemius, abbot of Sponheim, on the illustrious men of the Carmelite order",
         "## Book II — Illustrious Men of the Carmelite Order"),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.I)
    text = re.sub(
        r"(?mi)^## Chapter 3\s+## On the manner of life of the sons of the prophets",
        "## On the manner of life of the sons of the prophets",
        text,
    )
    text = re.sub(r"(?m)^\[Page\s+\d+\]\s*$", "", text, flags=re.I)
    text = re.sub(r"[ \t]+(## (?:Book|Chapter)\b)", r"\n\n\1", text)
    return text


def _polish_divine_love(text: str) -> str:
    """Clean and structure the continuous 1497 Erfurt chapter oration."""
    # Replace catalogue-card and damaged title-leaf OCR with a proper title.
    text = re.sub(
        r"^Trithemius, Johannes\. On the Working of Divine Love\. Erfurt, 27 August 1497\.\s+"
        r"4° he\.50 1875 Trithemius Flain 15636 vey On the Working of Divine Love\.",
        "## On the Working of Divine Love",
        text,
    )
    # Page 009 is a manifestly unrelated model hallucination: a long modern
    # botanical inventory absent from this theological oration.
    text = re.sub(
        r"\n\nThings of this kind are Alicteae,.*?and so forth\.\n\n",
        "\n\n",
        text,
        flags=re.S,
    )
    sections = [
        (r"And first, indeed, when the love of God is in a person,", "I — Contrition and Repentance", "When the love of God is in a person,"),
        (r"Secondly, the love of God mortifies all bestial passions in a human being,", "II — The Mortification of the Passions", "The love of God mortifies all bestial passions in a human being,"),
        (r"Third, the love of God makes the one who has it despise all things and love absolutely nothing in this world\.", "III — Contempt of Worldly Things", "The love of God makes the one who has it despise all things and love absolutely nothing in this world."),
        (r"Fourth, the love of God generates wondrous compunction and devotion in its host,", "IV — Compunction and Devotion", "The love of God generates wondrous compunction and devotion in its host,"),
        (r"Fifth, divine love illumines the understanding of the one who has it with a wonderful teaching,", "V — Illumination of the Understanding", "Divine love illumines the understanding of the one who has it with a wonderful teaching,"),
        (r"Sixth, divine love raises the mind to heavenly things,", "VI — Elevation to Heavenly Things", "Divine love raises the mind to heavenly things,"),
        (r"Seventh, the sweetness of divine love makes one despise death and long with continual sighs for the homeland of heavenly happiness\.", "VII — Contempt of Death and Longing for Heaven", "The sweetness of divine love makes one despise death and long with continual sighs for the homeland of heavenly happiness."),
        (r"Eighth, divine love makes the soul of its host, while still established in the flesh, known and familiar to the citizens of the heavenly fatherland,", "VIII — Fellowship with the Citizens of Heaven", "Divine love makes the soul of its host, while still established in the flesh, known and familiar to the citizens of the heavenly fatherland,"),
        (r"Ninth, divine love effects an inestimable adhesion of union between God and the soul,", "IX — Union between God and the Soul", "Divine love effects an inestimable adhesion of union between God and the soul,"),
        (r"Tenth, the love of God rewards the soul that truly possesses it in the heavenly homeland with an incomparable gift,", "X — The Heavenly Reward of Divine Love", "The love of God rewards the soul that truly possesses it in the heavenly homeland with an incomparable gift,"),
    ]
    for pattern, heading, continuation in sections:
        text = re.sub(pattern, f"## {heading}\n\n{continuation}", text, count=1)
    text = re.sub(r"[ \t]+(## (?:[IVX]+\s+—|On the Working))", r"\n\n\1", text)
    return text


def _polish_commonwealth(text: str) -> str:
    """Clean the continuous 1493 Cologne chapter discourse."""
    paragraphs = text.split("\n\n")
    # The scan contains the opening four paragraphs twice on successive leaves.
    for width in range(8, 1, -1):
        removed = False
        for i in range(1, len(paragraphs) - 2 * width + 1):
            if paragraphs[i:i + width] == paragraphs[i + width:i + 2 * width]:
                del paragraphs[i + width:i + 2 * width]
                removed = True
                break
        if removed:
            break
    text = "\n\n".join(paragraphs)
    text = re.sub(
        r"^Trithemius, Johannes On the Commonwealth of the Church and of the Monks of the Order of the Holy Father Benedict\. Cologne, 1 September 1493\.\s+"
        r"4° Inc\. 59\. 1869b Trithemius Hain \+ 15630 ",
        "## On the Commonwealth of the Church and of the Monks of the Order of Saint Benedict\n\n",
        text,
    )
    transitions = [
        (r"And to begin with the general commonwealth,", "The Commonwealth of the Church", "To begin with the general commonwealth,"),
        (r"The commonwealth, therefore, about which we intend to speak, is our most sacred order,", "The Commonwealth of the Benedictine Order", "The commonwealth about which we intend to speak is our most sacred order,"),
        (r"But where now is such study among monks\?", "The Present Decline of the Order", "But where now is such study among monks?"),
        (r"Behold, reverend fathers, we have briefly heard what the condition of our commonwealth is; it remains now for us to think about its remedy\.", "The Remedy: Reform of the Order", "Behold, reverend fathers, we have briefly heard what the condition of our commonwealth is; it remains now for us to think about its remedy."),
    ]
    for pattern, heading, continuation in transitions:
        text = re.sub(pattern, f"## {heading}\n\n{continuation}", text, count=1)
    # Alternate wording in the second printed witness of the same discourse.
    alternates = [
        (r"And, to begin with the general commonwealth,", "The Commonwealth of the Church", "To begin with the general commonwealth,"),
        (r"Now at last, then, venerable fathers, after the long discourse on the common commonwealth, which, persuaded by my elders, I have held as best I could, let us turn to our own commonwealth, which concerns us more closely\.", "The Commonwealth of the Benedictine Order", "Now at last, venerable fathers, let us turn to our own commonwealth, which concerns us more closely."),
        (r"But where now is such zeal among monks\?", "The Present Decline of the Order", "But where now is such zeal among monks?"),
        (r"Behold, reverend fathers, we have briefly heard what the condition of our commonwealth is; it remains now that we consider its remedy\.", "The Remedy: Reform of the Order", "Behold, reverend fathers, we have briefly heard what the condition of our commonwealth is; it remains now that we consider its remedy."),
    ]
    for pattern, heading, continuation in alternates:
        if f"## {heading}" not in text:
            text = re.sub(pattern, f"## {heading}\n\n{continuation}", text, count=1)
    text = re.sub(r"[ \t]+(## (?:The Commonwealth|The Present|The Remedy))", r"\n\n\1", text)
    return text


def clean(work_id: str, text: str) -> str | None:
    """Return continuous clean Markdown, or ``None`` for an unhandled work."""
    key = next((prefix for prefix in HANDLED if work_id.startswith(prefix)), None)
    if key is None:
        return None
    pages = _pages(text, octo=key in {"prdl-24381", "prdl-24382", "prdl-32286", "prdl-70286"})
    out: list[str] = []
    octo = key in {"prdl-24381", "prdl-24382", "prdl-32286", "prdl-70286"}
    seen_questions: set[str] = set()
    for page in pages:
        current: list[str] = []
        for paragraph in page.paragraphs:
            if octo:
                paragraph = _clean_octo_inline(paragraph)
                intro = re.match(
                    r"^(?:The|Your Serenity[’']s)\s+"
                    r"(first|second|third|fourth|fifth|sixth|seventh|eighth)\s+question\b",
                    paragraph, re.I,
                )
                if intro:
                    ordinal = intro.group(1).lower()
                    if ordinal not in seen_questions:
                        seen_questions.add(ordinal)
                        current.append("## Question " + ordinal.title())
                question_text = paragraph.strip("#* ")
                question = _QUESTION_ORDINAL.fullmatch(question_text)
                if question:
                    ordinal = (question.group(1) or question.group(2)).lower()
                    if ordinal in seen_questions:
                        continue
                    seen_questions.add(ordinal)
                    paragraph = "## " + question_text.rstrip(".").title()
                if re.fullmatch(r"CONCERNING THE REPROBATE", paragraph, re.I):
                    paragraph = "## Question Five — Concerning the Reprobate"
                    seen_questions.add("fifth")
                elif re.fullmatch(r"(?:ON THE POWER\s+)?Of Witches\. Question Six\.", paragraph, re.I):
                    paragraph = "## Question Six — On the Power of Witches"
                    seen_questions.add("sixth")
            if paragraph:
                current.append(paragraph)
        if not current:
            continue
        if out and _catchword(out[-1], current[0]):
            out.pop()
        if out and current and not out[-1].startswith("#") and _join_turn(out[-1], current[0]):
            # A hyphen at a page turn is an OCR line-break hyphen; otherwise a
            # normal space is required between the two translated fragments.
            glue = "" if out[-1].endswith("-") else " "
            out[-1] = out[-1].rstrip("-") + glue + current.pop(0).lstrip()
        out.extend(current)
    rendered = "\n\n".join(p if p.startswith("## ") else _as_heading(p) for p in out).strip()
    if key == "prdl-24361":
        rendered = _polish_de_cura(rendered)
    elif key == "prdl-24362":
        rendered = _polish_scriptorum(rendered)
    elif key == "prdl-24363":
        rendered = _polish_carmelites(rendered)
    elif key == "prdl-24368":
        rendered = _polish_divine_love(rendered)
    elif key in {"prdl-24371", "prdl-24372"}:
        rendered = _polish_commonwealth(rendered)
    return re.sub(r"\n{3,}", "\n\n", rendered)


def self_check() -> None:
    sample = """[segment 1]\n--- Page 1 ---\nA sentence that crosses\n\nCatch-\n--- Page 2 ---\nCatchword continuation.\n\nROYAL LIBRARY OF MUNICH\n--- Page 3 ---\nChapter 2. The subject\n\nBody.\n"""
    got = clean("prdl-24361_example", sample)
    assert got is not None
    assert "Page" not in got and "LIBRARY" not in got and "segment" not in got
    assert "crosses Catchword continuation" in got
    assert "## Chapter 2" in got
    assert clean("unhandled", sample) is None


if __name__ == "__main__":
    self_check()
    print("t4b_cleaners_prose: self-check passed")
