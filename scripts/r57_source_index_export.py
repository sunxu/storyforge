"""R57 G2 owner-local *private* index exporter. Offline, read-only source intake.

No discovery, network, protected-evaluation reads, training or inference.
Never store the generated private index inside a Git worktree.
"""
import argparse
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path

INDEX_FORMAT = "storyforge-r57-training-lineage-private-index-v1"
PLAN_FORMAT = "storyforge-r57-g2-source-pin-plan-private-v1"
ALIAS_FORMAT = "storyforge-r57-g2-world-alias-private-v1"
SHA = re.compile(r"^[0-9a-f]{64}$")
COMPONENT = re.compile(r"^C_[A-Za-z0-9_-]{16,80}$")
MAX_SOURCE_BYTES = 128 * 1024 * 1024
MAX_META_BYTES = 8 * 1024 * 1024

# No fuzzy paths, recursive scans, URLs, or name-based file discovery.
SOURCE_PATHS = {
    "GOLD87": ("REPO", "evaluations/v0.2/gold-quality-87/gold_quality_accepted_87.jsonl", 87),
    "GOLD108": ("REPO", "evaluations/v0.2/gold-quality-108/gold_quality_accepted_108.jsonl", 108),
    "V01_TRAIN": ("REPO", "data/compiled/v0.3/train.jsonl", 65),
    "V01_VALIDATION": ("REPO", "data/compiled/v0.3/validation.jsonl", 15),
    "R46_TRAIN": ("PRIVATE", "r46/train.jsonl", 49),
    "R46_VALIDATION": ("PRIVATE", "r46/validation.jsonl", 15),
    "R54_TRAIN": ("PRIVATE", "r54/train.jsonl", 31),
    "R54_VALIDATION": ("PRIVATE", "r54/validation.jsonl", 9),
}
GIT_BLOBS = {
    "GOLD87": "a2038e18bee8ddef96b93bb6746270a462f9a6e4",
    "GOLD108": "eedb8ff83e6e0629dc2dbc57ee4681fdfde3df90",
    "V01_TRAIN": "3e64c9932ca43fefa8ecfb200085fe718581b6f9",
    "V01_VALIDATION": "db0ae8b86038be1b372d547fdb2d6b0b7e33b54e",
}
WORLD_FIELDS = {"story_id", "source_story_id"}


class ExportHold(ValueError):
    """Fail-closed without disclosing private sample text or IDs."""


def _check(value, expected):
    if not isinstance(value, dict) or set(value) != expected:
        raise ExportHold("unexpected/missing metadata fields")


def _sha(value):
    return isinstance(value, str) and SHA.fullmatch(value) is not None


def _guard_path(root, relative):
    """Allow only fixed relative locations without symlink components."""
    if not isinstance(relative, str) or relative.startswith("/") or ".." in Path(relative).parts:
        raise ExportHold("unsafe file path")
    if any("r50" in part.lower() for part in (str(root), relative)):
        raise ExportHold("protected source path forbidden")
    base = Path(root).absolute()
    path = base / relative
    probe = Path(path.anchor)
    for component in path.parts[1:]:
        probe = probe / component
        if probe.is_symlink():
            raise ExportHold("symlink input/output path forbidden")
    return path


