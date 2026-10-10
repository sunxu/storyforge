"""Cross-check the frozen StoryForge v0.1 evidence using committed local files.

No network, credentials, HF job, training, inference or write operation.
Run from repo root: python3 scripts/audit_v01_integrity.py
This does not independently verify the bytes retained only in the private HF Bucket.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/compiled/v0.3"
EVAL = ROOT / "evaluations/v0.1"
FROZEN = "d1186a731a81219f86eb81b89ac1440dd116e9f4"
SPLITS = {"train": 65, "validation": 15, "test": 20}
EXPECTED_SHA256 = {
    "train.jsonl": "9a24f07befee9e701c587f4b154b0e780c29534abe3a0fa8b0c310511172a60f",
    "validation.jsonl": "083a6f124abc414a0edf268d1a95788f738d55e7ecd229a78c67087991f46c36",
    "test.jsonl": "d8eee6db5882d85dce7ffc01256e7c5b9b46e133bdb2cf8591259112b92e980d",
}
CHECKPOINT_JOB = "6ac8be0e095c578089304f37"
ADAPTER_SHA = "621d7328056758607c9d7797282ae4d5803cdb1727dab6b40a321ee959dd2478"


def fail_if(condition: bool, message: str) -> None:
    if condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def source_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def source_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def dataset_audit() -> dict:
    checksum_file = (DATA / "SHA256SUMS.txt").read_text(encoding="utf-8")
    checks = {}
    for line in checksum_file.splitlines():
        match = re.fullmatch(r"([a-f0-9]{64})  (data/compiled/v0\.3/[^/]+)", line)
        fail_if(match is None, "invalid Dataset SHA256SUMS line")
        digest, relpath = match.groups()
        name = Path(relpath).name
        fail_if(name in checks, f"duplicate Dataset manifest entry {name}")
        file_path = ROOT / relpath
        fail_if(not file_path.is_file(), f"missing Dataset artifact {relpath}")
        fail_if(sha256(file_path) != digest, f"Dataset byte hash mismatch: {relpath}")
        checks[name] = digest
    fail_if(set(checks) != {"train.jsonl", "validation.jsonl", "test.jsonl",
                           "budget_report.json", "token_report.json"},
            "unexpected Dataset v0.3 file set")
    for name, digest in EXPECTED_SHA256.items():
        fail_if(checks[name] != digest, f"accepted Dataset hash differs: {name}")

    story_ids = {}
    sample_ids = {}
    for split, n in SPLITS.items():
        records = source_jsonl(DATA / f"{split}.jsonl")
        fail_if(len(records) != n, f"{split}: sample count mismatch")
        story_ids[split] = set()
        sample_ids[split] = set()
        for r in records:
            sid = r.get("id")
            meta = r.get("metadata")
            msgs = r.get("messages")
            fail_if(not isinstance(sid, str) or sid in sample_ids[split],
                    f"{split}: duplicate/invalid sample ID")
            fail_if(not isinstance(meta, dict) or not meta.get("story_id"),
                    f"{split}: missing story metadata")
            fail_if(not isinstance(msgs, list) or len(msgs) < 2
                    or msgs[-2].get("role") != "user"
                    or msgs[-1].get("role") != "assistant"
                    or not isinstance(msgs[-1].get("content"), str)
                    or not msgs[-1]["content"].strip(),
                    f"{split}: missing final Gold target")
            sample_ids[split].add(sid)
            story_ids[split].add(meta["story_id"])
    for i, a in enumerate(SPLITS):
        for b in list(SPLITS)[i + 1:]:
            fail_if(bool(story_ids[a] & story_ids[b]),
                    f"story-level leakage {a}/{b}")
            fail_if(bool(sample_ids[a] & sample_ids[b]),
                    f"duplicate sample ID across {a}/{b}")

    budget = source_json(DATA / "budget_report.json")
    report = source_json(DATA / "token_report.json")
    fail_if(budget.get("split_sample_counts") != SPLITS
            or budget.get("sample_count") != 100 or budget.get("overflow_sample_count") != 0,
            "Dataset budget counts disagree")
    fail_if(report.get("sample_count") != 100
            or report.get("fit_by_max_length", {}).get("16384", {}).get("count") != 100
            or report.get("stats", {}).get("total_tokens", {}).get("max", 999999) > 16384,
            "token budget report contradicts expected fit")
    config = (ROOT / "configs/qwen38-27b-qlora-v0.1.yaml").read_text(encoding="utf-8")
    for line in ("- data/compiled/v0.3/train.jsonl",
                 "- data/compiled/v0.3/validation.jsonl",
                 "lora_rank: 64", "lora_alpha: 128", "loss_scale: last_round",
                 "max_length: 16384", "gradient_accumulation_steps: 8"):
        fail_if(line not in config, f"training config mismatch: {line}")
    return {"status": "PASS", "files_sha256": checks,
            "split_counts": SPLITS,
            "stories_by_split": {k: len(v) for k, v in story_ids.items()},
            "budget_report_verified_as_metadata_only": True,
            "token_count_retokenization_performed": False,
            "training_config_current_sha256": sha256(
                ROOT / "configs/qwen38-27b-qlora-v0.1.yaml")}


def test_alignment_audit() -> dict:
    src = source_jsonl(DATA / "test.jsonl")
    prompts = source_jsonl(EVAL / "test/prompts.jsonl")
    manifest = source_json(EVAL / "test/manifest.json")
    pairs = source_jsonl(EVAL / "test/blind-pairs.jsonl")
    key = source_json(EVAL / "test/answer-key.json")
    fail_if(manifest.get("schema") != "storyforge-blind-v1"
            or manifest.get("count") != 20
            or not (len(src) == len(prompts) == len(pairs) == len(key) ==
                    len(manifest["samples"]) == 20),
            "held-out file count or schema mismatch")
    for i, (r, prompt, entry, pair, answer) in enumerate(
            zip(src, prompts, manifest["samples"], pairs, key)):
        prefix = [{"role": msg["role"], "content": msg["content"]}
                  for msg in r["messages"][:-1]]
        fail_if(prefix != prompt["messages"], f"held-out prompt mismatch at {i}")
        blob = json.dumps({"messages": prefix}, sort_keys=True,
                          ensure_ascii=False).encode("utf-8")
        digest = hashlib.sha256(blob).hexdigest()
        sid = f"eval-{i:03d}-{digest[:12]}"
        fail_if(entry != {"sample_id": sid, "prompt_sha256": digest,
                          "source_line": i + 1}, f"held-out manifest mismatch at {i}")
        fail_if(pair.get("sample_id") != sid or pair.get("prompt_sha256") != digest
                or answer.get("sample_id") != sid
                or {answer.get("a"), answer.get("b")} != {"base", "adapter"}
                or not all(isinstance(pair.get(s), str) and pair[s].strip()
                           for s in ("response_a", "response_b")),
                f"held-out pair/key mismatch at {i}")

    for round_name, expected_counts in (
        ("round1-unblind.json", {"base": 13, "adapter": 7}),
        ("round2-original-key-verified.json", {"base": 10, "adapter": 10}),
    ):
        report = source_json(EVAL / "results" / round_name)
        fail_if(report["sample_majority"] != expected_counts, f"{round_name}: winners")
        fail_if(len(report["per_sample"]) != 20, f"{round_name}: sample count")
        fail_if({x["sample_id"] for x in report["per_sample"]}
                != {p["sample_id"] for p in pairs},
                f"{round_name}: IDs")
        fail_if(report["raw_votes"] != (
            {"base": 44, "adapter": 28, "tie": 8} if round_name.startswith("round1")
            else {"base": 34, "adapter": 25, "tie": 1}),
            f"{round_name}: raw vote counts")

    blobs = source_json(EVAL / "git-blobs.json")
    fail_if(blobs.get("job_id") != "6ac85c22fee2c90070172dad", "frozen job mismatch")
    seen = set()
    for item in blobs["sources"]:
        relative = item["path"]
        fail_if(relative in seen, f"duplicate frozen blob reference {relative}")
        seen.add(relative)
        data = (EVAL / relative).read_bytes()
        actual = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
        fail_if(actual != item["git_blob_sha1"], f"frozen original blob mismatch: {relative}")

    return {"status": "PASS", "test_alignment": "20/20",
            "historical_git_blob_sha1_verified": len(seen),
            "round1_majority": {"base": 13, "adapter": 7},
            "round2_majority": {"base": 10, "adapter": 10},
            "same_20_original_test_prompts_in_both_rounds": True}


def checkpoint_audit() -> dict:
    chk = source_json(ROOT / "docs/evidence/V01_CHECKPOINT_SIZE_MANIFEST_20261009.json")
    registry = (ROOT / "docs/HF_RUN_REGISTRY.md").read_text(encoding="utf-8")
    checksum_rows = {filename: digest for digest, filename in
                         re.findall(r"^([a-f0-9]{64})  \./([^\s]+)$",
                                    registry, re.MULTILINE)}
    items = chk["files"]
    fail_if(chk.get("file_count") != 10 or len(items) != 10
            or len(checksum_rows) != 10
            or len({r["filename"] for r in items}) != 10,
            "checkpoint file manifest count mismatch")
    for f in items:
        fail_if(checksum_rows.get(f["filename"]) != f["sha256"]
                or not isinstance(f["size_bytes"], int) or f["size_bytes"] <= 0,
                f"checkpoint hash/size mismatch: {f['filename']}")
    fail_if(sum(f["size_bytes"] for f in items) != chk["total_size_bytes"]
            or chk["total_size_bytes"] != 5603977212,
            "checkpoint total size mismatch")
    fail_if(chk.get("sha256_job_id") != CHECKPOINT_JOB
            or chk.get("sha256_recomputed_by_this_script") is not False
            or checksum_rows.get("adapter_model.safetensors") != ADAPTER_SHA,
            "checkpoint job/source/hash provenance mismatch")
    return {"status": "PASS_REPORTED_HASH_METADATA_ONLY",
            "file_count": 10, "total_bytes": chk["total_size_bytes"],
            "sha256_origin_job": CHECKPOINT_JOB,
            "actual_remote_checkpoint_bytes_rehashed_by_ci": False}


def _run_module(path: Path, function: str) -> dict:
    spec = importlib.util.spec_from_file_location("_v01_review_audit", path)
    fail_if(spec is None or spec.loader is None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, function)()


def validation_and_gold_audit() -> dict:
    val_root = EVAL / "validation-1536"
    val = _run_module(val_root / "unblind.py", "run")
    fail_if(val.get("status") != "VALIDATION_1536_ORIGINAL_KEY_AND_SCORER_REPRO_PASS"
            or val.get("votes") != {"base": 28, "adapter": 30, "tie": 2}
            or val.get("raw_hf_inference_bytes_in_git") is not False,
            "Validation source/key review replay failed")
    gold_root = EVAL / "gold-reference/2026-10-10"
    gold = _run_module(gold_root / "reproduce.py", "check")
    fail_if(gold["GOLD_BASE"]["votes"] != {"gold": 38, "model": 22, "tie": 0}
            or gold["GOLD_ADAPTER"]["votes"] != {"gold": 45, "model": 15, "tie": 0}
            or gold["GOLD_BASE"]["majority"] != {"gold": 14, "model": 6}
            or gold["GOLD_ADAPTER"]["majority"] != {"gold": 16, "model": 4},
            "six reviewer Gold reference reproducibility failed")
    verified = source_json(val_root / "hf-source/source_verification.json")
    fail_if(verified.get("source_job_id") != "6ac794fae7a0dae8a2788ee6"
            or verified.get("source_files") != 7,
            "Validation authenticated source reference mismatch")
    gold_manifest = source_json(gold_root / "source_manifest.json")
    fail_if(gold_manifest["status"] != "SIX_REVIEW_FILES_VALIDATED__THIRD_PARTY_INDEPENDENCE_UNVERIFIED",
            "third-party identity limitation missing")
    return {"status": "PASS_ARCHIVED_REVIEWS",
            "validation": {"votes": val["votes"], "strict_majority": val["strict_majority"],
                           "raw_inference_full_bytes_in_git": False},
            "gold": {"gold_vs_base": gold["GOLD_BASE"]["votes"],
                     "gold_vs_adapter": gold["GOLD_ADAPTER"]["votes"],
                     "reviewer_independence": "NOT_VERIFIED"}}


def run() -> dict:
    result = {"schema_version": 1,
              "scope": "StoryForge v0.1 frozen + post-freeze main evidence",
              "historical_frozen_tag_expected": FROZEN,
              "dataset": dataset_audit(),
              "heldout": test_alignment_audit(),
              "checkpoint": checkpoint_audit(),
              "evaluation": validation_and_gold_audit(),
              "external_limits": [
                  "No new HF Job; training logs/base-model revision remain prior verified reports.",
                  "CI does not rehash the private remote 5.60GB checkpoint.",
                  "Remote Train/Validation bytes were not separately re-downloaded from the training Job.",
                  "Original HF 1536 inference JSONL bytes were verified from user ZIP, not in Git.",
                  "Reviewers' real-world identity and independence not independently verified.",
                  "A frozen Git tag must be separately checked against the Git remote."
              ],
              "decision": "ENGINEERING_PASS / QUALITY_PROMOTION_NOT_APPROVED"}
    return {"status": "V01_LOCAL_EVIDENCE_INTEGRITY_PASS__EXTERNAL_LIMITS_RETAINED",
            "checks": result}


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2, sort_keys=True))
