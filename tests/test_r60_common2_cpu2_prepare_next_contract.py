"""Static safety contract for create-only R60 CPU2 next-run orchestration."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_orchestration_never_submits_or_mutates_old_stage():
    src = (ROOT / "scripts/r60_common2_cpu2_prepare_next.sh").read_text()
    assert 'OLD_KEY="r60-common2-cpu2-20261112T032815Z-71c840b37254"' in src
    assert "--old-stage \"$BASE/$OLD_KEY\"" in src
    assert "--new-stage \"$STAGE\"" in src
    assert "r60_common2_hf_cpu_stage_v2.py" in src
    assert '$(hf --version)' in src
    assert "2.4.0" in src
    assert 'export R60_HF_SDK_PYTHON="$PY"' in src
    assert "sync-existing" in src
    assert "r60_common2_hf_cpu_cli_dry_run.py" in src
    assert "r60_common2_hf_cpu_final_read_only.py" in src
    assert "hf jobs run" not in src
    assert "--execute" not in src
    assert "R60_COMMON2_NEXT_STAGE_READY_PASS__NO_JOB" in src


def test_sync_contract_uses_explicit_sdk_guard_and_keeps_submit_disabled():
    src = (ROOT / "scripts/r60_common2_hf_cpu_submit.sh").read_text()
    assert 'HF_SDK_PYTHON="${R60_HF_SDK_PYTHON:-python3}"' in src
    assert '"$HF_SDK_PYTHON" scripts/r60_common2_hf_cpu_bucket_guard.py empty' in src
    assert '"$HF_SDK_PYTHON" scripts/r60_common2_hf_cpu_bucket_guard.py ready' in src
    assert "R60_COMMON2_LEGACY_CLI_SUBMIT_DISABLED_MOUNT_POLICY_HOLD" in src