def _read(root, relative, limit):
    path = _guard_path(root, relative)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as file:
        info = os.fstat(file.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise ExportHold("nonregular or oversized source file")
        payload = file.read(limit + 1)
    if len(payload) > limit:
        raise ExportHold("source grew beyond declared limit")
    return payload


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\\0" + data).hexdigest()


def _project_messages(messages):
    """Deterministic role/content projection, NOT ms-swift template byte proof."""
    if not isinstance(messages, list) or len(messages) < 2:
        raise ExportHold("missing message sequence")
    projected = []
    for msg in messages:
        if not isinstance(msg, dict) or msg.get("role") not in {"system", "assistant", "user"}:
            raise ExportHold("unsupported role")
        content = msg.get("content")
        if not isinstance(content, str):
            raise ExportHold("unsupported message content")
        projected.append({"role": msg["role"], "content": content})
    if projected[-1]["role"] != "assistant" or projected[-2]["role"] != "user":
        raise ExportHold("invalid final supervised target suffix")
    return projected


def _projection_sha(messages):
    return _digest(json.dumps(
        {"messages": messages}, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8"))


def _rows(raw, source_id, world_field, aliases, expected):
    entries = []
    lines = raw.splitlines()
    if len(lines) != expected or any(not ln.strip() for ln in lines):
        raise ExportHold("source row count/blank line mismatch")
    for line in lines:
        if len(line) > 3 * 1024 * 1024:
            raise ExportHold("oversized source row")
        try:
            row = json.loads(line)
        except (UnicodeError, ValueError) as exc:
            raise ExportHold("invalid source JSONL record") from exc
        if not isinstance(row, dict) or not isinstance(row.get("metadata"), dict):
            raise ExportHold("row missing metadata")
        metadata = row["metadata"]
        world = metadata.get(world_field)
        if not isinstance(world, str) or not world:
            raise ExportHold("world ID absent from chosen metadata field")
        component = aliases.get(world)
        if not isinstance(component, str) or not COMPONENT.fullmatch(component):
            raise ExportHold("unresolved world/alias component")
        messages = _project_messages(row.get("messages"))
        target = _digest(messages[-1]["content"].encode("utf-8"))
        # Check real per-row source pins when they exist; never trust them as the only input.
        for name in ("target_sha256", "target_sha256_utf8"):
            if name in metadata and metadata[name] != target:
                raise ExportHold("target digest contradicts source metadata")
        entries.append({
            "target_sha256": target,
            "input_sha256": _projection_sha(messages),
            "history_sha256": _projection_sha(messages[:-1]),
            "world_component_token": component,
        })
    return entries


def build_index(plan, aliases, *, repo_root, private_root, read=_read):
    """No writes. Return private index only after every available source validates."""
    _check(plan, {"schema", "no_protected_evaluation_accessed", "training_authorized",
                  "alias_map_sha256", "source_pins"})
    if (plan["schema"] != PLAN_FORMAT or
            plan["no_protected_evaluation_accessed"] is not True or
            plan["training_authorized"] is not False):
        raise ExportHold("plan trust boundary failed")
    if not _sha(plan["alias_map_sha256"]):
        raise ExportHold("alias-map pin missing")
    _check(aliases, {"schema", "story_to_component"})
    if aliases["schema"] != ALIAS_FORMAT or not isinstance(aliases["story_to_component"], dict):
        raise ExportHold("invalid alias map")
    amap = aliases["story_to_component"]
    if not amap or any(not isinstance(k, str) or not k or
                       not isinstance(v, str) or not COMPONENT.fullmatch(v)
                       for k, v in amap.items()):
        raise ExportHold("invalid alias map entries")
    pin_entries = plan["source_pins"]
    if not isinstance(pin_entries, dict) or not pin_entries or not set(pin_entries) <= SOURCE_PATHS.keys():
        raise ExportHold("unknown or absent source pin collections")
    collected = []
    for name in sorted(pin_entries):
        pin = pin_entries[name]
        _check(pin, {"sha256", "metadata_world_field"})
        if not _sha(pin["sha256"]) or pin["metadata_world_field"] not in WORLD_FIELDS:
            raise ExportHold("source pin/world-field invalid")
        which_root, rel, expected = SOURCE_PATHS[name]
        base = repo_root if which_root == "REPO" else private_root
        payload = read(base, rel, MAX_SOURCE_BYTES)
        if _digest(payload) != pin["sha256"]:
            raise ExportHold("source original byte digest mismatch")
        if name in GIT_BLOBS and _git_blob(payload) != GIT_BLOBS[name]:
            raise ExportHold("frozen Git Blob identity mismatch")
        collected.append({
            "id": name,
            "source_file_sha256": _digest(payload),
            "rows": _rows(payload, name, pin["metadata_world_field"], amap, expected),
        })
    return {
        "schema": INDEX_FORMAT,
        "no_protected_evaluation_accessed": True,
        "training_authorized": False,
        "sources": collected,
    }


def _put_private(parent, filename, payload):
    path = _guard_path(parent, filename)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as file:
        file.write(payload)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", required=True, type=Path)
    ap.add_argument("--private-root", required=True, type=Path)
    ap.add_argument("--plan-name", default="R57_G2_SOURCE_PINS_PRIVATE.json")
    ap.add_argument("--alias-name", default="R57_G2_ALIAS_GRAPH_PRIVATE.json")
    ap.add_argument("--index-name", default="R57_G2_SOURCE_INDEX_PRIVATE.json")
    args = ap.parse_args()
    try:
        repo = args.repo_root.resolve(strict=True)
        private = args.private_root.resolve(strict=True)
        if repo == private or repo in private.parents or private in repo.parents:
            raise ExportHold("private index area and Git worktree must be separate")
        for name in (args.plan_name, args.alias_name, args.index_name):
            if name != Path(name).name or "/" in name or "\\\\" in name:
                raise ExportHold("plan/alias/output names must be plain basenames")
            if "r50" in name.lower():
                raise ExportHold("protected path forbidden")
        if (private / args.index_name).exists() or (private / args.index_name).is_symlink():
            raise ExportHold("index exists; overwrite prohibited")
        plan_raw = _read(private, args.plan_name, MAX_META_BYTES)
        aliases_raw = _read(private, args.alias_name, MAX_META_BYTES)
        plan = json.loads(plan_raw)
        if not isinstance(plan, dict) or plan.get("alias_map_sha256") != _digest(aliases_raw):
            raise ExportHold("alias map SHA256 mismatch")
        aliases = json.loads(aliases_raw)
        index = build_index(plan, aliases, repo_root=repo, private_root=private)
        output = json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\\n"
        _put_private(private, args.index_name, output)
        counts = {row["id"]: len(row["rows"]) for row in index["sources"]}
        print(json.dumps({"status": "PRIVATE_INDEX_CREATED__NOT_G2_SOURCE_CERTIFIED",
                          "source_counts": counts, "training_authorized": False}, sort_keys=True))
        return 0
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        reason = "filesystem IO failed" if isinstance(exc, OSError) else str(exc)
        print(f"R57_G2_EXPORT_HOLD: {type(exc).__name__}: {reason}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
