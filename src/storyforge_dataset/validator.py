from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .compiler import RawBundle


def validate_raw(root: Path, expected_selected: int | None = None) -> dict[str, Any]:
    bundle = RawBundle.load(root)
    types = Counter(r.get("record_type", "missing") for r in bundle.records)
    selected = [
        r
        for r in bundle.records
        if r.get("record_type") == "message"
        and r.get("role") == "assistant"
        and r.get("is_selected")
    ]
    story_ids = {
        r.get("story_id") for r in bundle.records if r.get("record_type") == "story_metadata"
    }
    transcripts = {
        r.get("transcript_id") for r in bundle.records if r.get("record_type") == "session"
    }

    issues: list[str] = []
    if expected_selected is not None and len(selected) != expected_selected:
        issues.append(f"expected {expected_selected} selected targets, found {len(selected)}")
    if not story_ids:
        issues.append("no story_metadata records")
    if not transcripts:
        issues.append("no session records")

    seen_target_ids: set[str] = set()
    for target in selected:
        mid = target.get("message_id")
        if not mid:
            issues.append("selected target without message_id")
        elif mid in seen_target_ids:
            issues.append(f"duplicate selected target message_id: {mid}")
        seen_target_ids.add(mid)
        if not (target.get("content") or "").strip():
            issues.append(f"empty selected target: {mid}")

    return {
        "ok": not issues,
        "record_count": len(bundle.records),
        "record_types": dict(types),
        "story_count": len(story_ids),
        "transcript_count": len(transcripts),
        "selected_target_count": len(selected),
        "issues": issues,
    }
