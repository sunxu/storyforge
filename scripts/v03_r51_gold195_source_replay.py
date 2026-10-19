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
import itertools
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

def parse_root_source_events(
    payload: bytes,
) -> list[tuple[str, str, str | None, int | None]]:
    """Exactly one authenticated JSONL export; only root.messages are events.

    A nested metadata/character/card field is not a second message, even
    if the recursive diagnostic discovers the same inherited message ID.
    The returned index is the true root.messages array index.
    """
    roots = 0
    events: list[tuple[str, str, str | None, int | None]] = []
    with io.TextIOWrapper(io.BytesIO(payload), encoding="utf-8-sig") as stream:
        for line in stream:
            if not line.strip():
                continue
            roots += 1
            require(roots == 1, "MULTIPLE_ROOT_SOURCE_RECORDS_HOLD")
            root = json.loads(line)
            require(isinstance(root, dict) and
                    isinstance(root.get("messages"), list),
                    "ORIGINAL_ROOT_MESSAGES_NOT_FOUND")
            for message in root["messages"]:
                require(isinstance(message, dict), "SOURCE_MESSAGE_NOT_OBJECT")
                oid = message.get("id")
                body = message.get("content")
                require(isinstance(oid, str) and bool(oid)
                        and isinstance(body, str),
                        "ORIGINAL_MESSAGE_ID_OR_BODY_TYPE_INVALID")
                turn = message.get("turn_index")
                require(turn is None or (isinstance(turn, int)
                                        and not isinstance(turn, bool)),
                        "SOURCE_TURN_INDEX_TYPE_INVALID")
                events.append((oid, sha256(body.encode("utf8")),
                               normalize_role(message.get("role")), turn))
    require(roots == 1 and len(events) > 0, "ORIGINAL_SOURCE_MESSAGES_EMPTY")
    return events



def ordered_history(
    events: list[tuple], target_pos: int, history: list[dict]
) -> tuple[bool, bool]:
    """Role+SHA ordered-subsequence and true immediate suffix separately."""
    require(target_pos >= 0, "SOURCE_TARGET_POSITION_INVALID")
    require(all("sha256" in h and "role" in h for h in history),
            "HISTORY_FINGERPRINT_MISSING_ROLE_OR_SHA")
    expected = [(h["sha256"], normalize_role(h["role"])) for h in history]
    before = [(e[1], e[2]) for e in events[:target_pos]]
    cursor = 0
    for item in expected:
        while cursor < len(before) and before[cursor] != item:
            cursor += 1
        if cursor >= len(before):
            return False, False
        cursor += 1
    suffix = (len(expected) <= len(before) and
              before[-len(expected):] == expected) if expected else True
    return True, suffix


