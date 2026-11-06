"""Auto-link frozen Gold192 Packet and A/B review evidence into Owner rows.

Only immutable source locators and observed snapshot fingerprints are added.
No Owner judgment, reviewer independence, source-version provenance, world
identity, split, protection-set result, Quality-v1 admission, or training
authorization is inferred.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
from pathlib import Path

try:
    from .r59_gold192_canonical_a import (
        A_SHA, B_SHA, B_SCHEMA, B_COUNTS, PACKETS_SHA, validate_reviewer_a_v3,
    )
except ImportError:
    from r59_gold192_canonical_a import (
        A_SHA, B_SHA, B_SCHEMA, B_COUNTS, PACKETS_SHA, validate_reviewer_a_v3,
    )

SCHEMA = "storyforge-r59-owner-evidence-autolink-safe-v1"
HEX = re.compile(r"^[0-9a-f]{64}$")
MAX_BYTES = 160 * 1024 * 1024
STAGE_SCHEMA = "storyforge-quality-v1-source-staging-private-v1"
STAGE_STATUS = "SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING"


class AutoLinkHold(ValueError):
    pass


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_private(path: Path, limit: int = MAX_BYTES) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise AutoLinkHold("INPUT_NOT_REGULAR_FILE")
    info = path.stat()
    if stat.S_IMODE(info.st_mode) != 0o600 or info.st_size <= 0 or info.st_size > limit:
        raise AutoLinkHold("INPUT_PERMISSION_OR_SIZE_INVALID")
    return path.read_bytes()


def parse_json(raw: bytes, code: str):
    try:
        return json.loads(raw)
    except (ValueError, UnicodeError):
        raise AutoLinkHold(code) from None


def parse_jsonl(raw: bytes, code: str):
    try:
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    except (ValueError, UnicodeError):
        raise AutoLinkHold(code) from None
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise AutoLinkHold(code)
    return rows


def canonical_sha(value) -> str:
    try:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError):
        raise AutoLinkHold("CANONICAL_SOURCE_INVALID") from None
    return sha(raw)


def _index_by_target(rows, label, *, require_case_id=False):
    index = {}
    for i, row in enumerate(rows):
        target = row.get("target_sha256")
        if not isinstance(target, str) or HEX.fullmatch(target) is None or target in index:
            raise AutoLinkHold(label + "_TARGET_IDENTITY_INVALID")
        if require_case_id and (not isinstance(row.get("case_id"), str) or not row["case_id"]):
            raise AutoLinkHold(label + "_CASE_ID_MISSING")
        index[target] = (i, row)
    return index


def build(packet_rows, staged_rows, a_doc, b_doc, owner_rows,
          packet_sha, staged_sha, a_sha, b_sha):
    if len(packet_rows) != 13 or a_sha != A_SHA or b_sha != B_SHA or packet_sha != PACKETS_SHA:
        raise AutoLinkHold("FROZEN_SOURCE_PIN_OR_COUNT_MISMATCH")
    try:
        canonical_a_index = validate_reviewer_a_v3(a_doc)
    except ValueError as exc:
        raise AutoLinkHold(str(exc)) from None
    if (not isinstance(b_doc, dict) or b_doc.get("schema") != B_SCHEMA
            or b_doc.get("counts") != B_COUNTS):
        raise AutoLinkHold("CANONICAL_REVIEWER_B_REQUIRED")

    packet_index = {}
    for packet_i, packet in enumerate(packet_rows):
        if not isinstance(packet.get("cases"), list):
            raise AutoLinkHold("PACKET_CASES_INVALID")
        for case_i, case in enumerate(packet["cases"]):
            cid, target = case.get("case_id"), case.get("target_sha256")
            if (not isinstance(cid, str) or not cid
                    or not isinstance(target, str) or HEX.fullmatch(target) is None
                    or (cid, target) in packet_index):
                raise AutoLinkHold("PACKET_IDENTITY_INVALID")
            packet_index[(cid, target)] = (packet_i, case_i, packet, case)

    a_rows = a_doc.get("records") if isinstance(a_doc, dict) else None
    b_rows = b_doc.get("cases") if isinstance(b_doc, dict) else None
    if not isinstance(a_rows, list) or not isinstance(b_rows, list):
        raise AutoLinkHold("REVIEW_STRUCTURE_INVALID")
    a_index = _index_by_target(a_rows, "REVIEWER_A", require_case_id=True)
    if set(a_index) != set(canonical_a_index):
        raise AutoLinkHold("CANONICAL_A_INDEX_MISMATCH")
    b_index = _index_by_target(b_rows, "REVIEWER_B")
    if len(a_index) != 192 or len(b_index) != 192 or set(a_index) != set(b_index):
        raise AutoLinkHold("FROZEN_REVIEW_COVERAGE_INVALID")

    ready = [
        row for row in staged_rows
        if row.get("schema") == STAGE_SCHEMA and row.get("status") == STAGE_STATUS
    ]
    if not ready or len({row.get("case_id") for row in ready}) != len(ready):
        raise AutoLinkHold("STAGED_CANDIDATES_INVALID")

    owner_by_id = {}
    for row in owner_rows:
        cid = row.get("case_id")
        if not isinstance(cid, str) or not cid or cid in owner_by_id:
            raise AutoLinkHold("OWNER_TEMPLATE_IDENTITY_INVALID")
        owner_by_id[cid] = row
    if set(owner_by_id) != {row.get("case_id") for row in ready}:
        raise AutoLinkHold("OWNER_TEMPLATE_COVERAGE_MISMATCH")

    enriched = []
    a_granularity_counts = {}
    for stage in ready:
        cid, target = stage["case_id"], stage["target_sha256"]
        owner = dict(owner_by_id[cid])
        if (owner.get("target_sha256") != target
                or owner.get("story_id") != stage.get("story_id")
                or owner.get("session_id") != stage.get("session_id")):
            raise AutoLinkHold("OWNER_STAGE_IDENTITY_MISMATCH")
        packet_match = packet_index.get((cid, target))
        a_match, b_match = a_index.get(target), b_index.get(target)
        if packet_match is None or a_match is None or b_match is None:
            raise AutoLinkHold("EXACT_SOURCE_ASSOCIATION_MISSING")
        if a_match[1].get("case_id") != cid:
            raise AutoLinkHold("REVIEWER_A_CASE_ID_MISMATCH")

        packet_i, case_i, packet, case = packet_match
        if case.get("target_assistant_text") is None:
            raise AutoLinkHold("PACKET_TARGET_MISSING")
        granularity = a_match[1]["evidence_granularity"]
        a_granularity_counts[granularity] = a_granularity_counts.get(granularity, 0) + 1
        owner.update({
            "reviewer_a_evidence_ref": f"sha256:{a_sha}#records[{a_match[0]}]",
            "reviewer_a_evidence_granularity": granularity,
            "reviewer_a_case_level_scored_review_present": (
                a_match[1]["case_level_scored_review_present"]
            ),
            "reviewer_b_evidence_ref": f"sha256:{b_sha}#cases[{b_match[0]}]",
            "packet_case_evidence_ref": (
                f"sha256:{packet_sha}#rows[{packet_i}].cases[{case_i}]"
            ),
            "packet_case_snapshot_sha256": canonical_sha(case),
            "world_card_snapshot_evidence_ref": (
                f"sha256:{packet_sha}#rows[{packet_i}].world_card"
            ),
            "world_card_snapshot_sha256": packet.get("world_card_sha256"),
            "world_card_snapshot_source_kind": packet.get("world_card_source_kind"),
            "world_card_snapshot_review_status": packet.get("world_card_review_status"),
            "world_card_snapshot_approved_for_system": packet.get("world_card_approved_for_system"),
            "reviewer_evidence_refs_are_locators_not_independence_proof": True,
            "packet_case_snapshot_is_not_historical_source_version": True,
        })
        enriched.append(owner)

    enriched.sort(key=lambda row: row["case_id"])
    safe = {
        "schema": SCHEMA,
        "status": "OWNER_EVIDENCE_LOCATORS_AUTOLINKED__OWNER_REVIEW_STILL_REQUIRED",
        "staged_candidates": len(ready),
        "packet_exact_matches": len(enriched),
        "reviewer_a_exact_matches": len(enriched),
        "reviewer_a_evidence_granularity_counts": dict(sorted(a_granularity_counts.items())),
        "reviewer_b_exact_matches": len(enriched),
        "owner_attestations_created": 0,
        "source_version_verified": False,
        "historical_snapshot_temporality_proven": False,
        "reviewer_independence_proven": False,
        "world_component_isolation_proven": False,
        "protected_set_completeness_proven": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }
    return enriched, safe


def create_only(path: Path, raw: bytes):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def run(packet_path, staged_path, a_path, b_path, owner_path, output_dir):
    packet_raw = read_private(packet_path)
    staged_raw = read_private(staged_path)
    a_raw = read_private(a_path)
    b_raw = read_private(b_path)
    owner_raw = read_private(owner_path)
    if sha(a_raw) != A_SHA or sha(b_raw) != B_SHA or sha(packet_raw) != PACKETS_SHA:
        raise AutoLinkHold("FROZEN_SOURCE_SHA_MISMATCH")
    packets = parse_jsonl(packet_raw, "PACKET_JSONL_INVALID")
    staged = parse_jsonl(staged_raw, "STAGED_JSONL_INVALID")
    a_doc, b_doc = parse_json(a_raw, "REVIEWER_A_JSON_INVALID"), parse_json(b_raw, "REVIEWER_B_JSON_INVALID")
    owners = parse_jsonl(owner_raw, "OWNER_TEMPLATE_JSONL_INVALID")
    enriched, safe = build(
        packets, staged, a_doc, b_doc, owners,
        sha(packet_raw), sha(staged_raw), sha(a_raw), sha(b_raw)
    )
    if output_dir.exists() or output_dir.is_symlink():
        raise AutoLinkHold("OUTPUT_EXISTS")
    if output_dir.resolve().is_relative_to(Path.cwd().resolve()):
        raise AutoLinkHold("OUTPUT_INSIDE_REPO")
    if (not output_dir.parent.is_dir() or output_dir.parent.is_symlink()
            or stat.S_IMODE(output_dir.parent.stat().st_mode) != 0o700):
        raise AutoLinkHold("OUTPUT_PARENT_INVALID")
    output_dir.mkdir(mode=0o700)
    try:
        payload = b"".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode() + b"\n"
            for row in enriched
        )
        create_only(output_dir / "OWNER_CASE_EVIDENCE_AUTOLINKED_PRIVATE.jsonl", payload)
        create_only(
            output_dir / "OWNER_EVIDENCE_AUTOLINK_SAFE.json",
            json.dumps(safe, sort_keys=True, indent=2).encode() + b"\n",
        )
    except BaseException:
        for item in output_dir.iterdir():
            item.unlink()
        output_dir.rmdir()
        raise
    return safe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("packet-jsonl", "staged-jsonl", "reviewer-a", "reviewer-b",
                 "owner-template-jsonl", "output-dir"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        safe = run(args.packet_jsonl, args.staged_jsonl, args.reviewer_a,
                   args.reviewer_b, args.owner_template_jsonl, args.output_dir)
        print(json.dumps(safe, sort_keys=True))
        return 0
    except AutoLinkHold as exc:
        # Exception messages are fixed reason codes; never include paths,
        # identifiers, hashes, or source content in the SAFE receipt.
        reason = str(exc) if re.fullmatch(r"[A-Z0-9_]{1,80}", str(exc)) else "OWNER_EVIDENCE_AUTOLINK_INPUT_HOLD"
    except OSError:
        reason = "OWNER_EVIDENCE_AUTOLINK_IO_HOLD"
    except Exception:  # noqa: BLE001 - no private exception text
        reason = "OWNER_EVIDENCE_AUTOLINK_INTERNAL_HOLD"
    print(json.dumps({
        "schema": SCHEMA, "status": "OWNER_EVIDENCE_AUTOLINK_HOLD",
        "reason_code": reason, "quality_v1_admitted": 0,
        "training_authorized": False, "gpu_started": False,
        "r50_accessed": False, "private_values_emitted": False,
    }, sort_keys=True))
    return 42


if __name__ == "__main__":
    raise SystemExit(main())
