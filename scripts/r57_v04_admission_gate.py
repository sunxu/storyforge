"""StoryForge R57-B Dataset v0.4 PRIVATE metadata-only admission gate.

Standard library only, no network, no source story read, no HF, no R50.
Validates explicit subset/semantics of accompanying JSON Schema and cross-record
world isolation. The JSON Schema remains the normative structural contract.
Never upload an actual populated private manifest to ordinary Git.
"""

import argparse
import json
import os
import re
import stat
import sys
from collections import Counter
from pathlib import Path

FORMAT = "storyforge-r57-v04-private-intake-v1"
SAFE = "storyforge-r57-v04-safe-intake-report-v1"
HEX = re.compile(r"^[0-9a-f]{64}$")
ROOT_FIELDS = {"schema", "no_r50_content_accessed", "training_authorized", "records"}
FIELDS = {
    "record_id", "source_pool", "source_target_sha256", "source_file_sha256",
    "history_sha256", "target_time_rules_sha256", "target_time_canon",
    "world_component_token", "rights_basis", "content_boundary",
    "source_provenance_verified", "world_isolation_verified",
    "historical_train_exposure", "historical_validation_exposure",
    "historical_dev_exposure", "protected_test_isolation", "corpus_kind",
    "parent_target_sha256", "derivation_delta_sha256", "source_quality_labels",
    "reviews", "owner_signoff", "decision", "split", "rationale",
}
SOURCES = {"GOLD87", "GOLD108", "R45_FROZEN", "NEW_OWNER_ORIGINAL", "OTHER_REVIEWED"}
EXPOSURE = {"MATCHED_DISCLOSED", "NO_OBSERVED_MATCH", "UNKNOWN"}
SPLITS = {"NONE", "TRAIN", "VALIDATION", "DEV_DIAGNOSTIC"}
DECISIONS = {"PENDING", "HOLD", "REJECT", "ACCEPT"}
CORPUS = {"CANONICAL_GOLD", "DERIVED_FROM_ORIGINAL", "SYNTHETIC", "DIAGNOSTIC_NEGATIVE"}
LABELS = {
    "NATURAL_NARRATIVE", "PLAYER_AGENCY", "NO_PLAYER_GHOSTWRITING",
    "USER_EVENT_CONTINUITY", "FORBIDDEN_PHRASE", "USER_ECHO_BAN",
    "BILINGUAL_DIALOGUE", "HARD_FACT_TIMELINE", "NPC_INITIATIVE", "OTHER",
}
REVIEW_FIELDS = {"reviewer_key", "kind", "outcome", "evidence_sha256"}
REVIEW_KIND = {"HUMAN", "AI_ASSISTED", "OWNER_DELEGATED"}
REVIEW_OUTCOME = {"ACCEPT", "REJECT", "HOLD"}


class GateError(ValueError):
    """Hard fail. Avoid exposing private row IDs and source paths in exceptions."""


def _field_set(obj, required, label):
    if not isinstance(obj, dict) or set(obj) != required:
        raise GateError(f"{label}: missing/unexpected metadata fields")


def _sha(value):
    return isinstance(value, str) and HEX.fullmatch(value) is not None


def _txt(value, lo, hi):
    return isinstance(value, str) and lo <= len(value) <= hi


