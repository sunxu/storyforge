"""Owner-local R57 G2: evidence-first alias review of two unseen Gold UUID worlds.

Do not guess alias links from UUID, names or automatic co-occurrence. Generate
54 candidate-to-historical plus one candidate-to-candidate PRIVATE questions.
All decisions default UNREVIEWED. The optional audit verifies coverage and
nonempty Owner evidence references, but NEVER certifies semantic independence.
Eight frozen source byte pins are revalidated on every invocation.
"""

import argparse
import itertools
import json
import os
import re
import sys
from pathlib import Path

import r57_g2_owner_world_review_roster as roster
import r57_source_index_export as frozen
import r57_trainer_exact_replay as exact

SCHEMA = "storyforge-r57-g2-owner-private-55-alias-pair-review-v1"
SAFE_SCHEMA = "storyforge-r57-g2-alias-pair-review-count-only-v1"
PAIR_FILE = re.compile(r"^R57_G2_ALIAS_EDGE_REVIEW_[0-9]{8}_[0-9]{6}_PRIVATE\.json$")
DECISIONS = {
    "UNREVIEWED",
    "LINKED_WITH_EVIDENCE",
    "DISTINCT_WITH_EVIDENCE",
    "HOLD_INSUFFICIENT_EVIDENCE",
}
COMPLETED = DECISIONS - {"UNREVIEWED"}


class PairReviewHold(ValueError):
    """Invalid private input, evidence, or source pin: cannot advance review."""


def _source_payloads(repo_root, private_root):
    repo = Path(repo_root).resolve(strict=True)
    private = Path(private_root).resolve(strict=True)
    if repo == private or private in repo.parents or repo in private.parents:
        raise PairReviewHold("Owner-private review root must be separate from Git checkout")
    payloads = {}
    for name in exact.SOURCE_IDS:
        group, relative, _ = frozen.SOURCE_PATHS[name]
        root = repo if group == "REPO" else private
        data = frozen._read(root, relative, frozen.MAX_SOURCE_BYTES)
        exact.verify_source_pin(name, data)
        payloads[name] = data
    return payloads, private


def expected_questions(payloads):
    """Compute private list, read-only; returns 55 unanswered exact UUID edges."""
    world_roster, safe = roster.build_roster(payloads)
    worlds = world_roster["worlds"]
    historic = sorted(x["source_story_uuid_PRIVATE"] for x in worlds
                      if x["same_exact_uuid_seen_in_previous_sft"])
    candidate = sorted(x["source_story_uuid_PRIVATE"] for x in worlds
                       if not x["same_exact_uuid_seen_in_previous_sft"]
                       and x["gold_final_targets_without_previous_exact_match"] > 0)
    if (len(historic), len(candidate), safe["world_uuid_count"]) != (27, 2, 29):
        raise PairReviewHold("frozen 27+2 world inventory changed")
    pairs = []
    for c in candidate:
        for h in historic:
            pairs.append({
                "candidate_world_uuid_PRIVATE": c,
                "compare_world_uuid_PRIVATE": h,
                "comparison_kind": "GOLD_VS_HISTORICAL_SFT",
                "owner_decision": "UNREVIEWED",
                "evidence_reference_PRIVATE": "",
                "owner_notes_PRIVATE": "",
            })
    for a, b in itertools.combinations(candidate, 2):
        pairs.append({
            "candidate_world_uuid_PRIVATE": a,
            "compare_world_uuid_PRIVATE": b,
            "comparison_kind": "GOLD_VS_GOLD",
            "owner_decision": "UNREVIEWED",
            "evidence_reference_PRIVATE": "",
            "owner_notes_PRIVATE": "",
        })
    if len(pairs) != 55 or len({(x["candidate_world_uuid_PRIVATE"],
                                x["compare_world_uuid_PRIVATE"]) for x in pairs}) != 55:
        raise PairReviewHold("frozen 55-pair inventory not complete")
    return {
        "schema": SCHEMA,
        "scope": "OWNER_MANUAL_ALIAS_EVIDENCE_REVIEW__NOT_WORLD_CLEARANCE",
        "frozen_eight_source_pins_required": True,
        "all_world_independence_certified": False,
        "dataset_v04_admitted": 0,
        "training_authorized": False,
        "questions_PRIVATE": pairs,
    }


