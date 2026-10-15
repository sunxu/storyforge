"""R50 independent prompt *provenance* gate: read-only, no GPU, no answers.

Input prompts and case provenance remain outside Git; output contains counts only.
This verifies chronology/identity and verbatim historical context. It does not
certify authorship, semantic world isolation, card facts or model quality.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path

from v03_r50_verify_sources import verify as verify_source_receipt

ROOT = Path("evaluations/v0.2/source-archives/16-20")
REQUIRED = {"case_id", "story_number", "source_story_id", "source_session_id",
            "cutoff_message_id", "history_message_ids", "card_evidence"}


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8-sig") as stream:
        for line in stream:
            if not line.strip():
                raise ValueError("blank input line")
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError("non-object JSONL record")
            rows.append(item)
    return rows


def timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("required source timestamp absent")
    x = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if x.tzinfo is None:
        raise ValueError("source timestamp lacks timezone")
    return x


def fold(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def select_card(card: dict, evidence: dict, cutoff: datetime) -> str:
    if not isinstance(evidence, dict) or set(evidence) != {"kind", "record_id"}:
        raise ValueError("card evidence kind/record_id required")
    kind = evidence["kind"]
    if kind == "export_time_card":
        candidates = [card.get("export_time_card")]
        field = "updated_at"
    elif kind == "content_versions":
        candidates = card.get("content_versions") or []
        field = "source_updated_at"
    elif kind == "moderation_source_snapshots":
        candidates = card.get("moderation_source_snapshots") or []
        field = "created_at"
    else:
        raise ValueError("unknown historical card evidence kind")
    matches = [x for x in candidates if isinstance(x, dict)
               and x.get("id") == evidence["record_id"]]
    if len(matches) != 1:
        raise ValueError("historical card evidence record missing or ambiguous")
    chosen = matches[0]
    time = timestamp(chosen.get(field))
    if time > cutoff:
        raise ValueError("historical card evidence postdates case cutoff")
    return kind


def verify_case_sources(repo: Path, inputs: list[dict], provenance: list[dict]) -> dict:
    if not 40 <= len(inputs) <= 60 or len(inputs) != len(provenance):
        raise ValueError("40-60 matching input and provenance cases required")
    if any(not isinstance(r, dict) or not isinstance(r.get("case_id"), str)
           for r in inputs + provenance):
        raise ValueError("case_id missing or invalid")
    inp_by_id = {r["case_id"]: r for r in inputs}
    prv_by_id = {r["case_id"]: r for r in provenance}
    if len(inp_by_id) != len(inputs) or len(prv_by_id) != len(provenance):
        raise ValueError("duplicate case_id")
    if inp_by_id.keys() != prv_by_id.keys():
        raise ValueError("unpaired prompt/provenance case")
    source = {}
    for folder in sorted((repo / ROOT).iterdir()):
        if not folder.is_dir() or folder.is_symlink():
            raise ValueError("unexpected source entry")
        rank = int(folder.name.split("-", 1)[0])
        card = json.loads((folder / "story-cards.json").read_text(encoding="utf-8"))
        transcript, = read_jsonl(folder / (folder.name + ".jsonl"))
        session = transcript.get("session")
        if not isinstance(session, dict):
            raise ValueError("source session missing")
        if card.get("rank") != rank or transcript.get("rank") != rank:
            raise ValueError("source story rank mismatch")
        if card.get("story_id") != transcript.get("story", {}).get("id"):
            raise ValueError("source story identity mismatch")
        if card.get("session_id") != session.get("session_id"):
            raise ValueError("source session identity mismatch")
        messages = transcript.get("messages")
        if not isinstance(messages, list):
            raise ValueError("source message list missing")
        ids = {}
        for position, message in enumerate(messages):
            if not isinstance(message, dict):
                raise ValueError("non-object source message")
            msg_id = message.get("id")
            if isinstance(msg_id, str) and msg_id:
                if msg_id in ids:
                    raise ValueError("duplicate message IDs in source")
                ids[msg_id] = position
        source[rank] = (card, messages, ids)
    if set(source) != set(range(16, 21)):
        raise ValueError("source stories 16-20 incomplete")

    worlds = {}
    card_kind_counts = Counter()
    prior_player_input_reuse = 0
    for case_id in inp_by_id:
        row = inp_by_id[case_id]
        att = prv_by_id[case_id]
        if set(att) != REQUIRED:
            raise ValueError("provenance schema differs")
        rank = att["story_number"]
        if not isinstance(rank, int) or isinstance(rank, bool) or rank not in source:
            raise ValueError("story_number not in source")
        if not isinstance(row.get("world_id"), str) or not row["world_id"]:
            raise ValueError("input world_id missing")
        if rank in worlds and worlds[rank] != row["world_id"]:
            raise ValueError("world_id inconsistent within a source story")
        if row["world_id"] in {v for k, v in worlds.items() if k != rank}:
            raise ValueError("world_id reused by different source stories")
        worlds[rank] = row["world_id"]
        card, messages, indices = source[rank]
        if card["story_id"] != att["source_story_id"] or card["session_id"] != att["source_session_id"]:
            raise ValueError("source story/session ID mismatch")
        cutoff_id = att["cutoff_message_id"]
        if not isinstance(cutoff_id, str) or cutoff_id not in indices:
            raise ValueError("invalid cutoff source message ID")
        end = indices[cutoff_id]
        cutoff = timestamp(messages[end].get("created_at"))
        cardsrc = select_card(card, att["card_evidence"], cutoff)
        card_kind_counts[cardsrc] += 1

        selected = att["history_message_ids"]
        hist = row.get("history")
        if not isinstance(hist, list) or not isinstance(selected, list) or not selected:
            raise ValueError("source-backed history required")
        if len(selected) != len(hist) or len(set(selected)) != len(selected):
            raise ValueError("historical source message count/ID conflict")
        positions = []
        for item, source_id in zip(hist, selected, strict=True):
            if not isinstance(source_id, str) or source_id not in indices:
                raise ValueError("history message ID not found")
            m = messages[indices[source_id]]
            if not isinstance(item, dict) or set(item) != {"role", "content"}:
                raise ValueError("historical prompt role/content invalid")
            if m.get("role") != item["role"] or m.get("content") != item["content"]:
                raise ValueError("historical prompt changed from immutable source")
            if item["role"] not in ("user", "assistant"):
                raise ValueError("unsupported historical role")
            if not isinstance(item["content"], str) or not item["content"].strip():
                raise ValueError("empty historical context")
            if timestamp(m.get("created_at")) > cutoff:
                raise ValueError("historical message occurs after cutoff")
            positions.append(indices[source_id])
        if positions[-1] != end:
            raise ValueError("last historical message must be the source cutoff")
        if any(b != a + 1 for a, b in zip(positions, positions[1:])):
            raise ValueError("history must be an unbroken consecutive source suffix")
        current = row.get("user_input")
        if not isinstance(current, str) or not current.strip():
            raise ValueError("missing independent current user input")
        fresh = fold(current)
        if len(fresh) >= 30 and any(fold(m.get("content", "")) == fresh
                                    for m in messages if m.get("role") == "user"
                                    and isinstance(m.get("content"), str)):
            prior_player_input_reuse += 1
    if len(worlds) < 4:
        raise ValueError("at least four distinct new worlds required")
    if prior_player_input_reuse:
        raise ValueError("new player input is copied verbatim from source conversation")
    return {
        "schema": "storyforge-r50-case-provenance-preflight-v1",
        "status": "SOURCE_CUTOFF_AND_VERBATIM_HISTORY_PASS__SEMANTIC_REVIEW_PENDING",
        "case_count": len(inputs),
        "source_story_case_counts": dict(sorted(Counter(
            str(a["story_number"]) for a in provenance).items())),
        "world_count": len(worlds),
        "card_evidence_type_counts": dict(sorted(card_kind_counts.items())),
        "source_history_exactly_matched": len(inputs),
        "future_source_card_or_history_accepted": False,
        "independent_authorship_attested": False,
        "semantic_world_and_card_fact_review": "PENDING",
        "private_r45_overlap": "PENDING",
        "new_cases_sealed_for_evaluation": False,
        "gpu_executed": False,
        "model_quality_promoted": False,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--inputs", type=Path, required=True)
    p.add_argument("--provenance", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    opts = p.parse_args()
    try:
        repo = opts.repo.resolve()
        for path in (opts.inputs, opts.provenance, opts.output):
            candidate = path.resolve()
            if candidate == repo or repo in candidate.parents:
                raise ValueError("private input/provenance/output must remain outside Git checkout")
        receipt = json.loads(opts.receipt.read_text(encoding="utf-8"))
        verify_source_receipt(repo, receipt)  # pinned Git bytes before source usage
        report = verify_case_sources(
            repo, read_jsonl(opts.inputs), read_jsonl(opts.provenance)
        )
        opts.output.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        fd = os.open(opts.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(report["status"])
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(f"R50_CASE_PROVENANCE_HOLD: {type(exc).__name__}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
