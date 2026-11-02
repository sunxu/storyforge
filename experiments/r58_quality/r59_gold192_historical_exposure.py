"""R59 Gold192 exact target exposure audit, reusing the pinned R57 replay sources.

Owner-local only. Compares Gold192 target digests with frozen prior Train,
Validation and v0.3 Test datasets. Emits aggregate SAFE plus a private
case-level ledger. No source data, review records, or frozen datasets modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import r57_source_index_export as frozen
import r57_trainer_exact_replay as exact
from r57_g3_private_exposure_ledger import prepare_ledger

PACKETS_SHA256 = "ae26a288382939aa79923d4a4c0602b0d575baa63f81c622ab362fbb70d56a5e"
V03_TEST_SHA256 = "d8eee6db5882d85dce7ffc01256e7c5b9b46e133bdb2cf8591259112b92e980d"
V03_TEST_GIT_BLOB = "c17f225967b6b2f8cbaf3d82fadac1b4031d0654"
V03_TEST_PATH = "data/compiled/v0.3/test.jsonl"
EXPECTED_GOLD192 = 192
EXPECTED_STORIES = 13
TRAIN_IDS = ("V01_TRAIN", "R46_TRAIN", "R54_TRAIN")
VALIDATION_IDS = ("V01_VALIDATION", "R46_VALIDATION", "R54_VALIDATION")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\\x00" + raw).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def read_gold192_packets(path: Path) -> tuple[list[dict], dict]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("PACKETS_FILE_INVALID")
    raw = path.read_bytes()
    if digest(raw) != PACKETS_SHA256:
        raise ValueError("PACKETS_SHA_MISMATCH")
    packets = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if len(packets) != EXPECTED_STORIES:
        raise ValueError("PACKET_STORY_COUNT_INVALID")
    cases, stories, ids, targets = [], set(), set(), set()
    for packet in packets:
        story = packet.get("story_uuid")
        if not isinstance(story, str) or not story or story in stories:
            raise ValueError("PACKET_STORY_ID_INVALID")
        stories.add(story)
        for case in packet.get("cases", []):
            cid = case.get("case_id")
            target = case.get("target_sha256")
            text = case.get("target_assistant_text")
            if (not isinstance(cid, str) or not cid or cid in ids
                    or not isinstance(target, str) or len(target) != 64
                    or not isinstance(text, str)
                    or digest(text.encode("utf-8")) != target):
                raise ValueError("PACKET_TARGET_IDENTITY_INVALID")
            if target in targets:
                raise ValueError("PACKET_TARGET_DUPLICATE")
            ids.add(cid)
            targets.add(target)
            cases.append({"case_id": cid, "story_uuid": story,
                          "target_sha256": target})
    if len(cases) != EXPECTED_GOLD192:
        raise ValueError("PACKET_CASE_COUNT_INVALID")
    return cases, {"packet_sha256": digest(raw), "story_count": len(stories),
                   "case_count": len(cases)}


def read_v03_test(repo: Path) -> tuple[set[str], str]:
    raw = frozen._read(repo, V03_TEST_PATH, frozen.MAX_SOURCE_BYTES)
    if digest(raw) != V03_TEST_SHA256:
        raise ValueError("V03_TEST_SHA256_MISMATCH")
    if git_blob(raw) != V03_TEST_GIT_BLOB:
        raise ValueError("V03_TEST_GIT_BLOB_MISMATCH")
    rows = []
    for line in raw.splitlines():
        row = json.loads(line)
        messages = row.get("messages")
        if not isinstance(messages, list) or not messages:
            raise ValueError("V03_TEST_MESSAGES_INVALID")
        final = messages[-1]
        if (not isinstance(final, dict) or final.get("role") != "assistant"
                or not isinstance(final.get("content"), str)):
            raise ValueError("V03_TEST_TARGET_INVALID")
        rows.append(digest(final["content"].encode("utf-8")))
    if len(rows) != 20 or len(set(rows)) != 20:
        raise ValueError("V03_TEST_ROW_COUNT_OR_DUPLICATE")
    return set(rows), digest(raw)


def classify(target: str, train: set[str], validation: set[str],
             test: set[str]) -> dict:
    in_train = target in train
    in_validation = target in validation
    in_test = target in test
    if not (in_train or in_validation or in_test):
        status = "NOT_FOUND_IN_PINNED_HISTORY"
    else:
        status = "EXPOSED"
    return {
        "status": status,
        "train_exposed": in_train,
        "validation_exposed": in_validation,
        "test_exposed": in_test,
        "matched_splits": [
            name for name, present in (
                ("TRAIN", in_train), ("VALIDATION", in_validation),
                ("TEST", in_test),
            ) if present
        ],
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
    return digest(payload)


def run(repo: Path, private_root: Path, packets_path: Path,
        output_dir: Path) -> dict:
    repo = repo.resolve(strict=True)
    private_root = private_root.resolve(strict=True)
    if repo in private_root.parents or private_root in repo.parents:
        raise ValueError("PRIVATE_ROOT_REPOSITORY_OVERLAP")
    if private_root.is_symlink() or stat.S_IMODE(private_root.stat().st_mode) & 0o077:
        raise ValueError("PRIVATE_ROOT_PERMISSIONS_INVALID")
    cases, packet_meta = read_gold192_packets(packets_path)

    payloads = {}
    parsed = {}
    for name in exact.SOURCE_IDS:
        root_tag, relative, _ = frozen.SOURCE_PATHS[name]
        root = repo if root_tag == "REPO" else private_root
        raw = frozen._read(root, relative, frozen.MAX_SOURCE_BYTES)
        exact.verify_source_pin(name, raw)
        payloads[name] = raw
        parsed[name], _ = exact._shape(raw, name)

    # Re-run the established R57 baseline invariant: 195 historical Gold
    # targets must reproduce the known 81 Train/Validation exact exposures.
    _, baseline_safe = prepare_ledger(payloads)
    if baseline_safe.get("historical_ever_train_exact") != 66:
        raise ValueError("GOLD195_BASELINE_TRAIN_EXPOSURE_MISMATCH")
    if baseline_safe.get("historical_ever_validation_exact") != 24:
        raise ValueError("GOLD195_BASELINE_VALIDATION_EXPOSURE_MISMATCH")

    train = set().union(*(r["target"] for name in TRAIN_IDS for r in parsed[name]))
    validation = set().union(*(r["target"] for name in VALIDATION_IDS for r in parsed[name]))
    test, test_sha = read_v03_test(repo)

    rows = []
    counts = Counter()
    for case in sorted(cases, key=lambda item: item["case_id"]):
        result = classify(case["target_sha256"], train, validation, test)
        row = {**case, **result}
        rows.append(row)
        counts[result["status"]] += 1
        counts["train_exposed"] += result["train_exposed"]
        counts["validation_exposed"] += result["validation_exposed"]
        counts["test_exposed"] += result["test_exposed"]
        if len(result["matched_splits"]) > 1:
            counts["multi_split_exposed"] += 1

    if len(rows) != EXPECTED_GOLD192:
        raise ValueError("GOLD192_EXPOSURE_ROW_COUNT_INVALID")

    if output_dir.exists() or output_dir.is_symlink():
        raise ValueError("OUTPUT_EXISTS")
    output_dir.mkdir(mode=0o700, parents=False)
    if stat.S_IMODE(output_dir.stat().st_mode) != 0o700:
        raise ValueError("OUTPUT_PERMISSIONS_INVALID")

    private_payload = b"".join(canonical(row) + b"\\n" for row in rows)
    private_sha = write_create_only(output_dir / "R59_GOLD192_HISTORICAL_EXPOSURE_PRIVATE.jsonl",
                                    private_payload)
    safe = {
        "schema": "r59_gold192_historical_exposure_safe_v1",
        "status": "GOLD192_HISTORICAL_TARGET_EXPOSURE_CLASSIFIED__NO_ADMISSION",
        "gold192_cases": len(rows),
        "source_packets_sha256": packet_meta["packet_sha256"],
        "gold192_story_count": packet_meta["story_count"],
        "historical_sources_byte_pinned": True,
        "gold195_baseline_reproduced": True,
        "gold195_ever_train_exact": baseline_safe["historical_ever_train_exact"],
        "gold195_ever_validation_exact": baseline_safe["historical_ever_validation_exact"],
        "gold192_train_exposed": counts["train_exposed"],
        "gold192_validation_exposed": counts["validation_exposed"],
        "gold192_test_exposed": counts["test_exposed"],
        "gold192_multi_split_exposed": counts["multi_split_exposed"],
        "gold192_not_found_in_pinned_history": counts["NOT_FOUND_IN_PINNED_HISTORY"],
        "test_source_sha256": test_sha,
        "test_source_rows": 20,
        "test_exposure_scope": "V03_COMPILED_TEST_ONLY",
        "test_exposure_scope_complete": False,
        "private_ledger": {
            "records": len(rows),
            "sha256": private_sha,
            "file": "R59_GOLD192_HISTORICAL_EXPOSURE_PRIVATE.jsonl",
        },
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }
    safe_payload = json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\\n"
    safe_sha = write_create_only(output_dir / "R59_GOLD192_HISTORICAL_EXPOSURE_SAFE.json", safe_payload)
    safe["safe_sha256"] = safe_sha
    return safe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True,
                        help="Owner R57 private root containing r46/ and r54/")
    parser.add_argument("--source-packets", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args.repo_root, args.private_root, args.source_packets, args.output_dir)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - no exception text/private values in stdout
        reason = str(exc) if isinstance(exc, ValueError) and exc.args and str(exc).isupper() else type(exc).__name__
        print(json.dumps({
            "schema": "r59_gold192_historical_exposure_safe_v1",
            "status": "HISTORICAL_EXPOSURE_HOLD",
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
