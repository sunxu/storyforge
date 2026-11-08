"""Reusable private HF two-slot blind staging and read-only quality reconciliation.

Business-specific adapters provide source-validated (case_key, history, target)
rows and a frozen pool SHA. This module never reads a source DB or submits a Job.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat

from . import hf_literary_review as reviewer

SCHEMA = "storyforge_hf_quality_dual_stage_private_v1"
MAP_NAME = "owner_crosswalk.private.json"
MANIFEST_NAME = "stage_manifest.private.json"
SAFE_SCHEMA = "storyforge_hf_quality_dual_safe_v1"
MAX_STAGE_ROWS = 1000
MAX_STAGE_BYTES = 64 * 1024 * 1024


class StageError(ValueError):
    pass


def safe_bytes(value: object) -> bytes:
    return reviewer.canonical(value) + b"\n"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def private_folder(path: Path) -> None:
    if (not path.is_absolute() or path.is_symlink() or not path.is_dir()
            or stat.S_IMODE(path.stat().st_mode) != 0o700):
        raise StageError("PRIVATE_STAGE_FOLDER_HOLD")


def private_read(path: Path, limit: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise StageError("PRIVATE_STAGE_INPUT_HOLD")
    st = path.stat()
    if (not stat.S_ISREG(st.st_mode) or stat.S_IMODE(st.st_mode) != 0o600
            or st.st_nlink != 1 or not 0 < st.st_size <= limit):
        raise StageError("PRIVATE_STAGE_INPUT_HOLD")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as src:
        return src.read(limit + 1)


def write_once(path: Path, payload: bytes) -> None:
    if not payload or len(payload) > MAX_STAGE_BYTES:
        raise StageError("PRIVATE_STAGE_OUTPUT_SIZE_HOLD")
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as dest:
        dest.write(payload)
        dest.flush()
        os.fsync(dest.fileno())


def stage(root: Path, cases: list[dict], pool_hash: str, runner: Path,
          model_a: str, revision_a: str, model_b: str, revision_b: str) -> dict:
    """Create isolated A/B inputs; owner mapping never enters either HF input."""
    if (not root.is_absolute() or root.exists() or root.is_symlink()
            or not root.parent.is_dir()):
        raise StageError("PRIVATE_STAGE_OUTPUT_EXISTS_HOLD")
    private_folder(root.parent)
    if (not isinstance(pool_hash, str) or len(pool_hash) != 64
            or not 1 <= len(cases) <= MAX_STAGE_ROWS):
        raise StageError("FROZEN_SOURCE_CONTRACT_HOLD")
    if (not isinstance(model_a, str) or not isinstance(model_b, str)
            or not model_a.strip() or not model_b.strip()
            or model_a.casefold() == model_b.casefold()
            or reviewer.HEX40.fullmatch(revision_a) is None
            or reviewer.HEX40.fullmatch(revision_b) is None):
        raise StageError("MODEL_REVISION_CONTRACT_HOLD")
    if runner.is_symlink() or not runner.is_file():
        raise StageError("REVIEWER_RUNNER_NOT_FOUND")
    code = runner.read_bytes()
    if not code or len(code) > 100_000:
        raise StageError("REVIEWER_RUNNER_SIZE_HOLD")
    # Stable per-case input row, no Source Story/Session/Message/Owner IDs.
    ids = [item.get("case_key") for item in cases]
    if (len(set(ids)) != len(ids)
            or any(not isinstance(x, str) or not x for x in ids)):
        raise StageError("SOURCE_CASE_DUPLICATE_HOLD")
    rows_by_slot = {}
    crosswalk = {}
    model_pins = {"A": [model_a, revision_a], "B": [model_b, revision_b]}
    for slot in ("A", "B"):
        rows = []
        bindings = []
        for n, case in enumerate(cases):
            msg = case.get("history_messages")
            target = case.get("target_text")
            if (not isinstance(msg, list) or not isinstance(target, str)
                    or case.get("target_semantics") !=
                    "DB_FINAL_PERSISTED_ASSISTANT"):
                raise StageError("SOURCE_CASE_SHAPE_HOLD")
            blind = {
                "schema": reviewer.SCHEMA,
                "blind_id": secrets.token_hex(16),
                "visible_history": [
                    {"role": x.get("role"), "content": x.get("content")}
                    for x in msg
                ],
                "target_text": target,
                "target_semantics": "DB_FINAL_PERSISTED_ASSISTANT",
                "policy": reviewer.POLICY,
            }
            reviewer.validate_input(blind)
            rows.append(blind)
            bindings.append({
                "source_index": n, "case_key": case["case_key"],
                "blind_id": blind["blind_id"],
                "target_sha256": case["assistant_target_sha256"],
                "history_sha256": case["history_messages_sha256"],
            })
        order = list(range(len(rows)))
        secrets.SystemRandom().shuffle(order)
        rows_by_slot[slot] = [rows[i] for i in order]
        crosswalk[slot] = [bindings[i] for i in order]
    root.mkdir(mode=0o700)
    for slot in ("A", "B"):
        inp = root / f"input_{slot}"
        out = root / f"output_{slot}"
        inp.mkdir(mode=0o700)
        out.mkdir(mode=0o700)
        payload = b"".join(safe_bytes(row) for row in rows_by_slot[slot])
        write_once(inp / "source.private.jsonl", payload)
        write_once(inp / "runner.py", code)
    owner = root / "owner"
    owner.mkdir(mode=0o700)
    write_once(owner / MAP_NAME, safe_bytes({
        "schema": SCHEMA, "pool_sha256": pool_hash,
        "count": len(cases), "bindings": crosswalk,
    }))
    manifest = {
        "schema": SCHEMA, "pool_sha256": pool_hash,
        "count": len(cases), "model_pins": model_pins,
        "runner_sha256": sha_bytes(code),
        "source_sha256": {
            slot: sha_bytes((root / f"input_{slot}" /
                            "source.private.jsonl").read_bytes())
            for slot in ("A", "B")
        },
    }
    manifest["receipt_sha256"] = reviewer.digest(manifest)
    write_once(owner / MANIFEST_NAME, safe_bytes(manifest))
    return {
        "schema": SAFE_SCHEMA, "status": "HF_QUALITY_BLIND_STAGE_READY__NOT_SUBMITTED",
        "cases_staged": len(cases), "reviewer_slots": 2,
        "owner_crosswalk_uploaded": False, "paid_gpu_submitted": False,
        "quality_v1_admitted": 0, "training_authorized": False,
        "r50_body_accessed": False, "private_values_emitted": False,
    }


def verified_stage(root: Path, pool_hash: str, cases: list[dict]) -> tuple[dict, dict]:
    private_folder(root)
    owner = root / "owner"
    private_folder(owner)
    try:
        manifest = json.loads(private_read(owner / MANIFEST_NAME, 20_000))
        crosswalk = json.loads(private_read(owner / MAP_NAME, 512_000))
    except (ValueError, TypeError) as exc:
        raise StageError("STAGE_OWNER_JSON_HOLD") from exc
    if not isinstance(manifest, dict) or not isinstance(crosswalk, dict):
        raise StageError("STAGE_OWNER_SCHEMA_HOLD")
    signed = {k: v for k, v in manifest.items() if k != "receipt_sha256"}
    if (set(manifest) != {
            "schema", "pool_sha256", "count", "model_pins", "runner_sha256",
            "source_sha256", "receipt_sha256",
        } or manifest["receipt_sha256"] != reviewer.digest(signed)
            or manifest["schema"] != SCHEMA or crosswalk.get("schema") != SCHEMA
            or manifest["pool_sha256"] != pool_hash
            or crosswalk.get("pool_sha256") != pool_hash
            or manifest["count"] != len(cases)
            or crosswalk.get("count") != len(cases)):
        raise StageError("STAGE_OWNER_SOURCE_HOLD")
    if set(manifest["model_pins"]) != {"A", "B"}:
        raise StageError("STAGE_MODEL_PINS_HOLD")
    if set(crosswalk.get("bindings", {})) != {"A", "B"}:
        raise StageError("STAGE_CROSSWALK_HOLD")
    for slot in ("A", "B"):
        inp = root / f"input_{slot}"
        out = root / f"output_{slot}"
        private_folder(inp)
        private_folder(out)
        src = private_read(inp / "source.private.jsonl", MAX_STAGE_BYTES)
        code = private_read(inp / "runner.py", 100_000)
        if (sha_bytes(src) != manifest["source_sha256"][slot]
                or sha_bytes(code) != manifest["runner_sha256"]):
            raise StageError("STAGE_BYTES_CHANGED_HOLD")
        try:
            rows = reviewer.read_input(inp / "source.private.jsonl")
        except reviewer.ReviewError as exc:
            raise StageError("STAGE_BLIND_SOURCE_HOLD") from exc
        bindings = crosswalk["bindings"][slot]
        if not isinstance(bindings, list) or len(rows) != len(cases):
            raise StageError("STAGE_ROW_COUNT_HOLD")
        seen = set()
        for pos, (row, bind) in enumerate(zip(rows, bindings, strict=True)):
            if (not isinstance(bind, dict)
                    or bind.get("blind_id") != row["blind_id"]
                    or type(bind.get("source_index")) is not int
                    or not 0 <= bind["source_index"] < len(cases)
                    or bind["source_index"] in seen):
                raise StageError("STAGE_ROW_BINDING_HOLD")
            seen.add(bind["source_index"])
            source = cases[bind["source_index"]]
            if (bind.get("case_key") != source["case_key"]
                    or bind.get("target_sha256") != source["assistant_target_sha256"]
                    or bind.get("history_sha256") != source["history_messages_sha256"]
                    or source["target_text"] != row["target_text"]
                    or source["history_messages"] != row["visible_history"]):
                raise StageError("STAGE_SOURCE_DRIFT_HOLD")
        if len(seen) != len(cases):
            raise StageError("STAGE_INCOMPLETE_BINDINGS_HOLD")
    return manifest, crosswalk


def audit(root: Path, pool_hash: str, cases: list[dict]) -> dict:
    manifest, crosswalk = verified_stage(root, pool_hash, cases)
    results = {}
    by_slot = {}
    for slot in ("A", "B"):
        model, revision = manifest["model_pins"][slot]
        rows = reviewer.read_input(root / f"input_{slot}" / "source.private.jsonl")
        outcomes = {}
        for pos, (row, bind) in enumerate(zip(
                rows, crosswalk["bindings"][slot], strict=True), 1):
            try:
                checkpoint = reviewer.read_checkpoint(
                    root / f"output_{slot}" / reviewer.checkpoint_name(pos),
                    pos, row, model, revision)
            except reviewer.ReviewError as exc:
                raise StageError("STAGE_CHECKPOINT_INVALID_HOLD") from exc
            if checkpoint is not None:
                outcomes[bind["source_index"]] = checkpoint["response"]["decision"]
        by_slot[slot] = outcomes
    counts = Counter()
    completed_pair = 0
    for i in range(len(cases)):
        a = by_slot["A"].get(i)
        b = by_slot["B"].get(i)
        if a is not None and b is not None:
            completed_pair += 1
        if "REJECT" in (a, b):
            verdict = "REJECT"
        elif a == b == "PASS":
            verdict = "PASS"
        else:
            verdict = "HOLD"
        counts[verdict] += 1
    return {
        "schema": SAFE_SCHEMA,
        "status": ("HF_QUALITY_DUAL_AUDITED__NO_ADMISSION"
                   if completed_pair == len(cases) else
                   "HF_QUALITY_DUAL_PARTIAL__NO_ADMISSION"),
        "cases_total": len(cases),
        "model_a_reviewed": len(by_slot["A"]),
        "model_b_reviewed": len(by_slot["B"]),
        "complete_pairs": completed_pair,
        "quality_decisions": {key: counts[key] for key in ("PASS", "HOLD", "REJECT")},
        "quality_pass": counts["PASS"],
        "reviewer_independence_cryptographically_proven": False,
        "quality_v1_admitted": 0, "training_authorized": False,
        "world_isolation_verified": False,
        "r50_complete_exclusion_verified": False,
        "r50_body_accessed": False, "paid_gpu_submitted": False,
        "private_values_emitted": False,
    }
