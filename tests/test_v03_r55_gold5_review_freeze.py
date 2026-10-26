"""Synthetic R55 Gold5 v2 round freeze tests. No actual private story texts."""
import csv
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import v03_r55_gold5_review_freeze as mod


def csvbytes(labels, idx, complete=False, flag='NONE', reason='Visible cited example'):
    fixed = (*mod.COMMON, *(f'回复{x}' for x in labels))
    _, _, pref, agency, banned = mod.MODES[{2:'pair',4:'four',5:'five'}[len(labels)]]
    score = tuple(f'{d}·{l}' for d in mod.DIMS for l in labels)
    fields = (*fixed, pref, *mod.NOTES, agency, banned, *score)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields)
    w.writeheader()
    for case in range(20):
        row = {'样本编号':f'case-{case}', '故事背景与系统规则':'Synthetic world',
               '历史对话':'History', '当前用户输入':'input', **{f'回复{l}':f'Answer for {l}' for l in labels}}
        if complete:
            row.update({pref:labels[0], '偏好理由与可见原文证据':reason + f' from reviewer {idx}',
                        agency:flag, banned:'NONE', '逐事件严重问题证据':reason if flag!='NONE' else '',
                        **{key:'4' for key in score}})
        w.writerow(row)
    return buf.getvalue().encode('utf-8-sig')

