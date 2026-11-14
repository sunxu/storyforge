"""R60 Base CPU336 HF CLI: strict profile of shared Common2 HF orchestrator.

No duplicated bucket sync, Job SDK/CLI, retry, marker or safety logic.
Explicit submit --execute is the only billable path.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import r60_base_cpu336_hf_stage as stage
import r60_common2_wrapped_hf_cli as shared

shared.stage_tool = stage
shared.PREFIX = "preflight/r60/base-start/cpu336"
shared.WORKER = "/input/common2/scripts/r60_base_cpu336_hf_worker.sh"
shared.SCHEMA = "storyforge_r60_base_cpu336_hf_cli_safe_v1"

if __name__ == "__main__":
    raise SystemExit(shared.main())
