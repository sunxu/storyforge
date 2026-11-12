"""Owner-Mac-only: prepare one pinned synthetic H200 launch script. NEVER submit it.

The resulting launch script must be invoked explicitly by the Owner. Uses only
the already-validated local input pack and a minimal git-archive source bundle,
never private history, training data or a Hugging Face credential.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import shlex
import subprocess
import tarfile
from pathlib import Path
from typing import Any

from .synthetic_gate import CALIBRATED_SHA256, authorize_synthetic_profile
from .worker import WorkerError

IMAGE = (
    "docker.io/pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime@"
    "sha256:77f17f843507062875ce8be2a6f76aa6aa3df7f9ef1e31d9d7432f4b0f563dee"
)
ARCHIVE_MEMBERS = (
    "src/storyforge_dataset",
    "requirements/hf-generation-eval.lock",
)
SHA40 = re.compile(r"^[0-9a-f]{40}$")
RUN_ID = re.compile(r"^r60-p4-h200-(a|b|challenger)-[0-9]{14}$")
ROLE_SLUG = {"A": "a", "B": "b", "challenger": "challenger"}
CODE_ROOT = "/workspace/storyforge"
REQUIRED_INPUTS = {
    "inputs.jsonl", "manifest.json", "generation-profile.json",
    "synthetic-authorization.json",
}


def _git_output(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def _validate_source_members(archive: Path) -> None:
    with tarfile.open(archive, "r:") as tar:
        members = tar.getmembers()
        if not members or len(members) > 20000:
            raise ValueError("SOURCE_ARCHIVE_MEMBER_COUNT_INVALID")
        total = 0
        for entry in members:
            path = entry.name
            allowed = (
                path == "src" or path == "requirements"
                or path.startswith("src/storyforge_dataset/")
                or path == "src/storyforge_dataset"
                or path == "requirements/hf-generation-eval.lock"
            )
            if (not allowed or path.startswith("/") or ".." in Path(path).parts
                    or not (entry.isfile() or entry.isdir())):
                raise ValueError("SOURCE_ARCHIVE_MEMBER_REJECTED")
            total += entry.size
        if total > 64 * 1024 * 1024:
            raise ValueError("SOURCE_ARCHIVE_OVERSIZE")


def _bootstrap_script(archive_sha: str) -> str:
    return f"""import hashlib, shutil, tarfile
from pathlib import Path
archive=Path('/input/source.tar')
raw=archive.read_bytes()
if len(raw)>64*1024*1024 or hashlib.sha256(raw).hexdigest()!={archive_sha!r}:
    raise SystemExit('PINNED_SOURCE_ARCHIVE_MISMATCH')
root=Path({CODE_ROOT!r})
root.mkdir(parents=True,exist_ok=False)
with tarfile.open(archive,mode='r:') as tf:
    members=tf.getmembers()
    if not members or len(members)>20000:
        raise SystemExit('SOURCE_ARCHIVE_MEMBER_COUNT_INVALID')
    total=0
    for member in members:
        name=member.name
        allowed=(name in ('src','requirements','src/storyforge_dataset',
              'requirements/hf-generation-eval.lock')
              or name.startswith('src/storyforge_dataset/'))
        if not allowed or name.startswith('/') or '..' in Path(name).parts:
            raise SystemExit('SOURCE_ARCHIVE_PATH_INVALID')
        if not (member.isfile() or member.isdir()):
            raise SystemExit('SOURCE_ARCHIVE_TYPE_INVALID')
        total+=member.size
        if total>64*1024*1024:
            raise SystemExit('SOURCE_ARCHIVE_CONTENT_LIMIT_EXCEEDED')
        target=root/name
        if member.isdir():
            target.mkdir(parents=True,exist_ok=True)
        else:
            target.parent.mkdir(parents=True,exist_ok=True)
            src=tf.extractfile(member)
            if src is None:
                raise SystemExit('SOURCE_ARCHIVE_UNREADABLE')
            with target.open('xb') as dst:
                shutil.copyfileobj(src,dst)
