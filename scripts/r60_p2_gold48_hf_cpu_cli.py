"""Gold48 HF CPU CLI: strict thin profile of existing Common2 CPU orchestrator.

No new upload algorithm, Job API, duplicate checks, retry or submitter.
The existing immutable Gold48 Stage is reused (no restaging). On the Owner Mac,
'ready' is read-only plus CLI dry-run, and 'submit --execute' is the sole
billable operation. Exactly one attempt, manifest-last already uploaded, CPU only.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import r60_common2_wrapped_hf_cli as shared
import r60_p2_gold48_hf_cpu_stage as stage

shared.stage_tool = stage
shared.PREFIX = "preflight/r60/p2/gold48/cpu"
shared.INPUT_MOUNT = "/input/gold48"
shared.WORKER = "/input/gold48/scripts/r60_p2_gold48_hf_cpu_worker.sh"
shared.CPU_FLAVOR = "cpu-basic"
shared.TIMEOUT_MINUTES = 30
shared.JOB_NAME_PREFIX = "r60-gold48"
shared.RUN_KEY_ENV = "STORYFORGE_R60_GOLD48_CPU_KEY"
shared.MARKER_SUFFIX = ".gold48-cpu-attempted"
shared.SCHEMA = "storyforge_r60_gold48_hf_cpu_cli_safe_v1"


def gold48_worker_command(key: str) -> list[str]:
    if not stage.RUN_RE.fullmatch(key):
        raise ValueError("RUN_KEY_HOLD")
    return ["bash", shared.WORKER, key]


shared.worker_command = gold48_worker_command


if __name__ == "__main__":
    raise SystemExit(shared.main())
