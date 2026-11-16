"""Strict R60 Base336 final CPU CLI; reuse proven Common2 orchestration."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import r60_base336_final_cpu_stage as stage
import r60_common2_wrapped_hf_cli as shared

shared.stage_tool = stage
shared.PREFIX = "preflight/r60/base-start/final-293-43-cpu"
shared.WORKER = "/input/common2/scripts/r60_base336_final_cpu_worker.sh"
shared.SCHEMA = "storyforge_r60_base336_final_cpu_cli_safe_v1"

if __name__ == "__main__":
    raise SystemExit(shared.main())
