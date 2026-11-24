"""Check the relationships between source editions, reading pages and their indexes."""
import json
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

from lxml import html

import build_site as bs
import build_editorial_ledger
import scan_evidence
from edition_corrections import history, validate_history
from edition_metadata import QA_LABELS, credit
from passage_model import plain_text
from publication_guard import read_input, validate_tree
from publication_inventory import canonical_inventory


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_edition(dist: Path, meta: dict, record: dict, folder: str) -> int:
    relative = bs.reading_path(meta)
    page = dist / relative
    doc = html.fromstring(page.read_text(encoding="utf-8"))
    url = bs.SITE_BASE + relative
    citation = doc.xpath("//pre[@class='cite-block']/text()")
    require(len(citation) == 1 and citation[0].endswith(url), f"{relative}: citation points to another edition")
    source = doc.xpath("//a[normalize-space(.)='Repository folder']/@href")
    require(source == [f"https://github.com/Trithemius-Corpus/Trithemius-Corpus/tree/main/{folder}/{meta['id']}"],
            f"{relative}: wrong source folder")
    books = [json.loads(x) for x in doc.xpath("//script[@type='application/ld+json']/text()")]
    require(books == [bs.work_jsonld(meta)] and books[0]["url"] == url, f"{relative}: Book metadata differs")
    rows = {row.xpath("string(./th)"): " ".join(row.xpath("string(./td)").split())
            for row in doc.xpath("//section[@class='work-meta']//tr")}
    require(rows.get("Authorship") == credit(meta), f"{relative}: credit")
    require(rows["Automated QA"].startswith(QA_LABELS[record["automated_qa"]]), f"{relative}: audit scope")
    require("Full machine audit" not in rows["Automated QA"] or record["chunks_graded"] == record["chunks_total"],
            f"{relative}: incomplete audit labelled complete")
    if folder == "works-t4b":
        witness = meta.get("standard_witness", meta["id"])
        require(doc.xpath("//a[.='Earlier translation of this witness']/@href") == [f"{witness}.html"] and
                (page.parent / f"{witness}.html").is_file(), f"{relative}: corresponding earlier witness")
        return 0
    index = json.loads((dist / "data/passages" / f"{meta['id']}.json").read_text(encoding="utf-8"))
    return len(index["passages"])


def check_apparatus(dist: Path) -> int:
    total = 0
    for wid, record in read_input("passage-contract.json")["apparatus"].items():
        inputs = read_input(f"apparatus/{wid}.json")
        work = (dist / "works" / f"{wid}.html").read_text(encoding="utf-8")
        for kind, count in record["types"].items():
            filename = f"{wid}_style-c-{kind}.html"
            require(filename in work, f"{wid}: apparatus not linked: {kind}")
            page = html.fromstring((dist / "works" / filename).read_text(encoding="utf-8"))
            ids = page.xpath("//article[@class='style-c-chunk']/@id")
            require(len(ids) >= count and set(ids) >= {c["name"] for c in inputs[kind]["chunks"]},
                    f"{filename}: published apparatus missing")
            for src in page.xpath("//a[@class='facs-link']/@href | //a[@class='facs-link']/img/@src"):
                require((dist / "works" / urlsplit(src).path).is_file(), f"{filename}: missing facsimile {src}")
            total += len(ids)
    return total


def restored_passages(body, change: dict) -> dict:
    """Verify the recorded position of a restored passage before a previously cited block."""
    ids = change["added_passages"]
    blocks = change["after"].split("\n\n")
    require(ids and len(set(ids)) == len(ids) == len(blocks) - 1 and blocks[-1] == change["before"],
            f"{change['item_id']}: restored paragraphs differ from the archival edit")
    published = body.xpath('.//*[@id and starts-with(@id, "p-t4b-")]/@id')
    following = change["insert_before"]
    require(following in published, f"{change['item_id']}: original following passage is missing")
    end = published.index(following)
    require(end >= len(ids) and published[end - len(ids):end] == ids,
            f"{change['item_id']}: restored passages are out of position")
    return dict(zip(ids, blocks[:-1], strict=True))


