"""Prepare Gold-free, reproducible blind evaluation prompts without touching test by default."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def build_prompts(source: Path, destination: Path, manifest: Path) -> int:
    if destination.exists() or manifest.exists():
        raise FileExistsError("refusing to overwrite existing blind evaluation files")
    prompts = []
    entries = []
    for index, line in enumerate(source.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        row = json.loads(line)
        messages = row["messages"]
        if len(messages) < 2 or messages[-2].get("role") != "user":
            raise ValueError(f"sample {index}: unexpected tail")
        if messages[-1].get("role") != "assistant" or messages[-1].get("loss") is not True:
            raise ValueError(f"sample {index}: missing Gold target")
        prompt = [{"role": m["role"], "content": m["content"]} for m in messages[:-1]]
        normalized = json.dumps({"messages": prompt}, sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        sample_id = f"eval-{len(prompts):03d}-{digest[:12]}"
        prompts.append(json.dumps({"messages": prompt}, ensure_ascii=False))
        entries.append({"sample_id": sample_id, "prompt_sha256": digest,
                        "source_line": index + 1})
    if not prompts:
        raise ValueError("empty evaluation dataset")
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(prompts) + "\n", encoding="utf-8")
    manifest.write_text(json.dumps({"schema": "storyforge-blind-v1",
                                    "count": len(prompts),
                                    "samples": entries}, indent=2) + "\n",
                        encoding="utf-8")
    return len(prompts)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--allow-heldout", action="store_true")
    args = parser.parse_args()
    if "test" in args.source.name.lower() and not args.allow_heldout:
        parser.error("held-out test is locked; explicitly pass --allow-heldout after rubric freeze")
    print(f"BLIND_PROMPTS_PASS: {build_prompts(args.source, args.output, args.manifest)}")


if __name__ == "__main__":
    main()
