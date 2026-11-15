"""Strict three-synthetic-case HF CPU CLI, reuse Common2 safety orchestrator.

Only explicit 'submit --execute' could incur CPU charges; all earlier steps
produce no job. This stage has no real story content or R50 data.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import r60_base_constructed_hf_cpu_stage as stage
import r60_common2_wrapped_hf_cli as shared

shared.stage_tool = stage
shared.PREFIX = "preflight/r60/base-start/constructed-system-cpu3"
shared.WORKER = "/input/common2/scripts/r60_base_constructed_hf_cpu_worker.sh"
shared.SCHEMA = "storyforge_r60_base_constructed_hf_cpu_cli_safe_v1"

if __name__ == "__main__":
    raise SystemExit(shared.main())
