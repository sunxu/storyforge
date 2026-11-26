"""R52 historical exposure triage of seven source worlds vs pinned old cohorts.

Checks v0.1 Train/Val/Test, frozen Gold87, optional private R45 Train49/Val15.
Exact UUID, normalized long-message equality and *sampled* normalized 120-
codepoint fragments are screening signals only. They do not certify absent
semantic aliases/paraphrases, owner world signoff, or Train/Val admissions.
"""
from __future__ import annotations
import argparse
import contextlib
import tempfile
import zipfile
import hashlib
import json
import os
import stat
import sys
from collections import Counter, defaultdict
from pathlib import Path

import v03_r52_reconcile_full21_world_graph as graph
import v03_r52_world_exact_isolation as exact
import v03_r51_gold195_readiness as gold
import v03_r50_private_r45_isolation as r45
from v03_r50_text_reuse_screen import normalized

HOLD = "PENDING_NOT_APPROVED"
MIN_EXACT = 80
FRAGMENT = 120
STRIDE = 40
MAX_EVIDENCE = 10000
R45_REQUIRED = {"train": 49, "validation": 15}
R45_ARCHIVE_NAMES = {
    "train": "R45_TRAIN_FROZEN_CANDIDATE_49_NOT_APPROVED.jsonl",
    "validation": "R45_VALIDATION_FROZEN_CANDIDATE_15_NOT_APPROVED.jsonl",
}
R45_MAX_MEMBER_BYTES = 128 * 1024 * 1024


def must(value, code):
    if not value:
        raise exact.GateHold(code)


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def probes(text: str):
    if len(text) < FRAGMENT:
        return
    spots = list(range(0, len(text) - FRAGMENT + 1, STRIDE))
    if not spots or spots[-1] != len(text) - FRAGMENT:
        spots.append(len(text) - FRAGMENT)
    for start in spots:
        yield text[start:start + FRAGMENT]


def rows_from_cohort(repo: Path, r45_train: Path | None,
                     r45_val: Path | None):
    sets = {}
    sha_pins = {}
    for name, (rel, count, story_count, expected) in exact.HISTORICAL.items():
        path = repo / rel
        must(path.is_file() and not path.is_symlink() and
             exact.sha_file(path) == expected, "V01_SOURCE_SHA_CHANGED")
        rows = list(exact.read_jsonl(path, private=False, count=count))
        story_ids = {row.get("metadata", {}).get("story_id") for row in rows}
        must(None not in story_ids and len(story_ids) == story_count,
             "V01_STORY_ID_SET_CHANGED")
        sets["v01_" + name] = rows
        sha_pins["v01_" + name] = expected
    gpath = repo / gold.GOLD87
    graw = gpath.read_bytes()
    must(gold.git_blob_sha1(graw) == gold.EXPECTED_GIT_SHA1_87,
         "GOLD87_FROZEN_GIT_BLOB_CHANGED")
    sets["gold87"] = gold.read_pinned_rows(
        repo, gold.GOLD87, 87, blob_sha1=gold.EXPECTED_GIT_SHA1_87)
    sha_pins["gold87_sha256"] = sha_bytes(graw)
    must((r45_train is None) == (r45_val is None),
         "R45_TWO_PRIVATE_SOURCES_REQUIRED_TOGETHER")
    if r45_train is not None:
        for label, path in (("r45_train", r45_train),
                            ("r45_validation", r45_val)):
            expected_split = label.removeprefix("r45_")
            spec = r45.FROZEN[expected_split]
            must(path.is_file() and not path.is_symlink() and
                 stat.S_IMODE(path.stat().st_mode) == 0o600 and
                 stat.S_IMODE(path.parent.stat().st_mode) & 0o077 == 0 and
                 exact.sha_file(path) == spec["sha256"],
                 "R45_FROZEN_PRIVATE_SOURCE_INVALID")
            sets[label] = list(exact.read_jsonl(
                path, private=True, count=spec["count"]))
            sha_pins[label] = spec["sha256"]
    return sets, sha_pins


def extract_verified_r45_archive(archive: Path, private_dir: Path) -> tuple[Path, Path]:
    """Read pinned two-source ZIP into a 0700 temporary directory only.

    Neither the original ZIP's arbitrary path names nor untrusted metadata
    influence output paths. No archive members are extracted by path.
    """
    must(archive.is_file() and not archive.is_symlink(),
         "R45_ARCHIVE_MISSING_OR_SYMLINK")
    must(private_dir.is_dir() and not private_dir.is_symlink() and
         stat.S_IMODE(private_dir.stat().st_mode) & 0o077 == 0,
         "R45_TEMP_DIRECTORY_NOT_PRIVATE")
    members = {}
    with zipfile.ZipFile(archive) as z:
        names = z.infolist()
        must(len(names) <= 10000, "R45_ARCHIVE_TOO_MANY_MEMBERS")
        for split, basename in R45_ARCHIVE_NAMES.items():
            hits = [info for info in names
                    if not info.is_dir() and
                    info.filename.rsplit("/", 1)[-1] == basename]
            must(len(hits) == 1, "R45_ORIGINAL_FROZEN_MEMBER_AMBIGUOUS")
            info = hits[0]
            must(0 < info.file_size <= R45_MAX_MEMBER_BYTES,
                 "R45_ORIGINAL_SOURCE_MEMBER_TOO_LARGE")
            payload = z.read(info)
            pin = r45.FROZEN[split]
            must(sha_bytes(payload) == pin["sha256"] and
                 len(payload.splitlines()) == pin["count"],
                 "R45_FROZEN_SOURCE_BYTES_OR_ROWS_CHANGED")
            dest = private_dir / f"r45_{split}.jsonl"
            fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
            members[split] = dest
    return members["train"], members["validation"]


