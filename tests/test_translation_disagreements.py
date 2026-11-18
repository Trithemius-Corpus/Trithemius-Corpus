import json
from pathlib import Path
import sys
import tempfile
import unittest
import jsonschema
import copy
import re
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_translation_disagreements as b
from validate_translation_disagreements import validate_reference, validate_queue, validate_inventory


class AlignmentTests(unittest.TestCase):
    def compare(self, left, right):
        return b.candidate_inventory(left, right, {"earlier": [0, len(left)], "t4b": [0, len(right)]})

    def test_negation_has_exact_nonempty_and_insertion_point_spans(self):
        left, right = "I knew it did not exceed my powers.", "I knew it did exceed my powers."
        rows, _ = self.compare(left, right)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["earlier_text"], "not")
        self.assertEqual(rows[0]["t4b_text"], "")
        self.assertIn("negation_token_difference", rows[0]["signals"])

    def test_different_chunk_and_page_boundaries_do_not_create_word_changes(self):
        left = "He writes.\n[segment 1]\nShe reads.\n[segment 2]\nThey learn."
        right = "He writes. She reads.\n--- Page 007 ---\nThey learn."
        rows, coverage = self.compare(left, right)
        self.assertEqual(rows, [])
        self.assertEqual(coverage["earlier_tokens"], coverage["matched_tokens"])

    def test_case_and_punctuation_alone_do_not_become_candidates(self):
        rows, _ = self.compare("The scribe’s book, written well.", "THE SCRIBE'S BOOK; WRITTEN WELL!")
        self.assertEqual(rows, [])

    def test_numbers_and_missing_clauses_remain_searchable_signals(self):
        rows, _ = self.compare("He bought three books.", "He bought four books. They were copied for the brothers of the monastery.")
        self.assertTrue(any("number_token_difference" in r["signals"] for r in rows))
        self.assertTrue(any("extended_text_difference" in r["signals"] for r in rows))

    def test_empty_side_is_a_valid_omission_not_an_index_error(self):
        rows, _ = self.compare("", "A missing sentence.")
        self.assertEqual(rows[0]["earlier"]["start"], rows[0]["earlier"]["end"])
        self.assertEqual(rows[0]["t4b_text"], "A missing sentence")

    def test_lexical_signal_does_not_claim_semantic_error(self):
        rows, _ = self.compare("They are unwilling to write.", "They do not wish to write.")
        self.assertTrue(any("negation_token_difference" in r["signals"] for r in rows))
        self.assertTrue(all(r["status"] == "untriaged_lexical_difference" for r in rows))
        self.assertTrue(all("priority" not in r for r in rows))

    def test_candidate_ids_are_bound_to_the_source_snapshot(self):
        a, _ = self.compare('A cat.', 'A dog.')
        c, _ = self.compare('A cow.', 'A pig.')
        self.assertNotEqual(a[0]['id'], c[0]['id'])

    def test_reordered_sentences_conserve_tokens_and_cover_eof_insertions(self):
        left='The abbot writes. The monk reads.'
        right='The monk reads. The abbot writes.'
        rows,counts=self.compare(left,right)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            sources={}
            for track,text in (('earlier',left),('t4b',right)):
                path=root/(track+'.txt');path.write_text(text,encoding='utf-8')
                sources[track+'_english']={'path':path.name,'sha256':b.digest(text)}
            inv={'work_id':'synthetic','sources':sources,'comparison_scope':{'earlier':[0,len(left)],'t4b':[0,len(right)]},'coverage':counts,'offset_convention':b.OFFSET_CONVENTION,'candidate_id_version':b.ID_VERSION,'candidates':rows}
            validate_inventory(inv,inv,root)
        self.assertEqual({row['operation'] for row in rows},{'insert','delete'})

    def test_split_or_merged_sentences_do_not_claim_lexical_change(self):
        rows,_=self.compare('He writes. She reads.', 'He writes; she reads.')
        self.assertEqual(rows,[])


