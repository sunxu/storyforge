"""R51 private raw-source replay for Gold108, using pinned 06–15 Git LFS archive.

Only original-message matching and historical order are checked, not semantic
card sufficiency, training rights, world splits or model quality. No source
message text, candidate identifiers or review comments enter Git or stdout.
All outputs are exclusive-created private files and every row remains HOLD.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import stat
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import v03_r51_gold195_private_triage as triage
import v03_r51_gold195_readiness as baseline

OUTER = Path("evaluations/v0.2/source-archives/06-15/"
             "StoryForge_v02_06-15_Full_Evidence_20261013.zip")
MANIFEST = Path("evaluations/v0.2/source-archives/06-15/source_bundle_manifest.json")
ASSET_ENTRY = "sources/StoryForge_v02_06-15_R02_Handoff_Assets_20261012.zip"
OUTER_SIZE = 65332700
OUTER_SHA256 = "b874cd07547092e9c3c967f69fab6b75262ff4f44ba2d368fd575f84e8886afb"
ASSET_SHA256 = "3d4c45250dceffc11af9f11fbf22eb40bfa1b316329b0d9908c97c1212401dd6"
MAX_ZIP_MEMBER = 256 * 1024 * 1024
MAX_DEPTH = 4
MAX_MEMBERS = 20000


def require(value: bool, code: str) -> None:
    if not value:
        raise ValueError(code)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def read_private_v2(path: Path, repo: Path) -> list[dict]:
    file = path.expanduser().absolute()
    require(file.is_file() and not file.is_symlink(), "PRIVATE_V2_NOT_FOUND")
    require(repo != file and repo not in file.parents, "PRIVATE_V2_INSIDE_REPO")
    require(stat.S_IMODE(file.stat().st_mode) == 0o600, "PRIVATE_V2_MODE_UNSAFE")
    require(stat.S_IMODE(file.parent.stat().st_mode) & 0o077 == 0,
            "PRIVATE_V2_PARENT_MODE_UNSAFE")
    for ancestor in (file.parent, *file.parent.parents):
        require(not ancestor.is_symlink(), "PRIVATE_V2_SYMLINK_PARENT")
    with file.open(encoding="utf8") as stream:
        actual = [json.loads(line) for line in stream]
    require(len(actual) == 195, "PRIVATE_V2_COUNT_CHANGED")
    a = baseline.read_pinned_rows(repo, baseline.GOLD87, 87,
                                  blob_sha1=baseline.EXPECTED_GIT_SHA1_87)
    b = baseline.read_pinned_rows(repo, baseline.GOLD108, 108,
                                  sha256_digest=baseline.EXPECTED_SHA256_108)
    ix = baseline.read_gold108_index(repo)
    expected, _ = triage.make_rows(a, b, ix)
    pinned = ("candidate_id", "cohort", "source_rank", "source_story_id",
              "original_target_message_id", "original_target_sha256",
              "history_fingerprints", "source_reference", "metadata_risks")
    for row, before in zip(actual, expected, strict=True):
        require(all(row.get(k) == before[k] for k in pinned),
                "PRIVATE_V2_FROZEN_ROW_PIN_MISMATCH")
        require(row.get("schema") == "storyforge-r51-private-gold195-triage-v2"
                and row.get("owner_attestation", {}).get("scope") ==
                "AGE_CONSENT_AND_CONTENT_BOUNDARIES",
                "PRIVATE_V2_OWNER_ATTESTATION_MISSING")
        require(row.get("training_admission") == triage.HOLD and
                row.get("split") is None and
                "CONTENT_OR_RIGHTS_HOLD" in row.get("holds", []),
                "PRIVATE_V2_PREMATURE_ADMISSION")
    return actual


def pinned_archive(repo: Path) -> tuple[bytes, dict[int, str]]:
    path = repo / OUTER
    require(path.is_file() and not path.is_symlink(), "LFS_ARCHIVE_MISSING")
    require(path.stat().st_size == OUTER_SIZE, "LFS_ARCHIVE_SIZE_MISMATCH")
    require(sha256(path.read_bytes()) == OUTER_SHA256, "LFS_ARCHIVE_HASH_MISMATCH")
    manifest = json.loads((repo / MANIFEST).read_text(encoding="utf8"))
    require(manifest["bundle_sha256"] == OUTER_SHA256 and
            manifest["bundle_size_bytes"] == OUTER_SIZE,
            "ARCHIVE_MANIFEST_CHANGED")
    mapped = {int(r["story_number"]): r["raw_zip_sha256"]
              for r in manifest["nested_source_sha256"]}
    require(set(mapped) == set(range(6, 16)), "EXPECTED_TEN_SOURCE_STORIES")
    with zipfile.ZipFile(path) as outer:
        require(outer.testzip() is None, "OUTER_ARCHIVE_CRC_MISMATCH")
        data = outer.read(ASSET_ENTRY)
    require(sha256(data) == ASSET_SHA256, "NESTED_ASSET_SHA_MISMATCH")
    return data, mapped


def discover_raw_zips(asset: bytes, story_hashes: dict[int, str]) -> dict[int, bytes]:
    expected_by_sha = {digest: rank for rank, digest in story_hashes.items()}
    found: dict[int, bytes] = {}
    examined = 0

    def walk(payload: bytes, level: int) -> None:
        nonlocal examined
        require(level <= MAX_DEPTH, "ZIP_DEPTH_LIMIT")
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            require(len(archive.infolist()) <= MAX_MEMBERS, "ZIP_MEMBER_LIMIT")
            for info in archive.infolist():
                if info.is_dir() or not info.filename.lower().endswith(".zip"):
                    continue
                examined += 1
                require(examined <= MAX_MEMBERS, "ZIP_GLOBAL_MEMBER_LIMIT")
                require(info.file_size <= MAX_ZIP_MEMBER, "ZIP_MEMBER_TOO_LARGE")
                raw = archive.read(info)
                digest = sha256(raw)
                if digest in expected_by_sha:
                    rank = expected_by_sha[digest]
                    require(rank not in found, "DUPLICATE_RAW_SOURCE_ZIP")
                    with zipfile.ZipFile(io.BytesIO(raw)) as original:
                        require(original.testzip() is None, "RAW_ZIP_CRC_MISMATCH")
                    found[rank] = raw
                elif level < MAX_DEPTH:
                    try:
                        if zipfile.is_zipfile(io.BytesIO(raw)):
                            walk(raw, level + 1)
                    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
                        raise ValueError("UNTRUSTED_NESTED_ZIP_INVALID") from exc

    walk(asset, 0)
    require(set(found) == set(story_hashes), "RAW_STORY_ZIPS_NOT_ALL_FOUND")
    return found


def choose_source_jsonl(raw_zip: bytes, expected_hashes: set[str]) -> bytes:
    matches = []
    candidates = []
    with zipfile.ZipFile(io.BytesIO(raw_zip)) as archive:
        for info in archive.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".jsonl"):
                continue
            require(info.file_size <= MAX_ZIP_MEMBER, "RAW_JSONL_TOO_LARGE")
            content = archive.read(info)
            candidates.append(content)
            if sha256(content) in expected_hashes:
                matches.append(content)
    if expected_hashes:
        require(len(matches) == 1, "SOURCE_JSONL_HASH_NOT_UNIQUE")
        return matches[0]
    require(len(candidates) == 1, "SOURCE_JSONL_AMBIGUOUS")
    return candidates[0]


def normalize_role(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip().lower()
    if value in ("assistant", "ai", "bot", "model", "character"):
        return "assistant"
    if value in ("user", "human", "player"):
        return "user"
    if value == "system":
        return "system"
    return None


def messages_in_json(value: object) -> list[tuple[str | None, str, str | None]]:
    """Best-effort structural parser. Never claim success without ID + exact SHA."""
    results = []
    max_objects = 150000
    objects = 0

    def descend(obj: object, inherited_id: str | None = None,
                inherited_role: str | None = None, level: int = 0) -> None:
        nonlocal objects
        require(level < 25, "RAW_MESSAGE_NESTING_LIMIT")
        objects += 1
        require(objects <= max_objects, "RAW_MESSAGE_OBJECT_LIMIT")
        if isinstance(obj, list):
            for child in obj:
                descend(child, inherited_id, inherited_role, level + 1)
            return
        if not isinstance(obj, dict):
            return
        oid = next((obj[key] for key in
                    ("message_id", "messageId", "id", "uuid")
                    if isinstance(obj.get(key), str) and obj[key]), inherited_id)
        role = (next((normalize_role(obj.get(key)) for key in
                      ("role", "sender_role", "speaker", "sender", "author")
                      if normalize_role(obj.get(key)) is not None), None)
                or inherited_role)
        fields = [
            obj[k] for k in ("content", "text", "message_text", "body")
            if isinstance(obj.get(k), str)
        ]
        if fields:
            digests = set()
            for field in fields:
                signature = sha256(field.encode("utf8"))
                if signature not in digests:
                    results.append((oid, signature, role))
                    digests.add(signature)
        for child in obj.values():
            if isinstance(child, (dict, list)):
                descend(child, oid, role, level + 1)

    descend(value)
    # Dedup two wrappers of the same literal message in one JSONL line.
    return list(dict.fromkeys(results))


def parse_source_events(payload: bytes) -> list[tuple[str | None, str, str | None]]:
    events = []
    raw = payload.decode("utf-8-sig")
    for line in raw.splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        events.extend(messages_in_json(item))
    require(len(events) > 0, "RAW_JSONL_NO_MESSAGE_EVENTS")
    return events


def ordered_history(events: list[tuple[str | None, str, str | None]],
                    target_pos: int, history: list[dict]) -> tuple[bool, bool]:
    expected = [x["sha256"] for x in history]
    prefix = [x[1] for x in events[:target_pos]]
    cursor = 0
    selected = []
    for digest in expected:
        while cursor < len(prefix) and prefix[cursor] != digest:
            cursor += 1
        if cursor >= len(prefix):
            return False, False
        selected.append(cursor)
        cursor += 1
    contiguous = bool(selected) and selected == list(
        range(target_pos - len(selected), target_pos))
    return True, contiguous


def replay_108(rows: list[dict], raw_zips: dict[int, bytes]) -> dict:
    groups = defaultdict(list)
    for row in rows:
        if row["cohort"] == 108:
            groups[row["source_rank"]].append(row)
    require(sum(map(len, groups.values())) == 108, "GOLD108_GROUP_COUNT")
    counter = Counter()
    story_summary = {}
    for rank in sorted(groups):
        group = groups[rank]
        expected_hashes = {r["source_reference"]["source_jsonl_sha256"]
                           for r in group
                           if r["source_reference"].get("source_jsonl_sha256")}
        raw_jsonl = choose_source_jsonl(raw_zips[rank], expected_hashes)
        raw_sha = sha256(raw_jsonl)
        events = parse_source_events(raw_jsonl)
        target_id_count = 0
        target_and_sha = 0
        history_ordered = 0
        history_contiguous = 0
        for row in group:
            matches = [(pos, digest) for pos, (oid, digest, _) in enumerate(events)
                       if oid == row["original_target_message_id"]]
            valid = [pos for pos, digest in matches
                     if digest == row["original_target_sha256"]]
            # Never silently take the first if source structure has duplicate IDs.
            unique = len(matches) == len(valid) == 1
            checked = row["source_review"]
            checked["raw_target_replay"] = "ID_SHA_UNIQUE_PASS" if unique else (
                "NO_ID_MATCH__HOLD" if not matches else "ID_SHA_NOT_UNIQUE__HOLD")
            checked["raw_source_receipt"] = {
                "raw_zip_sha256": sha256(raw_zips[rank]),
                "source_jsonl_sha256": raw_sha,
                "target_source_event_offset": valid[0] if unique else None,
                "historical_card_certified": False,
            }
            if not unique:
                continue
            counter["target_match"] += 1
            target_and_sha += 1
            target_id_count += 1
            # The raw source ZIP/JSONL and target-time record are authenticated.
            row["source_archive_replay"] = "RAW_TARGET_ID_AND_SHA_PASS"
            # Direct index is not the same as event position; do not forge it.
            history = row["history_fingerprints"]
            ordered, contiguous = ordered_history(events, valid[0], history)
            checked["raw_history_in_order"] = (
                "PASS" if ordered else "UNPROVEN__HOLD")
            checked["raw_history_contiguous_before_target"] = (
                "PASS" if contiguous else "UNPROVEN__HOLD")
            if ordered:
                history_ordered += 1
                counter["history_ordered"] += 1
            if contiguous:
                history_contiguous += 1
                counter["history_contiguous"] += 1
        story_summary[str(rank)] = {
            "candidates": len(group),
            "target_unique_id_and_sha": target_and_sha,
            "history_ordered_by_sha": history_ordered,
            "history_immediately_contiguous": history_contiguous,
        }
    return {
        "status": "RAW_GOLD108_REPLAY_PERFORMED__NO_SEMANTIC_ADMISSION",
        "source_stories_replayed": len(groups),
        "gold108_target_unique_id_sha_matches": counter["target_match"],
        "gold108_history_sha_in_original_order": counter["history_ordered"],
        "gold108_history_immediately_contiguous": counter["history_contiguous"],
        "gold87_source_replay": "NOT_PERFORMED",
        "by_story_rank": story_summary,
        "card_or_context_routes_decided": 0,
        "semantic_reviews_performed": 0,
        "training_admitted": 0,
        "validation_admitted": 0,
        "new_splits_assigned": 0,
        "r50_heldout_modified": False,
    }



# Only technical/schema-like field names may appear in diagnostic output.
SCHEMA_FIELDS = (
    "messages", "message", "id", "message_id", "messageId",
    "uuid", "role", "author", "sender", "speaker", "from",
    "type", "is_ai", "content", "text", "body", "payload",
    "data", "parts", "value", "message_text", "text_content",
    "content_text", "content_type", "turn_index", "created_at",
    "status", "metadata", "raw", "items",
)


def safe_shape(value: object, depth: int = 0) -> object:
    """Technical keys and Python types only. No arbitrary names or values."""
    if isinstance(value, dict):
        if depth >= 4:
            return {"type": "dict"}
        return {
            "type": "dict",
            "fields": {key: safe_shape(value[key], depth + 1)
                       for key in SCHEMA_FIELDS if key in value},
            "unlisted_key_count": sum(k not in SCHEMA_FIELDS for k in value),
        }
    if isinstance(value, list):
        return {"type": "list", "first": safe_shape(value[0], depth + 1)
                if value and depth < 4 else None}
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "str"
    return "other"


def probe_original_schema(repo: Path, raw_zip_by_rank: dict[int, bytes]) -> dict:
    gold108 = baseline.read_pinned_rows(
        repo, baseline.GOLD108, 108,
        sha256_digest=baseline.EXPECTED_SHA256_108)
    ix = baseline.read_gold108_index(repo)
    ranks: dict[int, set[str]] = defaultdict(set)
    for row, index_row in zip(gold108, ix, strict=True):
        digest = row["metadata"].get("source_jsonl_sha256")
        if digest:
            ranks[int(index_row["story_number"])].add(digest)
        else:
            ranks[int(index_row["story_number"])].add("")
    out = {}
    for rank in sorted(ranks):
        payload = choose_source_jsonl(
            raw_zip_by_rank[rank], ranks[rank] - {""})
        first = next((line for line in payload.decode("utf-8-sig").splitlines()
                      if line.strip()), None)
        require(first is not None, "SOURCE_JSONL_EMPTY")
        root = json.loads(first)
        # Shape of the first JSONL entry; no values, hashes or arbitrary keys.
        out[str(rank)] = {
            "first_jsonl_entry_shape": safe_shape(root),
            "first_entry_is_record_with_messages":
                isinstance(root, dict) and isinstance(root.get("messages"), list),
        }
    return {
        "schema": "storyforge-r51-original-source-shape-only-v1",
        "diagnostic": "SOURCE_PARSER_MISMATCH_INVESTIGATION",
        "stories_probed": len(out),
        "story_rank_only_structural_shapes": out,
        "source_message_bodies_returned": False,
        "candidate_identifiers_returned": False,
        "raw_target_match_or_training_admission": "NOT_ASSERTED",
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--private-v2", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--probe-schema", action="store_true",
                        help="Only print safe structural field names and types")
    args = parser.parse_args()
    os.umask(0o077)
    try:
        repo = args.repo.resolve(strict=True)
        require(args.probe_schema or
                (args.private_v2 is not None and args.output is not None),
                "PRIVATE_V2_AND_OUTPUT_REQUIRED")
        asset, manifest = pinned_archive(repo)
        raw = discover_raw_zips(asset, manifest)
        if args.probe_schema:
            require(args.private_v2 is None and args.output is None,
                    "SCHEMA_PROBE_TAKES_NO_WORKPAPER_ARGUMENTS")
            receipt = probe_original_schema(repo, raw)
            print(json.dumps(receipt, ensure_ascii=False,
                             sort_keys=True, indent=2))
            return 0
        rows = read_private_v2(args.private_v2, repo)
        receipt = replay_108(rows, raw)
        require(receipt["gold108_target_unique_id_sha_matches"] > 0,
                "ALL_108_TARGETS_UNMATCHED_PARSER_SCHEMA_HOLD")
        for row in rows:
            row["schema"] = "storyforge-r51-private-gold195-triage-v3"
            require(row["training_admission"] == triage.HOLD
                    and row["split"] is None, "R51_TRAIN_APPROVAL_FORBIDDEN")
        triage.write_private(args.output, rows, repo)
    except (OSError, ValueError, KeyError, TypeError, AssertionError,
            UnicodeError, json.JSONDecodeError, zipfile.BadZipFile,
            RuntimeError) as exc:
        # Never print exception values: ZIP member names can contain private text.
        print("R51_RAW_REPLAY_HOLD__" + type(exc).__name__, file=sys.stderr)
        return 2
    print("R51_ORIGINAL_GOLD108_RAW_REPLAY_RECORDED__NO_ADMISSION")
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
