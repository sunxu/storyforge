import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('r54_last_step',ROOT/'scripts/v03_r54_last_step_checkpoint_gate.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

class FinalStepGateTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.out=Path(t.name);self.final=self.out/'checkpoint-16';self.mid=self.out/'checkpoint-8'
        self.final.mkdir();self.mid.mkdir()
        self.state={'global_step':16,'epoch':1.0,'log_history':[
            {'step':1,'loss':2.3},{'step':4,'eval_loss':1.9},
            {'step':8,'eval_loss':1.8},{'step':12,'eval_loss':1.7},
            {'step':16,'eval_loss':1.6}]}
        self.config={'peft_type':'LORA','r':64,'lora_alpha':128}
        (self.final/'trainer_state.json').write_text(json.dumps(self.state))
        (self.final/'adapter_config.json').write_text(json.dumps(self.config))
        (self.final/'adapter_model.safetensors').write_bytes(b'Synthetic adapter content not a real model')
        self.reload=self.out/'reload.json'
        self.reload.write_text(json.dumps({'status':'R54_ADAPTER_RELOAD_INFERENCE_PASS',
            'final_global_step':16, 'adapter_sha256':g.sha(self.final/'adapter_model.safetensors'),
            'model_revision':g.MODEL_REVISION}))
    def write_state(self):
        (self.final/'trainer_state.json').write_text(json.dumps(self.state))
    def expect_block(self, message):
        with self.assertRaisesRegex(ValueError,message):g.check(self.out)
    def test_good_checkpoint_pre_reload(self):
        r=g.check(self.out);self.assertIn('RELOAD_PENDING',r['status']);self.assertEqual(r['global_step'],16)
    def test_real_ms_swift_nested_version_dir(self):
        # Real R46 path: output/v0-20261014-070817/checkpoint-7.
        version_dir=self.out/'v0-20261014-070817'
        version_dir.mkdir()
        self.final.rename(version_dir/'checkpoint-16')
        self.mid.rename(version_dir/'checkpoint-8')
        r=g.check(self.out,self.reload)
        self.assertEqual(r['final_checkpoint_relpath'],
                         'v0-20261014-070817/checkpoint-16')
        self.assertTrue(r['final_checkpoint_path'].endswith(
                        '/v0-20261014-070817/checkpoint-16'))
    def test_duplicate_terminal_checkpoint_blocked(self):
        version_dir=self.out/'v0-20261014-070817'
        version_dir.mkdir()
        (version_dir/'checkpoint-16').mkdir()
        self.expect_block('exactly one')
    def test_bad_nested_version_name_rejected(self):
        version_dir=self.out/'not-an-ms-swift-run'
        version_dir.mkdir()
        self.final.rename(version_dir/'checkpoint-16')
        self.mid.rename(version_dir/'checkpoint-8')
        self.expect_block('unexpected or symlinked')
    def test_good_checkpoint_with_reload(self):
        self.assertIn('AND_RELOAD',g.check(self.out,self.reload)['status'])
    def test_step3_or_step8_not_final(self):
        self.state['global_step']=8;self.write_state();self.expect_block('global_step')
    def test_no_final_checkpoint(self):
        self.final.rename(self.out/'checkpoint-15');self.expect_block('checkpoint-16')
    def test_no_intermediate_save(self):
        self.mid.rmdir();self.expect_block('checkpoint-8')
    def test_non_final_epoch(self):
        self.state['epoch']=0.5;self.write_state();self.expect_block('epoch')
    def test_nan_validation_loss(self):
        self.state['log_history'][2]['eval_loss']=float('nan');self.write_state();self.expect_block('eval_loss')
    def test_missing_final_weights(self):
        (self.final/'adapter_model.safetensors').unlink();self.expect_block('adapter weights')
    def test_wrong_lora_rank(self):
        self.config['r']=8;(self.final/'adapter_config.json').write_text(json.dumps(self.config));self.expect_block('r/alpha')
    def test_forged_reload_hash(self):
        r=json.loads(self.reload.read_text());r['adapter_sha256']='f'*64;self.reload.write_text(json.dumps(r))
        with self.assertRaisesRegex(ValueError,'reload proof'):g.check(self.out,self.reload)
    def test_reject_adapter_symlink(self):
        p=self.final/'adapter_model.safetensors';dst=self.out/'other.safetensors';p.rename(dst);p.symlink_to(dst)
        self.expect_block('adapter weights')
    def test_no_run_job_code(self):
        src=(ROOT/'scripts/v03_r54_last_step_checkpoint_gate.py').read_text()
        for bad in ('hf jobs run','swift sft','torch.cuda','subprocess.run','os.system'):
            self.assertNotIn(bad,src)

if __name__=='__main__':unittest.main()
