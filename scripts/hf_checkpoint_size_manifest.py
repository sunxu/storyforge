"""Enrich archived StoryForge v0.1 HF CPU Job hashes with size metadata.

This is a read-only metadata operation: no checkpoint bytes are downloaded,
no HF Jobs are submitted, and no objects are changed in the HF Bucket.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

CHECKPOINT_URI = (
    "hf://buckets/adradar/storyforge-training/baseline-runs/baseline/"
    "6ac75bafdf2184ac91acb293/output/v0-20261008-090236/checkpoint-9"
)
HASH_JOB_ID = "6ac8be0e095c578089304f37"
HASH_MARKER = "STORYFORGE_SHA256_PASS"
SECTION_HEADING = "## Baseline checkpoint SHA256 manifest (CPU verification, 2026-10-09)"
LINE_RE = re.compile(r"([0-9a-f]{64})  \./([^/\s]+)\Z")
DEFAULT_REGISTRY = Path(__file__).resolve().parents[1] / "docs/HF_RUN_REGISTRY.md"


def parse_archived_hashes(registry_text: str) -> dict[str, str]:
    """Parse only the archived checkpoint manifest block, rejecting ambiguity."""
    if registry_text.count(SECTION_HEADING) != 1:
        raise ValueError("Expected exactly one v0.1 checkpoint SHA256 section")
    after_heading = registry_text.split(SECTION_HEADING, 1)[1]
    fence = chr(96) * 3
    if fence + "text\n" not in after_heading:
        raise ValueError("SHA256 manifest fenced block not found")
    block = after_heading.split(fence + "text\n", 1)[1].split("\n" + fence, 1)
    if len(block) != 2:
        raise ValueError("SHA256 manifest closing fence not found")
    hashes: dict[str, str] = {}
    for line in block[0].splitlines():
        if not line.strip():
            continue
        match = LINE_RE.fullmatch(line)
        if not match:
            raise ValueError(f"Invalid SHA256 manifest entry: {line!r}")
        sha, name = match.groups()
        if name in hashes:
            raise ValueError(f"Duplicate checkpoint filename: {name}")
        hashes[name] = sha
    if not {"adapter_model.safetensors", "adapter_config.json"} <= hashes.keys():
        raise ValueError("Critical adapter files missing from the archived manifest")
    return hashes


def build_report(fs: Any, hashes: dict[str, str], *, observed_at: str) -> dict[str, Any]:
    """Use only HF metadata listing; never open or download any file."""
    entries = fs.ls(CHECKPOINT_URI, detail=True, refresh=True)
    found: dict[str, int] = {}
    for item in entries:
        if not isinstance(item, dict) or item.get("type") != "file":
            raise ValueError(f"Unexpected non-file entry in checkpoint metadata: {item!r}")
        name = PurePosixPath(str(item.get("name", ""))).name
        size = item.get("size")
        if not name or name in found:
            raise ValueError(f"Missing or duplicate filename in bucket listing: {name!r}")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise ValueError(f"Missing/invalid byte size for {name}: {size!r}")
        found[name] = size
    missing = sorted(hashes.keys() - found.keys())
    unexpected = sorted(found.keys() - hashes.keys())
    if missing or unexpected:
        raise ValueError(f"Bucket listing differs from archived hash manifest: missing={missing}, unexpected={unexpected}")
    return {
        "schema_version": 1,
        "status": "SIZE_METADATA_PASS__SHA256_REPORTED_BY_PRIOR_CPU_JOB",
        "checkpoint_uri": CHECKPOINT_URI,
        "sha256_job_id": HASH_JOB_ID,
        "sha256_job_terminal_marker": HASH_MARKER,
        "sha256_provenance": "docs/HF_RUN_REGISTRY.md (prior CPU Job output)",
        "sha256_recomputed_by_this_script": False,
        "size_source": "HfFileSystem.ls(detail=True, refresh=True)",
        "metadata_checked_at_utc": observed_at,
        "file_count": len(found),
        "total_size_bytes": sum(found.values()),
        "files": [
            {"filename": name, "size_bytes": found[name], "sha256": hashes[name]}
            for name in sorted(hashes)
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path, help="New local JSON file (will never overwrite)")
    args = parser.parse_args()
    hashes = parse_archived_hashes(args.registry.read_text(encoding="utf-8"))
    from huggingface_hub import HfFileSystem

    report = build_report(
        HfFileSystem(), hashes,
        observed_at=datetime.now(UTC).isoformat(),
    )
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        with args.output.open("x", encoding="utf-8") as target:
            target.write(payload)
    print(payload, end="")


if __name__ == "__main__":
    main()
