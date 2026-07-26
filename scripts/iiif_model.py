"""Discover provider IIIF endpoints and normalize cached v2 manifests to v3.

The normalizer is deliberately offline-first: a release build consumes checked
provider metadata snapshots. Network refresh is an explicit curatorial action.
Readable corpus text therefore never depends on a remote image service.
"""
from __future__ import annotations

import argparse
import json
import shutil
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "data" / "iiif_sources.json"
CACHE = ROOT / "data" / "iiif" / "provider"
OUTPUT = ROOT / "site" / "dist" / "iiif"
SITE_BASE = "https://trithemius-corpus.github.io/Trithemius-Corpus"
P3_CONTEXT = "http://iiif.io/api/presentation/3/context.json"


def discover_manifest(provider: str, source_url: str) -> str | None:
    """Return the official IIIF Presentation endpoint for a known provider."""
    provider = provider.casefold()
    if provider == "bsb":
        import re
        match = re.search(r"(bsb\d+)", source_url)
        return ("https://api.digitale-sammlungen.de/iiif/presentation/v2/"
                f"{match.group(1)}/manifest") if match else None
    if provider in {"bnf", "gallica"}:
        marker = "ark:/12148/"
        if marker in source_url:
            ark = source_url.split(marker, 1)[1].split("/", 1)[0]
            return f"https://gallica.bnf.fr/iiif/ark:/12148/{ark}/manifest.json"
    if provider in {"e-rara", "erara"}:
        digits = [part for part in urlparse(source_url).path.split("/") if part.isdigit()]
        return f"https://www.e-rara.ch/i3f/v20/{digits[-1]}/manifest" if digits else None
    return None


def _lang(value, fallback="Untitled") -> dict:
    if isinstance(value, list):
        value = value[0] if value else fallback
    if isinstance(value, dict):
        value = value.get("@value") or value.get("none") or fallback
        if isinstance(value, list):
            value = value[0] if value else fallback
    return {"none": [str(value or fallback)]}


def _image(canvas: dict) -> tuple[dict, str | None]:
    image = (canvas.get("images") or [{}])[0].get("resource") or {}
    service = image.get("service") or {}
    if isinstance(service, list):
        service = service[0] if service else {}
    service_id = service.get("@id") or service.get("id")
    body = {
        "id": image.get("@id") or image.get("id"),
        "type": "Image",
        "format": image.get("format", "image/jpeg"),
        "height": image.get("height") or canvas.get("height"),
        "width": image.get("width") or canvas.get("width"),
    }
    if service_id:
        body["service"] = [{
            "id": service_id,
            "type": "ImageService2",
            "profile": "level2",
        }]
    return {k: v for k, v in body.items() if v is not None}, service_id


