"""R50 full-original world inventory; fail-closed, no inference or final seal.

Read two immutable Git LFS ZIPs and five tracked R50 source transcripts.
Outputs only aggregate counts; AI alias/identity adjudication still required.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata
import zipfile
from io import BytesIO
from pathlib import Path

ARCHIVES = {
    "old14": ("050af7034f9b2f3ef0401542364d23ef6ce126dd1699a49b1124d69245c98fdb", 57602487),
    "old06_15": ("b874cd07547092e9c3c967f69fab6b75262ff4f44ba2d368fd575f84e8886afb", 65332700),
}
R45_RANKS = {2, 4, 6, 8, 9, 10, 12, 14, 15}
OLD_RANKS = R45_RANKS | {7}  # 04↔07 known linked component
NEW_RANKS = {16, 17, 18, 19, 20}
ROOT = Path("evaluations/v0.2/source-archives/16-20")
RECEIPT = Path("docs/evidence/V03_R50_SOURCE_16_20_RECEIPT_20261015.json")
GIT_SUMMARY = Path("docs/evidence/V03_R50_FULL_OLD_SOURCE_COVERAGE_20261016.json")
BRANCH = "audit/r49-r50-source-intake-20261015"
SOURCE_COMMIT = "a197923e1e15344e8c98bd96e593e84781b68c83"


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def checksum(path: Path) -> str:
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def verify_zip(path: Path, key: str) -> None:
    want_sha, want_len = ARCHIVES[key]
    require(path.is_file() and not path.is_symlink(), f"MISSING_{key}_LFS_PAYLOAD")
    require(path.stat().st_size == want_len, f"SIZE_MISMATCH_{key}_LFS_PAYLOAD")
    require(checksum(path) == want_sha, f"SHA256_MISMATCH_{key}_LFS_PAYLOAD")
    with zipfile.ZipFile(path) as z:
        require(z.testzip() is None, f"ZIP_CRC_FAIL_{key}")


def is_chat(obj: object) -> bool:
    return isinstance(obj, dict) and isinstance(obj.get("messages"), list) and bool(obj["messages"])


def identity(obj: dict) -> str | None:
    st = obj.get("story")
    for val in (obj.get("story_id"), obj.get("story_uuid"),
                st.get("id") if isinstance(st, dict) else None):
        if isinstance(val, str) and val.strip():
            return val
    return None


def old14_data(path: Path) -> dict[int, dict]:
    """One story per rank, permitting equivalent JSON and JSONL representations.

    Archive label '14 original exports' is NOT proof that story numbers
    are exactly 01–14. Parse and reconcile *all* numbered root chat exports,
    then require the nine R45-source ranks available in this archive.
    Any additional numbered sources remain visible to the scoped audit.
    """
    grouped: dict[int, list[tuple[str, dict]]] = {}
    with zipfile.ZipFile(path) as z:
        for member in z.infolist():
            name = member.filename
            if member.is_dir() or "/" in name:
                continue
            match = re.fullmatch(r"(\d{2})-[^/]+\.(json|jsonl)", name,
                                 flags=re.IGNORECASE)
            if not match:
                continue
            rank = int(match.group(1))
            require(1 <= rank <= 99, "OLD14_INVALID_SOURCE_RANK")
            require(member.file_size <= 150_000_000,
                    "OLD14_MEMBER_SIZE_LIMIT")
            data = json.loads(z.read(member).decode("utf-8-sig"))
            require(is_chat(data), "OLD14_SOURCE_NOT_CHAT")
            grouped.setdefault(rank, []).append((match.group(2).lower(), data))

    # Frozen R45 train/validation uses 02/04/06/08/09/10/12/14/15;
    # old 04↔07 is linked. World 15 comes from the second LFS bundle.
    # All other numeric ranks are retained for extra-ID overlap diagnostics.
    needed = (R45_RANKS | {7}) - {15}
    require(needed <= set(grouped), "OLD14_R45_REQUIRED_RANKS_MISSING")
    found = {}
    for rank, variants in sorted(grouped.items()):
        source_ids = {identity(obj) for _, obj in variants}
        require(len(source_ids) == 1 and None not in source_ids,
                "OLD14_VARIANT_ID_MISMATCH")
        signatures = set()
        for _, obj in variants:
            require(all(isinstance(msg, dict) for msg in obj["messages"]),
                    "OLD14_SOURCE_MALFORMED_MESSAGE")
            signature = hashlib.sha256(json.dumps(
                [(msg.get("role"), msg.get("content"))
                 for msg in obj["messages"]],
                ensure_ascii=False, separators=(",", ":"),
            ).encode("utf-8")).hexdigest()
            signatures.add(signature)
        require(len(signatures) == 1, "OLD14_VARIANTS_DIVERGE")
        # Both full JSON and JSONL must agree; prefer full .json wrapper
        # (and use .jsonl if there is no full JSON).
        found[rank] = min(variants, key=lambda x: x[0] != "json")[1]
    return found


def old15_data(path: Path) -> dict:
    candidates = []

    def walk(blob: bytes, level: int, root: bool) -> None:
        require(level <= 3, "OLD15_SOURCE_ZIP_NESTING_EXCEEDED")
        with zipfile.ZipFile(BytesIO(blob)) as z:
            for name in z.namelist():
                if name.endswith("/"):
                    continue
                base = Path(name).name
                lower = name.lower()
                if root and not (lower.startswith(("sources/", "raw/")) or base.startswith("15-")):
                    continue
                info = z.getinfo(name)
                require(info.file_size <= 150_000_000, "OLD15_MEMBER_SIZE_LIMIT")
                if lower.endswith(".zip") and level < 3:
                    try:
                        walk(z.read(name), level + 1, False)
                    except (EOFError, zipfile.BadZipFile):
                        continue
                elif re.fullmatch(r"15-[^/]+\.jsonl?", base, flags=re.IGNORECASE):
                    try:
                        row = json.loads(z.read(name).decode("utf-8-sig"))
                    except (json.JSONDecodeError, UnicodeError):
                        continue
                    if is_chat(row):
                        candidates.append(row)

    walk(path.read_bytes(), 0, True)
    require(bool(candidates), "OLD15_RAW_SOURCE_NOT_FOUND")
    ids = {identity(x) for x in candidates}
    require(len(ids) == 1 and None not in ids, "OLD15_SOURCE_ID_AMBIGUOUS")
    hashes = {
        hashlib.sha256(json.dumps(
            [(m.get("role"), m.get("content")) for m in x["messages"] if isinstance(m, dict)],
            ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        for x in candidates
    }
    require(len(hashes) == 1, "OLD15_MULTIPLE_DIFFERENT_TRANSCRIPTS")
    return candidates[0]


def new_data(repo: Path) -> dict[int, dict]:
    receipt = json.loads((repo / RECEIPT).read_text(encoding="utf8"))
    require(receipt.get("source_commit") == SOURCE_COMMIT and
            len(receipt.get("files", [])) == 35, "R50_FROZEN_RECEIPT_MISMATCH")
    require(receipt.get("source_root") == ROOT.as_posix(),
            "R50_SOURCE_ROOT_RECEIPT_MISMATCH")
    entries = receipt.get("worlds")
    require(isinstance(entries, list) and len(entries) == 5,
            "R50_WORLD_RECEIPT_COUNT_MISMATCH")
    expected = {}
    for world in entries:
        require(isinstance(world, dict) and type(world.get("number")) is int,
                "R50_WORLD_RECEIPT_INVALID")
        rank = world["number"]
        name = world.get("folder")
        require(rank in NEW_RANKS and rank not in expected and
                isinstance(name, str) and
                name.startswith(f"{rank}-") and
                name not in (".", "..") and
                "/" not in name and "\\" not in name,
                "R50_WORLD_RECEIPT_FOLDER_MISMATCH")
        expected[rank] = world
    require(set(expected) == NEW_RANKS, "R50_WORLD_RECEIPT_RANK_MISMATCH")

    root = repo / ROOT
    require(root.is_dir() and not root.is_symlink(),
            "R50_SOURCE_ROOT_NOT_DIRECTORY")
    expected_names = {w["folder"] for w in expected.values()}
    for entry in root.iterdir():
        # macOS Finder creates untracked metadata beside the Git-verified
        # folders. Ignore only known regular-file sidecars, never symlinks.
        require(not entry.is_symlink(), "R50_SOURCE_ROOT_SYMLINK_HOLD")
        if entry.name in expected_names:
            require(entry.is_dir(), "R50_EXPECTED_WORLD_FOLDER_NOT_DIRECTORY")
        elif entry.is_file() and (
            entry.name in (".DS_Store", ".localized") or
            entry.name.startswith("._")
        ):
            continue
        else:
            raise ValueError("R50_UNEXPECTED_SOURCE_ROOT_ENTRY")

    found = {}
    for rank, world in sorted(expected.items()):
        folder = root / world["folder"]
        require(folder.is_dir() and not folder.is_symlink(),
                "R50_EXPECTED_WORLD_FOLDER_MISSING")
        source = folder / (folder.name + ".jsonl")
        cards = folder / "story-cards.json"
        require(source.is_file() and not source.is_symlink() and
                cards.is_file() and not cards.is_symlink(),
                "R50_REQUIRED_WORLD_SOURCE_FILE_MISSING")
        raw = source.read_bytes()
        require(raw.endswith(b"\n"), "SOURCE_JSONL_TERMINATOR_MISSING")
        item = json.loads(raw)
        card = json.loads(cards.read_text(encoding="utf8"))
        require(is_chat(item), "BAD_NEW_WORLD_SOURCE")
        if "rank" in item:
            require(item["rank"] == rank, "BAD_NEW_WORLD_SOURCE_RANK")
        require(card.get("rank") == rank and
                card.get("story_id") == world.get("story_id") and
                identity(item) == world.get("story_id"),
                "NEW_WORLD_CARD_ID_MISMATCH")
        if world.get("session_id") is not None:
            require(card.get("session_id") == world["session_id"],
                    "NEW_WORLD_CARD_SESSION_MISMATCH")
        found[rank] = item
    require(set(found) == NEW_RANKS, "R50_NOT_FIVE_WORLDS")
    return found


def messages(obj: dict) -> list[str]:
    values = []
    for msg in obj["messages"]:
        if isinstance(msg, dict) and isinstance(msg.get("content"), str):
            text = re.sub(r"\s+", " ", unicodedata.normalize(
                "NFKC", msg["content"]).casefold()).strip()
            if text:
                values.append(text)
    require(bool(values), "SOURCE_WITHOUT_TEXT_MESSAGES")
    return values


def dig(s: str) -> bytes:
    return hashlib.blake2b(s.encode("utf8"), digest_size=16).digest()


def keys(msgs: list[str], *, blocks: bool) -> set[bytes]:
    if blocks:
        # Sampled 120-codepoint windows: not exhaustive and not semantic.
        return {dig(msg[i:i+120]) for msg in msgs
                for i in range(0, max(0, len(msg)-119), 48)}
    return {dig(msg) for msg in msgs if len(msg) >= 80}


def screen(repo: Path, old14: Path, old06_15: Path) -> dict:
    verify_zip(old14, "old14")
    verify_zip(old06_15, "old06_15")
    old14_all = old14_data(old14)
    nested_15 = old15_data(old06_15)
    # If the first archive also contains story 15, both archives must agree
    # on identity and ordered message contents before selecting either copy.
    if 15 in old14_all:
        require(identity(old14_all[15]) == identity(nested_15),
                "OLD15_CROSS_ARCHIVE_ID_MISMATCH")
        require(
            [(m.get("role"), m.get("content")) for m in old14_all[15]["messages"]]
            == [(m.get("role"), m.get("content")) for m in nested_15["messages"]],
            "OLD15_CROSS_ARCHIVE_TRANSCRIPT_MISMATCH",
        )
    old = {rank: (nested_15 if rank == 15 else old14_all[rank])
           for rank in sorted(OLD_RANKS)}
    new = new_data(repo)
    oi = [identity(v) for v in old.values()]
    ni = [identity(v) for v in new.values()]
    require(None not in oi + ni and len(set(oi)) == len(oi) and
            len(set(ni)) == len(ni), "STORY_ID_MISSING_OR_DUPLICATE")
    extras = sorted(set(old14_all) - (OLD_RANKS | {7}))
    extra_ids = [identity(old14_all[rank]) for rank in extras]
    require(None not in extra_ids, "OLD14_EXTRA_SOURCE_ID_MISSING")
    extra_new_id_conflicts = sum(sid in set(ni) for sid in extra_ids)
    old_msgs = {k:messages(v) for k,v in old.items()}
    new_msgs = {k:messages(v) for k,v in new.items()}
    old_full = {k:keys(v, blocks=False) for k,v in old_msgs.items()}
    new_full = {k:keys(v, blocks=False) for k,v in new_msgs.items()}
    old_chunks = {k:keys(v, blocks=True) for k,v in old_msgs.items()}
    new_chunks = {k:keys(v, blocks=True) for k,v in new_msgs.items()}
    pairs = [
        {"old_rank":a,"r50_rank":b,
         "same_source_id": identity(old[a]) == identity(new[b]),
         "long_exact_message_matches":len(old_full[a] & new_full[b]),
         "sampled_120char_matches":len(old_chunks[a] & new_chunks[b])}
        for a in sorted(old) for b in sorted(new)
    ]
    require(len(pairs) == 50, "EXPECTED_10_OLD_COMPONENTS_X_5_NEW")
    flags = sum(bool(p["same_source_id"] or p["long_exact_message_matches"] or
                     p["sampled_120char_matches"]) for p in pairs)
    flags += extra_new_id_conflicts
    return {
        "schema":"storyforge-r50-full-original-source-git-lfs-triage-v1",
        "archive_evidence":{k:{"sha256":v[0],"size_bytes":v[1],
                                 "full_bytes_and_crc":"PASS"} for k,v in ARCHIVES.items()},
        "r45_source_ranks":sorted(R45_RANKS),
        "transitive_known_old_link":[4,7],
        "old14_numbered_chat_source_count":len(old14_all),
        "old14_numbered_chat_ranks":sorted(old14_all),
        "extra_archive_ranks_outside_frozen_r45":extras,
        "extra_archive_source_id_conflicts_with_r50":extra_new_id_conflicts,
        "old15_checked_against_two_archives":15 in old14_all,
        "old_source_ranks_checked":sorted(old),
        "new_source_ranks_checked":sorted(new),
        "old_full_source_message_count":sum(map(len, old_msgs.values())),
        "r50_full_source_message_count":sum(map(len, new_msgs.values())),
        "source_pair_count":50,
        "same_story_id_pair_count":sum(p["same_source_id"] for p in pairs),
        "lexical_120_sampled_flagged_pairs":sum(p["sampled_120char_matches"]>0 for p in pairs),
        "exact_long_message_flagged_pairs":sum(p["long_exact_message_matches"]>0 for p in pairs),
        "pair_aggregate":pairs,
        "screen_status": ("LEXICAL_OR_IDENTITY_FLAGS_REQUIRE_AI_ADJUDICATION" if flags
                          else "NO_FLAGS_IN_SAMPLED_LEXICAL_SCREEN"),
        "sampling_warning":"120-character NFKC windows sampled at stride 48 ON BOTH sides; may miss shifted exact text and paraphrases",
        "semantic_hidden_alias_and_world_component_closure":"HOLD",
        "timepoint_card_field_review":"PENDING",
        "heldout_final_seal":"NOT_PERFORMED",
        "no_inference":True,"no_gpu":True,"model_promotion":False,
        "status":"FULL_SOURCE_BYTES_CHECKED__SCOPED_LEXICAL_SCREEN__SEMANTIC_HOLD",
        "privacy":"Counts and story rank numbers only. No UUIDs, narratives, prompt text or answer keys."
    }


def git(repo:Path,*args:str)->str:
    return subprocess.check_output(["git","-C",str(repo),*args],text=True).strip()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo",type=Path,required=True)
    ap.add_argument("--old14",type=Path,required=True)
    ap.add_argument("--old06-15",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--push",action="store_true")
    a=ap.parse_args()
    repo=a.repo.resolve();out=a.output.resolve()
    require((repo / ".git").exists(), "LOCAL_GIT_CHECKOUT_REQUIRED")
    require(not out.exists() and out != repo and repo not in out.parents,
            "OUTPUT_MUST_BE_NEW_OUTSIDE_REPO")
    os.umask(0o077)
    result=screen(repo,a.old14,a.old06_15)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    out.chmod(0o600)
    print(result["status"], "pairs=",result["source_pair_count"])
    if a.push:
        require(git(repo,"branch","--show-current") == BRANCH,"WRONG_AUDIT_BRANCH")
        require(not git(repo,"status","--porcelain"),"WORKTREE_NOT_CLEAN")
        target=repo / GIT_SUMMARY
        require(not target.exists(),"GIT_EVIDENCE_TARGET_ALREADY_EXISTS")
        target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
        subprocess.run(["git","-C",str(repo),"add","--",str(GIT_SUMMARY)],check=True)
        subprocess.run(["git","-C",str(repo),"commit","-m",
            "audit(r50): inventory full old source LFS originals (semantic HOLD)",
            "--",str(GIT_SUMMARY)],check=True)
        subprocess.run(["git","-C",str(repo),"push","origin",f"HEAD:refs/heads/{BRANCH}"],check=True)
        print("R50_FULL_SOURCE_AGGREGATE_COMMITTED_TO_GITHUB")
    else:
        print("DRY_RUN__NO_GIT_WRITE")


if __name__ == "__main__":
    try:
        main()
    except (ValueError,OSError,KeyError,TypeError,zipfile.BadZipFile,
            json.JSONDecodeError,subprocess.CalledProcessError) as e:
        print("R50_LFS_SOURCE_INVENTORY_HOLD:",type(e).__name__,str(e)[:250],file=sys.stderr)
        raise SystemExit(2)
