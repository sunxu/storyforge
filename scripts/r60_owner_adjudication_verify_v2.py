"""Verify Owner's 20 adjudications and 60 semantic checks; write private receipts only."""
from __future__ import annotations

import argparse
import json
import stat
from pathlib import Path

from storyforge_gold_quality import hf_owner_adjudication_v2 as adjudication


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--package-dir", type=Path, required=True)
    args = parser.parse_args()
    output_dir = args.package_dir.expanduser()
    try:
        repo_root = args.repo_root.resolve(strict=True)
        if (not output_dir.is_absolute() or output_dir.is_symlink()
                or not output_dir.is_dir()
                or stat.S_IMODE(output_dir.stat().st_mode) != 0o700
                or any(parent.is_symlink() for parent in output_dir.parents)
                or output_dir.resolve(strict=True) == repo_root
                or repo_root in output_dir.resolve(strict=True).parents):
            raise adjudication.AdjudicationHold("PRIVATE_PACKAGE_DIRECTORY_HOLD")
        packet_raw = adjudication._read_private(
            output_dir / adjudication.PACKET_NAME, repo_root
        )
        result_raw = adjudication._read_private(
            output_dir / "OWNER_ADJUDICATION_RESULTS_PRIVATE.jsonl", repo_root
        )
        semantic_raw = adjudication._read_private(
            output_dir / "OWNER_SEMANTIC_ENTAILMENT_CHECKS_PRIVATE.jsonl", repo_root
        )
        manifest, safe = adjudication.verify_owner_results(
            packet_raw, result_raw, semantic_raw
        )
        outputs = (
            ("OWNER_ADJUDICATION_RESULTS_MANIFEST_PRIVATE.json",
             adjudication.canonical(manifest) + b"\n"),
            ("OWNER_ADJUDICATION_RESULTS_SAFE.json",
             adjudication.canonical(safe) + b"\n"),
        )
        created: list[Path] = []
        try:
            for filename, raw in outputs:
                target = output_dir / filename
                adjudication._write_once(target, raw)
                created.append(target)
        except BaseException:
            for target in reversed(created):
                target.unlink(missing_ok=True)
            raise
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True))
        return 0
    except (adjudication.AdjudicationHold, OSError, ValueError, TypeError, KeyError) as exc:
        reason = (
            str(exc) if isinstance(exc, adjudication.AdjudicationHold)
            else "INPUT_OR_IO_ERROR"
        )
        print(json.dumps({
            "schema": "storyforge_r60_owner_adjudication_results_safe_v2",
            "status": "OWNER_RESULT_VERIFICATION_HOLD",
            "reason_code": reason,
            "private_values_emitted": False,
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