def normalize(work_id: str, source: dict, provider: dict, passages: dict) -> dict:
    manifest_id = f"{SITE_BASE}/iiif/{work_id}/manifest.json"
    canvases_v2 = provider.get("sequences", [{}])[0].get("canvases", [])
    canvases = []
    canvas_ids = []
    for index, old in enumerate(canvases_v2, 1):
        canvas_id = f"{SITE_BASE}/iiif/{work_id}/canvas/{index}"
        body, _service = _image(old)
        canvas_ids.append(canvas_id)
        canvases.append({
            "id": canvas_id,
            "type": "Canvas",
            "label": _lang(old.get("label"), str(index)),
            "height": old.get("height") or body.get("height"),
            "width": old.get("width") or body.get("width"),
            "items": [{
                "id": f"{canvas_id}/page/image",
                "type": "AnnotationPage",
                "items": [{
                    "id": f"{canvas_id}/annotation/image",
                    "type": "Annotation",
                    "motivation": "painting",
                    "body": body,
                    "target": canvas_id,
                }],
            }],
        })

    annotations: dict[int, list[dict]] = {}
    range_canvases: dict[str, list[str]] = {}
    range_labels: dict[str, str] = {}
    for passage in passages.get("passages", []):
        segment = next((s for s in passages.get("segments", [])
                        if s.get("segment") == passage.get("segment")), None)
        pages = ((segment or {}).get("source") or {}).get("pages") or []
        if not pages:
            continue
        page = int(pages[0].get("number", 1)) + int(source.get("page_offset", 0))
        if page < 1 or page > len(canvases):
            continue
        target = canvas_ids[page - 1]
        annotations.setdefault(page, []).append({
            "id": f"{manifest_id}/annotation/{passage['html_id']}",
            "type": "Annotation",
            "motivation": "supplementing",
            "body": {
                "type": "TextualBody",
                "language": "en",
                "format": "text/plain",
                "value": passage["text"],
            },
            "target": target,
            "seeAlso": [{
                "id": f"{SITE_BASE}/{passage['targets']['reading']}",
                "type": "Text",
                "format": "text/html",
            }],
        })
        chapter = passage.get("chapter_id") or "work"
        range_canvases.setdefault(chapter, [])
        if target not in range_canvases[chapter]:
            range_canvases[chapter].append(target)
        if passage.get("kind") == "heading" and chapter not in range_labels:
            range_labels[chapter] = passage["text"][:120]

    for page, items in annotations.items():
        canvas = canvases[page - 1]
        canvas["annotations"] = [{
            "id": f"{canvas['id']}/page/text",
            "type": "AnnotationPage",
            "items": items,
        }]

    ranges = [{
        "id": f"{manifest_id}/range/{chapter}",
        "type": "Range",
        "label": _lang(range_labels.get(chapter), chapter.replace("-", " ").title()),
        "items": [{"id": item, "type": "Canvas"} for item in items],
    } for chapter, items in range_canvases.items()]
    return {
        "@context": P3_CONTEXT,
        "id": manifest_id,
        "type": "Manifest",
        "label": _lang(provider.get("label"), work_id),
        "provider": [{
            "id": source["source_url"],
            "type": "Agent",
            "label": _lang(source["provider"]),
            "homepage": [{"id": source["source_url"], "type": "Text", "label": _lang("View institutional record"), "format": "text/html"}],
        }],
        "rights": source["rights"],
        "requiredStatement": {"label": _lang("Attribution"), "value": _lang(source["required_statement"])},
        "homepage": [{"id": source["source_url"], "type": "Text", "label": _lang("Institutional source"), "format": "text/html"}],
        "seeAlso": [{"id": source["provider_manifest"], "type": "Dataset", "label": _lang(f"Provider IIIF Presentation {source['api_version']} manifest"), "format": "application/ld+json"}],
        "behavior": ["paged"],
        "items": canvases,
        "structures": ranges,
        "metadata": [
            {"label": _lang("Text alignment"), "value": _lang(source["mapping_precision"])},
            {"label": _lang("Normalized by"), "value": _lang("Trithemius Corpus")},
        ],
    }


def generate_all(refresh: bool = False) -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))["works"]
    CACHE.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for work_id, source in config.items():
        cache = CACHE / f"{work_id}.json"
        if refresh:
            discovered = discover_manifest(source["provider_code"], source["source_url"])
            if discovered != source["provider_manifest"]:
                raise SystemExit(f"Discovery mismatch for {work_id}: {discovered}")
            request = urllib.request.Request(
                source["provider_manifest"],
                headers={"User-Agent": "Trithemius-Corpus-IIIF/1.0 (+https://github.com/Trithemius-Corpus/Trithemius-Corpus)"},
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                cache.write_bytes(response.read())
        if not cache.exists():
            raise SystemExit(f"Missing provider cache {cache}; run with --refresh")
        provider = json.loads(cache.read_text(encoding="utf-8-sig"))
        passage_path = ROOT / "site" / "dist" / "data" / "passages" / f"{work_id}.json"
        passages = json.loads(passage_path.read_text(encoding="utf-8"))
        target = OUTPUT / work_id / "manifest.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(normalize(work_id, source, provider, passages), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{work_id}: {len(provider.get('sequences', [{}])[0].get('canvases', []))} canvases")
    shutil.copy2(ROOT / "site" / "templates" / "iiif-viewer.html", OUTPUT / "viewer.html")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    generate_all(refresh=args.refresh)


if __name__ == "__main__":
    main()
