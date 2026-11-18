"""Rebuild just Scribes from committed sources, retaining every passage ID."""
import json
import re
import build_site as bs
import build_t4b_pages as t4b
import passage_model as pm
import iiif_model
import build_publication_exports as exports

WID='prdl-24362_de-laude-scriptorum-manualium'


def main():
    env=bs.make_env();manifest=bs.load_manifest()
    works=[bs.enrich_work(w) for w in manifest['works'] if not w['skip']]
    bs.attach_editions(works);bs.ALL_WORK_IDS=[w['id'] for w in works]
    work=next(w for w in works if w['id']==WID);position=works.index(work)
    index_path=bs.OUT/'data/passages'/f'{WID}.json'
    old=json.loads(index_path.read_text(encoding='utf-8'))
    pairs,stats=bs.load_pairs(WID);chapters=bs.load_chapters(WID)
    body,passages,annotations=bs.stitch_english_with_passages(WID,pairs,chapters)
    source_map={s['segment']:dict(s['source'],mapping_precision='approximate') for s in old['segments']}
    index=pm.build_passage_index(work,pairs,passages,annotations,generated_from=stats['source'],source_lookup=lambda n:source_map[n])
    assert [p['id'] for p in old['passages']]==[p['id'] for p in index['passages']], 'passage ID migration required'
    assert [a['id'] for a in old['annotations']]==[a['id'] for a in index['annotations']], 'annotation ID migration required'
    config_path=bs.ROOT/'data/iiif_sources.json';cfg=json.loads(config_path.read_text(encoding='utf-8'))
    cfg['works'][WID]['mapping_precision']='approximate'
    config_path.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    bs.IIIF_SOURCES[WID]['mapping_precision']='approximate'
    canvas_map={str(s['segment']):int(s['source']['pages'][0]['number']) for s in index['segments'] if s['source'].get('pages')}
    texts=bs.build_texts(works);this=bs.text_group_key(work)
    related=[{'id':t['rep']['id'],'title':t['title'],'title_en':t['title_en'],'year':t['year']} for t in texts if t['genre']==work['genre'] and t['key']!=this][:4]
    main_path=bs.OUT/'works'/f'{WID}.html';old_html=main_path.read_text(encoding='utf-8')
    main=bs.build_work(env,work,body,True,None,chapters,related,prev_work_id=works[position-1]['id'] if position else None,next_work_id=works[position+1]['id'] if position+1<len(works) else None,passage_count=len(passages),has_tei=True,iiif_canvas_map=canvas_map)
    assert set(re.findall(r'\bid="([^"]+)"',old_html))<=set(re.findall(r'\bid="([^"]+)"',main)),'existing HTML targets lost'
    main_path.write_text(main,encoding='utf-8',newline='\n')
    (bs.OUT/'works'/f'{WID}_parallel.html').write_text(bs.build_parallel(env,work,pairs,stats,None,chapters),encoding='utf-8',newline='\n')
    pm.write_passage_index(index_path,index);pm.write_tei(bs.OUT/'tei'/f'{WID}.xml',index)
    tw=next(w for w in t4b.load_t4b_works() if w['id']==WID)
    (bs.OUT/'works'/f'{WID}-trithemius-4b.html').write_text(t4b.build_t4b_work_page(env,tw),encoding='utf-8',newline='\n')
    t4b.link_t4b_into_main_pages([tw])
    provider=json.loads((bs.ROOT/'data/iiif/provider'/f'{WID}.json').read_text(encoding='utf-8'))
    normalized=iiif_model.normalize(WID,cfg['works'][WID],provider,index)
    (bs.OUT/'iiif'/WID/'manifest.json').write_text(json.dumps(normalized,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    record=exports.build_one(bs.ROOT/'works'/WID,exports.CSS_SOURCE.read_text(encoding='utf-8'),exports.EPUB_CSS_SOURCE.read_text(encoding='utf-8'),exports.publication_version(),exports.modified_timestamp())
    publication_index=exports.OUT/'index.json';publication=json.loads(publication_index.read_text(encoding='utf-8'))
    publication['works']=[record if row['id']==WID else row for row in publication['works']]
    publication_index.write_text(json.dumps(publication,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(f'Rebuilt Scribes: {len(passages)} passage IDs and {len(annotations)} annotation IDs preserved; both reading tracks, parallel view, TEI, IIIF, EPUB and print refreshed.')


if __name__=='__main__':main()
