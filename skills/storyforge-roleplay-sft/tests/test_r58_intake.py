import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SRC=Path(__file__).resolve().parents[1]/'scripts'/'r58_intake.py'
SHA='a'*64

def digest(s):
    return hashlib.sha256(s).hexdigest()

def jb(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')

def row(cid,world,split):
    msgs=[{'role':'system','content':'虚构的原始故事系统规则'}, {'role':'user','content':'请继续，测试会话 '+cid+' '+world}]
    target='NPC 说：'+cid
    return {'case_id':cid,'world_component_id':world,'split':split,'source_kind':'original_gold',
        'input_messages_sha256':digest(jb(msgs)), 'assistant_target_sha256':digest(target.encode()),
        'source_bytes_sha256':SHA, 'world_graph_certificate_sha256':SHA,
        'source_bytes_verified':True,'history_replay_verified':True,'target_time_canon_verified':True,
        'world_graph_verified':True,'protected_overlap_verified':True,'reviewer_independence_declared':True,
        'privacy_filtered':True,'owner_approved':True,'protected_test_exposed':False,
        'reviews':[{'reviewer_key':'independent_model_1','decision':'PASS','evidence_ref':'PRIVATE_EVIDENCE_1'},
                   {'reviewer_key':'independent_model_2','decision':'PASS','evidence_ref':'PRIVATE_EVIDENCE_2'}],
        'messages':msgs,'target_text':target}

class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self,*args,pass_expected=True):
        cp=subprocess.run([sys.executable,str(SRC),*map(str,args)],text=True,capture_output=True)
        if pass_expected:
            self.assertEqual(cp.returncode,0,cp.stderr)
        else:
            self.assertNotEqual(cp.returncode,0)
        return cp

    def jsonl(self,filename,rows):
        p=self.root/filename
        p.write_bytes(b''.join(jb(r)+b'\n' for r in rows))
        return p

    def gate(self,rows,filename='audit'):
        p=self.jsonl(filename+'.jsonl',rows)
        d=self.root/(filename+'.decision.jsonl')
        s=self.root/(filename+'.safe.json')
        self.run_cli('gate','--input',p,'--output',d,'--safe-output',s)
        return d,s

    def test_shortlist_filters_and_prevents_overwrite(self):
        rows=[]
        for i in range(5):
            rows.append({'story_id':str(i),'genre':'g'+str(i%2),'source_type':'original',
                'story_type':'v2_sandbox','not_deleted':'true','moderation_status':('approved' if i<4 else 'pending'),
                'assistant_completed':(60 if i<3 else 5),'session_count':3,
                'has_world':'t','has_character':'t','has_director':'t','has_opening':'t','has_characters':'t'})
        inp=self.root/'inventory.csv'
        with inp.open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
        dest=self.root/'shortlist.jsonl'
        self.run_cli('shortlist','--input',inp,'--output',dest,'--limit',2)
        self.assertEqual(len(dest.read_text().splitlines()),2)
        self.run_cli('shortlist','--input',inp,'--output',dest,'--limit',2,pass_expected=False)

    def test_gate_pass_requires_all_facts(self):
        a=row('a','world_a','train')
        b=row('b','world_b','validation')
        b['target_time_canon_verified']=False
        dec,safe=self.gate([a,b])
        results=[json.loads(x) for x in dec.read_text().splitlines()]
        self.assertEqual([x['decision'] for x in results],['PASS','HOLD'])
        self.assertNotIn('NPC 说',safe.read_text())

    def test_teacher_lineage_missing_blocks(self):
        a=row('a','world_a','train')
        a['source_kind']='teacher_rewrite'
        dec,_=self.gate([a]);self.assertEqual(json.loads(dec.read_text())['decision'],'HOLD')

    def test_same_reviewer_key_blocks(self):
        a=row('a','world_a','train')
        a['reviews'][1]['reviewer_key']='independent_model_1'
        dec,_=self.gate([a]);self.assertEqual(json.loads(dec.read_text())['decision'],'HOLD')

    def test_freeze_happy_and_no_overwrite(self):
        rows=[row('a','world_a','train'),row('b','world_b','validation')]
        dec,_=self.gate(rows)
        p=self.jsonl('content.jsonl',rows)
        output=self.root/'frozen'
        self.run_cli('freeze','--input',p,'--decision',dec,'--output-dir',output,'--world-graph-sha',SHA)
        self.assertTrue((output/'train.jsonl').exists())
        self.assertEqual(json.loads((output/'safe_manifest.json').read_text())['status'],
                         'CONTENT_FREEZE_ONLY__HF_CPU_PREFLIGHT_PENDING')
        self.assertNotIn('NPC 说',(output/'safe_manifest.json').read_text())
        self.run_cli('freeze','--input',p,'--decision',dec,'--output-dir',output,'--world-graph-sha',SHA,pass_expected=False)

    def test_freeze_world_leakage_holds(self):
        rows=[row('a','world_same','train'),row('b','world_same','validation')]
        dec,_=self.gate(rows)
        p=self.jsonl('content.jsonl',rows)
        output=self.root/'frozen'
        self.run_cli('freeze','--input',p,'--decision',dec,'--output-dir',output,'--world-graph-sha',SHA,pass_expected=False)
        self.assertFalse(output.exists())

    def test_freeze_corrupted_content_holds(self):
        rows=[row('a','world_a','train'),row('b','world_b','validation')]
        dec,_=self.gate(rows)
        rows[0]['target_text']='被篡改'
        p=self.jsonl('tampered.jsonl',rows)
        output=self.root/'frozen'
        self.run_cli('freeze','--input',p,'--decision',dec,'--output-dir',output,'--world-graph-sha',SHA,pass_expected=False)
        self.assertFalse(output.exists())

    def test_symlink_input_rejected(self):
        inp=self.jsonl('real.jsonl',[row('a','world_a','train')])
        link=self.root/'link.jsonl';link.symlink_to(inp)
        self.run_cli('gate','--input',link,'--output',self.root/'d.jsonl','--safe-output',self.root/'s.json',pass_expected=False)

    def test_teacher_target_never_validation(self):
        a=row('a','world_a','validation')
        a['source_kind']='teacher_generated'
        a['teacher_model']='teacher-pinned'
        a['teacher_recipe_sha256']=SHA
        a['parent_target_sha256']=SHA
        dec,_=self.gate([a])
        self.assertEqual(json.loads(dec.read_text())['reason'],'TEACHER_TARGET_NOT_ALLOWED_IN_VALIDATION')

    def test_teacher_ratio_blocks(self):
        rows=[row('a','world_a','train'),row('b','world_b','validation')]
        rows[0]['source_kind']='teacher_rewrite'
        rows[0]['teacher_model']='teacher-pinned-model'
        rows[0]['teacher_recipe_sha256']=SHA
        rows[0]['parent_target_sha256']=SHA
        dec,_=self.gate(rows)
        p=self.jsonl('content.jsonl',rows)
        output=self.root/'frozen'
        self.run_cli('freeze','--input',p,'--decision',dec,'--output-dir',output,'--world-graph-sha',SHA,pass_expected=False)
        self.assertFalse(output.exists())

if __name__=='__main__':
    unittest.main()