def check_scan_revisions(dist: Path, records: dict) -> None:
    root = bs.ROOT
    corrected = {wid for (wid, _), record in records.items() if record.get("ai_corrections")}
    declared = {p.parent.name for p in (root / "data/translation_disagreements").glob("*/corrections.json")}
    require(corrected == declared, "Correction inventory differs from the edition records")
    # A collation can confirm the existing English. Its evidence is still published.
    assessed = {p.parent.name for p in (root / "data/translation_disagreements").glob("*/scan-assessments.json")}
    for wid in sorted(assessed - corrected):
        require((wid, "earlier") in records and bool(scan_evidence.load(root, wid)),
                f"{wid}: invalid witness assessment")
    for wid in sorted(corrected):
        batches = history(root, wid)
        validate_history(root, wid, batches)
        scans = scan_evidence.load(root, wid)
        for track, edition, suffix in (("earlier", "earlier", ""), ("t4b", "trithemius-4b", "-trithemius-4b")):
            edits = [(batch["date"], c) for batch in batches for c in batch["changes"] if c["track"] == track]
            metadata = records.get((wid, edition), {}).get("ai_corrections")
            require(bool(edits) == bool(metadata), f"{wid}/{track}: correction metadata differs")
            if not edits:
                continue
            require(metadata["count"] == len(edits) and metadata["date"] == edits[-1][0]
                    and metadata["human_review"] == "none_documented", f"{wid}/{track}: incorrect correction history")
            doc = html.fromstring((dist / "works" / f"{wid}{suffix}.html").read_text(encoding="utf-8"))
            body = doc.get_element_by_id("translation-text")
            errata = doc.get_element_by_id("errata")
            latest = {}
            for _, change in edits:
                require({change["item_id"], *change.get("supporting_scans", [])} <= scans.keys(),
                        f"{wid}: missing scan assessment for {change['item_id']}")
                for alias in change.get("resolved_annotations", []):
                    require(errata.get_element_by_id(alias, None) is not None, f"{wid}: retired note link {alias}")
                if change.get("passage"):
                    latest[change["item_id"], change["passage"]] = change.get("rendered_reading", change["after"])
                if "insert_before" in change:
                    for anchor, wording in restored_passages(body, change).items():
                        latest[change["item_id"], anchor] = wording
            for (_, anchor), wording in latest.items():
                node = body.get_element_by_id(anchor)
                if "passage-anchor" in node.get("class", "").split():
                    node = node.getnext()
                text = plain_text(html.tostring(node, encoding="unicode", with_tail=False))
                require(" ".join(wording.split()) in text, f"{wid}#{anchor}: revised reading missing")


def main():
    dist = bs.OUT
    validate_tree(dist)
    for path, expected in build_editorial_ledger.distribution_files().items():
        require(path.read_text(encoding="utf-8") == expected, f"Stale editorial records: {path.name}")
    ledger = build_editorial_ledger.payload()["editions"]
    records = {(r["id"], r["edition_track"]): r for r in ledger}
    check_scan_revisions(dist, records)
    catalogue = {w["id"]: w for w in bs.load_manifest()["works"] if not w["skip"]}
    passages = editions = 0
    for folder, track in (("works", "earlier"), ("works-t4b", "trithemius-4b")):
        for source in sorted((bs.ROOT / folder).glob("*/metadata.json")):
            meta = json.loads(source.read_text(encoding="utf-8"))
            if folder == "works":
                meta = {**meta, **catalogue[meta["id"]]}
            passages += check_edition(dist, meta, records[meta["id"], track], folder)
            editions += 1
    require(editions == len(records), "Edition inventory differs from editorial ledger")
    apparatus = check_apparatus(dist)
    urls = [x.text for x in ET.parse(dist / "sitemap.xml").findall(".//{*}loc")]
    require(urls == canonical_inventory(dist, bs.SITE_BASE), "Sitemap differs from final canonical pages")
    require({bs.SITE_BASE + p.relative_to(dist).as_posix() for p in (dist / "works").glob("*.html")} <= set(urls),
            "Reading pages omitted from sitemap")
    print(f"Verified {editions} edition records, {passages} rendered passages, {apparatus} apparatus chunks and {len(urls)} canonical URLs.")


if __name__ == "__main__":
    main()