def get_historical_messages(row, corpus):
    must(isinstance(row, dict), "HISTORIC_ROW_NOT_OBJECT")
    meta = row.get("metadata")
    must(isinstance(meta, dict), "HISTORIC_METADATA_MISSING")
    sid = meta.get("source_story_id") if corpus.startswith("r45_") else (
        meta.get("story_id") or meta.get("source_story_id"))
    must(isinstance(sid, str) and bool(sid.strip()),
         "HISTORIC_SOURCE_STORY_ID_MISSING")
    messages = row.get("messages")
    must(isinstance(messages, list) and
         all(isinstance(m, dict) and isinstance(m.get("content"), str)
             for m in messages),
         "HISTORIC_MESSAGES_INVALID")
    return sid, messages


def triage(worlds: dict[int, dict], cohorts: dict[str, list],
           *, max_evidence: int = MAX_EVIDENCE):
    must(len(worlds) == 7, "R52_SEVEN_STORIES_REQUIRED")
    ids = {w["source_story_id"] for w in worlds.values()}
    must(len(ids) == 7, "R52_STORY_UUID_NOT_UNIQUE")
    hist_rows = []
    index = defaultdict(list)
    exactly = defaultdict(list)
    collisions = Counter()
    for corpus, records in cohorts.items():
        for row_number, row in enumerate(records):
            sid, messages = get_historical_messages(row, corpus)
            if sid in ids:
                collisions[corpus] += 1
            for msg_number, message in enumerate(messages):
                text = normalized(message["content"])
                if not text:
                    continue
                anchor = (corpus, row_number, msg_number,
                          sha_bytes(message["content"].encode("utf8")))
                if len(text) >= MIN_EXACT:
                    exactly[text].append(anchor)
                for fragment in set(probes(text) or []):
                    index[fragment].append(anchor)
    evidence = []
    seen_pairs = set()
    counts = Counter()
    for rank, world in sorted(worlds.items()):
        for msg in world["original_root_messages"]:
            i = msg["original_source_array_index"]
            text = normalized(msg["content"])
            hits = []
            if len(text) >= MIN_EXACT:
                hits.extend(("EXACT_LONG_MESSAGE", x) for x in exactly.get(text, []))
            for fragment in set(probes(text) or []):
                hits.extend(("SAMPLED_120_CODEPOINT_FRAGMENT", x)
                            for x in index.get(fragment, []))
            for kind, (corpus, row_no, message_no, hist_sha) in hits:
                key = (rank, i, corpus, row_no, message_no, kind)
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                counts[kind] += 1
                must(len(evidence) < max_evidence,
                     "TOO_MANY_HISTORIC_CANDIDATES_NEED_BOUNDED_REVIEW")
                evidence.append({
                    "schema": "storyforge-r52-private-historical-text-overlap-witness-v1",
                    "private_do_not_commit": True,
                    "source_rank": rank,
                    "source_story_id": world["source_story_id"],
                    "original_source_array_index": i,
                    "source_body_sha256": msg["source_body_sha256"],
                    "historical_corpus": corpus,
                    "historical_record_ordinal": row_no,
                    "historical_message_index": message_no,
                    "historical_message_sha256": hist_sha,
                    "match_kind": kind,
                    "review_status": "PENDING_OWNER_SEMANTIC_TRIAGE",
                    "historical_context_is_not_model_visible_input": True,
                    "training_admission": HOLD,
                })
    # Exact story ID collisions generate explicit HOLD even without text match.
    return evidence, counts, dict(collisions)