"""


def build_h200_argv(*, staging: Path, run_id: str, archive_sha: str,
                    model_role: str = "A") -> list[str]:
    """Generate explicit shell argv; no subprocess or HF client is invoked."""
    if model_role not in ROLE_SLUG or not RUN_ID.fullmatch(run_id) or not run_id.startswith(
        f"r60-p4-h200-{ROLE_SLUG[model_role]}-"
    ):
        raise ValueError("H200_RUN_ID_INVALID")
    if not re.fullmatch(r"[0-9a-f]{64}", archive_sha):
        raise ValueError("SOURCE_ARCHIVE_SHA_INVALID")
    command = (
        "set -euo pipefail; "
        "python -c "
        + shlex.quote("import base64; exec(base64.b64decode("
                      + repr(base64.b64encode(_bootstrap_script(archive_sha).encode()).decode())
                      + "))")
        + "; python -m pip install --disable-pip-version-check --require-hashes "
          "-r /workspace/storyforge/requirements/hf-generation-eval.lock; "
          "STORYFORGE_RUNTIME_IMAGE_DIGEST="
          "sha256:77f17f843507062875ce8be2a6f76aa6aa3df7f9ef1e31d9d7432f4b0f563dee "
          "PYTHONPATH=/workspace/storyforge/src "
          "python -m storyforge_dataset.generation_eval.worker_cli "
          f"--model-role {model_role} "
          "--profile /input/generation-profile.json "
          "--synthetic-authorization /input/synthetic-authorization.json "
          "--manifest /input/manifest.json "
          "--input /input/inputs.jsonl "
          "--output-dir /output/" + run_id + " "
          "--repo-root /workspace/storyforge"
    )
    return [
        "hf", "jobs", "run", "--namespace", "adradar",
        "--name", run_id,
        "--flavor", "h200",
        "--timeout", "60m",
        "--attempts", "1",
        "--detach",
        "-v", f"{staging / 'input'}:/input:ro",
        "-v", f"{staging / 'output'}:/output:rw",
        IMAGE,
        "--", "bash", "-lc", command,
    ]


def prepare(*, repo: Path, staging: Path, code_revision: str,
            model_role: str = "A") -> dict[str, Any]:
    """Perform CPU-only validations and write one human-executed launch script."""
    if not SHA40.fullmatch(code_revision):
        raise ValueError("CODE_REVISION_INVALID")
    repo = repo.resolve(strict=True)
    staging = staging.resolve(strict=True)
    run_id = staging.name
    if model_role not in ROLE_SLUG or not RUN_ID.fullmatch(run_id) or not run_id.startswith(
        f"r60-p4-h200-{ROLE_SLUG[model_role]}-"
    ):
        raise ValueError("H200_RUN_ID_INVALID")
    if _git_output(repo, "rev-parse", code_revision) != code_revision:
        raise ValueError("CODE_REVISION_UNRESOLVED")
    if _git_output(repo, "rev-parse", "origin/r60/p4-generation-eval-framework") != code_revision:
        raise ValueError("CODE_REVISION_NOT_CURRENT_BRANCH_HEAD")
    if staging.is_symlink() or (staging / "input").is_symlink() or (staging / "output").is_symlink():
        raise ValueError("STAGING_SYMLINK_REJECTED")
    input_dir, output_dir = staging / "input", staging / "output"
    if not input_dir.is_dir() or not output_dir.is_dir():
        raise ValueError("STAGING_MOUNT_DIRS_REQUIRED")
    if {p.name for p in input_dir.iterdir()} != REQUIRED_INPUTS:
        raise ValueError("STAGING_INPUT_FILE_SET_INVALID")
    if list(output_dir.iterdir()):
        raise ValueError("STAGING_OUTPUT_NOT_EMPTY")
    if (staging / f"launch-h200-{model_role}.sh").exists():
        raise ValueError("LAUNCH_SCRIPT_ALREADY_EXISTS")
    auth_profile = authorize_synthetic_profile(
        frozen_path=input_dir / "generation-profile.json",
        authorization_path=input_dir / "synthetic-authorization.json",
        manifest_path=input_dir / "manifest.json",
        input_path=input_dir / "inputs.jsonl",
        model_role=model_role,
    )
    if auth_profile["synthetic_only_runtime_scope"]["sha256"] != CALIBRATED_SHA256[model_role]:
        raise WorkerError("SYNTHETIC_SHA_NOT_CALIBRATED")
    with (input_dir / "source.tar").open("xb") as target:
        proc = subprocess.run(
            ["git", "-C", str(repo), "archive", "--format=tar", code_revision,
             *ARCHIVE_MEMBERS],
            check=False, stdout=target, stderr=subprocess.PIPE,
        )
    if proc.returncode:
        (input_dir / "source.tar").unlink(missing_ok=True)
        raise ValueError("GIT_ARCHIVE_FAILED")
    source = input_dir / "source.tar"
    _validate_source_members(source)
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    argv = build_h200_argv(staging=staging, run_id=run_id, archive_sha=sha,
                           model_role=model_role)
    launch = staging / f"launch-h200-{model_role}.sh"
    launch.write_text("#!/bin/bash\nset -euo pipefail\n" + shlex.join(argv) + "\n")
    launch.chmod(0o700)
    return {
        "schema": "storyforge_r60_p4_synthetic_h200_owner_plan_safe_v1",
        "status": f"H200_{model_role}_OWNER_LAUNCH_SCRIPT_PREPARED_NOT_SUBMITTED",
        "role": model_role, "code_revision": code_revision,
        "input_sha256": CALIBRATED_SHA256[model_role],
        "source_archive_sha256": sha,
        "flavor": "h200", "timeout_minutes": 60, "attempts": 1,
        "launch_script": str(launch),
        "gpu_started": False, "inference_started": False,
        "hf_job_submitted": False, "training_started": False,
        "private_values_emitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--staging", type=Path, required=True)
    parser.add_argument("--code-revision", required=True)
    parser.add_argument("--model-role", choices=("A", "B", "challenger"), default="A")
    args = parser.parse_args()
    try:
        receipt = prepare(repo=args.repo, staging=args.staging,
                          code_revision=args.code_revision, model_role=args.model_role)
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as exc:
        receipt = {
            "schema": "storyforge_r60_p4_synthetic_h200_owner_plan_safe_v1",
            "status": f"H200_{args.model_role}_OWNER_PLAN_HOLD",
            "reason_code": str(exc) if isinstance(exc, ValueError) else "PREPARATION_FAILED",
            "gpu_started": False, "inference_started": False,
            "hf_job_submitted": False, "training_started": False,
            "private_values_emitted": False,
        }
        print(json.dumps(receipt, sort_keys=True))
        return 2
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
