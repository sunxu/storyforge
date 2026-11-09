"""Owner-local P2-B 30/90 build or verify, with SAFE-only stdout."""
from __future__ import annotations

import argparse
import json
import stat
from pathlib import Path

from scripts import r60_calibration_p0_freeze as p0
from storyforge_gold_quality import hf_owner_adjudication_v2 as base
from storyforge_gold_quality import hf_owner_heldout_p2b_v1 as heldout


def _private_dir(path: Path, repo: Path, *, must_exist: bool) -> Path:
    path = path.expanduser()
    if (not path.is_absolute() or path.is_symlink()
            or any(parent.is_symlink() for parent in path.parents)
            or (must_exist and not path.is_dir())
            or (must_exist and stat.S_IMODE(path.stat().st_mode) != 0o700)
            or path.resolve(strict=False) == repo
            or repo in path.resolve(strict=False).parents):
        raise base.AdjudicationHold("P2B_PRIVATE_PACKAGE_DIR_HOLD")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--owner-data-root", type=Path,
                        default=Path.home() / ".local/share/storyforge")
    parser.add_argument("--p0-freeze-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--package-dir", type=Path,
                        help="Frozen P2-B package directory for --verify")
    parser.add_argument("--owner-results-dir", type=Path,
                        help="Directory containing formal Owner result files")
    parser.add_argument("--receipt-dir", type=Path,
                        help="Create-only directory for verifier receipts")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        repo = args.repo_root.resolve(strict=True)
        out = args.output_dir.expanduser() if args.output_dir is not None else None
        if args.verify:
            split_mode = any(x is not None for x in
                             (args.package_dir, args.owner_results_dir, args.receipt_dir))
            if split_mode:
                if not all(x is not None for x in
                           (args.package_dir, args.owner_results_dir, args.receipt_dir)):
                    raise base.AdjudicationHold("P2B_VERIFIER_PATHS_INCOMPLETE")
                package_dir = _private_dir(args.package_dir, repo, must_exist=True)
                owner_dir = _private_dir(args.owner_results_dir, repo, must_exist=True)
                receipt_dir = _private_dir(args.receipt_dir, repo, must_exist=True)
                resolved_dirs = {
                    package_dir.resolve(strict=True),
                    owner_dir.resolve(strict=True),
                    receipt_dir.resolve(strict=True),
                }
                if len(resolved_dirs) != 3:
                    raise base.AdjudicationHold("P2B_VERIFIER_DIRECTORIES_MUST_BE_DISTINCT")
                inputs = [
                    base._read_private(package_dir / filename, repo)
                    for filename in (heldout.PACKET_NAME, heldout.MANIFEST_NAME,
                                     heldout.MAP_NAME)
                ] + [
                    base._read_private(owner_dir / filename, repo)
                    for filename in (heldout.RESULT_NAME, heldout.CHECK_NAME)
                ]
                packet_raw, manifest_raw, map_raw, result_raw, check_raw = inputs
                manifest, safe = heldout.verify_package(
                    packet_raw, result_raw, check_raw, manifest_raw, map_raw
                )
                target = receipt_dir / "P2B_REVIEW_FINAL_SAFE.json"
                base._write_once(target, base.canonical(safe) + b"\n")
            else:
                if out is None:
                    raise base.AdjudicationHold("P2B_PRIVATE_PACKAGE_DIR_HOLD")
                out = _private_dir(out, repo, must_exist=True)
                inputs = [base._read_private(out / filename, repo) for filename in
                          (heldout.PACKET_NAME, heldout.RESULT_NAME, heldout.CHECK_NAME,
                           heldout.MANIFEST_NAME, heldout.MAP_NAME)]
                manifest, safe = heldout.verify_package(
                    inputs[0], inputs[1], inputs[2], inputs[3], inputs[4]
                )
            created = []
            if not (args.package_dir is not None):
                try:
                    for name, obj in (
                        ("P2B_OWNER_RESULTS_MANIFEST_PRIVATE.json", manifest),
                        ("P2B_OWNER_RESULTS_SAFE.json", safe),
                    ):
                        target = out / name
                        base._write_once(target, base.canonical(obj) + b"\n")
                        created.append(target)
                except BaseException:
                    for target in reversed(created):
                        target.unlink(missing_ok=True)
                    raise
        else:
            if args.p0_freeze_dir is None or args.output_dir is None:
                raise base.AdjudicationHold("P2B_PREPARE_PATHS_INCOMPLETE")
            owner_root = args.owner_data_root.expanduser().resolve(strict=True)
            freeze = args.p0_freeze_dir.expanduser()
            safe = heldout.prepare(
                freeze / "GOLD72_CALIBRATION_MANIFEST_PRIVATE.json",
                freeze / "R60_SEVERE10_CALIBRATION_MANIFEST_PRIVATE.json",
                freeze / "CALIBRATION_CROSSSET_DEDUP_PRIVATE.json",
                owner_root / p0.GOLD["c_dir"] / "R60_GOLD72_REVIEWER_C_BLIND_PACKETS_PRIVATE.jsonl",
                owner_root / p0.PILOT["c_dir"] / "C_BLIND_PACKETS_PRIVATE.jsonl",
                out, repo, dry_run=not args.write,
            )
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True))
        return 0
    except (base.AdjudicationHold, ValueError, TypeError, KeyError, OSError) as exc:
        reason = str(exc) if isinstance(exc, base.AdjudicationHold) else "INPUT_OR_IO_ERROR"
        print(json.dumps({
            "schema": "storyforge_r60_p2b_safe_v1",
            "status": "P2B_HOLD",
            "reason_code": reason,
            "private_values_emitted": False,
            "quality_v1_admitted": 0, "training_authorized": False,
            "gpu_started": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
