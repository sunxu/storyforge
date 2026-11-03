"""R59 Strict28 historical target/context exposure audit (Owner-local, CPU-only).

Authenticates the frozen Strict28 review intersection and pinned historical
SFT/evaluation sources. Compares target SHA, exact dialogue history, last-12
history, and conservative Chinese character n-gram similarity. Current story
snapshots are validated as current-only metadata and are never treated as
historical prompts. Emits aggregate SAFE plus a private per-case ledger.

No Supabase, R50, network, Hugging Face, GPU, training, or source writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import r57_source_index_export as frozen
import r57_trainer_exact_replay as exact

RECONCILED_SHA256 = "b0356782963dd3c4f85c210bf0f1c69dc01211d818011c16754ea95e9a4fbdb8"
REVIEWER_B_SHA256 = "bdd1980eacf9e21c08fb3e5ada482ea476f35c2018c6120e0f708718eda666e8"
EXCLUSIONS_SHA256 = "9ca99432e08b680cb67b5a1f89d172a337cb91c9bd02af70b68356938c6c04ed"
PACKETS_SHA256 = "ae26a288382939aa79923d4a4c0602b0d575baa63f81c622ab362fbb70d56a5e"
CONTEXT_SHA256 = "e5cfe9aad91dcd96e2d1709c611fa56478ba188d9dacecfde7ded8490089f3cb"
DRAFTS_SHA256 = "3cf5f87a8b65beb7532c722f3510e1e9a6e1aa7166f090d63a2e2e4798233456"
R47_PROMPTS_PATH = "evaluations/v0.1/test/prompts.jsonl"
R47_PROMPTS_GIT_BLOB = "ac301a61d4130369a83dc67ac02aa2d8dda9e82b"
R48_TEST_PATH = "data/compiled/v0.3/test.jsonl"
R48_TEST_SHA256 = "d8eee6db5882d85dce7ffc01256e7c5b9b46e133bdb2cf8591259112b92e980d"
R48_TEST_GIT_BLOB = "c17f225967b6b2f8cbaf3d82fadac1b4031d0654"
EXPECTED_STRICT28 = 28
EXPECTED_PRIORITY72 = 72
EXPECTED_DRAFTS = 13
EXPECTED_EXCLUSIONS = 11
EXPECTED_STRICT_STORY_GROUPS = [13, 15]
EXPECTED_STRICT_SESSION_COUNT = 2
SCORES = {
    "chinese_prose", "character_consistency", "npc_initiative",
    "player_agency", "narrative_continuity", "rule_fidelity",
}
NEAR_JACCARD = 0.72
NEAR_CONTAINMENT = 0.88
NGRAM_SIZE = 3
MIN_NGRAMS = 20
MAX_SOURCE_LINE = 3 * 1024 * 1024


class AuditHold(ValueError):
    """Fail-closed on missing, inconsistent, or unpinned evidence."""


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def private_read(path: Path, expected_sha: str, label: str) -> bytes:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise AuditHold(label + "_PATH_INVALID")
    if any(parent.is_symlink() for parent in path.parents if parent.exists()):
        raise AuditHold(label + "_PARENT_SYMLINK")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600:
        raise AuditHold(label + "_PERMISSIONS_INVALID")
    raw = path.read_bytes()
    if sha(raw) != expected_sha:
        raise AuditHold(label + "_SHA256_MISMATCH")
    return raw


def parse_json(raw: bytes, label: str) -> dict:
    try:
        value = json.loads(raw)
    except (UnicodeError, ValueError) as exc:
        raise AuditHold(label + "_JSON_INVALID") from exc
    if not isinstance(value, dict):
        raise AuditHold(label + "_OBJECT_INVALID")
    return value


def parse_jsonl(raw: bytes, label: str) -> list[dict]:
    rows = []
    try:
        for line in raw.splitlines():
            if not line.strip():
                continue
            if len(line) > MAX_SOURCE_LINE:
                raise AuditHold(label + "_ROW_TOO_LARGE")
            row = json.loads(line)
            if not isinstance(row, dict):
                raise AuditHold(label + "_ROW_INVALID")
            rows.append(row)
    except (UnicodeError, ValueError) as exc:
        if isinstance(exc, AuditHold):
            raise
        raise AuditHold(label + "_JSONL_INVALID") from exc
    return rows


def valid_sha(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def validate_scores(value: object) -> bool:
    return (isinstance(value, dict) and set(value) == SCORES
            and all(type(score) is int and 1 <= score <= 5 for score in value.values()))


def select_strict28(reconciled: dict, reviewer_b: dict, exclusions: list[dict],
                    packets: list[dict]) -> list[dict]:
    if reconciled.get("schema") != "r58_gold192_reviewer_a_results_v3_reconciled_private_v1":
        raise AuditHold("RECONCILED_SCHEMA_INVALID")
    if reviewer_b.get("schema") != "r58_gold192_reviewer_b_results_v1":
        raise AuditHold("REVIEWER_B_SCHEMA_INVALID")
    a_rows, b_rows = reconciled.get("records"), reviewer_b.get("cases")
    if (not isinstance(a_rows, list) or len(a_rows) != 192
            or not isinstance(b_rows, list) or len(b_rows) != 192):
        raise AuditHold("REVIEWER_ROW_COUNT_INVALID")
    if len(exclusions) != EXPECTED_EXCLUSIONS:
        raise AuditHold("EXCLUSION_ROW_COUNT_INVALID")
    if len(packets) != 13:
        raise AuditHold("PACKET_STORY_COUNT_INVALID")

    packet_by_sha = {}
    packet_ids = set()
    story_ids = set()
    for packet in packets:
        story = packet.get("story_uuid")
        if not isinstance(story, str) or not story or story in story_ids:
            raise AuditHold("PACKET_STORY_ID_INVALID")
        story_ids.add(story)
        for case in packet.get("cases", []):
            cid, target = case.get("case_id"), case.get("target_sha256")
            if (not isinstance(cid, str) or not cid or cid in packet_ids
                    or not valid_sha(target) or target in packet_by_sha):
                raise AuditHold("PACKET_CASE_IDENTITY_INVALID")
            packet_ids.add(cid)
            packet_by_sha[target] = {"case_id": cid, "story_uuid": story}
    if len(packet_by_sha) != 192 or len(packet_ids) != 192:
        raise AuditHold("PACKET_CASE_COUNT_INVALID")

    a_by_sha, b_by_sha = {}, {}
    for row in a_rows:
        target = row.get("target_sha256")
        if not valid_sha(target) or target in a_by_sha:
            raise AuditHold("RECONCILED_TARGET_DUPLICATE_OR_INVALID")
        a_by_sha[target] = row
    for row in b_rows:
        target = row.get("target_sha256")
        if not valid_sha(target) or target in b_by_sha:
            raise AuditHold("REVIEWER_B_TARGET_DUPLICATE_OR_INVALID")
        b_by_sha[target] = row
    if set(a_by_sha) != set(packet_by_sha) or set(b_by_sha) != set(packet_by_sha):
        raise AuditHold("REVIEW_TARGET_SET_MISMATCH")

    excluded = set()
    for row in exclusions:
        target = row.get("target_sha256")
        if not valid_sha(target) or target in excluded:
            raise AuditHold("EXCLUSION_TARGET_INVALID")
        if row.get("exclusion_reason") != "EXCLUDED_FROM_TRAINING_DISAGREEMENT":
            raise AuditHold("EXCLUSION_REASON_INVALID")
        excluded.add(target)
    if not excluded <= set(packet_by_sha):
        raise AuditHold("EXCLUSION_OUTSIDE_GOLD192")

    source_pins = reconciled.get("source_pins", {})
    if (source_pins.get("packets") != PACKETS_SHA256
            or source_pins.get("reviewer_b") != REVIEWER_B_SHA256):
        raise AuditHold("RECONCILED_UPSTREAM_PINS_INVALID")

    selected = []
    for target, a in a_by_sha.items():
        b = b_by_sha[target]
        identity = packet_by_sha[target]
        if a.get("case_id") != identity["case_id"]:
            raise AuditHold("RECONCILED_CASE_ID_MISMATCH")
        if (a.get("case_level_scored_review_present") is True
                and a.get("evidence_granularity") == "CASE_LEVEL_SCORED_REVIEW"
                and a.get("reported_final_decision") == "PASS_ONLY"
                and b.get("decision") == "PASS"
                and target not in excluded):
            if not validate_scores(a.get("scores_1_to_5")):
                raise AuditHold("STRICT_A_SCORES_INVALID")
            if not validate_scores(b.get("scores_1_to_5")):
                raise AuditHold("STRICT_B_SCORES_INVALID")
            flags = b.get("severe_flags")
            if flags not in ([], None):
                raise AuditHold("STRICT_B_SEVERE_FLAGS_NOT_EMPTY")
            selected.append({
                "case_id": identity["case_id"], "story_uuid": identity["story_uuid"],
                "target_sha256": target,
            })
    if len(selected) != EXPECTED_STRICT28:
        raise AuditHold("STRICT28_INTERSECTION_COUNT_INVALID")
    if any(row["target_sha256"] in excluded for row in selected):
        raise AuditHold("STRICT28_EXCLUSION_OVERLAP")
    return sorted(selected, key=lambda row: row["case_id"])


def project_history(messages: list[dict], *, allow_system: bool = False) -> list[dict]:
    out = []
    for item in messages:
        if not isinstance(item, dict):
            raise AuditHold("MESSAGE_INVALID")
        role, content = item.get("role"), item.get("content")
        if role == "system" and not allow_system:
            continue
        if role not in {"system", "user", "assistant"} or not isinstance(content, str):
            raise AuditHold("MESSAGE_ROLE_OR_CONTENT_INVALID")
        out.append({"role": role, "content": content})
    return out


def validate_contexts(
    context_rows: list[dict], selected: list[dict], drafts: list[dict]
) -> dict[str, dict]:
    if len(context_rows) != EXPECTED_PRIORITY72:
        raise AuditHold("PRIORITY_CONTEXT_COUNT_INVALID")
    if len(drafts) != EXPECTED_DRAFTS:
        raise AuditHold("STORY_DRAFT_COUNT_INVALID")
    draft_ids = {row.get("story_id") for row in drafts}
    if len(draft_ids) != EXPECTED_DRAFTS or any(not isinstance(x, str) or not x for x in draft_ids):
        raise AuditHold("STORY_DRAFT_IDENTITY_INVALID")
    if any(row.get("source_label") != "CURRENT_V2_DATA_NOT_HISTORICAL" for row in drafts):
        raise AuditHold("STORY_DRAFT_TEMPORAL_SCOPE_INVALID")

    by_id = {}
    for row in context_rows:
        cid = row.get("case_id")
        if not isinstance(cid, str) or not cid or cid in by_id:
            raise AuditHold("CONTEXT_CASE_ID_INVALID")
        target = row.get("target_sha256")
        text = row.get("target_assistant_text")
        if (not valid_sha(target) or not isinstance(text, str)
                or sha(text.encode("utf-8")) != target):
            raise AuditHold("CONTEXT_TARGET_IDENTITY_INVALID")
        history = project_history(row.get("history", []))
        if not history or history[-1]["role"] != "user":
            raise AuditHold("CONTEXT_HISTORY_SUFFIX_INVALID")
        turn = row.get("turn_index")
        if type(turn) is not int or any(
            type(message.get("turn_index")) is not int or message["turn_index"] >= turn
            for message in row.get("history", [])
        ):
            raise AuditHold("CONTEXT_FUTURE_LEAKAGE")
        if (row.get("session_summary_used") is not False
                or row.get("training_admitted") is not False):
            raise AuditHold("CONTEXT_ADMISSION_OR_SUMMARY_FLAG_INVALID")
        if row.get("story_draft_source") != "CURRENT_V2_DATA_NOT_HISTORICAL":
            raise AuditHold("CONTEXT_DRAFT_TEMPORAL_SCOPE_INVALID")
        if row.get("story_id") not in draft_ids:
            raise AuditHold("CONTEXT_STORY_DRAFT_BINDING_INVALID")
        session_id = row.get("session_id")
        if not isinstance(session_id, str) or not session_id:
            raise AuditHold("CONTEXT_SESSION_ID_MISSING")
        by_id[cid] = {
            "case_id": cid, "target_sha256": target,
            "history": history, "story_id": row["story_id"],
            "session_id": session_id, "turn_index": turn,
        }

    strict = {row["case_id"]: row for row in selected}
    if not set(strict) <= set(by_id):
        raise AuditHold("STRICT28_CONTEXT_MISSING")
    for cid, identity in strict.items():
        context = by_id[cid]
        if (context["target_sha256"] != identity["target_sha256"]
                or context["story_id"] != identity["story_uuid"]):
            raise AuditHold("STRICT28_CONTEXT_IDENTITY_MISMATCH")
    selected_contexts = {cid: by_id[cid] for cid in strict}
    story_sizes = sorted(Counter(row["story_id"] for row in selected_contexts.values()).values())
    story_ids = {row["story_id"] for row in selected_contexts.values()}
    session_ids = {row["session_id"] for row in selected_contexts.values()}
    story_session_pairs = {(row["story_id"], row["session_id"])
                           for row in selected_contexts.values()}
    if (story_sizes != EXPECTED_STRICT_STORY_GROUPS
            or len(story_ids) != EXPECTED_STRICT_SESSION_COUNT
            or len(session_ids) != EXPECTED_STRICT_SESSION_COUNT
            or len(story_session_pairs) != EXPECTED_STRICT_SESSION_COUNT):
        raise AuditHold("STRICT28_STORY_SESSION_DISTRIBUTION_INVALID")
    return selected_contexts


def normalize_for_ngrams(messages: list[dict]) -> str:
    raw = "\u241e".join(item["role"] + "\u241f" + item["content"] for item in messages)
    normalized = unicodedata.normalize("NFKC", raw).casefold()
    return "".join(ch for ch in normalized
                   if not ch.isspace() and not unicodedata.category(ch).startswith(("P", "C", "Z")))


def ngrams(value: str, n: int = NGRAM_SIZE) -> set[str]:
    if len(value) < n:
        return set()
    return {value[index:index + n] for index in range(len(value) - n + 1)}


def similarity(left: list[dict], right: list[dict]) -> tuple[float, float]:
    a, b = ngrams(normalize_for_ngrams(left)), ngrams(normalize_for_ngrams(right))
    if min(len(a), len(b)) < MIN_NGRAMS:
        return 0.0, 0.0
    common = len(a & b)
    return common / len(a | b), common / min(len(a), len(b))


def load_historical_source(
    repo: Path, private_root: Path, source_id: str
) -> tuple[bytes, list[dict]]:
    root_tag, relative, expected_rows = frozen.SOURCE_PATHS[source_id]
    root = repo if root_tag == "REPO" else private_root
    raw = frozen._read(root, relative, frozen.MAX_SOURCE_BYTES)
    exact.verify_source_pin(source_id, raw)
    parsed, _ = exact._shape(raw, source_id)
    rows = parse_jsonl(raw, source_id)
    if len(rows) != expected_rows or len(parsed) != expected_rows:
        raise AuditHold(source_id + "_ROW_COUNT_INVALID")
    samples = []
    for index, row in enumerate(rows, start=1):
        messages = frozen._project_messages(row.get("messages"))
        if sha(messages[-1]["content"].encode("utf-8")) != parsed[index - 1]["target"]:
            raise AuditHold(source_id + "_TARGET_REPLAY_MISMATCH")
        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        sample_id = (metadata.get("sample_id") or metadata.get("case_id")
                     or row.get("sample_id") or row.get("id") or f"row-{index:03d}")
        samples.append({
            "source": source_id, "sample_id": str(sample_id),
            "target_sha256": parsed[index - 1]["target"],
            "history": project_history(messages[:-1]),
            "system_sha256": sha(canonical([m for m in messages if m["role"] == "system"])),
        })
    return raw, samples


def load_r47_prompts(repo: Path) -> tuple[bytes, list[dict]]:
    raw = frozen._read(repo, R47_PROMPTS_PATH, frozen.MAX_SOURCE_BYTES)
    if frozen._git_blob(raw) != R47_PROMPTS_GIT_BLOB:
        raise AuditHold("R47_PROMPTS_GIT_BLOB_MISMATCH")
    rows = parse_jsonl(raw, "R47_PROMPTS")
    if len(rows) != 20:
        raise AuditHold("R47_PROMPTS_ROW_COUNT_INVALID")
    samples = []
    for index, row in enumerate(rows, start=1):
        messages = project_history(row.get("messages", []), allow_system=True)
        if not messages or messages[-1]["role"] != "user":
            raise AuditHold("R47_PROMPT_SUFFIX_INVALID")
        samples.append({
            "source": "R47_EVAL_PROMPTS", "sample_id": f"eval-{index - 1:03d}",
            "target_sha256": None,
            "history": project_history(messages),
            "system_sha256": sha(canonical([m for m in messages if m["role"] == "system"])),
        })
    return raw, samples


def load_r48_test(repo: Path) -> tuple[bytes, list[dict]]:
    raw = frozen._read(repo, R48_TEST_PATH, frozen.MAX_SOURCE_BYTES)
    if sha(raw) != R48_TEST_SHA256 or frozen._git_blob(raw) != R48_TEST_GIT_BLOB:
        raise AuditHold("R48_TEST_SOURCE_PIN_MISMATCH")
    rows = parse_jsonl(raw, "R48_TEST")
    if len(rows) != 20:
        raise AuditHold("R48_TEST_ROW_COUNT_INVALID")
    samples = []
    for index, row in enumerate(rows, start=1):
        messages = frozen._project_messages(row.get("messages"))
        samples.append({
            "source": "R48_TEST_V03", "sample_id": f"test-{index - 1:03d}",
            "target_sha256": sha(messages[-1]["content"].encode("utf-8")),
            "history": project_history(messages[:-1]),
            "system_sha256": sha(canonical([m for m in messages if m["role"] == "system"])),
        })
    if len({row["target_sha256"] for row in samples}) != 20:
        raise AuditHold("R48_TEST_TARGET_DUPLICATE")
    return raw, samples


def compare_one(current: dict, historical: list[dict]) -> dict:
    current_history = current["history"]
    current_suffix = current_history[-12:]
    current_full_sha = sha(canonical(current_history))
    current_suffix_sha = sha(canonical(current_suffix))
    full_exact = []
    suffix_exact = []
    best_full = (0.0, 0.0, None)
    best_suffix = (0.0, 0.0, None)
    for sample in historical:
        history = sample["history"]
        full_match = current_full_sha == sha(canonical(history))
        suffix_match = current_suffix_sha == sha(canonical(history[-12:]))
        if full_match:
            full_exact.append(sample)
        if suffix_match:
            suffix_exact.append(sample)
        full_jaccard, full_containment = similarity(current_history, history)
        suffix_jaccard, suffix_containment = similarity(current_suffix, history[-12:])
        if (full_jaccard, full_containment) > best_full[:2]:
            best_full = (full_jaccard, full_containment, sample["sample_id"])
        if (suffix_jaccard, suffix_containment) > best_suffix[:2]:
            best_suffix = (suffix_jaccard, suffix_containment, sample["sample_id"])
    near = any((jaccard >= NEAR_JACCARD or containment >= NEAR_CONTAINMENT)
               for jaccard, containment, _ in (best_full, best_suffix))
    return {
        "history_exact": bool(full_exact),
        "history_exact_match_count": len(full_exact),
        "history_exact_sample_ids": [sample["sample_id"] for sample in full_exact],
        "last12_exact": bool(suffix_exact),
        "last12_exact_match_count": len(suffix_exact),
        "last12_exact_sample_ids": [sample["sample_id"] for sample in suffix_exact],
        "near_candidate": near,
        "best_full_jaccard": round(best_full[0], 6),
        "best_full_containment": round(best_full[1], 6),
        "best_full_sample_id": best_full[2],
        "best_last12_jaccard": round(best_suffix[0], 6),
        "best_last12_containment": round(best_suffix[1], 6),
        "best_last12_sample_id": best_suffix[2],
    }


def write_create_only(path: Path, payload: bytes) -> str:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(payload)
            out.flush()
            os.fsync(out.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return sha(payload)


def run(repo_root: Path, r57_private_root: Path, reconciled_path: Path,
        reviewer_b_path: Path, exclusions_path: Path, packets_path: Path,
        context_path: Path, drafts_path: Path, output_dir: Path) -> dict:
    if r57_private_root.is_symlink() or any(
        parent.is_symlink() for parent in r57_private_root.parents if parent.exists()
    ):
        raise AuditHold("R57_PRIVATE_ROOT_SYMLINK")
    repo = repo_root.resolve(strict=True)
    private_root = r57_private_root.resolve(strict=True)
    if repo in private_root.parents or private_root in repo.parents:
        raise AuditHold("PRIVATE_ROOT_REPOSITORY_OVERLAP")
    if stat.S_IMODE(private_root.stat().st_mode) != 0o700:
        raise AuditHold("R57_PRIVATE_ROOT_PERMISSIONS_INVALID")

    reconciled_raw = private_read(reconciled_path, RECONCILED_SHA256, "RECONCILED")
    reviewer_b_raw = private_read(reviewer_b_path, REVIEWER_B_SHA256, "REVIEWER_B")
    exclusions_raw = private_read(exclusions_path, EXCLUSIONS_SHA256, "EXCLUSIONS")
    reconciled = parse_json(reconciled_raw, "RECONCILED")
    reviewer_b = parse_json(reviewer_b_raw, "REVIEWER_B")
    exclusions = parse_jsonl(exclusions_raw, "EXCLUSIONS")
    packets = parse_jsonl(private_read(packets_path, PACKETS_SHA256, "PACKETS"), "PACKETS")
    contexts = parse_jsonl(private_read(context_path, CONTEXT_SHA256, "CONTEXT"), "CONTEXT")
    drafts = parse_jsonl(private_read(drafts_path, DRAFTS_SHA256, "DRAFTS"), "DRAFTS")
    selected = select_strict28(reconciled, reviewer_b, exclusions, packets)
    current = validate_contexts(contexts, selected, drafts)

    source_samples = {}
    source_pins = {}
    for source_id in exact.SOURCE_IDS:
        raw, samples = load_historical_source(repo, private_root, source_id)
        source_samples[source_id] = samples
        source_pins[source_id] = sha(raw)

    # Reproduce the known Gold195 66/24/9 exposure baseline from the same
    # byte-pinned source collections; do not infer it from aggregate history.
    gold_targets = ({x["target_sha256"] for x in source_samples["GOLD87"]}
                    | {x["target_sha256"] for x in source_samples["GOLD108"]})
    train_targets = {x["target_sha256"] for name in ("V01_TRAIN", "R46_TRAIN", "R54_TRAIN")
                     for x in source_samples[name]}
    val_targets = {
        x["target_sha256"]
        for name in ("V01_VALIDATION", "R46_VALIDATION", "R54_VALIDATION")
        for x in source_samples[name]
    }
    gold_train = len(gold_targets & train_targets)
    gold_val = len(gold_targets & val_targets)
    gold_both = len(gold_targets & train_targets & val_targets)
    if (len(gold_targets) != 195 or gold_train != 66 or gold_val != 24 or gold_both != 9
            or len((gold_targets & train_targets) | (gold_targets & val_targets)) != 81):
        raise AuditHold("GOLD195_BASELINE_66_24_9_81_MISMATCH")

    r47_raw, r47_samples = load_r47_prompts(repo)
    r48_raw, r48_samples = load_r48_test(repo)
    source_samples["R47_EVAL_PROMPTS"] = r47_samples
    source_samples["R48_TEST_V03"] = r48_samples
    source_pins["R47_EVAL_PROMPTS_GIT_BLOB"] = frozen._git_blob(r47_raw)
    source_pins["R48_TEST_V03_SHA256"] = sha(r48_raw)
    source_pins["R48_TEST_V03_GIT_BLOB"] = frozen._git_blob(r48_raw)

    ledger = []
    source_counts = {name: Counter() for name in source_samples}
    split_aggregate = {
        split: Counter() for split in ("TRAIN", "VALIDATION", "TEST", "GOLD_REFERENCE")
    }
    source_split = {
        "GOLD87": "GOLD_REFERENCE", "GOLD108": "GOLD_REFERENCE",
        "V01_TRAIN": "TRAIN", "R46_TRAIN": "TRAIN", "R54_TRAIN": "TRAIN",
        "V01_VALIDATION": "VALIDATION", "R46_VALIDATION": "VALIDATION",
        "R54_VALIDATION": "VALIDATION", "R47_EVAL_PROMPTS": "TEST",
        "R48_TEST_V03": "TEST",
    }
    for identity in selected:
        cid = identity["case_id"]
        cur = current[cid]
        split_flags = {split: {
            "target_exact": False, "history_exact": False,
            "last12_exact": False, "near_context": False,
        } for split in split_aggregate}
        row = {
            **identity,
            "current_session_id": cur["session_id"],
            "current_story_id": cur["story_id"],
            "current_history_sha256_without_system": sha(canonical(cur["history"])),
            "current_last12_history_sha256_without_system": sha(canonical(cur["history"][-12:])),
            "target_exposure": {}, "context_exposure": {},
        }
        for source_name, samples in source_samples.items():
            target_hits = [sample for sample in samples
                           if sample["target_sha256"] is not None
                           and sample["target_sha256"] == identity["target_sha256"]]
            context_match = compare_one(cur, samples)
            row["target_exposure"][source_name] = {
                "exact_target_match": bool(target_hits),
                "match_count": len(target_hits),
                "matched_sample_ids": [sample["sample_id"] for sample in target_hits],
            }
            row["context_exposure"][source_name] = context_match
            source_counts[source_name]["cases_with_exact_target"] += bool(target_hits)
            source_counts[source_name]["cases_with_exact_history"] += context_match["history_exact"]
            source_counts[source_name]["cases_with_exact_last12"] += context_match["last12_exact"]
            source_counts[source_name]["cases_with_near_context_candidate"] += (
                context_match["near_candidate"]
            )
            source_counts[source_name]["exact_target_matches_total"] += len(target_hits)
            split = source_split[source_name]
            split_flags[split]["target_exact"] |= bool(target_hits)
            split_flags[split]["history_exact"] |= context_match["history_exact"]
            split_flags[split]["last12_exact"] |= context_match["last12_exact"]
            split_flags[split]["near_context"] |= context_match["near_candidate"]
        row["exposure_by_split"] = split_flags
        for split, flags in split_flags.items():
            split_aggregate[split]["target_exact_cases"] += flags["target_exact"]
            split_aggregate[split]["history_exact_cases"] += flags["history_exact"]
            split_aggregate[split]["last12_exact_cases"] += flags["last12_exact"]
            split_aggregate[split]["near_context_candidate_cases"] += flags["near_context"]
        ledger.append(row)

    if len(ledger) != EXPECTED_STRICT28:
        raise AuditHold("STRICT28_LEDGER_COUNT_INVALID")
    if output_dir.exists() or output_dir.is_symlink():
        raise AuditHold("OUTPUT_ALREADY_EXISTS")
    if (not output_dir.parent.is_dir() or output_dir.parent.is_symlink()
            or stat.S_IMODE(output_dir.parent.stat().st_mode) != 0o700):
        raise AuditHold("OUTPUT_PARENT_PERMISSIONS_INVALID")
    output_dir.mkdir(mode=0o700, parents=False)
    if stat.S_IMODE(output_dir.stat().st_mode) != 0o700:
        raise AuditHold("OUTPUT_PERMISSIONS_INVALID")

    private_payload = b"".join(canonical(row) + b"\n" for row in ledger)
    private_sha = write_create_only(
        output_dir / "R59_STRICT28_HISTORICAL_EXPOSURE_PRIVATE.jsonl", private_payload)
    safe = {
        "schema": "r59_strict28_historical_exposure_safe_v1",
        "status": "STRICT28_HISTORICAL_TARGET_AND_CONTEXT_EXPOSURE_CLASSIFIED__NO_ADMISSION",
        "strict28_cases": len(ledger),
        "strict28_contexts_verified": len(current),
        "review_intersection_verified": True,
        "strict28_exclusions_overlap": 0,
        "priority72_context_rows_verified": len(contexts),
        "current_story_drafts_verified": len(drafts),
        "current_story_drafts_used_as_historical_context": False,
        "session_summaries_used": False,
        "historical_sources_byte_pinned": True,
        "historical_source_row_counts": {name: len(rows) for name, rows in source_samples.items()},
        "historical_source_sha256": source_pins,
        "gold195_baseline_reproduced": {
            "unique_targets": len(gold_targets), "ever_train": gold_train,
            "ever_validation": gold_val, "both_train_and_validation": gold_both,
            "train_or_validation_union": 81,
        },
        "per_source_case_counts": {name: dict(counts) for name, counts in source_counts.items()},
        "strict28_exposure_by_split": {
            split: dict(counts) for split, counts in split_aggregate.items()
        },
        "near_match_method": {
            "normalization": (
                "Unicode NFKC + casefold + remove whitespace/punctuation/control/separators"
            ),
            "feature": "unique character 3-gram set Jaccard and containment",
            "candidate_threshold": {
                "jaccard_gte": NEAR_JACCARD, "containment_gte": NEAR_CONTAINMENT,
            },
            "minimum_ngrams_per_side": MIN_NGRAMS,
            "interpretation": "triage_only_not_semantic_equivalence_or_exposure_proof",
        },
        "system_prompt_equivalence_proven": False,
        "test_scope": ["R47_EVAL_PROMPTS", "R48_TEST_V03"],
        "test_context_scope_complete": False,
        "private_ledger": {
            "records": len(ledger), "sha256": private_sha,
            "file": "R59_STRICT28_HISTORICAL_EXPOSURE_PRIVATE.jsonl",
        },
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }
    safe_raw = (json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    safe_sha = write_create_only(
        output_dir / "R59_STRICT28_HISTORICAL_EXPOSURE_SAFE.json", safe_raw)
    safe["safe_sha256"] = safe_sha
    return safe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--r57-private-root", required=True, type=Path)
    parser.add_argument("--reconciled", required=True, type=Path)
    parser.add_argument("--reviewer-b", required=True, type=Path)
    parser.add_argument("--exclusions", required=True, type=Path)
    parser.add_argument("--packets", required=True, type=Path)
    parser.add_argument("--context", required=True, type=Path)
    parser.add_argument("--drafts", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = run(args.repo_root, args.r57_private_root, args.reconciled,
                     args.reviewer_b, args.exclusions, args.packets,
                     args.context, args.drafts, args.output_dir)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - never echo private values
        reason = (str(exc) if isinstance(exc, (AuditHold, ValueError))
                  and re.fullmatch(r"[A-Z0-9_]+", str(exc)) else type(exc).__name__)
        print(json.dumps({
            "schema": "r59_strict28_historical_exposure_safe_v1",
            "status": "STRICT28_HISTORICAL_EXPOSURE_HOLD",
            "reason_code": reason,
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "r50_accessed": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
