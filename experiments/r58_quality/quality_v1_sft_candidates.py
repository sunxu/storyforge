"""Private Gold Quality-v1 SFT candidate packer; not a training admission gate.

Uses the existing quality_v1 rubric and SHA contracts. Outputs are private,
create-only, and tagged CANDIDATES_NOT_ADMITTED. Never accesses R50, network,
Supabase, Hugging Face, or GPU. Run HF CPU preflight separately.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
from collections import Counter
from pathlib import Path

from quality_v1 import canonical, decide, read_private, sha, summarize

OUT_SCHEMA = "storyforge-quality-v1-sft-candidates-safe-v1"
SAFE_REASON = re.compile(r"^[A-Z][A-Z0-9_]{1,80}$")
MAX_OUTPUT_ROWS = 195


class CandidateHold(ValueError):
    pass


def _check_world_and_duplicate_boundaries(rows):
    """Reuse summarize() whole-set checks; no row-specific shortcut."""
    inspected = summarize(rows)
    if inspected["world_train_validation_collision_found"]:
        raise CandidateHold("TRAIN_VALIDATION_WORLD_COLLISION")
    # A duplicate case, prompt, or target cannot be admitted by filtering
    # out its counterpart: do not silently resolve frozen identity conflicts.
    for key in ("case_id", "input_messages_sha256", "assistant_target_sha256"):
        values = [row.get(key) for row in rows if isinstance(row, dict)]
        if len(values) != len(set(values)):
            raise CandidateHold("DUPLICATE_SOURCE_OR_TARGET")
    return inspected


def compile_candidates(rows):
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_OUTPUT_ROWS:
        raise CandidateHold("CANDIDATE_SET_INVALID")
    summary = _check_world_and_duplicate_boundaries(rows)
    decisions = [decide(row) for row in rows]
    candidates = []
    counts = Counter()
    for row, (verdict, reason) in zip(rows, decisions, strict=True):
        counts[verdict] += 1
        if verdict != "PASS":
            continue
        # Reviewer declarations are not verified independent evidence. This
        # output must never be represented as an admitted/frozen train split.
        msgs = [dict(msg) for msg in row["messages"]]
        for msg in msgs:
            if msg["role"] == "assistant":
                msg["loss"] = False
        msgs.append({"role": "assistant", "content": row["target_text"], "loss": True})
        if (msgs[-2]["role"] != "user"
                or sum(msg.get("loss") is True for msg in msgs) != 1
                or msgs[-1]["loss"] is not True
                or sha(msgs[-1]["content"].encode("utf-8"))
                != row["assistant_target_sha256"]):
            raise CandidateHold("LAST_ASSISTANT_MASK_INVALID")
        candidates.append({
            "case_id": row["case_id"],
            "split": row["split"],
            "world_component_id": row["world_component_id"],
            "source_target_sha256": row["assistant_target_sha256"],
            "messages": msgs,
            "status": "CANDIDATE_NOT_ADMITTED",
        })
    candidates.sort(key=lambda item: item["case_id"])
    splits = Counter(c["split"] for c in candidates)
    worlds = {
        split: len({c["world_component_id"] for c in candidates if c["split"] == split})
        for split in ("train", "validation")
    }
    return candidates, {
        "schema": OUT_SCHEMA,
        "status": "PRIVATE_SFT_CANDIDATES_BUILT__NOT_QUALITY_ADMITTED",
        "input_cases": len(rows),
        "candidate_cases": len(candidates),
        "candidate_train": splits["train"],
        "candidate_validation": splits["validation"],
        "train_world_components": worlds["train"],
        "validation_world_components": worlds["validation"],
        "held_or_rejected": counts["HOLD"] + counts["REJECT"],
        "quality_v1_structural_pass": summary["decision_counts"]["PASS"],
        "world_train_validation_collision_found": False,
        "reviewer_independence_independently_proven": False,
        "source_context_independently_authenticated": False,
        "tokenizer_collator_checked": False,
        "historical_provider_replay_required": False,
        "dataset_frozen": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }


def _write_exclusive(path: Path, data: bytes):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                 | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return hashlib.sha256(data).hexdigest()


def run(input_path: Path, output_dir: Path):
    rows = read_private(input_path)
    candidates, safe = compile_candidates(rows)
    if output_dir.is_symlink() or output_dir.exists():
        raise CandidateHold("OUTPUT_ALREADY_EXISTS")
    if output_dir.resolve().is_relative_to(Path.cwd().resolve()):
        raise CandidateHold("PRIVATE_OUTPUT_INSIDE_REPO")
    if not output_dir.parent.is_dir() or output_dir.parent.is_symlink():
        raise CandidateHold("OUTPUT_PARENT_INVALID")
    if stat.S_IMODE(output_dir.parent.stat().st_mode) != 0o700:
        raise CandidateHold("OUTPUT_PARENT_PERMISSIONS_INVALID")
    output_dir.mkdir(mode=0o700)
    try:
        data = b"".join(canonical(row) + b"\n" for row in candidates)
        digest = _write_exclusive(output_dir / "SFT_CANDIDATES_PRIVATE.jsonl", data)
        safe.update({
            "private_candidate_file_sha256": digest,
            "private_candidate_file_rows": len(candidates),
        })
        _write_exclusive(
            output_dir / "SFT_CANDIDATES_SAFE.json",
            json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n",
        )
    except BaseException:
        # No partial output or ambiguous ready markers.
        for path in output_dir.iterdir():
            path.unlink()
        output_dir.rmdir()
        raise
    return safe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-reviewed-jsonl", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args.private_reviewed_jsonl, args.output_dir)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - no traceback, private paths, values, SQL or hashes
        print(json.dumps({
            "schema": OUT_SCHEMA,
            "status": "SFT_CANDIDATE_PACK_HOLD",
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "r50_accessed": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