class ProvenanceTests(unittest.TestCase):
    def test_ambiguous_and_missing_quotations_are_rejected(self):
        for quote in ("same", "absent", ""):
            with self.assertRaises(ValueError):
                b.locate("same and same", quote)

    def test_unicode_offsets_and_lines_are_verified_independently(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            text = "αβ\nI knew it exceeded.\n"
            (root / "source.txt").write_text(text, encoding="utf-8", newline="\n")
            a, z = b.locate(text, "I knew it exceeded.")
            ref = b.reference("source.txt", text, a, z)
            validate_reference(ref, root)
            for field, bad in (("quote", "I knew it did not exceed."), ("start", a + 1), ("start_line", 1), ("sha256", "0" * 64)):
                damaged = dict(ref, **{field: bad})
                with self.assertRaises(ValueError, msg=field):
                    validate_reference(damaged, root)

    def test_source_paths_cannot_escape_repository(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                b.resolve_source("../outside.txt", Path(folder))

    def test_stale_frozen_source_is_rejected_before_alignment(self):
        spec = json.loads(b.read(b.ROOT / "data/translation_disagreements" / b.DEFAULT_WORK / "review.json"))
        spec["sources"]["earlier_english"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "frozen source changed"):
            b.assemble(spec)

    def test_different_printed_witness_is_rejected(self):
        spec = json.loads(b.read(b.ROOT / "data/translation_disagreements" / b.DEFAULT_WORK / "review.json"))
        spec["witness_id"] = "bsb00000000"
        with self.assertRaisesRegex(ValueError, "source-witness mismatch"):
            b.assemble(spec)

    def test_partial_empty_and_url_component_witness_ids_are_rejected(self):
        spec = json.loads(b.read(b.ROOT / "data/translation_disagreements" / b.DEFAULT_WORK / "review.json"))
        for identifier in ('bsb0003742', '', 'image_1', 'digitale-sammlungen.de', 'bsb00000000'):
            spec['witness_id'] = identifier
            with self.subTest(identifier=identifier), self.assertRaisesRegex(ValueError, 'source-witness mismatch'):
                b.assemble(spec)

    def test_independent_validator_rejects_consistently_rehashed_bad_metadata(self):
        path = b.ROOT / 'review/translation-disagreements' / b.DEFAULT_WORK / 'queue.json'
        original = json.loads(b.read(path))
        mutations = [
            lambda q: q['coverage'].update(matched_tokens=999999),
            lambda q: q['comparison_scope'].update(earlier=[0,1]),
            lambda q: q['sources']['earlier_english'].update(sha256='0'*64),
            lambda q: q.update(offset_convention=None),
        ]
        for mutate in mutations:
            q=copy.deepcopy(original);mutate(q)
            q['content_digest']=b.digest(b.json_text({k:v for k,v in q.items() if k!='content_digest'}))
            with self.assertRaises((ValueError,jsonschema.ValidationError)):
                validate_queue(q)

    def test_inventory_rejects_a_missing_difference_without_using_the_aligner(self):
        base=b.ROOT/'review/translation-disagreements'/b.DEFAULT_WORK
        q=json.loads(b.read(base/'queue.json')); inv=json.loads(b.read(base/'candidates.json'))
        inv['candidates'].pop()
        inv['coverage']['lexical_difference_count']-=1
        q['coverage']['lexical_difference_count']-=1
        with self.assertRaises(ValueError):validate_inventory(q,inv)

    def test_permalink_reveals_excluded_records_and_clears_incompatible_search(self):
        q=json.loads(b.read(b.ROOT/'review/translation-disagreements'/b.DEFAULT_WORK/'queue.json'))
        script=re.search(r'<script>(.*?)</script>',b.render(q),re.S)[1]
        harness = r'''const vm=require('vm');let script='';process.stdin.on('data',d=>script+=d);process.stdin.on('end',()=>{for(const id of ['scribes-101','scribes-102','scribes-103']){const controls={priority:{value:'queue',addEventListener(){}},'filter-text':{value:'incompatible',addEventListener(){}},count:{}};const card={id,dataset:{priority:'excluded'},textContent:'control',hidden:true,setAttribute(){},focus(){this.focused=true},scrollIntoView(){}};const events={};const context={document:{getElementById:id=>controls[id],querySelectorAll:()=>[card]},location:{hash:'#'+id},window:{addEventListener:(e,cb)=>events[e]=cb}};vm.runInNewContext(script,context);if(card.hidden||!card.focused||controls.priority.value!=='excluded'||controls['filter-text'].value!=='')throw Error(id);controls['filter-text'].value='mismatch';card.hidden=true;events.hashchange();if(card.hidden)throw Error('hashchange');}process.stdout.write('permalinks passed');});'''
        result=subprocess.run(['node','-e',harness],input=script,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_machine_queue_cannot_claim_facsimile_verification(self):
        queue = json.loads(b.read(b.ROOT / "review/translation-disagreements" / b.DEFAULT_WORK / "queue.json"))
        schema = json.loads(b.read(b.ROOT / "data/schemas/translation-disagreement-queue.schema.json"))
        queue["items"][0]["facsimile_verified"] = True
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(queue)


if __name__ == "__main__":
    unittest.main()
