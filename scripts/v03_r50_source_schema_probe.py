"""Metadata-only structural probe of R50 raw narrative JSONL.

Never emits original values, character names, texts or untrusted JSON object keys
except vetted schema-like ASCII identifiers. Does not establish Held-out admission.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SOURCE = Path("evaluations/v0.2/source-archives/16-20")
SCHEMA_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,39}$")


def safe_keys(x: object) -> list[str]:
    if not isinstance(x, dict):
        return []
    return sorted(k for k in x if SCHEMA_KEY.fullmatch(k))


def structure(repo: Path) -> dict:
    all_worlds = []
    for folder in sorted((repo / SOURCE).iterdir()):
        if not folder.is_dir() or folder.is_symlink():
            raise ValueError("invalid source folder")
        rank = int(folder.name.split("-", 1)[0])
        source = folder / (folder.name + ".jsonl")
        if not source.is_file():
            raise FileNotFoundError(source)
        count = 0
        example = None
        with source.open(encoding="utf-8-sig") as stream:
            for line in stream:
                if not line.strip():
                    raise ValueError("blank JSONL line")
                value = json.loads(line)
                if example is None:
                    example = value
                count += 1
        if count < 1:
            raise ValueError("no original source rows")
        x = example
        first_child = {}
        if isinstance(x, dict):
            for k in safe_keys(x):
                v = x[k]
                if isinstance(v, list):
                    first_child[k] = {
                        "type": "list",
                        "first_type": type(v[0]).__name__ if v else "empty",
                        "first_keys": safe_keys(v[0]) if v else [],
                    }
                elif isinstance(v, dict):
                    first_child[k] = {
                        "type": "dict",
                        "keys": safe_keys(v),
                    }
                else:
                    first_child[k] = {"type": type(v).__name__}
        all_worlds.append({
            "rank": rank, "rows": count, "root_type": type(x).__name__,
            "root_keys": safe_keys(x), "schema_fields": first_child,
        })
    if {w["rank"] for w in all_worlds} != set(range(16, 21)):
        raise ValueError("unexpected story ranks")
    return {
        "schema": "storyforge-r50-private-source-structure-v1",
        "status": "SOURCE_JSONL_SCHEMA_IDENTIFIED__DEDUP_NOT_YET_PERFORMED",
        "worlds": all_worlds,
        "no_source_text_output": True,
        "heldout_sealed": False,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    report = structure(a.repo.resolve())
    data = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if a.output:
        with a.output.open("x", encoding="utf-8") as file:
            file.write(data)
    else:
        print(data, end="")
