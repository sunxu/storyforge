"""Fail-closed runtime CLI for one authorized P4 model batch."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

from storyforge_dataset.hf_runtime.inputs import InputManager
from storyforge_dataset.hf_runtime.outputs import OutputManager

from .backend import TransformersGenerationBackend, download_pinned_tokenizer_snapshot
from .profiles import assess_profile, load_profile
from .worker import WorkerError, run_generation_batch


def main(argv: Sequence[str] | None = None) -> int:
    """Execute one explicitly authorized, single-model generation batch.

    This entry point is intentionally fail-closed: the production profile must
    already carry Owner freeze/inference/GPU authorization. It writes private
    generations only beneath a fresh output directory and prints SAFE metadata.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-role", required=True, choices=("A", "B", "challenger"))
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--synthetic-authorization", type=Path,
                        help="Enable exact-hash Owner-approved synthetic-only run; --profile must be Frozen")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        if args.synthetic_authorization is not None:
            from .synthetic_gate import authorize_synthetic_profile
            profile = authorize_synthetic_profile(
                frozen_path=args.profile,
                authorization_path=args.synthetic_authorization,
                manifest_path=args.manifest,
                input_path=args.input,
                model_role=args.model_role,
            )
        else:
            profile = load_profile(args.profile)
        assessment = assess_profile(profile)
        if not assessment.ready:
            raise WorkerError("GENERATION_PROFILE_NOT_AUTHORIZED")
        if profile.get("training_authorized") is True:
            raise WorkerError("TRAINING_AUTHORIZATION_MUST_REMAIN_DISABLED")

        repo_root = args.repo_root.resolve(strict=True)
        lock_relative = Path(profile["dependency_lock_path"])
        if lock_relative.is_absolute() or any(part in {"", ".", ".."} for part in lock_relative.parts):
            raise WorkerError("DEPENDENCY_LOCK_PATH_INVALID")
        lock_path = (repo_root / lock_relative).resolve(strict=True)
        if not lock_path.is_relative_to(repo_root):
            raise WorkerError("DEPENDENCY_LOCK_PATH_INVALID")
        lock_bytes = InputManager.open_verified(
            lock_path, max_bytes=8 * 1024 * 1024
        ).read_bytes()
        lock_sha = hashlib.sha256(lock_bytes).hexdigest()
        if lock_sha != profile.get("dependency_lock_sha256"):
            raise WorkerError("DEPENDENCY_LOCK_SHA256_MISMATCH")
        runtime_digest = profile.get("runtime_digest")
        if os.environ.get("STORYFORGE_RUNTIME_IMAGE_DIGEST") != runtime_digest:
            raise WorkerError("RUNTIME_IMAGE_DIGEST_MISMATCH")
        if sys.version_info[:2] != (3, 11):
            raise WorkerError("PYTHON_RUNTIME_MISMATCH")

        manifest_bytes = InputManager.open_verified(
            args.manifest, max_bytes=1024 * 1024
        ).read_bytes()
        try:
            manifest = json.loads(manifest_bytes)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WorkerError("INPUT_MANIFEST_INVALID") from exc
        if not isinstance(manifest, dict) or set(manifest) != {
            "schema", "record_count", "sha256", "max_input_tokens",
            "max_new_tokens", "seed",
        }:
            raise WorkerError("INPUT_MANIFEST_INVALID")

        output_dir = args.output_dir
        if (
            output_dir.parent != Path("/output")
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", output_dir.name)
        ):
            raise WorkerError("OUTPUT_DIRECTORY_INVALID")
        if output_dir.is_symlink() or output_dir.exists():
            raise WorkerError("OUTPUT_DIRECTORY_MUST_BE_NEW")
        parent = output_dir.parent
        OutputManager._check_root(parent)
        output_dir.mkdir(mode=0o700)
        os.chmod(output_dir, 0o700)
        OutputManager.probe(output_dir)

        selected = profile["model_profiles"][args.model_role]
        expected_files = profile["tokenizer_file_hashes"][args.model_role]
        model_id = selected["model"]
        revision = selected["revision"]
        output_path = output_dir / f"{args.model_role.lower()}-outputs.private.json"

        import torch
        import transformers

        if (
            torch.__version__ != "2.6.0+cu124"
            or torch.version.cuda != "12.4"
            or transformers.__version__ != "4.57.1"
        ):
            raise WorkerError("PINNED_RUNTIME_DEPENDENCY_MISMATCH")
        if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
            raise WorkerError("CUDA_BF16_RUNTIME_REQUIRED")

        with tempfile.TemporaryDirectory(prefix=f"r60-p4-{args.model_role}-") as tmp:
            snapshot = download_pinned_tokenizer_snapshot(
                model_id=model_id,
                revision=revision,
                destination=Path(tmp) / "tokenizer",
                expected_file_hashes=expected_files,
            )
            backend = TransformersGenerationBackend.from_pretrained(
                model_id=model_id,
                revision=revision,
                template_source=selected["chat_template_source"],
                expected_template_sha256=selected["chat_template_sha256"],
                tokenizer_snapshot=snapshot,
                expected_tokenizer_file_hashes=expected_files,
                torch_module=torch,
                transformers_module=transformers,
            )
            if backend.gpu_started is not True:
                raise WorkerError("MODEL_NOT_RESIDENT_ON_CUDA")
            receipt = run_generation_batch(
                profile=profile,
                model_role=args.model_role,
                manifest=manifest,
                input_path=args.input,
                output_path=output_path,
                backend=backend,
            )
            safe = receipt.to_safe_dict()
            safe.update({
                "dependency_lock_sha256": lock_sha,
                "runtime_digest": runtime_digest,
                "model_revision": revision,
                "private_output_path": output_path.name,
                "synthetic_only": args.synthetic_authorization is not None,
                "input_sha256": manifest["sha256"],
                "cpu_calibrated_input_tokens": (
                    profile.get("synthetic_only_runtime_scope", {}).get("input_tokens_cpu_calibrated")
                    if args.synthetic_authorization is not None else None
                ),
            })
            print(json.dumps(safe, sort_keys=True))
            return 0 if receipt.status != "GENERATION_BATCH_HOLD_UNRECOGNIZED_STOP" else 3
    except (OSError, RuntimeError, TypeError, ValueError, KeyError, ImportError) as exc:
        code = str(exc) if isinstance(exc, WorkerError) else "WORKER_RUNTIME_VALIDATION_FAILED"
        print(json.dumps({
            "schema": "storyforge_r60_generation_worker_receipt_safe_v1",
            "status": "GENERATION_WORKER_HOLD",
            "reason_code": code,
            "private_values_emitted": False,
            "inference_started": False,
            "gpu_started": False,
            "training_started": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
