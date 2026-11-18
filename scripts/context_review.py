"""Combine independent contextual ledgers and verify exact inventory coverage."""
import hashlib
import html
import json
from collections import Counter
from pathlib import Path

ALLOWED={'covered_existing','no_material_change_found','layout_furniture','needs_source_review','alignment_uncertain'}


def assemble(root: Path, work: str, spec: dict, inventory: dict) -> dict | None:
    base=root/'data/translation_disagreements'/work
    paths=[base/f'context-review-{suffix}.json' for suffix in 'abc']
    if not all(p.exists() for p in paths):return None
    texts={k:(root/v['path']).read_text(encoding='utf-8') for k,v in spec['sources'].items() if k.endswith(('_english','_latin'))}
    rows=[];findings=[];ledgers=[];ref_count=0
    def references(value):
        nonlocal ref_count
        if isinstance(value,dict):
            key=value.get('source_key',value.get('source'))
            if key in texts and {'quote','start','end'} <= value.keys():
                text=texts[key];a,z=value['start'],value['end']
                if not 0<=a<=z<=len(text) or text[a:z]!=value['quote']:raise ValueError(f'context quotation mismatch: {key} {a}:{z} {value["quote"][:80]!r}')
                if value.get('sha256')!=hashlib.sha256(text.encode('utf-8')).hexdigest():raise ValueError('context source hash mismatch')
                first=value.get('start_line',value.get('line_start'));last=value.get('end_line',value.get('line_end'))
                if first!=text.count('\n',0,a)+1 or last!=text.count('\n',0,max(a,z-1))+1:raise ValueError(f'context line mismatch: {key} {a}:{z}')
                ref_count+=1
                yield {'source':key,'path':spec['sources'][key]['path'],'start_line':first,'end_line':last,'quote':value['quote']}
            else:
                for v in value.values():yield from references(v)
        elif isinstance(value,list):
            for v in value:yield from references(v)
    for path in paths:
        data=json.loads(path.read_text(encoding='utf-8'))
        if any(data.get(k) is True for k in ('human_reviewed','human_verified','facsimile_verified')):raise ValueError('unexpected review claim')
        groups={g['id'] for g in data['groups']}
        for row in data['items']:
            if row['disposition'] not in ALLOWED or row['group_id'] not in groups or not row['rationale']:raise ValueError('invalid contextual disposition')
        rows.extend(data['items'])
        list(references(data))
        for f in data['findings']:
            findings.append({'id':f['id'],'priority':f.get('priority',f.get('provisional_priority','P3')),'title':f['title'],'assessment':f.get('assessment',''),'next_action':f.get('next_action','Inspect the source before correcting.'),'evidence':list(references(f))})
        # Use the same UTF-8/LF convention as the other textual sources. Git
        # can normalize a Windows working copy on its first checkout.
        ledger_text = path.read_text(encoding='utf-8')
        ledgers.append({'path':path.relative_to(root).as_posix(),'sha256':hashlib.sha256(ledger_text.encode('utf-8')).hexdigest(),'candidates':len(data['items']),'groups':len(groups)})
    ids=[r['candidate_id'] for r in rows];expected={c['id'] for c in inventory['candidates']}
    if len(ids)!=len(set(ids)) or set(ids)!=expected:raise ValueError('contextual coverage is not complete and unique')
    findings.sort(key=lambda f:(f['priority'],f['id']))
    return {'schema_version':'1.0','work_id':work,'review_method':'AI contextual comparison of every scoped lexical candidate; not human verification or exhaustive source-image adjudication','candidate_count':len(ids),'dispositions':dict(Counter(r['disposition'] for r in rows)),'ledgers':ledgers,'items':rows,'findings':findings,'verified_reference_visits':ref_count}


def render(data: dict) -> str:
    esc=html.escape
    cards=[]
    for f in data['findings']:
        refs=''.join(f'<h3>{esc(r["source"])}, lines {r["start_line"]}–{r["end_line"]}</h3><pre>{esc(r["quote"])}</pre>' for r in f['evidence'])
        cards.append(f'<article id="{esc(f["id"])}"><h2>{esc(f["priority"]+" · "+f["title"])}</h2><p>{esc(f["assessment"])}</p><p><strong>Next step:</strong> {esc(f["next_action"])}</p><details><summary>Exact local evidence</summary>{refs}</details></article>')
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Scribes contextual review</title><style>body{{font:16px/1.65 system-ui;margin:24px;background:#f4f2ed;color:#24303d}}main{{max-width:1050px;margin:auto}}article{{background:white;padding:22px;margin:24px 0;border:1px solid #ddd}}h2{{font-size:1.2rem}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font:16px/1.6 Georgia}}a{{color:#255d78}}summary{{cursor:pointer}}</style></head><body><main><a href="index.html">Prioritized queue and scan assessments</a><h1>Contextual review of the Scribes comparison</h1><p>Historical review of the pre-correction snapshot. Every lexical candidate has an AI contextual disposition. Some findings overlap the prioritized queue; these are review leads, not a count of proven errors. Source-image and human adjudication remain distinct.</p><p>{data['candidate_count']} candidates; {esc(str(data['dispositions']))}.</p><p><a href="context-review.json">Complete disposition ledger</a></p>{''.join(cards)}</main></body></html>'''
