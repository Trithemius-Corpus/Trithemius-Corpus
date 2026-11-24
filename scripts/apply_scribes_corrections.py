"""Apply the bounded AI scan-supported Scribes batch, preserving before-texts.

No network or deployment. The proposal and image evidence are mandatory;
unrecognized input changes fail before any translation is written.
"""
from pathlib import Path
import json
import shutil
import build_translation_disagreements as b
import scan_evidence
from edition_corrections import history, validate_history

ROOT=b.ROOT
BASE=ROOT/'data/translation_disagreements'/b.DEFAULT_WORK


def main():
    ledger_path=BASE/'corrections.json'
    if ledger_path.exists():
        batches = history(ROOT, b.DEFAULT_WORK)
        validate_history(ROOT, b.DEFAULT_WORK, batches)
        print(f"All {len(batches)} correction batches are already applied and match their frozen inputs.")
        return
    scans=scan_evidence.load(ROOT,b.DEFAULT_WORK)
    proposal=json.loads(b.read(BASE/'proposed-corrections.json'))
    spec=json.loads(b.read(BASE/'review.json'))
    snapshot=BASE/'snapshots/before-corrections'
    original={};updated={}
    for row in proposal['changes']:
        if scans[row['item_id']]['decision']!='accepted_for_local_correction':raise ValueError('unaccepted source reading')
        for path in row['files']:
            file=b.resolve_source(path)
            if not any(file.is_relative_to(ROOT/folder/b.DEFAULT_WORK) for folder in ('works','works-t4b')):raise ValueError('unexpected correction target')
            if path not in original:original[path]=b.read(file);updated[path]=original[path]
            if updated[path].count(row['before'])!=1:raise ValueError('old wording absent or ambiguous')
            updated[path]=updated[path].replace(row['before'],row['after'],1)
    # Freeze the comparison and every changed chunk before modifying sources.
    for path in set(original)|{v['path'] for v in spec['sources'].values()}:
        target=snapshot/path
        if not target.resolve().is_relative_to(snapshot.resolve()):raise ValueError('snapshot path escaped')
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():
            if target.read_bytes()!=(ROOT/path).read_bytes():raise ValueError('existing snapshot differs')
        else:shutil.copyfile(ROOT/path,target)
    frozen_spec=json.loads(json.dumps(spec))
    for source in frozen_spec['sources'].values():
        source['original_path']=source['path']
        source['path']=(snapshot/source['path']).relative_to(ROOT).as_posix()
    frozen_spec['scope_note'] += ' The comparison is retained as the frozen pre-correction snapshot; local correction resolutions are shown separately.'
    # Validate the frozen identity before writing any live translation.
    b.assemble(frozen_spec)
    metadata_edits=[]
    md=f'works/{b.DEFAULT_WORK}/english.md'
    before='Tier S · faithful 4.71 (GPT-5.5 audit).'
    after='Historical audit before the 2026-11-05 local AI corrections: Tier S · faithful 4.71 (GPT-5.5 audit).'
    if updated[md].count(before)!=1:raise ValueError('unexpected archival audit header')
    updated[md]=updated[md].replace(before,after,1)
    metadata_edits.append({'path':md,'before':before,'after':after})
    files=[]
    for path,text in updated.items():
        files.append({'path':path,'before_path':(snapshot/path).relative_to(ROOT).as_posix(),'before_sha256':b.digest(original[path]),'after_sha256':b.digest(text)})
    ledger={'schema_version':'1.0','work_id':b.DEFAULT_WORK,'date':proposal['date'],'status':'applied_locally','review_method':proposal['method'],'human_review':'none_documented','changes':proposal['changes'],'metadata_edits':metadata_edits,'files':files}
    for path,text in updated.items():(ROOT/path).write_text(text,encoding='utf-8',newline='\n')
    for track,folder in (('earlier','works'),('t4b','works-t4b')):
        changes=[r for r in proposal['changes'] if r['track']==track]
        workdir=ROOT/folder/b.DEFAULT_WORK
        path=workdir/'ERRATA.md'
        text=b.read(path) if path.exists() else f'# Errata — {b.DEFAULT_WORK}\n'
        text+='\n## 2026-11-05 — AI scan-supported local correction batch\n\nThese are Codex AI visual assessments of BSB bsb00037424, not documented human review. Historical machine grades predate these edits. Original texts and exact file hashes are preserved in the correction ledger and snapshots.\n'
        for row in changes:
            scan=scans[row['item_id']]
            text+=f'\n### {row["item_id"]}\n\n- Previous: {row["before"]}\n- Local correction: {row["after"]}\n- Latin (expanded/normalized): {scan["normalized_latin"]}\n- Source: BSB {scan["image"]["label"]}, [institutional image]({scan["image"]["image_url"]}).\n- Basis: {scan["reason"]}\n'
        if track=='earlier':text+='\nThe [ed.] marker replaces the resolved [unclear] marker to retain its annotation anchor and the numbering of later notes. It points to the scan-supported storehouse-of-the-mind correction above.\n'
        path.write_text(text,encoding='utf-8',newline='\n')
        meta_path=workdir/'metadata.json';meta=json.loads(b.read(meta_path))
        meta['ai_corrections']={'date':proposal['date'],'count':len(changes),'human_review':'none_documented','note':'AI scan-supported local corrections; historical machine audits predate these edits. See editorial corrections.'}
        if track=='earlier':meta['unclear_count']=sum(b.read(p).count('[unclear]') for p in (workdir/'chunks').glob('full_chunk_*.md'))
        meta_path.write_text(b.json_text(meta),encoding='utf-8',newline='\n')
    ledger_path.write_text(b.json_text(ledger),encoding='utf-8',newline='\n')
    (BASE/'review.json').write_text(b.json_text(frozen_spec),encoding='utf-8',newline='\n')
    fixtures=[]
    for item,scan in scans.items():
        fixes=[r for r in proposal['changes'] if r['item_id']==item]
        fixtures.append({'id':item,'latin':scan['normalized_latin'],'interpretation':scan['reason'],'source_image':scan['image'],'accepted_local_english':[r['after'] for r in fixes],'status':'AI scan-assessed benchmark seed; human validation pending'})
    (BASE/'benchmark-seed.json').write_text(b.json_text({'schema_version':'1.0','human_verified':False,'fixtures':fixtures}),encoding='utf-8',newline='\n')
    print(f'Applied {len(proposal["changes"])} exact corrections across {len(files)} text/chunk files; original comparison frozen.')


if __name__=='__main__':main()
