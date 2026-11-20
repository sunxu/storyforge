"""Synthetic-only Gold48 CLI profile and backward-compatibility tests.

All checks are in subprocesses to avoid changing the shared Common2 CLI
module's profile for any unrelated tests. Never use HF, network or private data.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEY = "r60-gold48-cpu-20261120T182842Z-e5de137532a1"


def python_check(script: str) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        (str(ROOT / "scripts"), str(ROOT / "src"))
    )
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=ROOT, env=env,
        capture_output=True, text=True, check=False, timeout=20,
    )
    assert result.returncode == 0, (result.stdout, result.stderr)


def test_gold48_cli_uses_existing_guard_and_pinned_cpu_mounts():
    python_check(
        f"""
import r60_p2_gold48_hf_cpu_cli as gold
from r60_common2_wrapped_hf_cli import hf_job_guard, job_command
import r60_common2_wrapped_hf_cli as shared
key = {KEY!r}
shared.missing_job_cli_flags = lambda _: []
shared.use_documented_default_attempts = lambda _: False
argv = job_command(key, "synthetic CLI help")
assert argv[:3] == ["hf", "jobs", "run"]
assert argv[argv.index("--namespace") + 1] == "adradar"
assert argv[argv.index("--flavor") + 1] == "cpu-basic"
assert argv[argv.index("--timeout") + 1] == "30m"
assert argv[argv.index("--attempts") + 1] == "1"
assert "--detach" in argv
assert (f"hf://buckets/adradar/storyforge-training/preflight/r60/p2/gold48/"
        f"cpu/runs/{{key}}:/input/gold48:ro") in argv
assert (f"hf://buckets/adradar/storyforge-training/preflight/r60/p2/gold48/"
        f"cpu/results/{{key}}:/output:rw") in argv
assert argv[-3:] == [
    "bash", "/input/gold48/scripts/r60_p2_gold48_hf_cpu_worker.sh", key,
]
assert f"STORYFORGE_R60_GOLD48_CPU_KEY={{key}}" in argv
assert argv[argv.index("--name") + 1].startswith("r60-gold48-")
assert shared.MARKER_SUFFIX == ".gold48-cpu-attempted"
try:
    shared.CPU_FLAVOR = "a100-large"
    job_command(key, "synthetic CLI help")
except hf_job_guard.PolicyError:
    pass
else:
    raise AssertionError("GPU flavor bypassed existing guard")
"""
    )


def test_common2_shared_cli_defaults_remain_unchanged():
    python_check(
        """
import r60_common2_wrapped_hf_cli as shared
shared.missing_job_cli_flags = lambda _: []
shared.use_documented_default_attempts = lambda _: False
argv = shared.job_command("r60-common2-test", "synthetic CLI help")
assert argv[argv.index("--flavor") + 1] == "cpu-upgrade"
assert argv[argv.index("--timeout") + 1] == "120m"
assert "hf://buckets/adradar/storyforge-training/preflight/r60/common2/wrapped-cpu/runs/r60-common2-test:/input/common2:ro" in argv
assert argv[-2:] == ["bash", "/input/common2/scripts/r60_common2_wrapped_hf_worker.sh"]
assert shared.MARKER_SUFFIX == ".wrapped-cpu-attempted"
"""
    )


def test_gold48_cli_denies_malformed_run_key():
    python_check(
        """
import r60_p2_gold48_hf_cpu_cli as gold
try:
    gold.gold48_worker_command("bad-key")
except ValueError as error:
    assert str(error) == "RUN_KEY_HOLD"
else:
    raise AssertionError("Invalid Gold48 RUN_KEY accepted")
"""
    )
