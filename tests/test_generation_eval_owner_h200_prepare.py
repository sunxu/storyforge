"""No-GPU tests of Owner-only H200 synthetic launch command generation."""
from pathlib import Path
import hashlib
import pytest

from storyforge_dataset.generation_eval.owner_h200_prepare import (
    _bootstrap_script,
    build_h200_argv,
)


def test_owner_h200_argv_stays_explicit_and_synthetic_only(tmp_path):
    stage = tmp_path / "r60-p4-h200-a-20261110221534"
    args = build_h200_argv(
        staging=stage, run_id=stage.name, archive_sha="f" * 64
    )
    joined = " ".join(args)
    assert args[:3] == ["hf", "jobs", "run"]
    assert args.count("--attempts") == 1
    assert args[args.index("--attempts") + 1] == "1"
    assert args[args.index("--timeout") + 1] == "60m"
    assert args[args.index("--flavor") + 1] == "h200"
    assert "--detach" in args
    assert f"{stage}/input:/input:ro" in args
    assert f"{stage}/output:/output:rw" in args
    assert "--synthetic-authorization /input/synthetic-authorization.json" in joined
    assert "--model-role A" in joined
    assert "--output-dir /output/r60-p4-h200-a-20261110221534" in joined
    assert "--model-role B" not in joined
    assert "--model-role challenger" not in joined
    assert "--train" not in joined
    assert "--repo-root /workspace/storyforge" in joined


@pytest.mark.parametrize("name", [
    "r60-p4-h200-b-20261110221534", "r60-p4-h200-a-other",
    "r60-p4-h200-a-20261110221534/../fake",
])
def test_other_run_names_refused(tmp_path, name):
    with pytest.raises(ValueError, match="H200_RUN_ID_INVALID"):
        build_h200_argv(staging=tmp_path, run_id=name, archive_sha="f" * 64)


def test_bad_archive_digest_refused(tmp_path):
    with pytest.raises(ValueError, match="SOURCE_ARCHIVE_SHA_INVALID"):
        build_h200_argv(staging=tmp_path, run_id="r60-p4-h200-a-20261110221534",
                        archive_sha="bad")


def test_bootstrap_enforces_digest_and_path():
    source = _bootstrap_script("a" * 64)
    assert "PINNED_SOURCE_ARCHIVE_MISMATCH" in source
    assert "SOURCE_ARCHIVE_PATH_INVALID" in source
    assert "SOURCE_ARCHIVE_TYPE_INVALID" in source
    assert "src/storyforge_dataset" in source