class TestFreeze(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.pack=self.root/'owner-pack-v2'
        self.reviews=self.pack/'reviewers'
        self.reviews.mkdir(parents=True)
        self.hashes={}
        self.done={}
        for mode,(prefix,labels,*_) in mod.MODES.items():
            self.done[mode]=[]
            for i in range(1,4):
                blank=f'R55_GOLD5_{prefix}_V2_Reviewer_{i:02d}_PRIVATE.csv'
                b=csvbytes(labels,i)
                (self.reviews/blank).write_bytes(b)
                self.hashes[blank]=mod.sha(b)
                target=self.root/f'done-{mode}-{i}.csv'
                target.write_bytes(csvbytes(labels,i,True))
                self.done[mode].append(target)
        receipt={
            'schema':'storyforge-r55-gold5-v2-safe-prep-v1',
            'status':mod.EXPECTED_STATUS,
            'case_count':20,'reviewer_count':3,'reviewer_csv_count':9,
            'reviewers_completed':0,'new_heldout':False,'r50_accessed':False,'gpu_inference':False,
            'training':False,'model_promoted':False,'three_distinct_blind_tasks':True,
            'reviewer_private_csv_sha256':self.hashes,
        }
        (self.pack/'R55_GOLD5_V2_PREP_SAFE_COUNT_ONLY.json').write_text(json.dumps(receipt))
    def freeze(self,mode,files=None,out=None,prior_pair=None,prior_four=None):
        if out is None:
            out=self.root/f'freeze-{mode}'
        return mod.freeze_round(self.pack,mode,tuple(files if files is not None else self.done[mode]),out,prior_pair,prior_four)
    def mutate(self,path, f):
        fields,rows=mod.parse_csv(path.read_bytes())
        f(rows)
        stream=io.StringIO()
        writer=csv.DictWriter(stream,fieldnames=fields)
        writer.writeheader();writer.writerows(rows)
        path.write_bytes(stream.getvalue().encode('utf-8-sig'))
    def expect_hold(self,mode,code,files=None,**kwargs):
        with self.assertRaises(mod.Hold) as ctx:
            self.freeze(mode,files,**kwargs)
        self.assertEqual(str(ctx.exception),code)
        self.assertFalse((self.root/f'freeze-{mode}').exists())
    def test_pair_pass_720_cells(self):
        result=self.freeze('pair')
        self.assertEqual(result['ratings_verified'],720)
        self.assertEqual(result['reviewer_count'],3)
        self.assertTrue((self.root/'freeze-pair/R55_GOLD5_V2_ROUND_FREEZE_SAFE.json').is_file())
        self.assertEqual((self.root/'freeze-pair/R55_GOLD5_PAIR_V2_Reviewer_01_FROZEN_PRIVATE.csv').stat().st_mode & 0o777, 0o400)
    def test_four_requires_pair(self):self.expect_hold('four','PAIR_FREEZE_REQUIRED_FIRST')
    def test_five_requires_pair(self):self.expect_hold('five','PAIR_FREEZE_REQUIRED_FIRST')
    def test_four_then_five(self):
        self.freeze('pair')
        pair=self.root/'freeze-pair/R55_GOLD5_V2_ROUND_FREEZE_SAFE.json'
        self.assertEqual(self.freeze('four',prior_pair=pair)['ratings_verified'],1440)
        four=self.root/'freeze-four/R55_GOLD5_V2_ROUND_FREEZE_SAFE.json'
        self.assertEqual(self.freeze('five',prior_pair=pair,prior_four=four)['ratings_verified'],1800)
    def test_five_requires_four(self):
        self.freeze('pair')
        self.expect_hold('five','FOUR_FREEZE_REQUIRED_FIRST',prior_pair=self.root/'freeze-pair/R55_GOLD5_V2_ROUND_FREEZE_SAFE.json')
    def test_edited_user_input(self):
        self.mutate(self.done['pair'][0],lambda rows:rows[3].__setitem__('当前用户输入','Tampered'))
        self.expect_hold('pair','FROZEN_SOURCE_OR_ORDER_MODIFIED')
    def test_edited_model_text(self):
        self.mutate(self.done['pair'][0],lambda rows:rows[0].__setitem__('回复LEFT','Tampered'))
        self.expect_hold('pair','FROZEN_SOURCE_OR_ORDER_MODIFIED')
    def test_missing_rating(self):
        self.mutate(self.done['pair'][0],lambda rows:rows[0].__setitem__('剧情连续性·LEFT',''))
        self.expect_hold('pair','INVALID_OR_MISSING_RATING')
    def test_bad_rating(self):
        self.mutate(self.done['pair'][0],lambda rows:rows[0].__setitem__('剧情连续性·LEFT','4.5'))
        self.expect_hold('pair','INVALID_OR_MISSING_RATING')
    def test_missing_preference(self):
        self.mutate(self.done['pair'][0],lambda rows:rows[0].__setitem__('偏好(LEFT/RIGHT/TIE)',''))
        self.expect_hold('pair','INVALID_PREFERENCE')
    def test_missing_explanation(self):
        self.mutate(self.done['pair'][0],lambda rows:rows[0].__setitem__('偏好理由与可见原文证据',''))
        self.expect_hold('pair','MISSING_REASON')
    def test_bad_agency_flag(self):
        self.mutate(self.done['pair'][0],lambda rows:rows[0].__setitem__('严重玩家自主权问题(LEFT/RIGHT/BOTH/NONE)','ALL'))
        self.expect_hold('pair','INVALID_AGENCY_FLAG')
    def test_missing_violation_evidence(self):
        self.mutate(self.done['pair'][0],lambda rows:(rows[0].__setitem__('严重玩家自主权问题(LEFT/RIGHT/BOTH/NONE)','LEFT'), rows[0].__setitem__('逐事件严重问题证据','')))
        self.expect_hold('pair','MISSING_VIOLATION_EVIDENCE')
    def test_valid_violation(self):
        self.mutate(self.done['pair'][0],lambda rows:(rows[0].__setitem__('严重玩家自主权问题(LEFT/RIGHT/BOTH/NONE)','LEFT'), rows[0].__setitem__('逐事件严重问题证据','Synthetic exact quotation')))
        self.assertEqual(self.freeze('pair')['reviewer_case_flag_presence_count'],1)
    def test_duplicate_completed(self):
        files=[self.done['pair'][0]]*3
        self.expect_hold('pair','DUPLICATE_COMPLETED_REVIEW_FILES',files)
    def test_empty_review_not_acceptable(self):
        self.expect_hold('pair','COMPLETED_POINTS_TO_PRISTINE',[self.reviews/'R55_GOLD5_PAIR_V2_Reviewer_01_PRIVATE.csv', *self.done['pair'][1:]])
    def test_tampered_pristine(self):
        p=self.reviews/'R55_GOLD5_PAIR_V2_Reviewer_01_PRIVATE.csv';p.write_bytes(p.read_bytes()+b'\n')
        self.expect_hold('pair','PRISTINE_CSV_SHA_MISMATCH')
    def test_out_exists(self):
        target=self.root/'freeze-pair';target.mkdir()
        with self.assertRaises(mod.Hold) as ctx: self.freeze('pair')
        self.assertEqual(str(ctx.exception),'FREEZE_DIR_ALREADY_EXISTS')
    def test_bad_receipt(self):
        path=self.pack/'R55_GOLD5_V2_PREP_SAFE_COUNT_ONLY.json';x=json.loads(path.read_text());x['r50_accessed']=True;path.write_text(json.dumps(x))
        self.expect_hold('pair','PREP_RECEIPT_GATES_CHANGED')
    def test_bad_prev_receipt(self):
        self.freeze('pair');p=self.root/'freeze-pair/R55_GOLD5_V2_ROUND_FREEZE_SAFE.json'
        x=json.loads(p.read_text());x['unblinding_performed']=True;p.write_text(json.dumps(x))
        self.expect_hold('four','WRONG_PRIOR_FREEZE_RECEIPT',prior_pair=p)
    def test_csv_duplicate_heading(self):
        with self.assertRaises(mod.Hold):mod.parse_csv(b'A,A\n1,2\n')
    def test_three_answer_duplicate_label(self):
        self.assertFalse(mod.check_flag('A,A',tuple('ABCD'),False))
    def test_unknown_letter(self):
        self.assertFalse(mod.check_flag('X',tuple('ABCD'),False))
    def test_four_valid_multilabel(self):
        self.assertTrue(mod.check_flag('A,C',tuple('ABCD'),False))
    def test_symlink_refused(self):
        link=self.root/'link.csv';link.symlink_to(self.done['pair'][0])
        self.expect_hold('pair','COMPLETED_REVIEW_MISSING_OR_SYMLINK',[link,*self.done['pair'][1:]])

if __name__=='__main__':unittest.main()
