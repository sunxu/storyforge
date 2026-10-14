#!/usr/bin/env python3
"""Reconstruct immutable StoryForge R45 49/15 inputs from private R27 data."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build(source: Path, manifest: Path, dest: Path) -> dict:
    meta = json.loads(manifest.read_text(encoding="utf-8"))
    if sha(source) != meta["original_r27_sha256"]:
        raise ValueError("R27 source SHA256 mismatch")
    rows = [json.loads(x) for x in source.read_bytes().splitlines() if x.strip()]
    if len(rows) != 117: raise ValueError("R27 should have 117 rows")
    by_id = {r["id"]: r for r in rows}
    if len(by_id) != 117: raise ValueError("duplicate source IDs")
    ids = meta["train_ids"] + meta["validation_ids"]
    if len(meta["train_ids"]) != 49 or len(meta["validation_ids"]) != 15 or len(set(ids)) != 64:
        raise ValueError("invalid R45 49/15 selection")
    if any(x not in by_id for x in ids): raise ValueError("unknown R45 sample ID")
    dest.mkdir(parents=True, exist_ok=True)
    world_sets = {}
    checks = {}
    for split, expected in (("train", 49), ("validation", 15)):
        members = [by_id[k] for k in meta[split + "_ids"]]
        worlds = set()
        for row in members:
            messages, md = row["messages"], row["metadata"]
            if md.get("dataset_admission") != "NOT_APPROVED":
                raise ValueError("source admission changed")
            if md.get("approved_split") is not None: raise ValueError("formal approval spoofed")
            if not (messages[0]["role"] == "system" and messages[-2]["role"] == "user"
                    and messages[-1]["role"] == "assistant"):
                raise ValueError("invalid dialogue roles")
            if any(x.get("loss") is not False for x in messages[:-1]):
                raise ValueError("historical/system/user loss leak")
            if messages[-1].get("loss") is not True:
                raise ValueError("missing final supervised target")
            if hashlib.sha256(messages[-1]["content"].encode()).hexdigest() != md["target_sha256"]:
                raise ValueError("target SHA mismatch")
            worlds.add(md["source_story_id"])
        payload = "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n"
                          for r in members).encode()
        out = dest / (split + ".jsonl")
        if out.exists() and out.read_bytes() != payload:
            raise ValueError("refusing to overwrite changed dataset")
        out.write_bytes(payload)
        if sha(out) != meta[split + "_sha256"]: raise ValueError(split + " final R45 SHA mismatch")
        checks[split] = {"rows": expected, "sha256": sha(out)}
        world_sets[split] = sorted(worlds)
    if set(world_sets["train"]) & set(world_sets["validation"]):
        raise ValueError("train-validation story overlap")
    known_link = {"efd7a773-9393-4055-a4c8-b83fbf1a5842",
                  "b8046b69-cf68-443d-9218-a16b5255dafd"}
    if known_link & set(world_sets["train"]) and known_link & set(world_sets["validation"]):
        raise ValueError("known cross-story linked world overlap")
    proof = {"status": "R46_R45_EXACT_49_15_REBUILT", "source_sha256": sha(source),
             "splits": checks, "worlds": world_sets, "formal_training_approved": False}
    (dest / "reconstruction_proof.json").write_text(json.dumps(proof, indent=2) + "\n")
    return proof

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()
    print(json.dumps(build(args.source, args.manifest, args.output_dir)))
