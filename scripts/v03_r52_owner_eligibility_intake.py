"""R52 owner-attested eligibility staging for independently reviewed Gold108.

Private-only data; no training admission, split assignment, or source mutation.
Owner confirmation is an operational declaration, not independent legal proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REG_SCHEMA = "storyforge-r51-private-post-c-risk-register-v1"
PACKET_SCHEMA = "storyforge-r51-private-gold108-context-review-packet-v1"
HOLD = "PENDING_NOT_APPROVED"
CONTEXT = "CONTEXT_ONLY_POSSIBLE__HOLD"
LONG = "CARD_OR_LONG_RANGE_SOURCE_REQUIRED__HOLD"
AGENCY = "TARGET_AGENCY_OR_RULE_CONCERN__HOLD"
AGREED = "A_B_AGREE__HOLD"
NEITHER = "C_MATCHES_NEITHER__HOLD"
CA = "C_MATCHES_A__HOLD"
CB = "C_MATCHES_B__HOLD"


class IntakeHold(ValueError):
    pass


def demand(cond: bool, error: str) -> None:
    if not cond:
        raise IntakeHold(error)


def read_private(path: Path, *, jsonl: bool = True):
    demand(path.is_file() and not path.is_symlink(), "PRIVATE_FILE_MISSING")
    demand(stat.S_IMODE(path.stat().st_mode) & 0o077 == 0,
           "PRIVATE_FILE_PERMISSIONS_UNSAFE")
    demand(stat.S_IMODE(path.parent.stat().st_mode) & 0o077 == 0,
           "PRIVATE_DIRECTORY_PERMISSIONS_UNSAFE")
    with path.open(encoding="utf-8") as stream:
        data = [json.loads(x) for x in stream if x.strip()] if jsonl else json.load(stream)
    demand(isinstance(data, list if jsonl else dict), "PRIVATE_FILE_FORMAT_INVALID")
    return data


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build(reg: list[dict], packets: list[dict]) -> tuple[dict[str, list[dict]], dict]:
    demand(len(reg) == len(packets) == 108, "GOLD108_EXPECTED_108")
    source = {}
    for packet in packets:
        ident = packet.get("candidate_id")
        demand(isinstance(ident, str) and ident not in source,
               "PACKET_ID_MISSING_OR_DUPLICATE")
        body = packet.get("target_content_for_review_only")
        demand(packet.get("schema") == PACKET_SCHEMA and
               packet.get("private_do_not_commit") is True and
               packet.get("training_admission") == HOLD and
               packet.get("split") is None and
               packet.get("historical_card_version_verified") is False and
               isinstance(body, str) and
               digest(body) == packet.get("target_sha256") and
               isinstance(packet.get("story_rank"), int) and
               isinstance(packet.get("target_original_array_index"), int),
               "PACKET_PROVENANCE_CHANGED")
        source[ident] = packet
    queues = {"context_62": [], "three_way_04": [],
              "other_disputes_10": [], "baseline_holds_32": []}
    seen = set()
    route_counter = Counter()
    for row in reg:
        cid = row.get("candidate_id")
        demand(isinstance(cid, str) and cid not in seen and cid in source,
               "RISK_ID_MISSING_DUPLICATE_OR_UNKNOWN")
        seen.add(cid)
        packet = source[cid]
        a, b, c, relation = (row.get("reviewer_A_route"),
                             row.get("reviewer_B_route"),
                             row.get("reviewer_C_route"),
                             row.get("post_c_relation"))
        demand(row.get("schema") == REG_SCHEMA and
               row.get("private_do_not_commit") is True and
               row.get("training_admission") == HOLD and
               row.get("train_admitted") is False and
               row.get("validation_admitted") is False and
               row.get("target_sha256") == packet["target_sha256"],
               "RISK_REGISTER_PROVENANCE_CHANGED")
        if relation == AGREED:
            demand(a == b and c is None and a in {CONTEXT, LONG, AGENCY},
                   "RISK_AGREEMENT_INCONSISTENT")
            key = "context_62" if a == CONTEXT else "baseline_holds_32"
        else:
            demand(a != b and c is not None and
                   relation in {NEITHER, CA, CB} and
                   (relation == NEITHER and c not in {a, b} or
                    relation == CA and c == a or
                    relation == CB and c == b),
                   "RISK_DISAGREEMENT_INCONSISTENT")
            key = "three_way_04" if relation == NEITHER else "other_disputes_10"
        route_counter[(key, a)] += 1
        queues[key].append({
            "schema": "storyforge-r52-private-owner-eligibility-queue-v1",
            "private_do_not_commit": True,
            "candidate_id": cid,
            "target_sha256": packet["target_sha256"],
            "story_rank": packet["story_rank"],
            "source_story_id": packet["source_story_id"],
            "target_original_array_index": packet["target_original_array_index"],
            "r51_review_relation": relation,
            "reviewer_A_route": a,
            "reviewer_B_route": b,
            "reviewer_C_route": c,
            "risk_flags_from_reviewer_routes_only": row.get(
                "risk_flags_from_reviewer_routes_only", []),
            "r52_queue": key,
            "owner_rights_status": "OWNER_ATTESTED_FULL_OWNERSHIP",
            "owner_rights_external_verification": "NOT_REQUESTED",
            "historical_card_at_target_time": "NOT_VERIFIED",
            "rule_and_agency_quality_gate": "PENDING",
            "target_content_quality_gate": "PENDING",
            "world_split": None,
            "owner_final_quality_disposition": "PENDING",
            "training_admission": HOLD,
            "source_packet_reference": "R51_GOLD108_PRIVATE_CONTEXT_REVIEW_v1.jsonl",
        })
    demand(len(seen) == len(source) == 108, "GOLD108_COVERAGE_INCOMPLETE")
    for name, expected in (("context_62", 62), ("three_way_04", 4),
                           ("other_disputes_10", 10),
                           ("baseline_holds_32", 32)):
        demand(len(queues[name]) == expected, "QUEUE_CATEGORY_COUNT_CHANGED")
        queues[name].sort(key=lambda x: (x["story_rank"], x["candidate_id"]))
    demand(route_counter[("baseline_holds_32", LONG)] == 26 and
           route_counter[("baseline_holds_32", AGENCY)] == 6,
           "BASELINE_HOLD_ROUTE_COUNTS_CHANGED")
    summary = {
        "schema": "storyforge-r52-owner-eligibility-intake-aggregate-v1",
        "status": "OWNER_ATTESTATION_RECORDED_QUEUES_PREPARED__NO_ADMISSION",
        "gold108": 108,
        "owner_attestation_scope": "ALL_CONTENT_OWNED_BY_PROJECT_OWNER",
        "owner_attestation_external_proof_required_to_stage": False,
        "context_quality_and_card_gate_pending": 62,
        "three_way_source_quality_followup": 4,
        "other_c_review_disagreements_held": 10,
        "long_range_holds": 26,
        "agency_rule_holds": 6,
        "rights_status": "OWNER_ATTESTED_NOT_INDEPENDENTLY_VERIFIED",
        "historical_card_verified": 0,
        "train_admitted": 0,
        "validation_admitted": 0,
        "world_split_assigned": 0,
        "private_candidate_identifiers_or_story_text_in_stdout": False,
    }
    return queues, summary


def write_new(path: Path, content: str) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(content)


def execute(reg_path: Path, packet_path: Path, out: Path,
            *, attested: bool, repo: Path) -> dict:
    demand(attested, "OWNER_ATTESTATION_EXPLICIT_SWITCH_REQUIRED")
    demand(out.is_dir() and not out.is_symlink() and
           stat.S_IMODE(out.stat().st_mode) & 0o077 == 0,
           "OUTPUT_DIR_NOT_PRIVATE")
    repo = repo.resolve(strict=True)
    out = out.resolve(strict=True)
    demand(repo != out and repo not in out.parents,
           "OUTPUT_MUST_BE_OUTSIDE_GIT_REPO")
    reg = read_private(reg_path)
    packets = read_private(packet_path)
    queues, summary = build(reg, packets)
    stamps = datetime.now(ZoneInfo("Asia/Singapore")).isoformat(timespec="seconds")
    attestation = {
        "schema": "storyforge-r52-owner-rights-attestation-v1",
        "attested_at_asia_singapore": stamps,
        "declaration_source": "PROJECT_OWNER_DIRECT_CHAT_CONFIRMATION_2026-10-20",
        "declaration": "Project owner confirms ownership of all StoryForge content.",
        "owner_declares_full_content_ownership": True,
        "source_training_use_basis": "OWNER_DECLARATION_ACCEPTED_FOR_PROJECT_INTAKE",
        "independent_legal_audit_completed": False,
        "does_not_approve_individual_samples": True,
        "training_admission": HOLD,
    }
    names = {
        "context_62": "R52_PRIVATE_CONTEXT_62_QUALITY_CARD_QUEUE.jsonl",
        "three_way_04": "R52_PRIVATE_THREE_WAY_04_FOLLOWUP_QUEUE.jsonl",
        "other_disputes_10": "R52_PRIVATE_OTHER_DISPUTES_10_HOLD_QUEUE.jsonl",
        "baseline_holds_32": "R52_PRIVATE_LONG_RANGE_AGENCY_32_HOLD_QUEUE.jsonl",
    }
    output = {out / name: "".join(json.dumps(item, ensure_ascii=False, sort_keys=True)
                                  + "\n" for item in queues[category])
              for category, name in names.items()}
    output[out / "R52_PRIVATE_OWNER_RIGHTS_ATTESTATION.json"] = (
        json.dumps(attestation, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    output[out / "R52_SAFE_ELIGIBILITY_INTAKE_AGGREGATE.json"] = (
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    demand(not any(path.exists() or path.is_symlink() for path in output),
           "OUTPUT_ALREADY_EXISTS")
    os.umask(0o077)
    for path, content in output.items():
        write_new(path, content)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--post-c-register", type=Path, required=True)
    parser.add_argument("--private-packets", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--owner-attests-full-content-ownership", action="store_true")
    args = parser.parse_args()
    try:
        summary = execute(
            args.post_c_register.expanduser().absolute(),
            args.private_packets.expanduser().absolute(),
            args.out_dir.expanduser().absolute(),
            attested=args.owner_attests_full_content_ownership,
            repo=args.repo,
        )
    except (IntakeHold, OSError, KeyError, TypeError, ValueError,
            json.JSONDecodeError, UnicodeError) as exc:
        code = str(exc) if isinstance(exc, IntakeHold) else type(exc).__name__
        print("R52_OWNER_INTAKE_HOLD__" + code, file=sys.stderr)
        return 2
    print("R52_OWNER_RIGHTS_ATTESTED_62_QUALITY_CANDIDATES_STAGED__NO_ADMISSION")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