def replay_108(rows: list[dict], raw_zips: dict[int, bytes]) -> dict:
    """Source-root ID+SHA replay only, preserving all semantic HOLDs."""
    groups: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        if row["cohort"] == 108:
            groups[row["source_rank"]].append(row)
    require(sum(len(v) for v in groups.values()) == 108,
            "GOLD108_GROUP_COUNT")
    totals = Counter()
    story_summary = {}
    for rank, group in sorted(groups.items()):
        expected_hashes = {r["source_reference"]["source_jsonl_sha256"]
                           for r in group
                           if r["source_reference"].get("source_jsonl_sha256")}
        raw_jsonl = choose_source_jsonl(raw_zips[rank], expected_hashes)
        jsonl_sha = sha256(raw_jsonl)
        events = parse_root_source_events(raw_jsonl)
        id_positions: dict[str, list[int]] = defaultdict(list)
        for pos, (msg_id, _, _, _) in enumerate(events):
            id_positions[msg_id].append(pos)
        local = Counter(candidates=len(group))
        for row in group:
            identity = row["original_target_message_id"]
            positions = id_positions.get(identity, [])
            matches = [
                pos for pos in positions
                if events[pos][1] == row["original_target_sha256"]
                and events[pos][2] == "assistant"
            ]
            unique = len(positions) == len(matches) == 1
            reviewed = row["source_review"]
            reviewed["raw_target_replay"] = (
                "ROOT_MESSAGES_UNIQUE_ASSISTANT_ID_SHA_PASS" if unique
                else "ROOT_MESSAGES_TARGET_NOT_UNIQUE_OR_DIFFERENT__HOLD")
            reviewed["raw_source_receipt"] = {
                "raw_zip_sha256": sha256(raw_zips[rank]),
                "source_jsonl_sha256": jsonl_sha,
                "original_root_messages_array_index": matches[0]
                if unique else None,
                "original_turn_index": events[matches[0]][3] if unique else None,
                "historical_card_certified": False,
            }
            if not unique:
                continue
            local["target_unique_id_sha_role_pass"] += 1
            row["source_archive_replay"] = "ORIGINAL_ROOT_MESSAGE_ID_SHA_ROLE_PASS"
            reviewed["source_pointer_verified"] = (
                "ROOT_MESSAGES_INDEX_ID_SHA_ROLE_VERIFIED")
            # Original metadata is immutable. Only the verified, private v4
            # workpaper receives the recovered raw-array index.
            history = row["history_fingerprints"]
            ordered, contiguous = ordered_history(events, matches[0], history)
            reviewed["raw_history_in_order"] = (
                "PASS_ROLE_SHA" if ordered else "UNPROVEN__HOLD")
            reviewed["raw_history_contiguous_before_target"] = (
                "PASS_ROLE_SHA" if contiguous else "UNPROVEN__HOLD")
            reviewed["source_replay_and_history_contiguity"] = (
                "PASS_SOURCE_WINDOW_ROLE_SHA"
                if contiguous else "SOURCE_WINDOW_UNPROVEN__HOLD")
            if ordered:
                local["history_ordered_by_sha_role"] += 1
            if contiguous:
                local["history_immediately_contiguous"] += 1
                turns = [event[3] for event in
                         events[matches[0] - len(history):matches[0] + 1]]
                if all(isinstance(turn, int) for turn in turns) and all(
                    b == a + 1 for a, b in itertools.pairwise(turns)
                ):
                    local["contiguous_turn_indices"] += 1
            if "SOURCE_POINTER_RECONCILIATION_HOLD" in row["holds"]:
                local["pointer_gap_candidates_root_index_recovered"] += 1
                # Retain original HOLD until source reviewer reconciles the
                # crosslinked audit evidence with this recovered index.
        for k in ("candidates", "target_unique_id_sha_role_pass",
                  "history_ordered_by_sha_role",
                  "history_immediately_contiguous",
                  "contiguous_turn_indices",
                  "pointer_gap_candidates_root_index_recovered"):
            totals[k] += local[k]
        story_summary[str(rank)] = dict(local)
    return {
        "schema": "storyforge-r51-original-root-message-replay-v4",
        "status": "GOLD108_TARGET_REPLAY_COMPLETE__SEMANTIC_ADMISSION_HOLD",
        "source_stories_replayed": len(groups),
        "gold108_target_unique_id_sha_matches":
            totals["target_unique_id_sha_role_pass"],
        "gold108_history_sha_in_original_order":
            totals["history_ordered_by_sha_role"],
        "gold108_history_immediately_contiguous":
            totals["history_immediately_contiguous"],
        "gold108_history_source_turns_consecutive":
            totals["contiguous_turn_indices"],
        "previous_22_pointer_gaps_original_indices_recovered":
            totals["pointer_gap_candidates_root_index_recovered"],
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


def probe_original_target_matching(
    repo: Path, private_v2: Path, raw_zip_by_rank: dict[int, bytes]
) -> dict:
    """Cross-check original root.messages schema, IDs and body hashes separately.

    Purely structural/aggregate diagnostics. The generic recursive parser
    is evaluated separately from the direct root.messages parser to expose
    accidental wrapper/ordering assumptions. No user content leaves memory.
    """
    rows = read_private_v2(private_v2, repo)
    groups: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        if row["cohort"] == 108:
            groups[row["source_rank"]].append(row)
    require(sum(len(v) for v in groups.values()) == 108,
            "GOLD108_EXPECTED_FOR_DIAGNOSTIC")
    total = Counter()
    summaries: dict[str, dict] = {}
    for rank, candidates in sorted(groups.items()):
        hashes = {r["source_reference"]["source_jsonl_sha256"]
                  for r in candidates
                  if r["source_reference"].get("source_jsonl_sha256")}
        payload = choose_source_jsonl(raw_zip_by_rank[rank], hashes)
        directly_parsed = []
        source_roots = 0
        source_message_dicts = 0
        with io.TextIOWrapper(io.BytesIO(payload), encoding="utf-8-sig") as stream:
            for line in stream:
                if not line.strip():
                    continue
                source_roots += 1
                root = json.loads(line)
                require(isinstance(root, dict) and
                        isinstance(root.get("messages"), list),
                        "RAW_ROOT_MESSAGES_FORMAT_UNEXPECTED")
                for msg in root["messages"]:
                    if not isinstance(msg, dict):
                        continue
                    source_message_dicts += 1
                    msg_id = msg.get("id")
                    content = msg.get("content")
                    if isinstance(content, str):
                        directly_parsed.append((
                            msg_id if isinstance(msg_id, str) else None,
                            sha256(content.encode("utf8")),
                            normalize_role(msg.get("role")),
                        ))
        recursive = parse_source_events(payload)
        explicit_id_set = {eid for eid, _, _ in directly_parsed if eid is not None}
        explicit_hash_set = {digest for _, digest, _ in directly_parsed}
        explicit_pair_counts = Counter((eid, digest)
                                       for eid, digest, _ in directly_parsed)
        generic_pair_counts = Counter((eid, digest)
                                      for eid, digest, _ in recursive)
        rank_counts = Counter()
        for row in candidates:
            identity = row["original_target_message_id"]
            expected = row["original_target_sha256"]
            checks = {
                "root_messages_id_hit": identity in explicit_id_set,
                "root_messages_sha_hit": expected in explicit_hash_set,
                "root_messages_id_and_sha_hit":
                    explicit_pair_counts[(identity, expected)] > 0,
                "root_messages_unique_id_and_sha_hit":
                    explicit_pair_counts[(identity, expected)] == 1,
                "recursive_parser_id_and_sha_hit":
                    generic_pair_counts[(identity, expected)] > 0,
            }
            for label, hit in checks.items():
                if hit:
                    rank_counts[label] += 1
        # With no message IDs or body strings in the source, no match can
        # be inferred from positional guesses or partial metadata.
        rank_counts["candidates"] = len(candidates)
        rank_counts["jsonl_root_records"] = source_roots
        rank_counts["root_message_objects"] = source_message_dicts
        rank_counts["root_messages_id_and_string_content"] = sum(
            mid is not None for mid, _, _ in directly_parsed)
        rank_counts["recursive_parser_event_count"] = len(recursive)
        for key in ("candidates", "root_messages_id_hit",
                    "root_messages_sha_hit", "root_messages_id_and_sha_hit",
                    "root_messages_unique_id_and_sha_hit",
                    "recursive_parser_id_and_sha_hit"):
            total[key] += rank_counts[key]
        summaries[str(rank)] = dict(rank_counts)
    return {
        "schema": "storyforge-r51-raw-target-match-diagnostic-v1",
        "status": "RAW_SOURCE_ID_VS_SHA_MATCH_COUNTS_ONLY__NO_ADMISSION",
        "gold108": len(groups) and total["candidates"],
        "summary": dict(total),
        "by_story_rank": summaries,
        "private_values_or_hashes_emitted": False,
        "training_admitted": 0,
        "validation_admitted": 0,
        "raw_history_or_semantic_review_certified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--private-v2", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--probe-schema", action="store_true",
                        help="Only print safe structural field names and types")
    parser.add_argument("--probe-matches", action="store_true",
                        help="Aggregate direct root.messages ID and SHA matching diagnostics")
    args = parser.parse_args()
    os.umask(0o077)
    try:
        repo = args.repo.resolve(strict=True)
        require(not (args.probe_schema and args.probe_matches),
                "CHOOSE_ONE_DIAGNOSTIC")
        require(args.probe_schema or args.probe_matches or
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
        if args.probe_matches:
            require(args.private_v2 is not None and args.output is None,
                    "MATCH_PROBE_REQUIRES_PRIVATE_V2_ONLY")
            receipt = probe_original_target_matching(repo, args.private_v2, raw)
            print(json.dumps(receipt, ensure_ascii=False,
                             sort_keys=True, indent=2))
            return 0
        rows = read_private_v2(args.private_v2, repo)
        receipt = replay_108(rows, raw)
        require(receipt["gold108_target_unique_id_sha_matches"] == 108,
                "GOLD108_TARGET_REPLAY_INCOMPLETE_HOLD")
        for row in rows:
            row["schema"] = "storyforge-r51-private-gold195-triage-v4"
            require(row["training_admission"] == triage.HOLD
                    and row["split"] is None, "R51_TRAIN_APPROVAL_FORBIDDEN")
        triage.write_private(args.output, rows, repo)
    except (OSError, ValueError, KeyError, TypeError, AssertionError,
            UnicodeError, json.JSONDecodeError, zipfile.BadZipFile,
            RuntimeError) as exc:
        # Never print exception values: ZIP member names can contain private text.
        print("R51_RAW_REPLAY_HOLD__" + type(exc).__name__, file=sys.stderr)
        return 2
    print("R51_ORIGINAL_GOLD108_ROOT_MESSAGES_V4_REPLAY_PASS__NO_ADMISSION")
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
