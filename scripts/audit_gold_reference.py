"""Audit historical candidate Gold texts against the canonical compiled v0.3 Test.

This is a CPU-only provenance gate. It does not score model outputs or modify
frozen v0.1 records. It never promotes a candidate merely on prompt identity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def _jsonl(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    if any(not isinstance(row, dict) for row in rows):
        raise TypeError(f"{path}: expected JSON objects")
    return rows


def _sha256_bytes(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def audit(
    compiled_test: Path,
    prompts_file: Path,
    manifest_file: Path,
    candidate_file: Path,
    output: Path,
) -> dict:
    """Write comparison report; do not claim PASS unless all 20 Gold texts equal.

    The candidate input is TRIPLETS_INTERNAL_UNBLINDED.json from the earlier
    local source audit. The compiled Test is the authoritative reference.
    """
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing audit: {output}")

    canonical = _jsonl(compiled_test)
    prompts = _jsonl(prompts_file)
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    candidate = json.loads(candidate_file.read_text(encoding="utf-8"))
    if manifest.get("schema") != "storyforge-blind-v1":
        raise ValueError("unexpected frozen manifest schema")
    entries = manifest.get("samples")
    if not isinstance(entries, list) or not isinstance(candidate, list):
        raise TypeError("expected manifest samples and candidate triplets to be lists")
    if not (len(canonical) == len(prompts) == len(entries) == len(candidate) == 20
            and manifest.get("count") == 20):
        raise ValueError("require exactly 20 matching source, prompt, manifest and candidate rows")

    candidate_by_id: dict[str, dict] = {}
    for row in candidate:
        if not isinstance(row, dict):
            raise TypeError("candidate row must be a JSON object")
        sid = row.get("id")
        if not isinstance(sid, str) or not sid or sid in candidate_by_id:
            raise ValueError("missing or duplicate candidate sample ID")
        candidate_by_id[sid] = row
    if {entry.get("sample_id") for entry in entries} != set(candidate_by_id):
        raise ValueError("candidate IDs do not match frozen manifest")

    results = []
    for index, (source, prompt, entry) in enumerate(zip(canonical, prompts, entries)):
        messages = source.get("messages")
        if not isinstance(messages, list) or len(messages) < 2:
            raise ValueError(f"sample {index:03d}: invalid canonical messages")
        if messages[-1].get("role") != "assistant" or messages[-2].get("role") != "user":
            raise ValueError(f"sample {index:03d}: invalid canonical target suffix")
        gold = messages[-1].get("content")
        if not isinstance(gold, str) or not gold.strip():
            raise ValueError(f"sample {index:03d}: empty canonical Gold")
        context = [{"role": m["role"], "content": m["content"]} for m in messages[:-1]]
        if any(not isinstance(m["content"], str) for m in context):
            raise TypeError(f"sample {index:03d}: non-text prompt")
        if prompt.get("messages") != context:
            raise ValueError(f"sample {index:03d}: canonical prompt differs from frozen prompt")
        normalized = json.dumps({"messages": context}, sort_keys=True, ensure_ascii=False)
        prompt_hash = _sha256_text(normalized)
        sid = f"eval-{index:03d}-{prompt_hash[:12]}"
        if (entry.get("sample_id") != sid or entry.get("prompt_sha256") != prompt_hash
                or entry.get("source_line") != index + 1):
            raise ValueError(f"sample {index:03d}: manifest/hash/line mismatch")

        row = candidate_by_id[sid]
        if row.get("index") != index:
            raise ValueError(f"sample {index:03d}: wrong candidate index")
        candidate_gold = row.get("gold")
        if not isinstance(candidate_gold, str) or not candidate_gold.strip():
            raise ValueError(f"sample {index:03d}: invalid candidate Gold")
        matches = candidate_gold == gold
        results.append({
            "sample_id": sid,
            "source_line": index + 1,
            "candidate_gold_sha256": _sha256_text(candidate_gold),
            "canonical_gold_sha256": _sha256_text(gold),
            "candidate_gold_chars": len(candidate_gold),
            "canonical_gold_chars": len(gold),
            "exact_match": matches,
        })

    matched = sum(row["exact_match"] for row in results)
    report = {
        "schema_version": 1,
        "status": ("CANONICAL_GOLD_MATCH_PASS" if matched == 20
                   else "CANONICAL_GOLD_MISMATCH__REBUILD_REVIEW_SHEETS"),
        "source_count": 20,
        "exact_match_count": matched,
        "mismatch_count": 20 - matched,
        "candidate_is_canonical": matched == 20,
        "no_inference_or_training": True,
        "source_sha256": {
            "compiled_test": _sha256_bytes(compiled_test),
            "frozen_prompts": _sha256_bytes(prompts_file),
            "frozen_manifest": _sha256_bytes(manifest_file),
            "candidate_triplets": _sha256_bytes(candidate_file),
        },
        "results": results,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiled-test", type=Path, required=True)
    parser.add_argument("--prompts", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.compiled_test, args.prompts, args.manifest,
                   args.candidate, args.output)
    print(f"{report['status']}: {report['exact_match_count']}/20 matched")
    if report["mismatch_count"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
