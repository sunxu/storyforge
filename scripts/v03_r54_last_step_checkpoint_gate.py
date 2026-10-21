#!/usr/bin/env python3
"""Fail-closed R54 training artifact check; NEVER starts training or imports model.

Requires a checkpoint that corresponds to the *actual final optimizer step* and
includes adapter weights, config and Trainer state. Final inference reload
requires separate proof from the future GPU runner; checkpoint PASS != reload PASS.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys

EXPECTED_STEPS = 16
EXPECTED_EVAL_STEPS = (4, 8, 12, 16)
MODEL_REVISION = '1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0'


def must(ok: bool, msg: str) -> None:
    if not ok:
        raise ValueError(msg)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def normal_file(p: Path) -> bool:
    return p.is_file() and not p.is_symlink() and p.stat().st_size > 0


def read_json(p: Path):
    must(normal_file(p), f'missing or empty artifact: {p.name}')
    return json.loads(p.read_bytes())


def finite(x) -> bool:
    try:
        return isinstance(x, (int, float)) and math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def check(output: Path, reload_report: Path | None = None) -> dict:
    must(output.is_dir() and not output.is_symlink(), 'training output missing')
    final = output / f'checkpoint-{EXPECTED_STEPS}'
    must(final.is_dir() and not final.is_symlink(), 'final step checkpoint-16 missing')
    mid = output / 'checkpoint-8'
    must(mid.is_dir() and not mid.is_symlink(), 'scheduled intermediate checkpoint-8 missing')
    state = read_json(final / 'trainer_state.json')
    must(type(state.get('global_step')) is int and state['global_step'] == EXPECTED_STEPS,
         'final checkpoint trainer_state global_step is not 16')
    must(finite(state.get('epoch')) and float(state['epoch']) >= 0.99,
         'one epoch did not finish')
    logs = state.get('log_history')
    must(isinstance(logs, list), 'trainer_state log_history missing')
    eval_steps = set()
    has_finite_loss = False
    for entry in logs:
        if not isinstance(entry, dict):
            continue
        step = entry.get('step')
        if step in EXPECTED_EVAL_STEPS and finite(entry.get('eval_loss')):
            eval_steps.add(step)
        if finite(entry.get('loss')):
            has_finite_loss = True
    must(set(EXPECTED_EVAL_STEPS).issubset(eval_steps),
         'expected scheduled eval_loss at steps 4,8,12 missing')
    must(has_finite_loss, 'no finite train loss in Trainer state')
    must(normal_file(final / 'adapter_model.safetensors'), 'final adapter weights absent')
    cfg = read_json(final / 'adapter_config.json')
    must(isinstance(cfg, dict) and str(cfg.get('peft_type', '')).upper() == 'LORA',
         'final adapter is not LoRA')
    must(cfg.get('r') == 64 and cfg.get('lora_alpha') == 128,
         'final adapter r/alpha mismatch')
    digest = sha(final / 'adapter_model.safetensors')
    report = {
        'schema': 'storyforge-r54-final-checkpoint-v2',
        'status': 'R54_FINAL_OPTIMIZER_STEP_16_CHECKPOINT_PRESENT__RELOAD_PENDING',
        'global_step': EXPECTED_STEPS,
        'final_checkpoint': final.name,
        'intermediate_checkpoint': mid.name,
        'final_adapter_sha256': digest,
        'final_adapter_config_sha256': sha(final / 'adapter_config.json'),
        'trainer_state_sha256': sha(final / 'trainer_state.json'),
        'eval_steps_verified': sorted(eval_steps),
        'gpu_job_launched_by_this_checker': False,
        'r50_read_by_this_checker': False,
    }
    if reload_report is not None:
        reload = read_json(reload_report)
        must(reload.get('status') == 'R54_ADAPTER_RELOAD_INFERENCE_PASS' and
             reload.get('final_global_step') == EXPECTED_STEPS and
             reload.get('adapter_sha256') == digest and
             reload.get('model_revision') == MODEL_REVISION,
             'final step adapter reload proof does not match exact saved adapter')
        report['status'] = 'R54_FINAL_STEP_16_CHECKPOINT_AND_RELOAD_EVIDENCE_ACCEPTED__NOT_PROMOTED'
        report['reload_report_sha256'] = sha(reload_report)
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output-dir', type=Path, required=True)
    ap.add_argument('--reload-report', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    try:
        result = check(a.output_dir, a.reload_report)
        must(not a.out.exists(), 'receipt overwrite forbidden')
        a.out.parent.mkdir(parents=True, exist_ok=True)
        with a.out.open('x', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write('\n')
        print(result['status'])
        return 0
    except (OSError, ValueError, KeyError, TypeError) as e:
        print('R54_FINAL_CHECKPOINT_GATE_BLOCKED:', str(e), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
