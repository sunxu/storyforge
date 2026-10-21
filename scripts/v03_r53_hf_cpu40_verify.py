#!/usr/bin/env python3
"""R53 CPU 40-row results intake: strict, read-only, fail-closed.

This verifies the returned HF private Bucket report and log against frozen local data.
It is not independent proof of remote CPU execution without the original HF Job ID/log.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path
from v03_r53_hf_cpu40_audit import (COUNTS, EXPECTED_AUDITOR_BLOB, EXPECTED_PACKAGE_VERSIONS,
                                    MANIFEST_SHA, REV, SOURCE_SHA, COMPILED_SHA, MODEL, preflight, sha)

EXPECTED_STATUS = "R53_HF_CPU40_REAL_TOKENIZER_COLLATOR_MASK_PASS__NO_DATA_ADMISSION"

def ensure(val: bool, why: str):
    if not val: raise ValueError(why)

def verify(stage: Path, report_file: Path, log_file: Path, result_out: Path) -> dict:
    rows, compiled = preflight(stage)
    ensure(not result_out.exists(), "R53 verify output exists: refusing overwrite")
    report_bytes = report_file.read_bytes()
    data = json.loads(report_bytes)
    ensure(data["status"] == EXPECTED_STATUS, "R53 remote result is not genuine PASS status")
    ensure(data["expected_rows"] == COUNTS and data["checked"] == COUNTS,
           "R53 remote report 31/9 counts mismatch")
    ensure(data["formal_training_admission"] is False and data["training_performed"] is False
           and data["gpu_used"] is False and data["r50_read"] is False,
           "R53 unauthorized training, GPU, or heldout claim")
    ensure(data["model"] == MODEL and data["model_revision"] == REV,
           "R53 Qwen model revision changed")
    ensure(data["stage_manifest_sha256"] == MANIFEST_SHA and data["compiled_input_sha256"] == COMPILED_SHA
           and data["source_input_sha256"] == SOURCE_SHA,
           "R53 source provenance fingerprint mismatch")
    ensure(data["versions"] == EXPECTED_PACKAGE_VERSIONS,
           "R53 ms-swift/transformers versions mismatch")
    ensure(data["snapshot_revision"] == REV, "R53 resolved Qwen snapshot revision mismatch")
    ensure(isinstance(data.get("tokenizer_asset_sha256"), dict)
           and all(isinstance(x, str) and len(x) == 64
                   for x in data["tokenizer_asset_sha256"].values())
           and set(data["tokenizer_asset_sha256"]) == {"tokenizer.json", "tokenizer_config.json"},
           "R53 tokenizer asset fingerprints missing")
    ensure(isinstance(data.get("chat_template_sha256"), str)
           and len(data["chat_template_sha256"]) == 64, "R53 chat-template fingerprint missing")
    ensure(isinstance(data.get("auditor_script_sha256"), str)
           and len(data["auditor_script_sha256"]) == 64, "R53 audit script fingerprint absent")
    actual_rows = data.get("rows")
    ensure(isinstance(actual_rows, list) and len(actual_rows) == 40, "R53 report needs 40 audited rows")
    targets = {r["id"]: (part, r["metadata"]["target_sha256"])
               for part, group in rows.items() for r in group}
    seen = set()
    for r in actual_rows:
        cid = r["id"]
        ensure(cid in targets and cid not in seen, "R53 unknown or duplicate auditor case")
        seen.add(cid)
        split, target = targets[cid]
        ensure(r["split"] == split and r["target_sha256"] == target,
               "R53 returned case split or target mismatches private frozen source")
        ensure(r["status"] == "REAL_LAST_ASSISTANT_AND_COLLATOR_PASS", "R53 per-case failure")
        counts = (r["transformers_tokens"], r["native_tokens"], r["supervised_tokens"],
                  r["collated_tokens"], r["padding_tokens"])
        ensure(all(type(x) is int for x in counts) and 0 < counts[0] <= 16384
               and 0 < counts[1] <= 16384 and 0 < counts[2] <= counts[1]
               and counts[3] >= counts[1] and counts[4] == counts[3] - counts[1],
               "R53 invalid per-case token/collator counts")
        ensure(type(r["transformers_vs_swift_input_identical"]) is bool,
               "R53 missing tokenizer/template comparison result")
        ensure(isinstance(r["native_label_sha256"], str)
               and len(r["native_label_sha256"]) == 64, "R53 per-case label hash invalid")
    ensure(set(targets) == seen, "R53 incomplete case universe")
    log = log_file.read_bytes()
    ensure(b"R53_ACTUAL_HF_CPU40_LABEL_MASK_PASS 40/40" in log,
           "R53 no terminal 40/40 runtime marker in submitted log")
    ensure(b"R53_STATUS= R53_HF_CPU40_REAL_TOKENIZER_COLLATOR_MASK_PASS__NO_DATA_ADMISSION" in log,
           "R53 no exact report confirmation in log")
    if (log_file.parent / "R53_CPU40_RUNTIME_LOG_SHA256SUMS.txt").is_file():
        checksum_line = (log_file.parent / "R53_CPU40_RUNTIME_LOG_SHA256SUMS.txt").read_text().strip().split()
        ensure(checksum_line[0] == sha(log), "R53 log SHA256 sidecar mismatch")
    result = {
        "schema": "storyforge-r53-hf-cpu40-owner-intake-v1",
        "status": "R53_CPU40_RECEIPT_SOURCE_LOG_CROSSCHECK_PASS__NOT_DATA_RELEASE",
        "source_frozen_verified": True,
        "runtime_report_rows": COUNTS,
        "report_sha256": sha(report_bytes),
        "log_sha256": sha(log),
        "unique_source_cases": len(seen),
        "model_revision": f"{MODEL}@{REV}",
        "runtime_mask_status_from_submitted_report": EXPECTED_STATUS,
        "formal_training_admission": False,
        "paid_gpu_authorized": False,
        "r50_unopened": True,
        "limitations": "Owner-returned HF CPU report/log verified against frozen sources. Not an independent HF provider signature."
    }
    result_out.parent.mkdir(parents=True, exist_ok=True)
    result_out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)+"\n",encoding="utf-8")
    return result


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--stage", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--runtime-log", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args=ap.parse_args()
    try:
        result=verify(args.stage,args.report,args.runtime_log,args.out)
        print(result["status"])
    except (ValueError, KeyError, TypeError, FileNotFoundError, json.JSONDecodeError) as ex:
        print("R53_HF_CPU40_REPORT_REJECTED:", str(ex),file=sys.stderr)
        raise SystemExit(2)

if __name__=='__main__':main()
