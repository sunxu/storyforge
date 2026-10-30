#!/usr/bin/env python3
"""R58 G1 metadata-index filename discovery: private, bounded, no source reads.

Scans only explicit allowlisted local evidence directories. Refuses to descend
into R50/protected/raw source directories. Matches basename tokens only.
Results stay in new mode-0600 private files; stdout is SAFE counts only.
No discovered source automatically satisfies G1 or proof of coverage.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import re
import stat
import sys

SCOPES = (
    "semantic_world_graph", "r50_protected_worlds", "prior_sft_exposure",
    "r55_r57_dev_worlds", "other_protected_or_holdout",
)
ROOTS = (
    "r52/world_isolation", "r52/world_review",
    "r52/history_exposure_with_r45", "r57/private",
)
META_EXTS = {".json", ".csv", ".md", ".txt"}
SKIP_DIR = re.compile(r"(^|[_.-])(r50|source|sources|raw|message|messages|prompt|prompts|original|originals|cases|items|answers|responses|checkpoint|models?)([_.-]|$)", re.I)
SKIP_FILE = re.compile(r"(raw|full.source|message|prompt|answer|response|blind.items|case.content|model|train\.json|validation\.json)", re.I)
INDEX_HINT = re.compile(r"(world|alias|graph|identity|lineage|isolation|metadata|index|roster|ledger|coverage|exposure|manifest|registry|freeze|split|safe)", re.I)
SCOPE_PATTERNS = {
    "semantic_world_graph": re.compile(r"world|alias|graph|identity|lineage|isolation", re.I),
    "prior_sft_exposure": re.compile(r"exposure|trainer|compiled|r45|r46|r54|training|sft", re.I),
    "r55_r57_dev_worlds": re.compile(r"r55|r57|dev|arbiter", re.I),
    "other_protected_or_holdout": re.compile(r"held.?out|holdout|reserved|freeze|protected|split|hold", re.I),
}
OUTPUT_FIELDS = (
    "scope","private_source_reference","source_revision","coverage_status",
    "world_identity_namespace","independent_review_status",
)
MAX_FILES_PER_ROOT = 2500
MAX_CANDIDATES_PER_SCOPE = 40

class Hold(Exception):
    pass

def safe_dir(path: Path) -> bool:
    try:
        st=path.lstat()
        return stat.S_ISDIR(st.st_mode) and not path.is_symlink()
    except OSError:
        return False

def find_candidates(base: Path) -> dict[str,list[str]]:
    found={scope:[] for scope in SCOPES}
    for relative in ROOTS:
        root=base/relative
        if not safe_dir(root):
            continue
        queue=[(root,0)]
        examined=0
        while queue:
            directory,depth=queue.pop(0)
            try:
                with os.scandir(directory) as it:
                    entries=sorted(it, key=lambda e:e.name)
            except OSError:
                continue
            for entry in entries:
                examined+=1
                if examined>MAX_FILES_PER_ROOT:
                    raise Hold("bounded metadata discovery limit exceeded")
                name=entry.name
                if entry.is_symlink():
                    continue
                try:
                    if entry.is_dir(follow_symlinks=False):
                        if depth<2 and not SKIP_DIR.search(name):
                            queue.append((Path(entry.path),depth+1))
                        continue
                    if not entry.is_file(follow_symlinks=False):
                        continue
                    path=Path(entry.path)
                    if path.suffix.lower() not in META_EXTS:
                        continue
                    if SKIP_FILE.search(name) or not INDEX_HINT.search(name):
                        continue
                    if entry.stat(follow_symlinks=False).st_size>3_000_000:
                        continue
                    for scope, pattern in SCOPE_PATTERNS.items():
                        if pattern.search(name):
                            if len(found[scope])<MAX_CANDIDATES_PER_SCOPE:
                                found[scope].append(str(path.absolute()))
                except OSError:
                    continue
    # R50 files are NOT searched. Only explicitly approved metadata may fill it later.
    return {scope:sorted(set(paths)) for scope,paths in found.items()}

def draft_rows(found:dict[str,list[str]]) -> list[dict]:
    rows=[]
    for scope in SCOPES:
        candidates=found[scope]
        rows.append({
            "scope":scope,
            "private_source_reference":candidates[0] if len(candidates)==1 else "",
            "source_revision":"",
            "coverage_status":"UNKNOWN",
            "world_identity_namespace":"",
            "independent_review_status":"PENDING",
        })
    return rows

def write_private(path:Path, content:str):
    parent=path.parent
    if (not safe_dir(parent) or (parent.stat().st_mode & 0o077)
        or path.exists() or path.is_symlink()):
        raise Hold("private output path must be new in mode-0700 directory")
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as out:
            out.write(content)
    except BaseException:
        path.unlink(missing_ok=True)
        raise

def run(source_base:Path, private_candidates:Path, private_draft:Path):
    if not safe_dir(source_base):
        raise Hold("evidence base missing")
    if private_candidates==private_draft:
        raise Hold("separate output names required")
    found=find_candidates(source_base)
    draft=draft_rows(found)
    listing={
        "schema":"r58_g1_filename_candidates_private_v1",
        "note":"Filename heuristics only, unverified metadata source; not G1 evidence",
        "candidate_paths_by_scope":found,
        "protected_set_contents_accessed":False,
    }
    # Write the CSV first, keep it if second write fails to avoid any unsafe overwrite.
    from io import StringIO
    buffer=StringIO()
    wr=csv.DictWriter(buffer,fieldnames=OUTPUT_FIELDS)
    wr.writeheader(); wr.writerows(draft)
    if private_candidates.exists() or private_draft.exists():
        raise Hold("outputs already exist")
    write_private(private_draft,buffer.getvalue())
    write_private(private_candidates,json.dumps(listing,indent=2,ensure_ascii=False)+"\n")
    return {
        "schema":"r58_g1_autodiscovery_safe_v1",
        "status":"R58_G1_FILENAME_DISCOVERY_ONLY__SOURCE_COVERAGE_AND_WORLD_HOLD",
        "candidate_counts_by_scope":{x:len(found[x]) for x in SCOPES},
        "unambiguous_path_suggestions":sum(len(found[x])==1 for x in SCOPES),
        "files_with_contents_read":0,
        "protected_r50_directories_scanned":False,
        "draft_coverage_attested":False,
        "independent_validation_complete":False,
        "private_path_values_in_stdout":False,
        "g1_clearance":"HOLD",
        "training_admitted":0,
        "expansion_allowed":False,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--evidence-base",type=Path,default=Path.home()/".local/share/storyforge")
    ap.add_argument("--private-candidates",type=Path,required=True)
    ap.add_argument("--private-draft",type=Path,required=True)
    args=ap.parse_args()
    try:
        print(json.dumps(run(args.evidence_base,args.private_candidates,args.private_draft),
                         indent=2,ensure_ascii=False,sort_keys=True))
        return 0
    except (Hold,OSError,ValueError,TypeError):
        print("R58_G1_AUTODISCOVER: HOLD (private source/path/count)",file=sys.stderr)
        return 42

if __name__=="__main__":
    raise SystemExit(main())
