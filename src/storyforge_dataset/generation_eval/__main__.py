"""CPU-only profile readiness CLI; does not submit or execute model inference."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .profiles import assess_profile, load_profile
from .sampling import assess_sampling_decision


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument("--purpose", choices=("generation", "runtime_smoke", "freeze_review"), default="generation")
    parser.add_argument("--sampling-decision", type=Path)
    args = parser.parse_args()
    try:
        profile = load_profile(args.profile)
        result = assess_profile(profile, purpose=args.purpose).to_safe_dict()
        if args.purpose == "freeze_review":
            sampling_path = args.sampling_decision or args.profile.with_name("r60_sampling_decision_candidate_v1.json")
            sampling_document = json.loads(sampling_path.read_text(encoding="utf-8"))
            sampling_safe = assess_sampling_decision(sampling_document).to_safe_dict()
            blockers = list(result["blockers"])
            blockers.extend("SAMPLING_" + code for code in sampling_safe["blockers"])
            result["sampling_decision"] = sampling_safe
            result["blockers"] = list(dict.fromkeys(blockers))
            result["ready"] = not result["blockers"]
            result["status"] = "P4_FREEZE_REVIEW_READY_NOT_FROZEN" if result["ready"] else "P4_FREEZE_REVIEW_HOLD"
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        result = {
            "schema": "storyforge_r60_generation_profile_assessment_safe_v1",
            "status": "P4_PROFILE_INVALID_HOLD",
            "ready": False,
            "model_count": 0,
            "roles": [],
            "blockers": ["PROFILE_INPUT_INVALID"],
            "private_values_emitted": False,
            "inference_started": False,
            "gpu_started": False,
            "training_started": False,
        }
        print(json.dumps(result, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result["ready"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