def review_counts(questionnaire, original):
    """Validate exact private pair identities, statuses and evidence without leaks."""
    if not isinstance(questionnaire, dict) or set(questionnaire) != set(original):
        raise PairReviewHold("private review file schema keys differ")
    for name in ("schema", "scope", "frozen_eight_source_pins_required",
                 "all_world_independence_certified", "dataset_v04_admitted",
                 "training_authorized"):
        if questionnaire[name] != original[name]:
            raise PairReviewHold("private review boundary metadata changed")
    items = questionnaire["questions_PRIVATE"]
    baseline = original["questions_PRIVATE"]
    if not isinstance(items, list) or len(items) != len(baseline):
        raise PairReviewHold("private review pair inventory is incomplete")
    lookup = {}
    fields = set(baseline[0])
    for row in items:
        if not isinstance(row, dict) or set(row) != fields:
            raise PairReviewHold("unknown private pair fields")
        key = (row["candidate_world_uuid_PRIVATE"], row["compare_world_uuid_PRIVATE"])
        if key in lookup:
            raise PairReviewHold("duplicate world review pair")
        lookup[key] = row
    status_counts = {name: 0 for name in sorted(DECISIONS)}
    for original_row in baseline:
        key = (original_row["candidate_world_uuid_PRIVATE"],
               original_row["compare_world_uuid_PRIVATE"])
        row = lookup.get(key)
        if row is None or row["comparison_kind"] != original_row["comparison_kind"]:
            raise PairReviewHold("private review pair key or classification drifted")
        decision = row["owner_decision"]
        if not isinstance(decision, str) or decision not in DECISIONS:
            raise PairReviewHold("unknown review decision")
        citation = row["evidence_reference_PRIVATE"]
        notes = row["owner_notes_PRIVATE"]
        if not isinstance(citation, str) or not isinstance(notes, str):
            raise PairReviewHold("review evidence/notes must be strings")
        if len(citation) > 300 or len(notes) > 2000 or "r50" in citation.lower():
            raise PairReviewHold("unsafe or oversized private evidence reference")
        if decision in COMPLETED and not citation.strip():
            raise PairReviewHold("reviewed alias pair has no local evidence citation")
        if decision == "UNREVIEWED" and (citation or notes):
            raise PairReviewHold("unreviewed pair cannot carry prefilled verdict evidence")
        status_counts[decision] += 1
    return {
        "schema": SAFE_SCHEMA,
        "status": "R57_G2_MANUAL_ALIAS_PAIR_COVERAGE_REVIEW__NO_INDEPENDENCE_CERTIFICATION",
        "total_required_pairs": len(items),
        "historical_comparison_pairs": 54,
        "two_gold_candidate_comparison_pairs": 1,
        "decision_counts": status_counts,
        "reviewed_pair_count": len(items) - status_counts["UNREVIEWED"],
        "unreviewed_pair_count": status_counts["UNREVIEWED"],
        "source_pins_reverified_by_cli": False,
        "owner_alias_component_signoff_complete": False,
        "independent_semantic_alias_review_complete": False,
        "world_independence_certified": False,
        "dataset_v04_admitted": 0,
        "r50_content_accessed": False,
        "training_authorized": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", type=Path, required=True)
    p.add_argument("--private-root", type=Path, required=True)
    actions = p.add_mutually_exclusive_group(required=True)
    actions.add_argument("--create-private-name", type=str)
    actions.add_argument("--audit-private-name", type=str)
    args = p.parse_args()
    filename = args.create_private_name or args.audit_private_name
    try:
        if not PAIR_FILE.fullmatch(filename):
            raise PairReviewHold("review file must use fixed private basename format")
        payloads, priv = _source_payloads(args.repo_root, args.private_root)
        expected = expected_questions(payloads)
        path = frozen._guard_path(priv, filename)
        if args.create_private_name:
            if path.exists() or path.is_symlink():
                raise PairReviewHold("refusing to overwrite existing private file")
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            fd = os.open(path, flags, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as sink:
                json.dump(expected, sink, ensure_ascii=False, sort_keys=True, indent=2)
                sink.write("\n")
            report = review_counts(expected, expected)
        else:
            raw = frozen._read(priv, filename, frozen.MAX_META_BYTES)
            packet = json.loads(raw)
            report = review_counts(packet, expected)
        report["source_pins_reverified_by_cli"] = True
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        error = "filesystem IO failed" if isinstance(exc, OSError) else str(exc)
        print("R57_G2_ALIAS_PAIR_HOLD: " + type(exc).__name__ + ": " + error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
