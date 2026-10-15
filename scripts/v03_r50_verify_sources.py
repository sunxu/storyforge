"""Read-only verification of R50 candidate story sources against a frozen Git receipt.

The tool checks bytes and computes SHA256 without viewing or modifying test prompts.
It does not certify independence, rights or model quality.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def digest_file(path: Path) -> tuple[int, str, str]:
    size = path.stat().st_size
    git_blob = hashlib.sha1(
        b"blob " + str(size).encode("ascii") + b"\0", usedforsecurity=False
    )
    sha256 = hashlib.sha256()
    count = 0
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            count += len(data)
            git_blob.update(data)
            sha256.update(data)
    if count != size:
        raise ValueError(f"file changed while reading: {path}")
    return count, git_blob.hexdigest(), sha256.hexdigest()


def verify(repo: Path, receipt: dict) -> dict:
    if receipt.get("schema") != "storyforge-r50-source-receipt-v1":
        raise ValueError("unexpected receipt schema")
    prefix = Path(receipt["source_root"])
    if prefix.is_absolute() or ".." in prefix.parts:
        raise ValueError("invalid source root")
    files = receipt.get("files")
    worlds = receipt.get("worlds", [])
    if not isinstance(files, list) or len(files) != 35:
        raise ValueError("expected exactly 35 source files")
    if len(worlds) != 5 or len({w["story_id"] for w in worlds}) != 5:
        raise ValueError("expected five different story IDs")

    seen = set()
    out = []
    for item in files:
        path = Path(item["path"])
        if path.is_absolute() or ".." in path.parts or prefix not in path.parents:
            raise ValueError(f"invalid file path: {path}")
        if str(path) in seen:
            raise ValueError(f"duplicate source: {path}")
        seen.add(str(path))
        source = repo / path
        if not source.is_file() or source.is_symlink():
            raise ValueError(f"missing file or symlink: {path}")
        size, git_sha, raw_sha = digest_file(source)
        if size != item["size_bytes"] or git_sha != item["git_blob_sha1"]:
            raise ValueError(f"source changed since Git commit: {path}")
        out.append({"path": str(path), "size_bytes": size, "sha256": raw_sha})

    present = {
        str(p.relative_to(repo))
        for p in (repo / prefix).rglob("*")
        if p.is_file()
    }
    if present != seen:
        raise ValueError(
            f"file inventory mismatch; missing={sorted(seen - present)} "
            f"extra={sorted(present - seen)}"
        )
    return {
        "schema": "storyforge-r50-local-source-sha256-v1",
        "status": "SOURCE_BYTES_VERIFIED_ONLY__NO_HELDOUT_ADMISSION",
        "source_commit": receipt["source_commit"],
        "file_count": len(out),
        "world_count": len(worlds),
        "total_bytes": sum(x["size_bytes"] for x in out),
        "files": out,
        "independent_heldout_cases": 0,
        "world_alias_and_train_test_isolation": "PENDING",
        "duplicate_screen": "PENDING",
        "human_provenance_review": "PENDING",
        "gpu_executed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
        report = verify(args.repo.resolve(), receipt)
        body = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(body)
        else:
            sys.stdout.write(body)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"R50_SOURCE_VERIFY_BLOCKED: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
