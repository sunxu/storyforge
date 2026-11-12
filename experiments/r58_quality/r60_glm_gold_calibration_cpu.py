"""R60 GLM CPU-only comparison of model SAFE decisions with Owner-attested Gold.

Owner attestation is NOT independent proof. No private text or input is printed.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

MODEL_SCHEMA = "storyforge_r60_glm_raw_decision_diagnostic_safe_v1"
GOLD_SCHEMA = "storyforge_r60_owner_independent_gold25_v1"
OUT_SCHEMA = "storyforge_r60_glm_gold_calibration_safe_v1"
DECISIONS = frozenset({"PASS", "HOLD", "REJECT"})


class CalibrationHold(ValueError):
    """Fail closed on scope or evidence mismatch."""


def load(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 65536:
        raise CalibrationHold("FILE_SCOPE_HOLD")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CalibrationHold("JSON_TYPE_HOLD")
    return value


def check_model(value: dict) -> None:
    if (
        value.get("schema") != MODEL_SCHEMA
        or value.get("status") != "GLM_RAW_DECISION_DIAGNOSTIC"
        or value.get("private_values_emitted") is not False
        or value.get("gpu_started") is not False
        or value.get("quality_v1_admitted") != 0
    ):
        raise CalibrationHold("MODEL_SAFE_EVIDENCE_HOLD")
    counts = value.get("counts")
    positions = value.get("positions")
    if (
        not isinstance(counts, dict)
        or not isinstance(positions, dict)
        or counts.get("REJECT") != 25
        or any(counts.get(name, 0) != 0 for name in ("PASS", "HOLD", "OTHER"))
        or set(positions) != {"PASS", "HOLD", "REJECT", "OTHER"}
        or positions.get("REJECT") != list(range(1, 26))
        or any(positions.get(name) != [] for name in ("PASS", "HOLD", "OTHER"))
    ):
        raise CalibrationHold("MODEL_DECISION_INVENTORY_HOLD")


def check_gold(value: dict) -> Counter:
    if (
        set(value) != {"schema", "rubric_version", "owner_attests_independent", "cases"}
        or value["schema"] != GOLD_SCHEMA
        or value["rubric_version"] != "v2.1"
        or value["owner_attests_independent"] is not True
        or not isinstance(value["cases"], list)
        or len(value["cases"]) != 25
    ):
        raise CalibrationHold("GOLD_SCOPE_OR_INDEPENDENCE_HOLD")
    positions = set()
    counts = Counter()
    for item in value["cases"]:
        if (
            not isinstance(item, dict)
            or set(item) != {"original_position", "gold_decision", "finalized"}
            or type(item["original_position"]) is not int
            or item["original_position"] not in range(1, 26)
            or item["original_position"] in positions
            or item["gold_decision"] not in DECISIONS
            or item["finalized"] is not True
        ):
            raise CalibrationHold("GOLD_ROW_HOLD")
        positions.add(item["original_position"])
        counts[item["gold_decision"]] += 1
    if positions != set(range(1, 26)):
        raise CalibrationHold("GOLD_COVERAGE_HOLD")
    return counts


def summarize(model: dict, gold: dict) -> dict:
    check_model(model)
    counts = check_gold(gold)
    return {
        "schema": OUT_SCHEMA,
        "status": "GLM_GOLD_CALIBRATION_COUNTS__OWNER_ATTESTED",
        "model_decision": "REJECT",
        "model_decision_count": 25,
        "rubric_version": "v2.1",
        "independence_proven": False,
        "independence_owner_attested": True,
        "gold_counts": {name: counts[name] for name in ("PASS", "HOLD", "REJECT")},
        "candidate_false_rejections_vs_gold_pass": counts["PASS"],
        "model_reject_vs_gold_hold": counts["HOLD"],
        "model_reject_vs_gold_reject_agreement": counts["REJECT"],
        "gpu_started": False,
        "private_values_emitted": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-safe", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = summarize(load(args.model_safe), load(args.gold))
    except (CalibrationHold, OSError, UnicodeError, ValueError, TypeError, KeyError):
        print(json.dumps({
            "schema": OUT_SCHEMA,
            "status": "GLM_GOLD_CALIBRATION_HOLD",
            "gpu_started": False,
            "private_values_emitted": False,
            "quality_v1_admitted": 0,
            "training_authorized": False,
        }, sort_keys=True))
        return 42
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
