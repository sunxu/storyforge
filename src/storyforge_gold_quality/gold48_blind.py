"""Gold48 48x5 blind packet: reuse frozen Owner sources, no API/model calls.

The reviewer receives only randomly ordered (blind_id, visible messages, reply).
All case/source/Story/Session/risk/finish metadata stays in Owner-only 0600 key.
The caller must supply existing audited files; this module does NOT recover data,
re-run inference, or authorize third-party disclosure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import stat
from collections import Counter
from pathlib import Path

from storyforge_dataset.generation_eval.gold48_contract_bridge import (
    INPUT_SCHEMA,
    MODEL,
    REVISION,
    ROLES,
    _read_existing_gold48_output,
)
from storyforge_dataset.generation_eval.worker import _validate_records
from storyforge_dataset.hf_runtime.inputs import InputManager

from .hf_blind_stage import private_folder, write_once
from .hf_literary_review import canonical

PACK_SCHEMA = "storyforge_r60_gold48_blind_item_v1"
OWNER_SCHEMA = "storyforge_r60_gold48_blind_owner_key_v1"
SUMMARY_SCHEMA = "storyforge_r60_gold48_blind_prep_safe_v1"
ORIGINAL_SCHEMA = "storyforge_r60_gold48_recovered_references_private_v1"
FROZEN_SCHEMA = "storyforge_r60_gold48_owner_scoped_freeze_private_v1"
LOCATOR_SCHEMA = "storyforge_r60_gold48_recovered_locators_private_v1"
LENGTH_COUNTS = {"base": 1, "r46_v02": 2, "r54_v03a": 1, "r60_base336": 3}


class Gold48BlindHold(ValueError):
    """No private values are included in error messages."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise Gold48BlindHold(code)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def private_input(path: Path, limit: int = 16 * 1024 * 1024) -> bytes:
    require(path.is_absolute() and not path.is_symlink(), "PRIVATE_PATH_HOLD")
    try:
        st = path.lstat()
        require(stat.S_ISREG(st.st_mode) and stat.S_IMODE(st.st_mode) == 0o600
                and st.st_nlink == 1, "PRIVATE_MODE_HOLD")
        return InputManager.open_verified(path, max_bytes=limit).read_bytes()
    except (OSError, ValueError) as exc:
        if isinstance(exc, Gold48BlindHold):
            raise
        raise Gold48BlindHold("PRIVATE_READ_HOLD") from None


def private_json(path: Path, limit: int = 16 * 1024 * 1024) -> dict:
    try:
        obj = json.loads(private_input(path, limit=limit))
        require(type(obj) is dict, "PRIVATE_JSON_HOLD")
        return obj
    except (ValueError, TypeError):
        raise Gold48BlindHold("PRIVATE_JSON_HOLD") from None


def load_inputs(input_path: Path, manifest_path: Path, freeze: dict) -> list[dict]:
    manifest = private_json(manifest_path, 2 * 1024 * 1024)
    require(manifest.get("schema") == INPUT_SCHEMA
            and manifest.get("record_count") == 48
            and manifest.get("seed") == 42
            and len(manifest.get("cases", [])) == 48,
            "FROZEN_INPUT_MANIFEST_HOLD")
    raw = private_input(input_path)
    require(sha(raw) == manifest.get("sha256"), "FROZEN_INPUT_SHA_HOLD")
    try:
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
        _validate_records(rows, 48)
    except (ValueError, TypeError):
        raise Gold48BlindHold("FROZEN_INPUT_ROWS_HOLD") from None
    for index, (row, desc, case) in enumerate(
        zip(rows, manifest["cases"], freeze["cases_PRIVATE"], strict=True), 1
    ):
        case_id = f"G48-C{index:02d}"
        require(row["sample_id"] == case_id
                and desc == {"sample_id": case_id,
                             "messages_sha256":
                             case["reconstructed_messages_sha256_PRIVATE"]}
                and sha(canonical(row["messages"])) == desc["messages_sha256"],
                "FROZEN_INPUT_CASE_SHA_HOLD")
    return rows


