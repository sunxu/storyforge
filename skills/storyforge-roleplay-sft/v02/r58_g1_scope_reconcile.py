"""R58 v0.2: reconcile EXISTING authorized UUID metadata, never grant G1.

Input is a small owner-private UUID-only manifest and the existing fixed-pilot
prior-SFT ledger. Never read R50 examples or narrative text, never call DB/HF.
Source coverage claims and matching SHA digests are NOT independent provenance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from contextlib import ExitStack
from pathlib import Path

SCHEMA = "r58_g1_private_scoped_uuid_manifest_v1"
LEDGER_SCHEMA = "r58_round1_g1_prior_sft_exact_id_holds_private_v2"
RESULT_SCHEMA = "r58_g1_uuid_scope_reconciliation_safe_v1"
POLICY = "ONE_ROLEPLAY_STORY_UUID_PER_WORLD"
SCOPES = (
    "known_historical_sft", "r50_known_protected", "gold195_source",
    "legacy_dev20", "r04_non_gold", "r55_r57_other_dev",
    "other_reserved_heldout", "other_historical_training",
)
# Scoped historical known sets, NOT authoritative full-universe coverage.
KNOWN_COUNTS = {
    "known_historical_sft": 27,
    "r50_known_protected": 5,
    "gold195_source": 13,
    "legacy_dev20": 2,
    "r04_non_gold": 2,
}
UUID_RE = re.compile(r"[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}\Z")
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
CLAIMS = frozenset(("UNKNOWN", "OWNER_PARTIAL", "OWNER_COMPLETE"))
MAX_BYTES = 1_000_000
MAX_UUIDS = 5000


class Hold(ValueError):
    pass


def distinct_uuids(values: object, *, expected: int | None = None) -> set[str]:
    if not isinstance(values, list) or len(values) > MAX_UUIDS:
        raise Hold("invalid metadata UUID roster")
    if expected is not None and len(values) != expected:
        raise Hold("frozen metadata roster size changed")
    if not all(isinstance(v, str) and UUID_RE.fullmatch(v) for v in values):
        raise Hold("noncanonical UUID or non-metadata content")
    output = set(values)
    if len(output) != len(values):
        raise Hold("duplicate UUID in metadata roster")
    return output


def roster_digest(values: set[str]) -> str:
    """Integrity fingerprint of local canonical UUID list, NOT its origin."""
    data = "".join(value + "\n" for value in sorted(values)).encode("ascii")
    return hashlib.sha256(data).hexdigest()


def exactly(obj: object, fields: set[str]) -> bool:
    return isinstance(obj, dict) and set(obj) == fields


def decode_json(raw: bytes) -> dict:
    if not 0 < len(raw) <= MAX_BYTES:
        raise Hold("invalid private metadata file size")

    def no_duplicates(pairs):
        record = {}
        for key, value in pairs:
            if key in record:
                raise Hold("duplicate JSON field")
            record[key] = value
        return record

    try:
        obj = json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicates)
    except (UnicodeError, ValueError, TypeError) as exc:
        raise Hold("invalid private metadata JSON") from exc
    if not isinstance(obj, dict):
        raise Hold("expected metadata object")
    return obj


def read_private(path: Path, root: Path) -> dict:
    """Normalize denied OS-level private-file access to fail-closed Hold."""
    try:
        return _read_private(path, root)
    except OSError:
        # macOS and Linux may raise ELOOP or ENOTDIR for O_NOFOLLOW.
        # Never leak private path/errno details to the calling layer.
        raise Hold("private metadata access denied") from None


def _read_private(path: Path, root: Path) -> dict:
    """Open owner-private metadata via dirfds; refuse traversal and symlink races."""
    if (not path.is_absolute() or not root.is_absolute()
            or ".." in path.parts or ".." in root.parts
            or not path.is_relative_to(root) or path == root):
        raise Hold("private input is outside authorized directory")
    # The required flags are available on supported POSIX Mac/Linux; never silently downgrade.
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise Hold("secure private directory open unsupported")
    parts = path.relative_to(root).parts
    if not parts or len(parts) > 16:
        raise Hold("private path depth invalid")
    dir_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    file_flags = os.O_RDONLY | os.O_NOFOLLOW

    def check_directory(fd: int) -> None:
        info = os.fstat(fd)
        if not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o077:
            raise Hold("private directory permissions unsafe")

    with ExitStack() as stack:
        directory = os.open(root, dir_flags)
        stack.callback(os.close, directory)
        check_directory(directory)
        for component in parts[:-1]:
            directory = os.open(component, dir_flags, dir_fd=directory)
            stack.callback(os.close, directory)
            check_directory(directory)
        fd = os.open(parts[-1], file_flags, dir_fd=directory)
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077
                    or info.st_nlink != 1 or not 0 < info.st_size <= MAX_BYTES):
                raise Hold("private file permissions or size invalid")
            raw = handle.read(MAX_BYTES + 1)
            if len(raw) != info.st_size:
                raise Hold("private metadata changed during read")
    return decode_json(raw)


def reconcile(manifest: dict, ledger: dict) -> dict:
    if not exactly(manifest, {"schema", "world_identity_policy", "candidate_uuids", "source_scopes"}):
        raise Hold("private UUID-only manifest schema invalid")
    if manifest["schema"] != SCHEMA or manifest["world_identity_policy"] != POLICY:
        raise Hold("metadata namespace mismatch")
    candidates = distinct_uuids(manifest["candidate_uuids"], expected=5)
    if not exactly(ledger, {
        "schema", "owner_world_identity_policy", "status",
        "roster_bytes_sha256_PRIVATE", "namespace_equivalence_owner_confirmed",
        "cross_uuid_semantic_world_review_required", "entries",
        "frozen_queue_unmodified", "expansion_allowed",
    }):
        raise Hold("fixed pilot ledger schema fields mismatch")
    if (ledger["schema"] != LEDGER_SCHEMA
            or ledger["owner_world_identity_policy"] !=
                "OWNER_ATTESTED_ROLEPLAY_UUID_ONE_UUID_ONE_WORLD_V1"
            or ledger["status"] != "G1_FIVE_STORIES_HOLD_ONLY__NOT_ADMITTED"
            or not isinstance(ledger["roster_bytes_sha256_PRIVATE"], str)
            or not HEX64.fullmatch(ledger["roster_bytes_sha256_PRIVATE"])
            or ledger["namespace_equivalence_owner_confirmed"] is not True
            or ledger["cross_uuid_semantic_world_review_required"] is not False
            or ledger["frozen_queue_unmodified"] is not True
            or ledger["expansion_allowed"] is not False):
        raise Hold("fixed pilot identity not attested")
    entries = ledger["entries"]
    if not isinstance(entries, list) or len(entries) != 5:
        raise Hold("fixed pilot five-row ledger missing")
    from_ledger = set()
    excluded = set()
    for row in entries:
        if not exactly(row, {
            "story_id_PRIVATE", "historical_sft_exact_uuid_overlap", "status",
            "owner_attested_world_component_UUID", "owner_attested_distinct_semantic_world",
            "historical_sft_exact_uuid_set_nonoverlap", "r50_protected_clear",
            "prior_sft_clear", "r55_r57_dev_clear", "other_protected_clear",
            "train_admitted",
        }):
            raise Hold("unexpected non-metadata ledger field")
        ident = row["story_id_PRIVATE"]
        overlap = row["historical_sft_exact_uuid_overlap"]
        if not isinstance(ident, str) or not UUID_RE.fullmatch(ident) or type(overlap) is not bool:
            raise Hold("invalid frozen ledger UUID/overlap")
        if (row["owner_attested_world_component_UUID"] != ident
                or row["owner_attested_distinct_semantic_world"] is not True
                or row["historical_sft_exact_uuid_set_nonoverlap"] is not (not overlap)
                or any(row[k] is not False for k in (
                    "r50_protected_clear", "prior_sft_clear", "r55_r57_dev_clear",
                    "other_protected_clear", "train_admitted",
                ))):
            raise Hold("private ledger attempted premature clearance")
        label = ("EXCLUDED_PRIOR_SFT_EXACT_UUID_EXPOSURE" if overlap
                 else "HOLD_R50_DEV_OTHER_PROTECTED_UUID_CHECK_PENDING")
        if ident in from_ledger or row["status"] != label:
            raise Hold("frozen ledger duplicate or status drift")
        from_ledger.add(ident)
        if overlap:
            excluded.add(ident)
    if from_ledger != candidates or len(excluded) != 1:
        raise Hold("five frozen world identities changed")
    remaining = candidates - excluded
    scopes = manifest["source_scopes"]
    if not isinstance(scopes, list) or len(scopes) != len(SCOPES):
        raise Hold("eight metadata source scopes required")
    by_scope = {}
    summaries = {}
    for item in scopes:
        if not exactly(item, {
            "scope", "world_uuids", "roster_sha256", "coverage_claim", "source_revision"
        }):
            raise Hold("unexpected metadata scope field")
        scope = item["scope"]
        if scope not in SCOPES or scope in by_scope:
            raise Hold("missing/duplicated source scope")
        ids = distinct_uuids(item["world_uuids"], expected=KNOWN_COUNTS.get(scope))
        digest = item["roster_sha256"]
        if not isinstance(digest, str) or not HEX64.fullmatch(digest) or digest != roster_digest(ids):
            raise Hold("local UUID roster fingerprint mismatch")
        claim = item["coverage_claim"]
        rev = item["source_revision"]
        if claim not in CLAIMS or (rev is not None and (
            not isinstance(rev, str) or not (HEX40.fullmatch(rev) or HEX64.fullmatch(rev))
        )):
            raise Hold("invalid metadata source claim/revision")
        if claim == "OWNER_COMPLETE" and rev is None:
            raise Hold("complete claim without source revision")
        by_scope[scope] = ids
        summaries[scope] = {
            "worlds_in_scoped_roster": len(ids),
            "remaining_four_exact_uuid_matches": len(ids & remaining),
            "coverage_claim": claim,
            "source_revision_recorded": rev is not None,
            "roster_integrity_checked_not_source_authenticated": True,
            "independent_universe_completeness_verified": False,
        }
    if set(by_scope) != set(SCOPES):
        raise Hold("incomplete eight-scope evidence universe")
    if len(candidates & by_scope["known_historical_sft"]) != 1 or (
        candidates & by_scope["known_historical_sft"] != excluded
    ):
        raise Hold("historical training exclusion mismatch")
    return {
        "schema": RESULT_SCHEMA,
        "status": "SCOPED_UUID_RECONCILED__ALL_UNVERIFIED_COVERAGE_HOLD",
        "frozen_candidates": 5,
        "known_historical_sft_excluded": 1,
        "remaining_candidates_held": 4,
        "owner_private_ledger_exact_identity_match": True,
        "scopes_checked": len(SCOPES),
        "scoped_results": {s: summaries[s] for s in SCOPES},
        "remaining_four_with_any_scoped_collision": len(set().union(
            *(ids & remaining for ids in by_scope.values())
        )),
        "independently_complete_scope_count": 0,
        "all_source_universes_verified": False,
        "candidate_target_or_story_text_read": False,
        "protected_test_content_read": False,
        "private_story_ids_or_paths_returned": False,
        "g1_clearance": "HOLD",
        "g2_clearance": "HOLD",
        "train_admitted": 0,
        "validation_admitted": 0,
        "teacher_admitted": 0,
        "expansion_allowed": False,
        "paid_hf_job_started": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-manifest", type=Path, required=True)
    parser.add_argument("--prior-sft-ledger", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        root = Path.home() / ".storyforge-r58-private"
        manifest = read_private(args.private_manifest, root)
        ledger = read_private(args.prior_sft_ledger, root)
        print(json.dumps(reconcile(manifest, ledger), ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (Hold, OSError, TypeError, ValueError, UnicodeError, RecursionError):
        print("R58_G1_UUID_SCOPE: HOLD (private metadata source missing/inconsistent)", file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
