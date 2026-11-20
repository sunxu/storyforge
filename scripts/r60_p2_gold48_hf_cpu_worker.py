"""HF CPU-only Gold48 tokenizer worker. No model weights/inference/training.

Reuse prior Gold48 token preflight.assess and the shared token_preflight core,
plus hf_runtime input/output/resource primitives. Only SAFE summaries go to
stdout and to the dedicated Owner-private RW result. No story names, token ids,
original replies, per-case hashes or exception texts leave the private volume.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from importlib.metadata import version
from pathlib import Path

from r60_p2_gold48_token_preflight_cpu import MODEL, REVISION, assess
from storyforge_dataset.hf_runtime import (
    InputManager,
    OutputManager,
    ResourceGuard,
    RuntimeContext,
)

RUN_RE = re.compile(r"r60-gold48-cpu-\d{8}T\d{6}Z-[0-9a-f]{12}\Z")
SCHEMA = "storyforge_r60_gold48_hf_cpu_token_receipt_safe_v1"
MANIFEST_SCHEMA = "storyforge_r60_gold48_hf_cpu_token_stage_private_v1"
STAGED_INPUT = "private/GOLD48_HF_CPU_MINIMAL_INPUT_PRIVATE.json"
RECEIPT_NAME = "GOLD48_HF_CPU_TOKEN_SAFE.json"
EXPECTED = {
    "transformers": "5.16.1",
    "tokenizers": "0.23.3",
    "huggingface_hub": "1.33.0",
    "jinja2": "3.1.6",
    "sentencepiece": "0.2.1",
    "regex": "2026.11.7",
}
MAX_STAGE_FILE = 32 * 1024 * 1024


class Hold(ValueError):
    pass


def require(value, reason):
    if not value:
        raise Hold(reason)


def stage_check(stage, run_key):
    require(RUN_RE.fullmatch(run_key) is not None
            and stage.is_dir() and not stage.is_symlink(),
            "RUN_KEY_OR_STAGE_HOLD")
    raw = InputManager.open_verified(
        stage / "SHA256_MANIFEST_PRIVATE.json", max_bytes=32768
    ).read_bytes()
    manifest = json.loads(raw)
    require(isinstance(manifest, dict)
            and manifest.get("schema") == MANIFEST_SCHEMA
            and manifest.get("status") == "STAGED_NOT_SUBMITTED"
            and manifest.get("run_key") == run_key
            and manifest.get("candidate_count") == 48
            and manifest.get("original_reference_present") is False
            and manifest.get("model") == MODEL
            and manifest.get("model_revision") == REVISION,
            "MANIFEST_IDENTITY_HOLD")
    files = manifest.get("files")
    require(isinstance(files, dict) and STAGED_INPUT in files
            and len(files) >= 8
            and all(isinstance(k, str) and k and not k.startswith("/")
                    and ".." not in Path(k).parts
                    and isinstance(digest, str)
                    and re.fullmatch(r"[0-9a-f]{64}", digest) is not None
                    for k, digest in files.items()),
            "STAGE_FILE_HASH_SHAPE_HOLD")
    actual = {
        p.relative_to(stage).as_posix()
        for p in stage.rglob("*")
        if p.is_file() and not p.is_symlink()
    }
    require(actual == set(files) | {"SHA256_MANIFEST_PRIVATE.json"},
            "STAGE_FILESET_HOLD")
    for name, digest in files.items():
        InputManager.open_verified(
            stage / name, max_bytes=MAX_STAGE_FILE,
            expected_sha256=digest,
        )
    return files[STAGED_INPUT]


def run(stage, run_key, *, tokenizer_factory=None, check_runtime=True):
    out = {
        "schema": SCHEMA,
        "status": "GOLD48_HF_CPU_TOKEN_PREFLIGHT_HOLD",
        "reason_code": "UNVERIFIED",
        "stage": "RUNTIME",
        "run_key": run_key if isinstance(run_key, str) and RUN_RE.fullmatch(run_key)
        else "INVALID_RUN_KEY",
        "model": MODEL,
        "model_revision": REVISION,
        "input_sha256_verified": False,
        "tokenizer_checked": False,
        "case_count": 0,
        "owner_gold48_freeze": False,
        "training_authorized": False,
        "gpu_started": False,
        "model_calls": 0,
        "private_values_emitted": False,
    }
    try:
        require(RUN_RE.fullmatch(run_key) is not None, "RUN_KEY_HOLD")
        if check_runtime:
            runtime = RuntimeContext.detect(profile="cpu")
            require(runtime.runtime == "HF_JOB" and runtime.operating_system == "linux",
                    "EXPECTED_HF_CPU_JOB_HOLD")
            resource = ResourceGuard.check_cpu_only()
            require(resource.status == "PASS", "CPU_PROFILE_RESOURCE_HOLD")
        out["stage"] = "INPUT_INTEGRITY"
        input_sha = stage_check(stage, run_key)
        out["input_sha256_verified"] = True
        out["stage"] = "TOKENIZER_DEPENDENCIES"
        if tokenizer_factory is None:
            for package, expected_version in EXPECTED.items():
                require(version(package) == expected_version,
                        "PINNED_CPU_DEPENDENCY_HOLD")
            from transformers import AutoTokenizer
            tokenizer_factory = AutoTokenizer.from_pretrained
        out["stage"] = "TOKENIZER_LOAD"
        tokenizer = tokenizer_factory(MODEL, revision=REVISION,
                                      trust_remote_code=False)
        out["stage"] = "TOKEN_COUNT"
        # Public read-only HF mount can normalize file modes; copy to a
        # 0600 temporary file for the existing validated Gold48 preflight.
        with tempfile.TemporaryDirectory(prefix="r60-gold48-cpu-") as root:
            private = Path(root) / "input.private.json"
            data = InputManager.open_verified(
                stage / STAGED_INPUT, max_bytes=MAX_STAGE_FILE,
                expected_sha256=input_sha,
            ).read_bytes()
            fd = os.open(private, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
            details, receipt = assess(private, tokenizer, version("transformers")
                                      if check_runtime else "5.16.1")
        require(receipt["status"] ==
                "GOLD48_48_INPUT_TOKEN_PREFLIGHT_COMPLETE__NO_FREEZE"
                and receipt["case_count"] == 48
                and receipt["chat_template_modes_checked"] == 2,
                "GOLD48_SOURCE_TOKEN_PREFLIGHT_HOLD")
        out.update(
            status="GOLD48_HF_CPU_TOKEN_PREFLIGHT_COMPLETE__NO_FREEZE",
            reason_code="ACTUAL_PINNED_CHAT_TEMPLATE_TOKENS_MEASURED",
            stage="COMPLETE",
            case_count=48,
            tokenizer_checked=True,
            tokenizer_model_pinned=True,
            tokenizer_revision_pinned=True,
            tokenizer_version=details["tokenizer_version"],
            memory_pretarget_verified_count=receipt["memory_pretarget_verified_count"],
            memory_unverified_omitted_count=receipt["memory_unverified_omitted_count"],
            mode_stats=receipt["mode_stats"],
            diagnostic_budgets_only=True,
            full_model_runtime_compatibility_verified=False,
        )
    except Exception:  # noqa: BLE001 - never disclose private exception details
        out["reason_code"] = out["stage"] + "_HOLD"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=Path, default=Path("/input/gold48"))
    ap.add_argument("--output", type=Path, default=Path("/output"))
    ap.add_argument("--run-key", required=True)
    args = ap.parse_args()
    result = run(args.stage, args.run_key)
    try:
        capability = OutputManager.probe(args.output)
        if not capability.writable:
            raise ValueError("OUTPUT_PROBE_HOLD")
        OutputManager.write_safe(args.output / RECEIPT_NAME, result)
    except Exception:  # noqa: BLE001 - no traceback, contents or paths
        print("GOLD48_HF_CPU_OUTPUT_PUBLICATION_HOLD")
        return 42
    print(json.dumps(result, sort_keys=True))
    return 0 if result["tokenizer_checked"] else 42


if __name__ == "__main__":
    raise SystemExit(main())
