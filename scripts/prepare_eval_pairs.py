"""CPU-only utilities for validating matched base/adapter generations."""
from __future__ import annotations

import argparse
import json
import secrets
from pathlib import Path


def read_results(path: Path, expected: int, prompts: list[dict]) -> list[str]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != expected:
        raise ValueError(f"{path}: expected {expected} responses, received {len(rows)}")
    # Fail closed unless output carries the original prompt context for alignment.
    for index, row in enumerate(rows):
        messages = row.get("messages")
        if not isinstance(messages, list) or messages[:len(prompts[index]["messages"])] != prompts[index]["messages"]:
            raise ValueError(f"{path}:{index}: missing or mismatched prompt context")
    answers = [row.get("response") for row in rows]
    if any(not isinstance(answer, str) or not answer.strip() for answer in answers):
        raise ValueError(f"{path}: empty or invalid response")
    return answers


def prepare_pairs(manifest_path: Path, base_path: Path, adapter_path: Path, output: Path, key_path: Path, prompt_path: Path) -> int:
    if output.exists() or key_path.exists():
        raise FileExistsError("will not overwrite blind evaluation or secret key")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    samples = manifest["samples"]
    count = manifest["count"]
    if len(samples) != count or len({s["sample_id"] for s in samples}) != count:
        raise ValueError("invalid manifest count or duplicate sample identifiers")
    prompts = [json.loads(line) for line in prompt_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(prompts) != count:
        raise ValueError("prompt count mismatch")
    base = read_results(base_path, count, prompts)
    adapter = read_results(adapter_path, count, prompts)
    pairs = []
    mapping = []
    for i, sample in enumerate(samples):
        # Randomized concealed order, independently assigned per sample.
        order = ("base", "adapter") if secrets.randbelow(2) == 0 else ("adapter", "base")
        mapping.append({"sample_id": sample["sample_id"], "a": order[0], "b": order[1]})
        candidates = {"base": base[i], "adapter": adapter[i]}
        pairs.append({"sample_id": sample["sample_id"],
                      "prompt_sha256": sample["prompt_sha256"],
                      "response_a": candidates[order[0]],
                      "response_b": candidates[order[1]],
                      "preference": None,
                      "narrative_continuity_a": None,
                      "narrative_continuity_b": None,
                      "character_consistency_a": None,
                      "character_consistency_b": None,
                      "instruction_adherence_a": None,
                      "instruction_adherence_b": None,
                      "writing_quality_a": None,
                      "writing_quality_b": None,
                      "interactive_progression_a": None,
                      "interactive_progression_b": None})
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(pair, ensure_ascii=False) + "\n" for pair in pairs),
                      encoding="utf-8")
    key_path.parent.mkdir(parents=True, exist_ok=True)
    with key_path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n")
    key_path.chmod(0o600)
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--base-results", type=Path, required=True)
    parser.add_argument("--adapter-results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--secret-key", type=Path, required=True)
    parser.add_argument("--prompts", type=Path, required=True)
    args = parser.parse_args()
    print(f"PAIRED_EVAL_PASS: {prepare_pairs(args.manifest, args.base_results, args.adapter_results, args.output, args.secret_key, args.prompts)}")


if __name__ == "__main__":
    main()