def load_outputs(paths: dict[str, Path], input_sha: str) -> dict[str, list[dict]]:
    all_outputs = {}
    for role in ROLES:
        path = paths[role]
        require(path.name == role + ".private.json", "GENERATION_FILE_NAME_HOLD")
        result_manifest = private_json(
            path.with_name(role + ".private.json.result-sha256-manifest.private.json"),
            8192,
        )
        require(result_manifest.get("schema") ==
                "storyforge_r60_gold48_private_result_delivery_v1"
                and result_manifest.get("model_role") == role
                and result_manifest.get("record_count") == 48
                and isinstance(result_manifest.get("files"), list)
                and len(result_manifest["files"]) == 3,
                "GENERATION_DELIVERY_MANIFEST_HOLD")
        first = result_manifest["files"][0]
        receipt = _read_existing_gold48_output(
            output_path=path,
            profile={"model_profiles": {role: {"model": MODEL, "revision": REVISION}}},
            worker_manifest={"max_input_tokens": 30720, "max_new_tokens": 2048},
            model_role=role, gpu_started=False,
        )
        require(first.get("name") == path.name
                and first.get("sha256") == receipt.output_sha256,
                "GENERATION_DELIVERY_SHA_HOLD")
        identity = private_json(path.with_name(role + ".private.json.identity.private.json"), 65536)
        require(identity.get("input_sha256") == input_sha
                and identity.get("selected_model_role") == role
                and identity.get("output_sha256") == receipt.output_sha256,
                "GENERATION_INPUT_IDENTITY_HOLD")
        obj = private_json(path)
        outputs = obj["outputs"]
        require(sum(x["finish_reason"] == "length" for x in outputs) ==
                LENGTH_COUNTS[role], "FROZEN_LENGTH_COUNT_HOLD")
        require(all(isinstance(x["text"], str) and x["text"].strip()
                    for x in outputs), "EMPTY_GENERATION_HOLD")
        all_outputs[role] = outputs
    return all_outputs


