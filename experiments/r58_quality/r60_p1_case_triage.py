#!/usr/bin/env python3
"""R60 P1 frozen Gold192 identity triage; Owner-local, no network/DB/GPU/R50.

Only ranks *review candidates*. No evidence-class promotion, Owner attestation,
Binder binding, Quality-v1 admission, or training permission is conferred.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path

LOCATOR_PIN = "eb2b186b03ffc31585c224ac75cbfd7dd20c8d762887a6463c85bc5090ae9739"
INITIAL_SLOTS_PIN = "69e83d6c61a6be5eb1516d3fd2987fc086259597fd8f900cc02c445debb9a5e9"
EXPECTED_HEAD = "9812d5dd3c09512c537dacc4427fa4b5d3cb64f5"
MAX_BYTES = 160_000_000


class Hold(ValueError):
    pass


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_private(path: Path) -> bytes:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise Hold("PRIVATE_INPUT_PATH_INVALID")
    if path.parent.is_symlink() or stat.S_IMODE(path.parent.stat().st_mode) != 0o700:
        raise Hold("PRIVATE_INPUT_PARENT_MODE_INVALID")
    st = path.stat()
    if (stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1
            or not 0 < st.st_size <= MAX_BYTES):
        raise Hold("PRIVATE_INPUT_MODE_OR_SIZE_INVALID")
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) != st.st_size:
        raise Hold("PRIVATE_INPUT_CHANGED_DURING_READ")
    return raw


def jsonl(raw: bytes) -> list[dict]:
    values = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if any(not isinstance(row, dict) for row in values):
        raise Hold("JSONL_ROW_INVALID")
    return values


def save_new(path: Path, value: object, *, lines: bool = False) -> None:
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                 | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        if lines:
            for item in value:
                stream.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
        else:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")


def triage(raws: dict[str, bytes], source, canon) -> tuple[list[dict], dict]:
    pins = {
        "reviewer_a": canon.A_SHA, "reviewer_b": canon.B_SHA,
        "exclusions": canon.EX_SHA, "source_packets": canon.PACKETS_SHA,
        "source_locators": LOCATOR_PIN, "evidence_slots": INITIAL_SLOTS_PIN,
    }
    for key, expected in pins.items():
        if digest(raws[key]) != expected:
            raise Hold("FROZEN_PIN_MISMATCH")

    source_safe = json.loads(raws["source_safe"])
    artifact = source_safe.get("artifacts", {}).get("R60_SOURCE_LOCATORS_192.jsonl", {})
    if (source_safe.get("schema") != "r60_gold192_supabase_extract_v3_safe_v1"
            or source_safe.get("status") != "SOURCE_EXTRACTED__NOT_QUALITY_ADMITTED"
            or source_safe.get("gold192") != 192
            or artifact.get("records") != 192
            or artifact.get("sha256") != digest(raws["source_locators"])
            or source_safe.get("quality_v1_admitted") != 0
            or source_safe.get("training_authorized") is not False
            or source_safe.get("gpu_started") is not False
            or source_safe.get("database_modified") is not False
            or source_safe.get("private_values_emitted") is not False):
        raise Hold("SOURCE_SAFE_PIN_INVALID")

    packets = source.index_packets(jsonl(raws["source_packets"]))
    selected = source.select_candidates(
        json.loads(raws["reviewer_a"]), json.loads(raws["reviewer_b"]),
        jsonl(raws["exclusions"]), packets,
    )
    locators = jsonl(raws["source_locators"])
    slots = jsonl(raws["evidence_slots"])
    if len(locators) != 192 or len(slots) != 192:
        raise Hold("CASE_COVERAGE_INVALID")
    li = {row.get("case_id"): row for row in locators}
    si = {row.get("case_id"): row for row in slots}
    if len(li) != 192 or len(si) != 192 or set(li) != set(packets) or set(si) != set(packets):
        raise Hold("CASE_SET_MISMATCH")
    if any(li[k].get("target_sha256") != packets[k]["target_sha256"] for k in packets):
        raise Hold("LOCATOR_TARGET_MISMATCH")
    if any(si[k].get("input_evidence_class") != "UNKNOWN_NOT_REVIEWED" for k in packets):
        raise Hold("INITIAL_EVIDENCE_SLOTS_EXPECTED")

    ordered = source.choose_pilot(selected, 0)
    ranks = {row["case_id"]: i + 1 for i, row in enumerate(ordered)}
    selected_ids = set(ranks)
    rows = []
    for case_id in sorted(packets):
        exact = li[case_id].get("source_status") == "EXACT_MATCH"
        chosen = case_id in selected_ids
        rows.append({
            "case_id": case_id,
            "target_sha256": packets[case_id]["target_sha256"],
            "source_status": li[case_id].get("source_status"),
            "explicit_ab_selected": chosen,
            "priority_rank": ranks.get(case_id),
            "input_evidence_class": "UNKNOWN_NOT_REVIEWED",
            "owner_complete": False,
            "binder_bound": False,
            "quality_v1_admitted": False,
            "reason_codes": (
                ([] if chosen else ["NOT_EXPLICIT_CASE_SCORED_A_AND_B_PASS"])
                + ([] if exact else ["SOURCE_NOT_EXACT"])
                + ["MODEL_INPUT_EVIDENCE_UNREVIEWED"]
            ),
        })
    safe = {
        "schema": "storyforge_r60_p1_case_triage_safe_v1",
        "status": "P1_IDENTITIES_TRIAGED__INPUT_EVIDENCE_NOT_REVIEWED",
        "frozen_gold192_total": 192,
        "source_identity_exact": sum(r["source_status"] == "EXACT_MATCH" for r in rows),
        "reviewer_a_case_scored_v3": 31,
        "explicit_ab_candidate_count": len(selected_ids),
        "excluded_frozen_count": 11,
        "old_strict_ready_crosscheck": "NOT_CHECKED",
        "input_evidence_class_counts": {
            "A": None, "B": None, "C": None, "D": None,
            "UNKNOWN_NOT_REVIEWED": 192,
        },
        "owner_complete": 0, "binder_bound": 0, "quality_v1_admitted": 0,
        "dataset_frozen": False, "cpu_tokenizer_collator_pass": False,
        "training_authorized": False, "gpu_started": False,
        "r50_accessed": False, "database_modified": False,
        "private_values_emitted": False,
    }
    return rows, safe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("reviewer-a", "reviewer-b", "exclusions", "source-packets",
                 "source-locators", "source-safe", "evidence-slots", "output-dir"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    try:
        from experiments.r58_quality import r60_gold192_supabase_extract_v3 as source
        from experiments.r58_quality import r60_gold192_canonical_a_v3 as canon

        inputs = ("reviewer_a", "reviewer_b", "exclusions", "source_packets",
                  "source_locators", "source_safe", "evidence_slots")
        raws = {key: read_private(getattr(args, key)) for key in inputs}
        output = args.output_dir
        if (not output.is_absolute() or output.exists() or output.is_symlink()
                or output.resolve().is_relative_to(Path(__file__).resolve().parents[2])
                or not output.parent.is_dir() or output.parent.is_symlink()
                or stat.S_IMODE(output.parent.stat().st_mode) != 0o700):
            raise Hold("PRIVATE_OUTPUT_DIR_INVALID")
        rows, safe = triage(raws, source, canon)
        output.mkdir(mode=0o700)
        save_new(output / "R60_P1_CASE_MATRIX_PRIVATE.jsonl", rows, lines=True)
        save_new(output / "R60_P1_SAFE.json", safe)
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:
        code = str(exc) if isinstance(exc, Hold) and re.fullmatch(r"[A-Z0-9_]{1,80}", str(exc)) else "P1_VALIDATION_FAILED"
        print(json.dumps({
            "status": "P1_HOLD", "reason_code": code,
            "quality_v1_admitted": 0, "gpu_started": False,
            "database_modified": False, "r50_accessed": False,
            "private_values_emitted": False,
        }), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
