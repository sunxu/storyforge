"""Owner-local P2-B 30/90 build or verify, with SAFE-only stdout."""
from __future__ import annotations

import argparse
import json
import stat
from pathlib import Path

from scripts import r60_calibration_p0_freeze as p0
from storyforge_gold_quality import hf_owner_adjudication_v2 as base
from storyforge_gold_quality import hf_owner_heldout_p2b_v1 as heldout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--owner-data-root", type=Path,
                        default=Path.home() / ".local/share/storyforge")
    parser.add_argument("--p0-freeze-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        repo = args.repo_root.resolve(strict=True)
        out = args.output_dir.expanduser()
        if args.verify:
            if (not out.is_absolute() or out.is_symlink() or not out.is_dir()
                    or any(p.is_symlink() for p in out.parents)
                    or stat.S_IMODE(out.stat().st_mode) != 0o700
                    or out.resolve(strict=True) == repo
                    or repo in out.resolve(strict=True).parents):
                raise base.AdjudicationHold("P2B_PRIVATE_PACKAGE_DIR_HOLD")
            inputs = [base._read_private(out / filename, repo) for filename in
                      (heldout.PACKET_NAME, heldout.RESULT_NAME, heldout.CHECK_NAME)]
            manifest, safe = heldout.verify(*inputs)
            created = []
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
