#!/usr/bin/env python3
"""Offline verification of completed R47 old-test evaluation outputs. No GPU."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from v02_r47_eval_validate import validate_prompts, validate_responses

RUN_KEY = "r47-20261014T091647Z-637890"
OLD_KEY = "r47-20261014T082109Z-820409"
OLD_BASE_SHA = "becd890268edb1002c3f7195a1906f73045a86643fdac45eaf7090ee82d4dcfe"
STATUS = "R47_THREE_MODEL_REGRESSION_GENERATION_PASS_NOT_PROMOTED"
ADAPTERS = {
    "v01": "621d7328056758607c9d7797282ae4d5803cdb1727dab6b40a321ee959dd2478",
    "v02": "bec4ba74d858db3ff117d581478ef9cac41b1ecc7ea2a67523f6db1096addf2b",
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def check(ok: bool, why: str) -> None:
    if not ok:
        raise ValueError(why)


def verify(directory: Path, prompts: Path, manifest: Path) -> dict:
    own = directory / "coordinator"
    review = directory / "reviewers"
    report = load(own / "R47_PRIVATE_RUN_REPORT.json")
    check(report.get("status") == STATUS and report.get("generation_complete") is True,
          "the three-arm job did not finish successfully")
    check(report.get("run_key") == RUN_KEY, "wrong R47 Job run key")
    check(report.get("scope") == "EXPOSED_V01_20_RETROSPECTIVE_ONLY", "wrong test scope")
    check(report.get("completed_arms") == ["base", "v01", "v02"], "missing model inference")
    check(report.get("training_performed") is False
          and report.get("fresh_heldout") is False
          and report.get("promotion_approved") is False,
          "unexpected evaluation gate or training status")
    check(not report.get("error"), "GPU runner reported error")
    check(report.get("model_revision") == "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0",
          "base model revision mismatch")
    check(report.get("adapter_weight_sha256") == ADAPTERS, "adapter identity mismatch")
    reused = report.get("reused_base") or {}
    check(reused.get("run_key") == OLD_KEY and reused.get("sha256") == OLD_BASE_SHA,
          "old Base model response was not reused intact")
    inputs, samples = validate_prompts(prompts, manifest)
    source = report.get("input") or {}
    check(source.get("count") == 20
          and source.get("prompts_sha256") == sha(prompts)
          and source.get("manifest_sha256") == sha(manifest),
          "frozen prompts or manifest changed")
    digests = {}
    answers = {}
    for model in ("base", "v01", "v02"):
        result = own / f"{model}-results.jsonl"
        answers[model] = validate_responses(result, inputs)
        digests[model] = sha(result)
        check(len(answers[model]) == 20, f"{model}: not 20 replies")
        check((report.get("results_sha256") or {}).get(model) == digests[model],
              f"{model}: result hash changed")
    check(digests["base"] == OLD_BASE_SHA, "old Base bytes changed")
    blind = review / "R47_BLIND_THREE_WAY_20.jsonl"
    key = own / "private" / "R47_PRIVATE_ANSWER_KEY.json"
    audit = load(own / "private" / "R47_AUDIT_SUMMARY.json")
    details = report.get("blind_pack") or {}
    values = {
        "samples": 20, "responses": 60, "prompt_sha256": sha(prompts),
        "manifest_sha256": sha(manifest), "blind_sha256": sha(blind),
        "key_sha256": sha(key), "results_sha256": digests,
        "fresh_independent_heldout": False, "model_promotion": False,
    }
    for name, value in values.items():
        check(details.get(name) == value and audit.get(name) == value,
              f"private blind audit mismatch: {name}")
    check(audit.get("status") == "R47_BLIND_EXPORT_PASS_NOT_FRESH_HELDOUT",
          "blind export not accepted")
    key_data = load(key)
    check(key_data.get("mode") == "RETROSPECTIVE_EXPOSED_V01_TEST",
          "wrong private answer key")
    keys = key_data.get("items") or []
    blind_rows = [
        json.loads(line) for line in blind.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    check(len(keys) == len(blind_rows) == 20, "blind count mismatch")
    for i, (secret, row, sample) in enumerate(zip(keys, blind_rows, samples, strict=True)):
        check(secret.get("sample_id") == row.get("sample_id") == sample["sample_id"],
              f"blind ID mismatch at {i}")
        check(row.get("prompt_sha256") == sample["prompt_sha256"],
              f"blind prompt hash mismatch at {i}")
        mapping = secret.get("mapping")
        check(isinstance(mapping, dict) and set(mapping) == set("ABC")
              and set(mapping.values()) == set(answers),
              f"invalid private permutation at {i}")
        for letter, model in mapping.items():
            check(row.get(f"response_{letter.lower()}") == answers[model][i],
                  f"response permutation mismatch at {i}/{letter}")
    for reviewer_id in (1, 2, 3):
        csv_file = review / f"R47_Reviewer_{reviewer_id:02d}.csv"
        with csv_file.open(encoding="utf-8-sig", newline="") as handle:
            sheet = list(csv.DictReader(handle))
        check(len(sheet) == 20, f"reviewer {reviewer_id}: wrong row count")
        for i, (row, blind_row) in enumerate(zip(sheet, blind_rows, strict=True)):
            check(row.get("样本编号") == blind_row["sample_id"],
                  f"reviewer {reviewer_id}: wrong sample at {i}")
            for letter in "ABC":
                check(row.get(f"回复{letter}") == blind_row[f"response_{letter.lower()}"],
                      f"reviewer {reviewer_id}: wrong response {i}/{letter}")
            check(row.get("整体最佳(A/B/C/TIE)") in ("", None),
                  f"reviewer {reviewer_id}: preference unexpectedly filled")
    return {
        "status": "R47_THREE_ARM_20_60_BLIND_INTEGRITY_PASS_NO_PROMOTION",
        "run_key": RUN_KEY,
        "job_id_reported_by_owner": "6acf48935ccb47ba0f79853d",
        "responses": 60,
        "reviewer_files": 3,
        "reused_base_sha256": OLD_BASE_SHA,
        "result_file_sha256": digests,
        "answer_key_sha256": sha(key),
        "private_report_sha256": sha(own / "R47_PRIVATE_RUN_REPORT.json"),
        "fresh_independent_heldout": False,
        "model_promotion": False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--directory", type=Path, required=True)
    p.add_argument("--prompts", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    args = p.parse_args()
    result = verify(args.directory, args.prompts, args.manifest)
    target = args.directory / "coordinator" / "R47_LOCAL_INTEGRITY_PASS.json"
    if target.exists():
        raise FileExistsError("refusing to overwrite local acceptance evidence")
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    print("R47_LOCAL_REPORT=" + str(target))
    print("R47_REVIEWER_DIR=" + str(args.directory / "reviewers"))
    print("R47_PRIVATE_COORDINATOR_DIR=" + str(args.directory / "coordinator"))


if __name__ == "__main__":
    main()
