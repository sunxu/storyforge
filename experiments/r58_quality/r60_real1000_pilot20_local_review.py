"""R60 REAL pilot20: bounded Owner-local single-reviewer quality pilot.

Reuses the existing literary rubric and OpenAI-compatible client. One receipt
per case, create-only. Model verdict is ADVISORY, never training admission.
Only localhost endpoints are accepted; no DB/GPU job setup here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import r60_real1000_pilot20_packets_cpu as pilot
import r60_real_ai_dual_review as reviewer
import r60_real_private_batch as private

SCHEMA = "storyforge_r60_real1000_pilot20_local_review_v1"
SAFE_SCHEMA = "storyforge_r60_real1000_pilot20_local_review_safe_v1"
CONFIG = "R60_PILOT20_REVIEW_CONFIG_PRIVATE.json"
MAX_PACKETS_BYTES = 200000
MAX_RECEIPT_BYTES = 16000
MAX_CASES_PER_CALL = 5


class Hold(ValueError):
    """Reject a missing or inconsistent local review artifact."""


def canonical(data: object) -> bytes:
    return (json.dumps(
        data, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False,
    ) + "\n").encode("utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_packets(directory: Path) -> tuple[dict, str]:
    private.private_dir(directory, create=False)
    raw = private.read_private(directory / pilot.FILENAME, MAX_PACKETS_BYTES)
    data = json.loads(raw)
    if (
        not isinstance(data, dict)
        or data.get("schema") != pilot.SCHEMA
        or data.get("status") != "PILOT20_PACKETS_PRIVATE__NOT_REVIEWED"
        or data.get("sample100_binding") != "RECOMPUTED_EXACT"
        or not isinstance(data.get("packets"), list)
        or len(data["packets"]) != 20
        or data.get("quality_review_performed") is not False
        or data.get("train_admitted") != 0
    ):
        raise Hold("PACKETS_SCHEMA_HOLD")
    bins = Counter()
    for i, packet in enumerate(data["packets"], 1):
        if (
            not isinstance(packet, dict)
            or packet.get("pilot_position") != i
            or packet.get("human_reference_status") != "NOT_ADJUDICATED"
            or packet.get("model_quality_status") != "NOT_REVIEWED"
            or type(packet.get("sample100_position")) is not int
            or not 1 <= packet["sample100_position"] <= 1000
            or packet.get("target_char_bin") not in pilot.SAMPLE_QUOTAS
        ):
            raise Hold("PACKET_ENTRY_HOLD")
        payload = {
            "history_messages": packet.get("history_messages"),
            "target_text": packet.get("assistant_target"),
        }
        reviewer.prompt_for_case(payload)
        bins[packet["target_char_bin"]] += 1
    if bins != Counter(pilot.SAMPLE_QUOTAS):
        raise Hold("PACKETS_QUOTA_HOLD")
    if len({p["sample100_position"] for p in data["packets"]}) != 20:
        raise Hold("PACKET_POSITION_DUPLICATE_HOLD")
    return data, sha(raw)


def receipt_name(i: int) -> str:
    if not 1 <= i <= 20:
        raise Hold("POSITION_HOLD")
    return f"R60_PILOT20_REVIEW_{i:04d}_PRIVATE.json"


def validate_config(folder: Path) -> dict:
    private.private_dir(folder, create=False)
    config = json.loads(private.read_private(folder / CONFIG, MAX_RECEIPT_BYTES))
    if (
        not isinstance(config, dict)
        or set(config) != {"schema", "packet_dir", "packets_sha256", "model_id",
                           "endpoint", "json_mode", "timeout"}
        or config["schema"] != SCHEMA
        or type(config["packet_dir"]) is not str
        or type(config["packets_sha256"]) is not str
        or len(config["packets_sha256"]) != 64
        or type(config["model_id"]) is not str
        or not config["model_id"].strip()
        or type(config["json_mode"]) is not bool
        or type(config["timeout"]) is not int
        or not 10 <= config["timeout"] <= 300
        or reviewer.validate_endpoint(
            config["endpoint"][:-len("/chat/completions")], False
        ) != config["endpoint"]
    ):
        raise Hold("CONFIG_HOLD")
    return config


def read_progress(folder: Path, config: dict, packets: dict) -> dict:
    entries = sorted(folder.iterdir())
    allowed = {CONFIG} | {receipt_name(i) for i in range(1, 21)}
    if any(item.is_symlink() or not item.is_file() or item.name not in allowed
           for item in entries):
        raise Hold("FOREIGN_FILE_HOLD")
    receipts = [x for x in entries if x.name != CONFIG]
    if [x.name for x in receipts] != [
        receipt_name(i) for i in range(1, len(receipts) + 1)
    ]:
        raise Hold("NONCONTIGUOUS_HOLD")
    decisions = Counter()
    flags = Counter()
    for i, path in enumerate(receipts, 1):
        row = json.loads(private.read_private(path, MAX_RECEIPT_BYTES))
        if not isinstance(row, dict):
            raise Hold("RECEIPT_SCHEMA_HOLD")
        checksum = row.get("receipt_sha256")
        source = {key: value for key, value in row.items()
                  if key != "receipt_sha256"}
        if (
            set(row) != {"schema", "position", "packets_sha256", "model_id",
                         "decision", "scores", "severe_flags", "reason_cn",
                         "receipt_sha256"}
            or row["schema"] != SCHEMA
            or row["position"] != i
            or row["packets_sha256"] != config["packets_sha256"]
            or row["model_id"] != config["model_id"]
            or checksum != sha(canonical(source))
        ):
            raise Hold("RECEIPT_BINDING_HOLD")
        answer = {k: row[k] for k in
                  ("decision", "scores", "severe_flags", "reason_cn")}
        reviewer.parse_model_response(answer)
        decisions[answer["decision"]] += 1
        flags.update({k: 1 for k, v in answer["severe_flags"].items() if v})
    return {
        "schema": SAFE_SCHEMA,
        "status": "PILOT20_LOCAL_REVIEW_COMPLETE__OWNER_ADJUDICATION_PENDING"
        if len(receipts) == 20 else
        "PILOT20_LOCAL_REVIEW_PARTIAL__OWNER_ADJUDICATION_PENDING",
        "total_cases": len(packets["packets"]),
        "model_reviewed": len(receipts),
        "remaining": 20 - len(receipts),
        "model_decisions_advisory": {name: decisions[name] for name in
                                    ("PASS", "HOLD", "REJECT")},
        "model_severe_flag_counts_advisory": {
            name: flags[name] for name in private.SEVERE
        },
        "independent_reference_reviews": 0,
        "quality_v1_admitted": 0,
        "train_admitted": 0,
        "database_accessed": False,
        "gpu_job_started": False,
        "private_values_emitted": False,
    }


def initialize(packets_dir: Path, output_dir: Path, endpoint: str,
               model: str, json_mode: bool, timeout: int) -> dict:
    if output_dir.exists() or output_dir.is_symlink():
        raise Hold("OUTPUT_EXISTS_HOLD")
    packets, digest = load_packets(packets_dir)
    if not model.strip() or not 10 <= timeout <= 300:
        raise Hold("CONFIG_ARGS_HOLD")
    local_endpoint = reviewer.validate_endpoint(endpoint, False)
    private.private_dir(output_dir, create=True)
    config = {
        "schema": SCHEMA, "packet_dir": str(packets_dir),
        "packets_sha256": digest, "model_id": model,
        "endpoint": local_endpoint, "json_mode": bool(json_mode),
        "timeout": timeout,
    }
    private.write_new(output_dir / CONFIG, canonical(config))
    return read_progress(output_dir, config, packets)


def get_state(output_dir: Path) -> tuple[dict, dict, dict]:
    config = validate_config(output_dir)
    packets, digest = load_packets(Path(config["packet_dir"]))
    if config["packets_sha256"] != digest:
        raise Hold("PACKETS_MODIFIED_HOLD")
    return config, packets, read_progress(output_dir, config, packets)


def advance(output_dir: Path, max_cases: int) -> dict:
    if type(max_cases) is not int or not 1 <= max_cases <= MAX_CASES_PER_CALL:
        raise Hold("MAX_CASES_HOLD")
    config, packets, current = get_state(output_dir)
    start = current["model_reviewed"]
    for i in range(start, min(start + max_cases, 20)):
        packet = packets["packets"][i]
        prompt = reviewer.prompt_for_case({
            "history_messages": packet["history_messages"],
            "target_text": packet["assistant_target"],
        })
        answer = reviewer.model_request(
            config["endpoint"], config["model_id"], "",
            prompt, config["timeout"], config["json_mode"],
        )
        receipt = {
            "schema": SCHEMA,
            "position": i + 1,
            "packets_sha256": config["packets_sha256"],
            "model_id": config["model_id"],
            **answer,
        }
        receipt["receipt_sha256"] = sha(canonical(receipt))
        private.write_new(output_dir / receipt_name(i + 1), canonical(receipt))
    return get_state(output_dir)[2]


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    init = sub.add_parser("init")
    init.add_argument("--packets-dir", type=Path, required=True)
    init.add_argument("--output-dir", type=Path, required=True)
    init.add_argument("--endpoint", required=True)
    init.add_argument("--model", required=True)
    init.add_argument("--json-mode", action="store_true")
    init.add_argument("--timeout", type=int, default=180)
    run = sub.add_parser("advance")
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--max-cases", type=int, default=5)
    inspect = sub.add_parser("inspect")
    inspect.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.mode == "init":
            result = initialize(args.packets_dir, args.output_dir, args.endpoint,
                                args.model, args.json_mode, args.timeout)
        elif args.mode == "advance":
            result = advance(args.output_dir, args.max_cases)
        else:
            result = get_state(args.output_dir)[2]
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - redact all local texts and API errors
        print(json.dumps({
            "schema": SAFE_SCHEMA,
            "status": "PILOT20_LOCAL_REVIEW_HOLD",
            "database_accessed": False, "gpu_job_started": False,
            "private_values_emitted": False, "quality_v1_admitted": 0,
            "train_admitted": 0,
        }, sort_keys=True), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
