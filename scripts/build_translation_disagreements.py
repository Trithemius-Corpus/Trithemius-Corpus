"""Build an offline translation-review queue from frozen, citable sources.

English token alignment proposes lexical differences. Editorial assessments
come only from the explicitly authored review specification, never from a
negation count or a model quality score. Nothing writes into site/dist.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from lxml import html as lxml_html
import scan_evidence
import context_review

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORK = "prdl-24362_de-laude-scriptorum-manualium"
PRIORITY = {"P1": 0, "P2": 1, "P3": 2, "excluded": 3}
TOKEN = re.compile(r"\w+(?:['’]\w+)?", re.UNICODE)
MARKER = re.compile(r"(?m)^(?:\[segment \d+\]|--- Page \d+ ---)\s*$")
NEGATION = {"no", "not", "never", "neither", "nor", "unless", "without", "cannot"}
NUMBERS = set("one two three four five six seven eight nine ten eleven twelve twenty thirty forty fifty hundred thousand".split())
OFFSET_CONVENTION = "zero-based Unicode code points in UTF-8 text with LF newlines; end exclusive; lines one-based"
ID_VERSION = "source-snapshot-v2"


def witness_from_url(url: str) -> str:
    """Extract this pilot's complete BSB identifier from an exact URL path part."""
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {
        "daten.digitale-sammlungen.de", "www.digitale-sammlungen.de", "api.digitale-sammlungen.de"
    }:
        raise ValueError("unsupported source-witness URL")
    ids = [p for p in parsed.path.split("/") if re.fullmatch(r"bsb\d{8}", p)]
    if len(ids) != 1:
        raise ValueError("source-witness URL must contain one complete BSB identifier")
    return ids[0]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")  # universal-newline normalization


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def json_text(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def resolve_source(path: str, root: Path = ROOT) -> Path:
    target = (root / path).resolve()
    if not target.is_relative_to(root.resolve()) or Path(path).is_absolute():
        raise ValueError(f"source path escapes repository: {path}")
    return target


def locate(text: str, quote: str) -> tuple[int, int]:
    if not quote or text.count(quote) != 1:
        raise ValueError(f"quotation must occur exactly once: {quote[:100]!r}")
    start = text.index(quote)
    return start, start + len(quote)


def reference(path: str, text: str, start: int, end: int) -> dict:
    if not 0 <= start <= end <= len(text):
        raise ValueError("invalid source offsets")
    return {
        "path": path, "sha256": digest(text), "start": start, "end": end,
        "start_line": text.count("\n", 0, start) + 1,
        "end_line": text.count("\n", 0, max(start, end - 1)) + 1,
        "quote": text[start:end],
    }


def tokens(text: str, start: int = 0, end: int | None = None) -> list[tuple[str, int, int]]:
    end = len(text) if end is None else end
    markers = [m.span() for m in MARKER.finditer(text)]
    return [(m[0].casefold().replace("’", "'"), m.start(), m.end())
            for m in TOKEN.finditer(text, start, end)
            if not any(a <= m.start() < b for a, b in markers)]


def lexical_signals(left: list[str], right: list[str]) -> list[str]:
    changed = set(left) ^ set(right)
    signals = []
    if changed & NEGATION:
        signals.append("negation_token_difference")
    if changed & NUMBERS or any(t.isdigit() for t in changed):
        signals.append("number_token_difference")
    if max(len(left), len(right)) >= 8:
        signals.append("extended_text_difference")
    return signals or ["wording_difference"]


def candidate_inventory(left: str, right: str, scopes: dict) -> tuple[list[dict], dict]:
    streams = [tokens(text, *scopes[track]) for track, text in (("earlier", left), ("t4b", right))]
    a, b = streams
    matcher = difflib.SequenceMatcher(None, [t[0] for t in a], [t[0] for t in b], autojunk=False)
    rows = []
    for op, i, j, k, l in matcher.get_opcodes():
        if op == "equal":
            continue
        spans = []
        for stream, first, last, track in ((a, i, j, "earlier"), (b, k, l, "t4b")):
            start = stream[first][1] if first < len(stream) else scopes[track][1]
            end = stream[last - 1][2] if last > first else start
            context_start = stream[max(0, first - 12)][1] if stream else start
            context_end = stream[min(len(stream) - 1, max(first, last - 1) + 12)][2] if stream else end
            context_end = max(end, context_end)  # an EOF insertion may follow final punctuation
            spans.append({"start": start, "end": end, "context_start": context_start, "context_end": context_end})
        identity = json.dumps([ID_VERSION, digest(left), digest(right), scopes, op, spans], sort_keys=True)
        rows.append({
            "id": "lex-" + digest(identity)[:16], "operation": op,
            "earlier": spans[0], "t4b": spans[1],
            "earlier_text": left[spans[0]["start"]:spans[0]["end"]],
            "t4b_text": right[spans[1]["start"]:spans[1]["end"]],
            "earlier_context": left[spans[0]["context_start"]:spans[0]["context_end"]],
            "t4b_context": right[spans[1]["context_start"]:spans[1]["context_end"]],
            "signals": lexical_signals([t[0] for t in a[i:j]], [t[0] for t in b[k:l]]),
            "status": "untriaged_lexical_difference",
        })
    return rows, {"earlier_tokens": len(a), "t4b_tokens": len(b),
                  "matched_tokens": sum(block.size for block in matcher.get_matching_blocks()),
                  "lexical_difference_count": len(rows)}


def flat(text: str) -> str:
    return " ".join(text.replace("*", "").split())


def marker_before(text: str, offset: int) -> dict | None:
    matches = list(re.finditer(r"(?m)^(?:\[segment (\d+)\]|--- Page (\d+) ---)", text[:offset]))
    if not matches:
        return None
    m = matches[-1]
    return {"kind": "segment" if m[1] else "ocr_page_marker", "number": int(m[1] or m[2])}


def assemble(spec: dict, root: Path = ROOT) -> tuple[dict, dict]:
    sources = {}
    for name, source in spec["sources"].items():
        text = read(resolve_source(source["path"], root))
        if digest(text) != source["sha256"]:
            raise ValueError(f"frozen source changed: {source['path']}; re-review before updating its hash")
        sources[name] = text
    earlier_meta = json.loads(sources["earlier_metadata"])
    t4b_meta = json.loads(sources["t4b_metadata"])
    for meta in (earlier_meta, t4b_meta):
        if (not re.fullmatch(r"bsb\d{8}", spec["witness_id"])
                or meta["id"] != spec["work_id"] or spec["witness_id"] != witness_from_url(meta["source"]["url"])):
            raise ValueError("edition identity or source-witness mismatch")
    scopes = {}
    for track, anchors in spec["comparison_scope"].items():
        text = sources[track + "_english"]
        start, _ = locate(text, anchors["start"])
        _, end = locate(text, anchors["end"])
        if end <= start:
            raise ValueError("reversed comparison scope")
        scopes[track] = [start, end]
    candidates, coverage = candidate_inventory(sources["earlier_english"], sources["t4b_english"], scopes)
    passages = json.loads(sources["passage_index"])["passages"]
    reader_text = {}
    reader_paths = {}
    for track, suffix in (("earlier", ""), ("t4b", "-trithemius-4b")):
        path = f"site/dist/works/{spec['work_id']}{suffix}.html"
        document = lxml_html.fromstring(sources[track + "_reader"])
        containers = document.xpath('//*[@id="reading-text"]') or document.xpath('//*[@id="study-reader"]')
        if len(containers) != 1:
            raise ValueError(f"missing or ambiguous reading container: {path}")
        reader_text[track] = flat(containers[0].text_content())
        reader_paths[track] = path + "#" + containers[0].get("id")
    rows = []
    scans = scan_evidence.load(root, spec['work_id'])
    correction_path = root/'data/translation_disagreements'/spec['work_id']/'corrections.json'
    corrections = json.loads(read(correction_path)) if correction_path.exists() else None
    if corrections:
        if corrections['human_review']!='none_documented':raise ValueError('undocumented review claim')
        for file in corrections['files']:
            if digest(read(resolve_source(file['path'],root)))!=file['after_sha256']:raise ValueError('local correction revision changed')
    for item in spec["items"]:
        if item["priority"] not in PRIORITY or item["disposition"] not in {"queue", "excluded"}:
            raise ValueError("invalid review disposition")
        if (item["priority"] == "excluded") != (item["disposition"] == "excluded"):
            raise ValueError("priority/disposition mismatch")
        row = {k: v for k, v in item.items() if k not in {"english", "latin"}}
        row["review_status"] = "ai_triaged_pending_human_review"
        row["facsimile_verified"] = False
        if item['id'] in scans:
            row['ai_scan_assessment'] = scans[item['id']]
        if corrections:
            edits=[c for c in corrections['changes'] if c['item_id']==item['id']]
            if edits:row['local_corrections']={'date':corrections['date'],'status':'applied_locally','human_review':'none_documented','changes':edits}
        row["english"] = {}
        for track in ("earlier", "t4b"):
            key = track + "_english"
            text = sources[key]
            start, end = locate(text, item["english"][track])
            if not scopes[track][0] <= start < end <= scopes[track][1]:
                raise ValueError(f"{item['id']}: evidence falls outside comparison scope")
            ref = reference(spec["sources"][key]["path"], text, start, end)
            ref["source_marker"] = marker_before(text, start)
            ref["present_in_reading_view"] = flat(ref["quote"]) in reader_text[track]
            target, precision = reader_paths[track], "work"
            if track == "earlier":
                hits = [p for p in passages if flat(ref["quote"]) in flat(p["text"])]
                if len(hits) == 1:
                    target, precision = "site/dist/" + hits[0]["targets"]["reading"], "passage"
            ref["reader_target"], ref["reader_precision"] = target, precision
            row["english"][track] = ref
        row["latin"] = {}
        for track, quote in item.get("latin", {}).items():
            key = track + "_latin"
            text = sources[key]
            start, end = locate(text, quote)
            ref = reference(spec["sources"][key]["path"], text, start, end)
            ref["source_marker"] = marker_before(text, start)
            row["latin"][track] = ref
        if item["disposition"] == "queue" and set(row["latin"]) != {"earlier", "t4b"}:
            raise ValueError(f"{item['id']}: queued item needs both Latin witnesses")
        row["lexical_candidates"] = [c["id"] for c in candidates if any(
            c[t]["start"] < row["english"][t]["end"] and c[t]["end"] >= row["english"][t]["start"]
            for t in ("earlier", "t4b"))]
        if not row["lexical_candidates"]:
            raise ValueError(f"{item['id']}: no differing text in the cited pair")
        rows.append(row)
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("duplicate item IDs")
    rows.sort(key=lambda r: (PRIORITY[r["priority"]], r["rank"], r["id"]))
    for candidate in candidates:
        candidate["overlapping_review_items"] = [r["id"] for r in rows if candidate["id"] in r["lexical_candidates"]]
    queue = {
        "schema_version": "1.0", "work_id": spec["work_id"], "title": spec["title"],
        "witness_id": spec["witness_id"], "source_record": earlier_meta["source"]["url"],
        "review_method": "AI-assisted triage of frozen local texts, with explicitly attributed AI image assessments where supplied; no human verification claimed",
        "offset_convention": OFFSET_CONVENTION,
        "candidate_id_version": ID_VERSION,
        "sources": spec["sources"], "comparison_scope": scopes,
        "scope_note": spec["scope_note"], "coverage": coverage,
        "summary": {p: sum(r["priority"] == p for r in rows) for p in PRIORITY},
        "items": rows,
    }
    queue["content_digest"] = digest(json_text(queue))
    inventory = {"schema_version": "1.0", "work_id": spec["work_id"], "sources": spec["sources"],
                 "candidate_id_version": ID_VERSION,
                 "offset_convention": queue["offset_convention"], "comparison_scope": scopes,
                 "coverage": coverage, "candidates": candidates}
    return queue, inventory


def render(queue: dict) -> str:
    esc = html.escape
    cards = []
    for item in queue["items"]:
        columns = []
        for track, label in (("earlier", "Earlier English"), ("t4b", "Trithemius 4B English")):
            ref = item["english"][track]
            present = "Present in frozen reading view" if ref["present_in_reading_view"] else "Archive excerpt; rendering differs"
            columns.append(f'<section><h3>{label}</h3><blockquote>{esc(ref["quote"])}</blockquote>'
                           f'<p class="source"><a href="sources/{track}-english.html#L{ref["start_line"]}">Frozen source, lines {ref["start_line"]}–{ref["end_line"]}</a> · '
                           f'<a href="https://trithemius-corpus.github.io/Trithemius-Corpus/{esc(ref["reader_target"].removeprefix("site/dist/"))}">Published reader ({ref["reader_precision"]})</a><br>{present}<br><code>{esc(ref["path"])}</code></p></section>')
        latin = []
        for track, ref in item["latin"].items():
            marker = ref["source_marker"]
            label = f'{marker["kind"].replace("_", " ")} {marker["number"]}' if marker else "no local marker"
            latin.append(f'<section><h3>{"Earlier" if track == "earlier" else "T4B"} Latin OCR</h3>'
                         f'<pre lang="la">{esc(ref["quote"])}</pre><p class="source">{label} · '
                         f'<a href="sources/{track}-latin.html#L{ref["start_line"]}">Frozen source, lines {ref["start_line"]}–{ref["end_line"]}</a><br><code>{esc(ref["path"])}</code></p></section>')
        excluded = item["disposition"] == "excluded"
        resolution=''
        if item.get('local_corrections'):
            resolution='<aside class="notice"><strong>Corrected locally after AI scan assessment.</strong> Original comparison retained below; human review remains pending.'
            for edit in item['local_corrections']['changes']:
                resolution+=f'<p><strong>{esc(edit["track"])} revised wording:</strong> {esc(edit["after"])}</p>'
            resolution+='</aside>'
        evidence = (f'<details><summary>Inspect Latin evidence and source locations</summary><div class="columns">{"".join(latin)}</div>'
                    f'<p class="source">OCR segment and page labels are archival locators. Image mapping is established only in the explicit AI scan assessment where provided. <a href="{esc(queue["source_record"])}">Institutional source record</a>.</p></details>'
                    if latin else '<p class="source">Equivalent-wording control: no Latin adjudication recorded.</p>')
        scan = item.get('ai_scan_assessment')
        if scan:
            evidence += (f'<details><summary>AI scan assessment — {esc(scan["image"]["label"])}</summary>'
                         f'<img style="max-width:100%;height:auto" src="evidence/{item["id"]}.png" alt="Source crop for {esc(item["title"])}">'
                         f'<p lang="la">{esc(scan["normalized_latin"])}</p><p>{esc(scan["reason"])}</p>'
                         f'<p class="source">Interpretive transcription with expanded abbreviations; brackets mark uncertain letter readings. Codex AI visual assessment; no human review documented. Image: Bayerische Staatsbibliothek, Public Domain Mark 1.0. <a href="{esc(scan["image"]["image_url"])}">Full institutional image</a>.</p></details>')
        cards.append(f'''<article id="{esc(item['id'])}" data-priority="{item['priority']}" {'hidden' if excluded else ''}>
<div class="eyebrow">{item['priority']} · {esc(item['category'].replace('_',' '))} · {esc(item['id'])}</div>
<h2><a href="#{esc(item['id'])}">{esc(item['title'])}</a></h2>
{resolution}
<p>{esc(item['difference'])}</p><div class="columns">{''.join(columns)}</div>
<p><strong>Why it matters:</strong> {esc(item['impact'])}</p>
<p><strong>{'Initial OCR assessment' if item.get('local_corrections') else 'Latin assessment'}:</strong> {esc(item['latin_assessment'])}</p>
<p class="source">{'Initial proposed reading' if item.get('local_corrections') else 'Tentative reading to check'}: {esc({'earlier':'earlier English','t4b':'T4B English','none':'undecided'}[item['tentative_preference']])}. {'The later AI scan assessment supports the local correction above; human review remains pending.' if item.get('local_corrections') else 'This is an AI triage judgment, not an accepted correction.'}</p>
<p><strong>{'Original review task' if item.get('local_corrections') else 'Next review step'}:</strong> {esc(item['next_action'])}</p>
{evidence}
<p class="status">AI triage · Awaiting human review · {'Local correction recorded' if item.get('local_corrections') else 'No correction applied'}</p></article>''')
    summary = queue["summary"]
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Translation review — {esc(queue['title'])}</title><style>
:root{{color-scheme:light;font-family:system-ui,sans-serif;color:#24303d;background:#f4f2ed}}*{{box-sizing:border-box}}body{{margin:0}}main{{max-width:1140px;margin:auto;padding:36px 24px}}h1{{font-family:Georgia,serif;font-size:clamp(2rem,5vw,3rem);margin:10px 0}}h2{{font-size:1.3rem;line-height:1.4;margin:8px 0 14px}}h3{{font-size:.95rem;margin:0 0 12px}}a{{color:#255d78;text-underline-offset:3px}}h2 a{{color:inherit;text-decoration:none}}p{{line-height:1.65}}.eyebrow{{font-size:.8rem;font-weight:700;letter-spacing:.06em;color:#59636e}}.notice{{border-left:4px solid #b47728;padding:12px 18px;background:#fff8e9}}.metrics{{font-size:1.05rem}}.tools{{display:flex;gap:16px;flex-wrap:wrap;align-items:end;margin:24px 0}}label{{display:grid;gap:5px;font-size:.9rem}}input,select{{font:inherit;padding:10px;border:1px solid #87919c;border-radius:5px;background:white;max-width:100%}}#filter-text{{width:320px}}article{{background:white;border:1px solid #d8d9d9;border-top:4px solid #b47728;border-radius:7px;padding:24px;margin:24px 0;scroll-margin-top:20px}}article[data-priority=P2]{{border-top-color:#43768b}}article[data-priority=P3],article[data-priority=excluded]{{border-top-color:#858b92}}.columns{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}.columns section{{min-width:0}}blockquote{{margin:0;padding:16px;background:#f7f7f5;border-left:3px solid #d8c8aa;font-family:Georgia,serif;line-height:1.65;white-space:pre-wrap}}.source,.status{{font-size:.82rem;color:#56626e;overflow-wrap:anywhere}}.status{{border-top:1px solid #eee;padding-top:12px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font:1rem/1.6 Georgia,serif;background:#f7f7f5;padding:16px}}summary{{cursor:pointer;font-weight:600;padding:12px 0}}:focus-visible{{outline:3px solid #b47728;outline-offset:3px}}[hidden]{{display:none!important}}@media(max-width:650px){{main{{padding:22px 14px}}article{{padding:18px}}.columns{{grid-template-columns:1fr}}.tools,label,#filter-text{{width:100%}}}}@media print{{.tools{{display:none}}article{{break-inside:avoid}}details{{display:block}}}}
</style></head><body><main>
<div class="eyebrow">Local editorial review · BSB {esc(queue['witness_id'])}</div>
<h1>{esc(queue['title'])}</h1><p>Translation disagreement queue</p>
<p class="notice">AI triage of two translations of the same printed witness. Priorities describe potential effects on meaning. Explicit AI scan assessments are included where available; documented human review remains pending.</p>
<p class="metrics"><strong>{summary['P1']}</strong> P1 meaning conflicts · <strong>{summary['P2']}</strong> P2 review candidates · <strong>{summary['P3']}</strong> P3 lower-priority cases · <strong>{summary['excluded']}</strong> excluded controls</p>
<p>{esc(queue['scope_note'])}</p>
<p class="source">The full token comparison produced {queue['coverage']['lexical_difference_count']} lexical differences. These are search aids, not confirmed errors. <a href="queue.json">Queue JSON</a> · <a href="candidates.json">Complete lexical inventory</a></p>
<div class="tools"><label>Priority<select id="priority"><option value="queue">Review queue</option><option value="P1">P1 — Meaning conflicts</option><option value="P2">P2 — Review candidates</option><option value="P3">P3 — Lower priority</option><option value="excluded">Excluded controls</option><option value="all">All records</option></select></label><label>Find in review records<input id="filter-text" type="search" placeholder="e.g. negation, Aristotle, monastery"></label><output id="count" aria-live="polite"></output></div>
{''.join(cards)}<p class="source">Source digests and character offsets are recorded in queue.json. Earlier and T4B chunk numbers are not treated as equivalent. Coverage of lexical changes does not establish exhaustive semantic review.</p>
</main><script>
const priority=document.getElementById('priority'), query=document.getElementById('filter-text'), cards=[...document.querySelectorAll('article')], count=document.getElementById('count');
function filter(){{let visible=0;const q=query.value.toLocaleLowerCase();for(const card of cards){{const p=card.dataset.priority;const scope=priority.value==='all'||priority.value===p||(priority.value==='queue'&&p!=='excluded');card.hidden=!(scope&&card.textContent.toLocaleLowerCase().includes(q));if(!card.hidden)visible++;}}count.textContent=visible+' record'+(visible===1?'':'s')+' shown';}}
function revealHash(){{let id;try{{id=decodeURIComponent(location.hash.slice(1));}}catch{{return;}}const card=cards.find(c=>c.id===id);if(!card)return;priority.value=card.dataset.priority;query.value='';filter();card.setAttribute('tabindex','-1');card.focus({{preventScroll:true}});card.scrollIntoView({{block:'start'}});}}
priority.addEventListener('change',filter);query.addEventListener('input',filter);window.addEventListener('hashchange',revealHash);filter();revealHash();
</script></body></html>'''


def source_view(source: dict, language: str) -> str:
    text = read(resolve_source(source["path"]))
    if digest(text) != source["sha256"]:
        raise ValueError("source changed while rendering evidence")
    lines = "\n".join(f'<span id="L{n}"><a href="#L{n}" aria-label="Line {n}">{n:04d}</a> {html.escape(line)}</span>'
                      for n, line in enumerate(text.split("\n"), 1))
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Frozen source — {html.escape(source['path'])}</title><style>body{{font:16px/1.6 system-ui;background:#f4f2ed;color:#24303d;margin:24px}}main{{max-width:1100px;margin:auto}}h1,p{{overflow-wrap:anywhere}}h1{{font-size:1.25rem}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font:16px/1.7 monospace;background:white;padding:20px}}span:target{{background:#ffe6a8}}a{{color:#255d78}}pre a{{font-size:.8em;color:#687680}}span{{scroll-margin-top:20px}}</style></head><body><main><a href="../index.html">Back to review queue</a><h1>{html.escape(source['path'])}</h1><p>Frozen archival text, with original line divisions after LF normalization. Historical audit labels in the archive are not review conclusions.</p><p>SHA-256: <code>{source['sha256']}</code></p><pre lang="{language}">{lines}</pre></main></body></html>'''


def build(work: str = DEFAULT_WORK, check: bool = False) -> dict:
    if not re.fullmatch(r"[a-z0-9_-]+", work):
        raise ValueError("invalid work ID")
    spec_path = ROOT / "data" / "translation_disagreements" / work / "review.json"
    spec = json.loads(read(spec_path))
    queue, candidates = assemble(spec)
    outputs = {"queue.json": json_text(queue), "candidates.json": json_text(candidates), "index.html": render(queue)}
    contextual = context_review.assemble(ROOT,work,spec,candidates)
    if contextual:
        dispositions={row['candidate_id']:row for row in contextual['items']}
        for candidate in candidates['candidates']:
            candidate['status']='ai_contextually_reviewed'
            candidate['contextual_review']=dispositions[candidate['id']]
        outputs['candidates.json']=json_text(candidates)
        outputs['context-review.json']=json_text(contextual)
        outputs['context-review.html']=context_review.render(contextual)
        outputs['index.html']=outputs['index.html'].replace('<div class="tools">','<p><a href="context-review.html">Full contextual review and additional source-review leads</a></p><div class="tools">')
    if (ROOT/'data/translation_disagreements'/work/'corrections.json').exists():
        current_sources={};live={};scopes={}
        for track in ('earlier','t4b'):
            src=spec['sources'][track+'_english'];path=src.get('original_path',src['path'])
            live[track]=read(resolve_source(path));current_sources[track+'_english']={'path':path,'sha256':digest(live[track])}
            anchors=spec['comparison_scope'][track]
            scopes[track]=[locate(live[track],anchors['start'])[0],locate(live[track],anchors['end'])[1]]
        diffs,counts=candidate_inventory(live['earlier'],live['t4b'],scopes)
        outputs['post-correction-comparison.json']=json_text({'schema_version':'1.0','work_id':work,'candidate_id_version':ID_VERSION,'offset_convention':OFFSET_CONVENTION,'sources':current_sources,'comparison_scope':scopes,'coverage':counts,'candidates':diffs,'note':'Current local texts after the recorded batch. Lexical counts are not accuracy scores; contextual dispositions belong to the original frozen snapshot.'})
        outputs['index.html']=outputs['index.html'].replace('<div class="tools">','<p><a href="post-correction-comparison.json">Recomparison of the locally corrected texts</a></p><div class="tools">')
    for track in ("earlier", "t4b"):
        for kind, language in (("english", "en"), ("latin", "la")):
            outputs[f"sources/{track}-{kind}.html"] = source_view(queue["sources"][f"{track}_{kind}"], language)
    for item in queue['items']:
        if item.get('ai_scan_assessment'):
            outputs[f"evidence/{item['id']}.png"] = resolve_source(item['ai_scan_assessment']['crop']['crop_path']).read_bytes()
    out = ROOT / "review" / "translation-disagreements" / work
    if check:
        for name, value in outputs.items():
            actual = (out/name).read_bytes() if isinstance(value,bytes) and (out/name).exists() else read(out/name) if (out/name).exists() else None
            if actual != value:
                raise ValueError(f"stale or missing review artifact: {name}")
    else:
        out.mkdir(parents=True, exist_ok=True)
        for name, value in outputs.items():
            (out / name).parent.mkdir(parents=True, exist_ok=True)
            if isinstance(value,bytes):(out/name).write_bytes(value)
            else:(out / name).write_text(value, encoding="utf-8", newline="\n")
    return queue


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", default=DEFAULT_WORK)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    queue = build(args.work, args.check)
    print(("Verified" if args.check else "Built") + " local disagreement queue: " + json.dumps(queue["summary"]))
    print(f"Lexical differences: {queue['coverage']['lexical_difference_count']}; all source hashes and quotations verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
