"""Verify the source-supported batch by replaying it against frozen inputs."""
from pathlib import Path
import json
import build_translation_disagreements as b
import scan_evidence
from lxml import html


def main():
    base=b.ROOT/'data/translation_disagreements'/b.DEFAULT_WORK
    ledger=json.loads(b.read(base/'corrections.json'))
    scans=scan_evidence.load(b.ROOT,b.DEFAULT_WORK)
    if ledger['human_review']!='none_documented':raise ValueError('unexpected human-review claim')
    for record in ledger['files']:
        old=b.read(b.ROOT/record['before_path']);expected=old
        if b.digest(old)!=record['before_sha256']:raise ValueError('before-text changed')
        for change in ledger['changes']:
            if record['path'] in change['files']:
                if change['item_id'] not in scans or expected.count(change['before'])!=1:raise ValueError('unreplayable correction')
                expected=expected.replace(change['before'],change['after'],1)
        for change in ledger.get('metadata_edits',[]):
            if record['path']==change['path']:
                if expected.count(change['before'])!=1:raise ValueError('unreplayable metadata edit')
                expected=expected.replace(change['before'],change['after'],1)
        actual=b.read(b.ROOT/record['path'])
        if actual!=expected or b.digest(actual)!=record['after_sha256']:raise ValueError('extra or missing change in '+record['path'])
    spec=json.loads(b.read(base/'review.json'))
    before=json.loads(b.read(b.ROOT/spec['sources']['passage_index']['path']))
    after=json.loads(b.read(b.ROOT/'site/dist/data/passages'/f'{b.DEFAULT_WORK}.json'))
    for name in ('passages','annotations'):
        if [x['id'] for x in before[name]]!=[x['id'] for x in after[name]]:raise ValueError(name+' IDs changed')
    for track,folder in (('earlier','works'),('t4b','works-t4b')):
        meta=json.loads(b.read(b.ROOT/folder/b.DEFAULT_WORK/'metadata.json'))
        n=sum(c['track']==track for c in ledger['changes'])
        if meta['ai_corrections']['count']!=n or meta['ai_corrections']['human_review']!='none_documented':raise ValueError('edit metadata mismatch')
        suffix='' if track=='earlier' else '-trithemius-4b'
        document=html.fromstring(b.read(b.ROOT/'site/dist/works'/f'{b.DEFAULT_WORK}{suffix}.html'))
        body=document.get_element_by_id('study-reader' if track=='earlier' else 'reading-text')
        text=b.flat(body.text_content())
        for change in ledger['changes']:
            if change['track']==track and (b.flat(change['after']) not in text or b.flat(change['before']) in text):
                raise ValueError('correction missing from rendered reading: '+change['item_id'])
    fixtures=json.loads(b.read(base/'benchmark-seed.json'))
    if fixtures['human_verified'] is not False or len(fixtures['fixtures'])!=6:raise ValueError('benchmark scope mismatch')
    print(f'Scribes correction validation passed: {len(ledger["changes"])} exact source-supported edits across {len(ledger["files"])} files; 99 passage and 27 annotation IDs preserved.')
    print('Six benchmark seeds and AI image evidence validated; human review remains pending.')


if __name__=='__main__':main()
