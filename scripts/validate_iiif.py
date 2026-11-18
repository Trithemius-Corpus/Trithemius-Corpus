"""Validate the corpus IIIF registry, provider cache, and Presentation 3 output."""
from __future__ import annotations

import json
import re
from pathlib import Path

import iiif_model

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    config = json.loads((ROOT / "data" / "iiif_sources.json").read_text(encoding="utf-8"))["works"]
    require(iiif_model.discover_manifest("bsb", "https://daten.digitale-sammlungen.de/bsb00037424/image_1") ==
            "https://api.digitale-sammlungen.de/iiif/presentation/v2/bsb00037424/manifest", "BSB discovery")
    require(iiif_model.discover_manifest("gallica", "https://gallica.bnf.fr/ark:/12148/bpt6k5832538j") ==
            "https://gallica.bnf.fr/iiif/ark:/12148/bpt6k5832538j/manifest.json", "Gallica discovery")
    require(iiif_model.discover_manifest("e-rara", "https://www.e-rara.ch/zuz/content/titleinfo/1761179") ==
            "https://www.e-rara.ch/i3f/v20/1761179/manifest", "e-rara discovery")
    canvas_total = annotation_total = range_total = 0
    exact_total = 0
    for work_id, source in config.items():
        require(source["rights"].startswith("https://"), f"{work_id}: rights URI")
        require(source["required_statement"].strip(), f"{work_id}: attribution")
        require((ROOT / "data" / "iiif" / "provider" / f"{work_id}.json").exists(), f"{work_id}: provider cache")
        path = ROOT / "site" / "dist" / "iiif" / work_id / "manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        require(manifest.get("@context") == iiif_model.P3_CONTEXT, f"{work_id}: v3 context")
        require(manifest.get("type") == "Manifest", f"{work_id}: manifest type")
        require(manifest.get("provider") and manifest.get("requiredStatement"), f"{work_id}: provider statement")
        require(manifest.get("rights") == source["rights"], f"{work_id}: rights preserved")
        canvases = manifest.get("items", [])
        dist = ROOT / "site/dist"
        page = (dist / "works" / f"{work_id}.html").read_text(encoding="utf-8")
        settings = json.loads(re.search(r"window\.TC_WORK=(\{[^\n]+\});", page)[1])
        provider = json.loads((iiif_model.CACHE / f"{work_id}.json").read_text(encoding="utf-8"))
        index = json.loads((dist / "data/passages" / f"{work_id}.json").read_text(encoding="utf-8"))
        approximate, exact = iiif_model.canvas_targets(work_id, source, provider, index)
        require(settings["reviewedCanvases"] == exact and settings["iiifCanvasMap"] == approximate,
                f"{work_id}: reader and source maps disagree")
        require(all(1 <= n <= len(canvases) for n in [*exact.values(), *approximate.values()]),
                f"{work_id}: out-of-bounds source link")
        require(settings["institutionalSource"] == source["source_url"], f"{work_id}: institutional fallback")
        placed = {}
        for n, canvas in enumerate(canvases, 1):
            for layer in canvas.get("annotations", []):
                for annotation in layer["items"]:
                    anchor = annotation["seeAlso"][0]["id"].split("#")[-1]
                    require(anchor not in placed, f"{work_id}: duplicate source annotation {anchor}")
                    placed[anchor] = n
        expected = {p["html_id"]: exact.get(p["html_id"], approximate.get(str(p["segment"])))
                    for p in index["passages"]}
        require(placed == {k: v for k, v in expected.items() if v is not None}, f"{work_id}: canvas annotation drift")
        queue = ROOT / "review/translation-disagreements" / work_id / "queue.json"
        if queue.exists():
            for item in json.loads(queue.read_text(encoding="utf-8"))["items"]:
                assessment = item.get("ai_scan_assessment")
                if assessment:
                    anchor = item["english"]["earlier"]["reader_target"].split("#")[-1]
                    require(exact.get(anchor) == assessment["crop"]["canvas_number"], f"{item['id']}: reviewed source page")
        exact_total += len(exact)
        ids = {canvas["id"] for canvas in canvases}
        require(canvases, f"{work_id}: canvases")
        for canvas in canvases:
            require(canvas.get("height") and canvas.get("width"), f"{work_id}: canvas dimensions")
            require(canvas.get("items", [{}])[0].get("items"), f"{work_id}: painting annotation")
            for page in canvas.get("annotations", []):
                for annotation in page.get("items", []):
                    require(annotation.get("target") == canvas["id"], f"{work_id}: text target")
                    require(annotation.get("body", {}).get("language") == "en", f"{work_id}: text language")
                    annotation_total += 1
        for item_range in manifest.get("structures", []):
            require(item_range.get("items"), f"{work_id}: empty range")
            require(all(item.get("id") in ids for item in item_range["items"]), f"{work_id}: range target")
            range_total += 1
        canvas_total += len(canvases)
    require((ROOT / "site" / "dist" / "iiif" / "viewer.html").exists(), "viewer artifact")
    print("IIIF validation passed.")
    print(f"  manifests: {len(config)}")
    print(f"  canvases: {canvas_total}")
    print(f"  text annotations: {annotation_total}")
    print(f"  ranges: {range_total}")
    print(f"  distinct passages with reviewed source canvases: {exact_total}")


if __name__ == "__main__":
    main()
