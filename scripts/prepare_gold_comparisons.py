"""Prepare blind Gold-vs-Base and Gold-vs-Adapter v0.1 retrospective reviews.

CPU only. Read the original compiled test and frozen evaluation records,
fail on any prompt alignment error, and never modify historical evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def _read_jsonl(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"empty or invalid JSONL: {path}")
    return rows


def _digest(messages: list[dict]) -> str:
    normalized = json.dumps({"messages": messages}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_gold_comparisons(
    compiled_test: Path,
    prompts_path: Path,
    manifest_path: Path,
    blind_pairs_path: Path,
    answer_key_path: Path,
    out_dir: Path,
    *,
    seed: int = 42,
    expected_count: int = 20,
) -> int:
    """Create two blind 20-pair datasets and separate answer keys.

    Existing output directory is refused, including empty directories.
    Comparison outputs are deliberately distinct from the frozen v0.1 source.
    """
    if out_dir.exists():
        raise FileExistsError(f"refusing to overwrite directory: {out_dir}")

    compiled = _read_jsonl(compiled_test)
    prompts = _read_jsonl(prompts_path)
    blind_pairs = _read_jsonl(blind_pairs_path)
    key = json.loads(answer_key_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("samples")
    if manifest.get("schema") != "storyforge-blind-v1" or not isinstance(entries, list):
        raise ValueError("unexpected manifest schema")
    if not isinstance(key, list):
        raise TypeError("answer key must be a list")
    if not (
        len(compiled) == len(prompts) == len(entries) == len(blind_pairs) == len(key)
        == manifest.get("count") == expected_count
    ):
        raise ValueError("test source / prompt / manifest / pair / key count mismatch")

    def indexed(rows: list[dict], description: str) -> dict[str, dict]:
        result = {}
        for row in rows:
            sid = row.get("sample_id")
            if not isinstance(sid, str) or not sid or sid in result:
                raise ValueError(f"missing or duplicate {description} sample_id")
            result[sid] = row
        return result

    pairs_by_id = indexed(blind_pairs, "blind pair")
    key_by_id = indexed(key, "answer key")
    expected_ids = {entry.get("sample_id") for entry in entries}
    if len(expected_ids) != expected_count or set(pairs_by_id) != expected_ids or set(key_by_id) != expected_ids:
        raise ValueError("sample IDs do not match across archives")

    outputs: dict[str, list[dict]] = {"base": [], "adapter": []}
    mappings: dict[str, list[dict]] = {"base": [], "adapter": []}
    for index, (raw, archived, entry) in enumerate(zip(compiled, prompts, entries), start=1):
        messages = raw.get("messages")
        if not isinstance(messages, list) or len(messages) < 2:
            raise ValueError(f"source row {index}: invalid messages")
        if messages[-1].get("role") != "assistant" or messages[-2].get("role") != "user":
            raise ValueError(f"source row {index}: invalid Gold target suffix")
        gold = messages[-1].get("content")
        if not isinstance(gold, str) or not gold.strip():
            raise ValueError(f"source row {index}: missing Gold content")
        context = [{"role": m["role"], "content": m["content"]} for m in messages[:-1]]
        if any(not isinstance(m["content"], str) for m in context):
            raise ValueError(f"source row {index}: non-text context")
        if archived.get("messages") != context:
            raise ValueError(f"source row {index}: exact prompt mismatch")
        digest = _digest(context)
        sid = f"eval-{index - 1:03d}-{digest[:12]}"
        if (entry.get("sample_id") != sid or entry.get("prompt_sha256") != digest
                or entry.get("source_line") != index):
            raise ValueError(f"source row {index}: manifest hash, ID or source_line mismatch")
        pair = pairs_by_id[sid]
        original_key = key_by_id[sid]
        if pair.get("prompt_sha256") != digest:
            raise ValueError(f"source row {index}: blind-pair prompt hash mismatch")
        if {original_key.get("a"), original_key.get("b")} != {"base", "adapter"}:
            raise ValueError(f"source row {index}: invalid original model mapping")
        restored = {
            original_key["a"]: pair.get("response_a"),
            original_key["b"]: pair.get("response_b"),
        }
        if any(not isinstance(v, str) or not v.strip() for v in restored.values()):
            raise ValueError(f"source row {index}: missing original model output")

        for model in ("base", "adapter"):
            # A per-sample deterministic permutation prevents global position bias.
            swap = int(hashlib.sha256(f"{seed}:{sid}:{model}".encode()).hexdigest(), 16) % 2
            a_role, b_role = (model, "gold") if swap else ("gold", model)
            content = {"gold": gold, model: restored[model]}
            outputs[model].append({
                "sample_id": sid,
                "prompt_sha256": digest,
                "response_a": content[a_role],
                "response_b": content[b_role],
            })
            mappings[model].append({"sample_id": sid, "a": a_role, "b": b_role})

    audit = {
        "schema": "storyforge-v0.1-gold-retrospective-v1",
        "status": "SOURCE_ALIGNMENT_PASS__REVIEW_NOT_YET_PERFORMED",
        "sample_count": expected_count,
        "blind_pairs_per_comparison": expected_count,
        "comparisons": ["gold_vs_base", "gold_vs_adapter"],
        "randomization_seed": seed,
        "no_new_inference": True,
        "gold_is_reference_not_absolute_truth": True,
        "input_sha256": {
            name: _file_digest(path)
            for name, path in [
                ("compiled_test", compiled_test),
                ("archived_prompts", prompts_path),
                ("archived_manifest", manifest_path),
                ("archived_blind_pairs", blind_pairs_path),
                ("archived_answer_key", answer_key_path),
            ]
        },
    }
    out_dir.mkdir(parents=True, exist_ok=False)
    for model in ("base", "adapter"):
        comparison = f"gold-vs-{model}"
        pairs_text = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in outputs[model])
        (out_dir / f"{comparison}-blind-pairs.jsonl").write_text(pairs_text, encoding="utf-8")
        (out_dir / f"{comparison}-answer-key.json").write_text(
            json.dumps(mappings[model], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    (out_dir / "audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return expected_count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiled-test", type=Path, required=True)
    parser.add_argument("--prompts", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--blind-pairs", type=Path, required=True)
    parser.add_argument("--answer-key", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    count = prepare_gold_comparisons(
        args.compiled_test, args.prompts, args.manifest, args.blind_pairs,
        args.answer_key, args.out_dir, seed=args.seed
    )
    print(f"GOLD_COMPARISON_PREP_PASS: {count} source samples, {count * 2} blind pairs")


if __name__ == "__main__":
    main()
