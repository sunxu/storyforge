"""Read-only exact-text triage for R50 W17; no raw text in output."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import v03_r50_full_original_world_inventory as inv

CANDIDATE_SHA = "109642a6c0e27895ae83274bec79ec9f53d922e407ca435431acf3f31a31e1f2"
SYSTEM_SHA = "5e1b28cd9181f5d334f1f10a54a251f9255e655a3e597519c7cfcc530d8c5e83"
EXPECTED_FLAGS = {(2, 17), (4, 17), (10, 17)}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text).casefold()).strip()


def prepared(obj: dict) -> list[tuple[str, str]]:
    out = []
    for item in obj["messages"]:
        if isinstance(item, dict) and isinstance(item.get("content"), str):
            value = normalize(item["content"])
            if value:
                role = item.get("role")
                out.append((role if role in ("assistant", "user", "system") else "other", value))
    return out


def chunks(text: str) -> set[str]:
    return {text[i:i + 120] for i in range(0, max(0, len(text) - 119), 48)}


def diagnose(old: dict[int, dict], new: dict[int, dict]) -> tuple[dict, set[str], set[str]]:
    left = {rank: prepared(obj) for rank, obj in old.items()}
    right = {rank: prepared(obj) for rank, obj in new.items()}
    flagged = []
    # Compute windows once per source rather than once for every 10x5 pair.
    left_chunks = {rank: set().union(*(chunks(v) for _, v in rows))
                   for rank, rows in left.items()}
    right_chunks = {rank: set().union(*(chunks(v) for _, v in rows))
                    for rank, rows in right.items()}
    exact_union: set[str] = set()
    snippets: set[str] = set()
    worlds: dict[str, set[int]] = defaultdict(set)
    roles_old: Counter[str] = Counter()
    roles_new: Counter[str] = Counter()
    for a, old_messages in sorted(left.items()):
        for b, new_messages in sorted(right.items()):
            matches = {v for _, v in old_messages if len(v) >= 80} & {
                v for _, v in new_messages if len(v) >= 80
            }
            common_chunks = left_chunks[a] & right_chunks[b]
            if not (matches or common_chunks):
                continue
            literal_chunks = set().union(*(chunks(v) for v in matches))
            flagged.append({
                "old_rank": a, "new_rank": b,
                "long_message_matches": len(matches),
                "sampled_120char_matches": len(common_chunks),
                "all_sampled_chunks_from_full_exact_message":
                    common_chunks <= literal_chunks,
            })
            exact_union |= matches
            snippets |= common_chunks
            for matched in matches:
                worlds[matched].add(a)
                roles_old.update({role: 1 for role, v in old_messages if v == matched})
                roles_new.update({role: 1 for role, v in new_messages if v == matched})
    summary = {
        "scoped_pairs_checked": len(old) * len(new),
        "flagged_pairs": flagged,
        "distinct_exact_long_literals": len(exact_union),
        "one_literal_shared_by_old_02_04_10":
            any({2, 4, 10} <= ranks for ranks in worlds.values()),
        "shared_exact_literal_old_world_count_distribution":
            dict(sorted(Counter(len(x) for x in worlds.values()).items())),
        "distinct_sampled_120char_windows": len(snippets),
        "matched_old_message_roles": dict(sorted(roles_old.items())),
        "matched_new_message_roles": dict(sorted(roles_new.items())),
        "min_shared_literal_length": min(map(len, exact_union)) if exact_union else None,
        "max_shared_literal_length": max(map(len, exact_union)) if exact_union else None,
    }
    return summary, exact_union, snippets


def check_46_cases(cases: list[dict], exact: set[str],
                   snippets: set[str], system: str) -> dict:
    per_world: Counter[str] = Counter()
    labels = ("history", "world_card", "long_term_rules", "user_input")
    matched_full = dict.fromkeys(labels, 0)
    matched_window = dict.fromkeys(labels, 0)
    for case in cases:
        match = re.fullmatch(r"SFH50-W(16|17|18|19|20)-\d{3}", case["case_id"])
        inv.require(match is not None, "PRIVATE_CASE_ID_INVALID")
        per_world[match.group(1)] += 1
        if match.group(1) != "17":
            continue
        history = case["history"]
        rules = case["long_term_rules"]
        inv.require(isinstance(history, list) and
                    all(isinstance(m, dict) and isinstance(m.get("content"), str)
                        for m in history), "PRIVATE_HISTORY_INVALID")
        inv.require(isinstance(rules, list) and all(isinstance(x, str) for x in rules),
                    "PRIVATE_RULES_INVALID")
        fields = {
            "history": [normalize(m["content"]) for m in history],
            "world_card": [normalize(case["world_card"])],
            "long_term_rules": [normalize(x) for x in rules],
            "user_input": [normalize(case["user_input"])],
        }
        for field, values in fields.items():
            matched_full[field] += int(any(t in value for value in values for t in exact))
            matched_window[field] += int(any(t in value for value in values for t in snippets))
    inv.require(dict(per_world) == {
        "16": 9, "17": 10, "18": 9, "19": 8, "20": 10,
    }, "PRIVATE_CASE_WORLD_COUNTS_CHANGED")
    text = normalize(system)
    return {
        "case_count": 46, "w17_case_count": 10,
        "w17_cases_containing_shared_long_literal": matched_full,
        "w17_cases_containing_shared_120_window": matched_window,
        "common_system_contains_literal": any(v in text for v in exact),
        "common_system_contains_120_window": any(v in text for v in snippets),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", required=True, type=Path)
    p.add_argument("--old14", required=True, type=Path)
    p.add_argument("--old06-15", required=True, type=Path)
    p.add_argument("--stage-key", help="Optional existing private HF Bucket stage; no job")
    a = p.parse_args()
    inv.verify_zip(a.old14, "old14")
    inv.verify_zip(a.old06_15, "old06_15")
    all_old = inv.old14_data(a.old14)
    old15 = inv.old15_data(a.old06_15)
    old = {rank: (old15 if rank == 15 else all_old[rank]) for rank in inv.OLD_RANKS}
    new = inv.new_data(a.repo)
    report, exact, snippets = diagnose(old, new)
    flags = {(x["old_rank"], x["new_rank"]) for x in report["flagged_pairs"]}
    inv.require(flags == EXPECTED_FLAGS, "W17_SOURCE_FLAGS_CHANGED")
    inv.require(all(x["long_message_matches"] == 1 and
                    x["sampled_120char_matches"] == 5
                    for x in report["flagged_pairs"]), "W17_MATCH_COUNTS_CHANGED")
    report["retained_case_exposure"] = "NOT_YET_CHECKED"
    if a.stage_key:
        inv.require(re.fullmatch(r"r50-token-\d{8}T\d{6}Z-[a-f0-9]{8}",
                                 a.stage_key) is not None, "STAGE_KEY_INVALID")
        with tempfile.TemporaryDirectory(prefix="r50-w17-private-") as d:
            root = ("hf://buckets/adradar/storyforge-training/"
                    "preflight/v03-r50/cpu-tokenizer/" + a.stage_key + "/private/")
            paths = [("R50_CANDIDATE_46_PRESEAL_PRIVATE.jsonl", "case.jsonl"),
                     ("R45_SYSTEM_CANDIDATE_64_OF_64_NOT_APPROVED_PRIVATE.txt", "system.txt")]
            for remote, local in paths:
                subprocess.run(["hf", "buckets", "cp", root + remote,
                                str(Path(d) / local)], check=True,
                               stdout=subprocess.DEVNULL)
            raw = (Path(d) / "case.jsonl").read_bytes()
            sys_bytes = (Path(d) / "system.txt").read_bytes()
            inv.require(hashlib.sha256(raw).hexdigest() == CANDIDATE_SHA,
                        "PRIVATE_CANDIDATE_SHA_MISMATCH")
            inv.require(hashlib.sha256(sys_bytes).hexdigest() == SYSTEM_SHA,
                        "PRIVATE_SYSTEM_SHA_MISMATCH")
            cases = [json.loads(x) for x in raw.splitlines() if x.strip()]
            inv.require(len(cases) == 46 and
                        len({x["case_id"] for x in cases}) == 46,
                        "PRIVATE_CASE_COUNT_MISMATCH")
            report["retained_case_exposure"] = check_46_cases(
                cases, exact, snippets, sys_bytes.decode("utf8")
            )
    report["semantic_world_alias_certification"] = "HOLD"
    report["final_heldout_seal"] = "NOT_PERFORMED"
    report["no_model_inference"] = True
    report["no_gpu"] = True
    print("R50_W17_SOURCE_LITERAL_DIAGNOSTIC_DONE__SEMANTIC_HOLD")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError, UnicodeError,
            json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print("R50_W17_SOURCE_DIAGNOSTIC_HOLD:", type(exc).__name__,
              str(exc)[:120], file=sys.stderr)
        sys.exit(2)