def screen(repo: Path, source_zip: Path, graph_receipt: Path,
           train: Path | None, validation: Path | None):
    aggregate = json.loads(graph_receipt.read_text(encoding="utf8"))
    must(graph_receipt.is_file() and not graph_receipt.is_symlink() and
         stat.S_IMODE(graph_receipt.stat().st_mode) == 0o600 and
         stat.S_IMODE(graph_receipt.parent.stat().st_mode) & 0o077 == 0 and
         aggregate.get("schema") ==
         "storyforge-r52-all21-world-graph-audit-safe-aggregate-v1" and
         aggregate.get("status") ==
         "R52_FULL_SOURCE_21_21_REVIEW_RECEIPTS_RECONCILED__GRAPH_HOLD" and
         aggregate.get("distinct_edges_reconciled") == 21 and
         aggregate.get("source_citations_reverified") == 87 and
         aggregate.get("first_pass_quality_possible") == 46 and
         aggregate.get("quality_hold") == 16 and
         aggregate.get("linked_world_component_owner_signatures") == 0 and
         aggregate.get("historic_gold87_v01_semantic_exposure_checked") is False and
         aggregate.get("train_admitted") ==
         aggregate.get("validation_admitted") ==
         aggregate.get("training_split_allocated") == 0,
         "R52_GRAPH21_RECEIPT_UNVERIFIED")
    worlds, _ = graph.recover_worlds(source_zip)
    cohorts, pins = rows_from_cohort(repo, train, validation)
    findings, counters, collision_counts = triage(worlds, cohorts)
    r45_complete = train is not None and validation is not None
    return findings, {
        "schema": "storyforge-r52-historical-exposure-triage-safe-aggregate-v1",
        "status": "R52_SEVEN_WORLD_HISTORICAL_EXPOSURE_SCREEN_COMPLETED__SEMANTIC_HOLD",
        "original_source_worlds": 7,
        "source_messages_read": 20577,
        "historic_cohorts_checked": {k: len(v) for k, v in cohorts.items()},
        "frozen_source_sha256": pins,
        "r45_private_49_15_included": r45_complete,
        "exact_source_id_collision_rows_by_corpus": collision_counts,
        "long_text_candidate_witnesses": len(findings),
        "long_text_screen_kind_counts": dict(counters),
        "screen_scope": "EXACT_NORMALIZED_MESSAGE_AND_SAMPLED_120_CODEPOINT_BLOCKS_ONLY",
        "semantic_name_alias_or_paraphrase_isolation_verified": False,
        "source_exposure_owner_signed": False,
        "world_components_signed": 0,
        "first_pass_candidates": 46,
        "training_split_assigned": 0,
        "train_admitted": 0,
        "validation_admitted": 0,
        "r50_sealed_heldout_opened": False,
        "original_story_text_or_source_uuid_emitted": False,
        "next_gate": "OWNER_HISTORIC_EXPOSURE_WITNESS_TRIAGE_AND_SEVEN_WORLD_SIGNOFF",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", required=True, type=Path)
    p.add_argument("--source-zip", required=True, type=Path)
    p.add_argument("--graph21-receipt", required=True, type=Path)
    p.add_argument("--r45-train", type=Path)
    p.add_argument("--r45-validation", type=Path)
    p.add_argument("--r45-original-zip", type=Path,
                   help="authenticated original R45 Train49/Val15 ZIP; use instead of two loose files")
    p.add_argument("--out-dir", required=True, type=Path)
    args = p.parse_args()
    try:
        repo = args.repo.resolve(strict=True)
        out = args.out_dir.expanduser().absolute()
        must(out.is_dir() and not out.is_symlink() and
             stat.S_IMODE(out.stat().st_mode) & 0o077 == 0 and
             repo not in out.resolve().parents and out.resolve() != repo,
             "OUTPUT_DIRECTORY_NOT_PRIVATE")
        must(not (args.r45_original_zip and
                  (args.r45_train or args.r45_validation)),
             "R45_ARCHIVE_AND_LOOSE_FILES_MUTUALLY_EXCLUSIVE")
        with contextlib.ExitStack() as stack:
            train = args.r45_train.expanduser().absolute() if args.r45_train else None
            validation = (args.r45_validation.expanduser().absolute()
                          if args.r45_validation else None)
            archive_digest = None
            if args.r45_original_zip:
                archive = args.r45_original_zip.expanduser().absolute()
                must(archive.is_file() and not archive.is_symlink(),
                     "R45_ARCHIVE_MISSING_OR_SYMLINK")
                archive_digest = exact.sha_file(archive)
                temp = Path(stack.enter_context(tempfile.TemporaryDirectory(
                    prefix="r52-historical-r45-")))
                temp.chmod(0o700)
                train, validation = extract_verified_r45_archive(archive, temp)
            findings, safe = screen(
                repo, args.source_zip.expanduser().absolute(),
                args.graph21_receipt.expanduser().absolute(),
                train, validation)
            safe["r45_original_archive_used_ephemerally"] = (
                bool(args.r45_original_zip))
            if archive_digest:
                safe["r45_original_archive_sha256"] = archive_digest
        artifacts = {
            out / "R52_PRIVATE_HISTORICAL_EXPOSURE_WITNESSES.jsonl":
                "".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n"
                        for x in findings),
            out / "R52_HISTORICAL_EXPOSURE_SAFE_AGGREGATE.json":
                json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        }
        must(not any(x.exists() or x.is_symlink() for x in artifacts),
             "EXPOSURE_OUTPUT_ALREADY_EXISTS")
        old = os.umask(0o077)
        try:
            for path, body in artifacts.items():
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "w", encoding="utf8") as dest:
                    dest.write(body)
        finally:
            os.umask(old)
    except (OSError, TypeError, KeyError, ValueError,
            zipfile.BadZipFile, json.JSONDecodeError) as exc:
        code = str(exc) if isinstance(exc, exact.GateHold) else type(exc).__name__
        print("R52_HISTORICAL_EXPOSURE_HOLD__" + code, file=sys.stderr)
        return 2
    print(safe["status"])
    print(json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