def check_manifest(data, *, require_admission=False):
    """Return SAFE COUNT-ONLY receipt, never include row IDs, worlds, or hashes."""
    _field_set(data, ROOT_FIELDS, "manifest")
    if data["schema"] != FORMAT:
        raise GateError("unsupported manifest schema")
    if data["no_r50_content_accessed"] is not True:
        raise GateError("R50 access boundary not certified")
    if data["training_authorized"] is not False:
        raise GateError("training authorization must remain false")
    rows = data["records"]
    if not isinstance(rows, list) or len(rows) > 10000:
        raise GateError("invalid records list")
    if require_admission and not rows:
        raise GateError("no admitted samples for admission-mode validation")

    by_decision = Counter()
    by_split = Counter()
    by_pool = Counter()
    seen_ids = set()
    seen_targets = set()
    component_splits = {}
    for row in rows:
        _field_set(row, FIELDS, "row")
        if (not _txt(row["record_id"], 3, 128)
                or not _txt(row["world_component_token"], 3, 128)
                or not _txt(row["rationale"], 12, 2000)):
            raise GateError("invalid record token/component/rationale length")
        if row["record_id"] in seen_ids:
            raise GateError("duplicate private record identifier")
        seen_ids.add(row["record_id"])
        for name in ("source_target_sha256", "source_file_sha256",
                     "history_sha256", "target_time_rules_sha256"):
            if not _sha(row[name]):
                raise GateError("invalid source SHA256")
        if row["source_pool"] not in SOURCES:
            raise GateError("unexpected source pool")
        for name, acceptable in (
            ("target_time_canon", {"VERIFIED", "HOLD", "NOT_CHECKED"}),
            ("rights_basis", {"OWNER_ATTESTED_SCOPED", "INDEPENDENTLY_VERIFIED", "HOLD", "NOT_CHECKED"}),
            ("content_boundary", {"CASE_VERIFIED_PASS", "HOLD", "REJECT", "NOT_CHECKED"}),
            ("protected_test_isolation", {"CUSTODIAN_METADATA_ATTESTED_CLEAR", "HOLD_NOT_CHECKED"}),
            ("owner_signoff", {"PENDING", "APPROVED", "REJECTED"}),
            ("corpus_kind", CORPUS),
            ("decision", DECISIONS),
            ("split", SPLITS),
        ):
            if row[name] not in acceptable:
                raise GateError("invalid metadata enum")
        for name in ("source_provenance_verified", "world_isolation_verified"):
            if type(row[name]) is not bool:
                raise GateError("invalid attestation value")
        for name in ("historical_train_exposure", "historical_validation_exposure",
                     "historical_dev_exposure"):
            if row[name] not in EXPOSURE:
                raise GateError("invalid historical exposure status")
        for name in ("parent_target_sha256", "derivation_delta_sha256"):
            if row[name] is not None and not _sha(row[name]):
                raise GateError("invalid parent/derivative SHA256")
        if row["corpus_kind"] == "DERIVED_FROM_ORIGINAL" and (
            not _sha(row["parent_target_sha256"]) or not _sha(row["derivation_delta_sha256"])
        ):
            raise GateError("derived row missing parent/change digests")
        if row["corpus_kind"] in ("CANONICAL_GOLD", "DIAGNOSTIC_NEGATIVE") and (
            row["parent_target_sha256"] is not None or row["derivation_delta_sha256"] is not None
        ):
            raise GateError("non-derived row with parent/derivative data")
        labels = row["source_quality_labels"]
        if (not isinstance(labels, list) or not labels or
                any(not isinstance(t, str) or t not in LABELS for t in labels) or
                len(labels) != len(set(labels))):
            raise GateError("invalid or duplicate quality labels")
        reviews = row["reviews"]
        if not isinstance(reviews, list) or len(reviews) > 6:
            raise GateError("invalid independent review list")
        reviewed = set()
        for rv in reviews:
            _field_set(rv, REVIEW_FIELDS, "review")
            if (not _txt(rv["reviewer_key"], 3, 128) or
                    rv["reviewer_key"] in reviewed or
                    rv["kind"] not in REVIEW_KIND or
                    rv["outcome"] not in REVIEW_OUTCOME or
                    not _sha(rv["evidence_sha256"])):
                raise GateError("invalid/duplicate reviewer evidence")
            reviewed.add(rv["reviewer_key"])
        by_decision[row["decision"]] += 1
        by_split[row["split"]] += 1
        by_pool[row["source_pool"]] += 1

        if row["decision"] == "ACCEPT":
            if row["split"] not in ("TRAIN", "VALIDATION"):
                raise GateError("accepted row must have TRAIN/VALIDATION split")
            if row["corpus_kind"] in ("SYNTHETIC", "DIAGNOSTIC_NEGATIVE"):
                raise GateError("synthetic/negative corpus cannot enter canonical SFT admission")
            if (row["target_time_canon"] != "VERIFIED" or
                    row["rights_basis"] not in ("OWNER_ATTESTED_SCOPED", "INDEPENDENTLY_VERIFIED") or
                    row["content_boundary"] != "CASE_VERIFIED_PASS" or
                    row["source_provenance_verified"] is not True or
                    row["world_isolation_verified"] is not True or
                    row["protected_test_isolation"] != "CUSTODIAN_METADATA_ATTESTED_CLEAR" or
                    row["owner_signoff"] != "APPROVED"):
                raise GateError("accepted row has unresolved source, safety, or owner gate")
            if row["historical_dev_exposure"] != "NO_OBSERVED_MATCH":
                raise GateError("accepted row reuses or has unchecked development material")
            if (row["historical_train_exposure"] == "UNKNOWN" or
                    row["historical_validation_exposure"] == "UNKNOWN"):
                raise GateError("accepted row has unresolved historical exposure")
            if len(reviews) < 2 or any(rv["outcome"] != "ACCEPT" for rv in reviews):
                raise GateError("accepted row lacks two agreeing reviewers")
            if row["source_target_sha256"] in seen_targets:
                raise GateError("exact duplicate target in admitted manifest")
            seen_targets.add(row["source_target_sha256"])
            splits = component_splits.setdefault(row["world_component_token"], set())
            splits.add(row["split"])
            if len(splits) != 1:
                raise GateError("world/alias component appears in TRAIN and VALIDATION")
        else:
            if row["split"] in ("TRAIN", "VALIDATION"):
                raise GateError("unadmitted row allocated to train or validation")
            if row["owner_signoff"] == "APPROVED":
                raise GateError("owner APPROVED contradicts unadmitted decision")
            if row["decision"] == "PENDING" and row["split"] != "NONE":
                raise GateError("pending row has nonempty split")
            if row["split"] == "DEV_DIAGNOSTIC" and row["decision"] != "REJECT":
                raise GateError("diagnostic negative row requires explicit REJECT")
    accepted = by_decision["ACCEPT"]
    if require_admission and accepted == 0:
        raise GateError("zero admitted records; no admission PASS")
    return {
        "schema": SAFE,
        "status": ("R57_V04_METADATA_ADMISSION_STRUCTURAL_PASS__NOT_SEMANTIC_CERTIFIED"
                   if require_admission else
                   "R57_V04_DRAFT_METADATA_ONLY_PASS__ZERO_ADMISSION_NOT_ASSUMED"),
        "record_count": len(rows),
        "count_by_decision": {k: by_decision[k] for k in sorted(DECISIONS)},
        "count_by_split": {k: by_split[k] for k in sorted(SPLITS)},
        "count_by_source_pool": {k: by_pool[k] for k in sorted(SOURCES)},
        "admitted_total": accepted,
        "isolated_world_component_count_for_accepted": len(component_splits),
        "no_r50_content_accessed": True,
        "training_authorized": False,
        "semantic_independence_and_source_verification_not_automatically_proven": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-manifest", type=Path, required=True)
    parser.add_argument("--mode", choices=["draft", "admission"], default="draft")
    parser.add_argument("--safe-out", type=Path)
    args = parser.parse_args()
    try:
        # A descriptor-based, size-bounded read avoids following final symlinks.
        # This CLI must only be given owner-approved, nonprotected metadata files.
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        if args.private_manifest.is_symlink():
            raise GateError("private manifest symlink is not allowed")
        fd = os.open(args.private_manifest, flags)
        with os.fdopen(fd, "r", encoding="utf-8") as manifest:
            st = os.fstat(manifest.fileno())
            if not stat.S_ISREG(st.st_mode) or st.st_size > 64 * 1024 * 1024:
                raise GateError("private manifest must be a regular file at most 64 MiB")
            data = json.load(manifest)
        result = check_manifest(data, require_admission=args.mode == "admission")
        safe = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if args.safe_out:
            if args.private_manifest.resolve() == args.safe_out.resolve():
                raise GateError("safe output must not overwrite private input")
            # Exclusive creation: do not replace receipts, private data, or symlink targets.
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            fd = os.open(args.safe_out, flags, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as receipt:
                receipt.write(safe)
        print(safe, end="")
        return 0
    except (ValueError, OSError, json.JSONDecodeError, TypeError) as exc:
        # Suppress OS paths in stderr: a private manifest path may itself be sensitive.
        message = "filesystem IO failed" if isinstance(exc, OSError) else str(exc)
        print(f"R57_V04_ADMISSION_HOLD: {type(exc).__name__}: {message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