def prepare(
    *, freeze_path: Path, input_path: Path, input_manifest_path: Path,
    original_path: Path, locator_path: Path, generated: dict[str, Path],
    output_dir: Path,
) -> dict:
    """Produce one new Owner-private pack; never contact a provider."""
    require(set(generated) == set(ROLES), "FOUR_GENERATION_PATHS_HOLD")
    freeze = private_json(freeze_path, 2 * 1024 * 1024)
    require(freeze.get("schema") == FROZEN_SCHEMA
            and freeze.get("owner_gold48_freeze") is True
            and freeze.get("input_contract") == "RECONSTRUCTED_EVALUATION_INPUT"
            and freeze.get("main_analysis_count") == 48
            and freeze.get("sensitivity_analysis_count") == 42
            and freeze.get("session_count") == 25
            and isinstance(freeze.get("cases_PRIVATE"), list)
            and len(freeze["cases_PRIVATE"]) == 48,
            "OWNER_FROZEN_SCOPE_HOLD")
    rows = load_inputs(input_path, input_manifest_path, freeze)
    original = private_json(original_path)
    locators = private_json(locator_path)
    require(original.get("schema") == ORIGINAL_SCHEMA
            and locators.get("schema") == LOCATOR_SCHEMA
            and len(original.get("cases_PRIVATE", [])) == 48
            and len(locators.get("cases_PRIVATE", [])) == 48,
            "ORIGINAL_LOCATOR_SCOPE_HOLD")
    input_sha = sha(private_input(input_path))
    outputs = load_outputs(generated, input_sha)
    reviewer_items, bindings = [], []
    groups, excluded, sessions = Counter(), Counter(), set()
    seen_source_stories: dict[str, str] = {}
    seen_labels = set()
    rng = secrets.SystemRandom()
    for i, (row, case, orig, loc) in enumerate(zip(
        rows, freeze["cases_PRIVATE"], original["cases_PRIVATE"],
        locators["cases_PRIVATE"], strict=True
    )):
        case_id = f"G48-C{i + 1:02d}"
        group = case.get("anonymous_group_PRIVATE")
        source_story = loc.get("story_id_PRIVATE")
        session = loc.get("session_id_PRIVATE")
        flag = case.get("exclude_from_42_sensitivity")
        require(case.get("candidate_case_id_PRIVATE") == case_id
                and orig.get("candidate_case_id_PRIVATE") == case_id
                and loc.get("candidate_case_id_PRIVATE") == case_id
                and isinstance(group, str) and group.startswith("ANON-GROUP-")
                and isinstance(source_story, str) and bool(source_story)
                and isinstance(session, str) and bool(session)
                and type(flag) is bool
                and loc.get("exclude_from_42_sensitivity") is flag,
                "OWNER_CASE_ALIGNMENT_HOLD")
        prev = seen_source_stories.setdefault(source_story, group)
        require(prev == group, "OWNER_STORY_GROUP_ALIGNMENT_HOLD")
        groups[group] += 1
        excluded[group] += int(flag)
        sessions.add(session)
        reply = orig.get("original_reply_PRIVATE")
        require(isinstance(reply, str) and bool(reply.strip())
                and sha(reply.encode("utf-8")) ==
                case.get("original_reference_sha256_PRIVATE")
                and sha(reply.encode("utf-8")) ==
                orig.get("original_reply_sha256_PRIVATE"),
                "ORIGINAL_FROZEN_REPLY_HOLD")
        source_text = {role: outputs[role][i]["text"] for role in ROLES}
        source_text["original"] = reply
        order = list(source_text)
        rng.shuffle(order)
        for role in order:
            blind_id = secrets.token_hex(16)
            require(blind_id not in seen_labels, "BLIND_ID_COLLISION_HOLD")
            seen_labels.add(blind_id)
            text = source_text[role]
            reviewer_items.append({
                "schema": PACK_SCHEMA, "blind_id": blind_id,
                "visible_messages": row["messages"], "target_text": text,
            })
            bindings.append({
                "blind_id": blind_id, "candidate_case_id_PRIVATE": case_id,
                "source_role_PRIVATE": role, "anonymous_group_PRIVATE": group,
                "session_id_PRIVATE": session, "exclude_from_42_sensitivity": flag,
                "target_sha256_PRIVATE": sha(text.encode("utf-8")),
                "finish_reason_PRIVATE": (
                    None if role == "original" else outputs[role][i]["finish_reason"]
                ),
            })
    require(len(groups) == 8 and set(groups.values()) == {6}
            and len(seen_source_stories) == 8 and len(sessions) == 25
            and sorted(excluded.values()) == [0] * 7 + [6]
            and len(reviewer_items) == len(bindings) == 240,
            "GOLD48_48_42_CLUSTER_SCOPE_HOLD")
    # Hide case order as well as source assignment; key stays Owner-only.
    order = list(range(240))
    rng.shuffle(order)
    reviewer_items = [reviewer_items[i] for i in order]
    bindings = [bindings[i] for i in order]
    pack = b"".join(canonical(x) + b"\n" for x in reviewer_items)
    key = canonical({
        "schema": OWNER_SCHEMA, "input_contract": "RECONSTRUCTED_EVALUATION_INPUT",
        "reviewer_packet_sha256": sha(pack), "bindings": bindings,
        "answer_sources": list(ROLES) + ["original"],
        "historical_original_description_only": True,
        "quality_v1_admitted": 0,
    }) + b"\n"
    require(len(pack) <= 64 * 1024 * 1024 and len(key) <= 64 * 1024 * 1024,
            "BLIND_PACKET_SIZE_HOLD")
    require(output_dir.is_absolute() and not output_dir.exists()
            and not output_dir.is_symlink(), "PRIVATE_OUTPUT_EXISTS_HOLD")
    private_folder(output_dir.parent)
    output_dir.mkdir(mode=0o700, exist_ok=False)
    (output_dir / "reviewers").mkdir(mode=0o700)
    (output_dir / "owner").mkdir(mode=0o700)
    write_once(output_dir / "reviewers" / "GOLD48_BLIND_240_PRIVATE.jsonl", pack)
    write_once(output_dir / "owner" / "GOLD48_COORDINATOR_KEY_PRIVATE.json", key)
    safe = {
        "schema": SUMMARY_SCHEMA,
        "status": "GOLD48_240_BLIND_OBJECTS_PREPARED__NO_JUDGE_CALLS",
        "cases": 48, "answers": 240, "sources": 5, "stories": 8,
        "sessions": 25, "main_cases": 48, "sensitivity_cases": 42,
        "length_answers_retained": 7, "judge_scores_completed": 0,
        "api_calls": 0, "cost_usd": 0, "private_values_emitted": False,
        "owner_mapping_uploaded": False, "model_promoted": False,
        "quality_v1_admitted": 0,
    }
    write_once(output_dir / "GOLD48_PREP_SAFE.json", canonical(safe) + b"\n")
    return safe


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for opt in ("freeze", "input", "input-manifest", "original", "locators",
                "base", "r46-v02", "r54-v03a", "r60-base336", "out"):
        parser.add_argument("--" + opt, required=True, type=Path)
    args = parser.parse_args()
    try:
        safe = prepare(
            freeze_path=args.freeze, input_path=args.input,
            input_manifest_path=args.input_manifest,
            original_path=args.original, locator_path=args.locators,
            generated={k: getattr(args, k.replace("-", "_")) for k in ROLES},
            output_dir=args.out,
        )
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True))
    except (Gold48BlindHold, ValueError, OSError) as exc:
        code = str(exc) if isinstance(exc, Gold48BlindHold) else "DATA_CONTRACT_HOLD"
        print(json.dumps({"status": "GOLD48_BLIND_PREP_HOLD", "reason": code,
                          "private_values_emitted": False}))
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
