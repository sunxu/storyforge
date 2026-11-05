#!/usr/bin/env python3
"""R58 G1: verify PINNED Git-only R55 Gold5 / R57 BPrompt DEV20 contracts.

Reads fixed Git blobs of publicly tracked Python source and JSON SAFE receipts.
Never opens compiled Test narrative bytes, prompts, PRIVATE artifacts, UUID
rosters, R50, provider logs, HF storage or network; never writes files or Jobs.

A successful audit proves only the contracts and the R57 Owner SAFE report's
declaration; it does not independently replay R57's private 20 source prompts
or certify the complete R55/R57 Dev/Reserved source universe.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess

SCHEMA = "r58_g1_r55_r57_dev20_pinned_source_contract_safe_v1"
BRANCH = "r58/roleplay-sft-skill-v01"
PINS = {
    "R48_VALIDATOR": "82d12d305b1388bb357dc2918b919393b1a417a5",
    "R55_GOLD5_BUILDER": "36b15fe7ed8ae25f8e0151c9e419c391e7bb22f3",
    "R55_GOLD5_V2_BUILDER": "c57a5569cc4a889c0539180610e108aea75a5d64",
    "R55_DEV20_PREREG": "ac053a49a8f182ebbedad276ea12d513b7276d04",
    "R57_BPROMPT_SAFE_RECEIPT": "15dd3b6b6e64f3b637673df4cac613d96519cf93",
}
TEST_SHA256 = "d8eee6db5882d85dce7ffc01256e7c5b9b46e133bdb2cf8591259112b92e980d"
PROMPTS_BLOB = "ac301a61d4130369a83dc67ac02aa2d8dda9e82b"
MANIFEST_BLOB = "f4e39196c6aa0a87b095d7de5cae4acd8b2fca63"
MAX_SOURCE_BYTES = 80_000
HEX40 = re.compile(r"[0-9a-f]{40}\Z")


class Hold(Exception):
    pass


def pinned_blob(repo: Path, sha: str) -> bytes:
    if HEX40.fullmatch(sha) is None:
        raise Hold("invalid Git pin")
    proc = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "blob", sha],
        check=False, capture_output=True, timeout=12,
    )
    payload = proc.stdout
    if proc.returncode != 0 or not 0 < len(payload) < MAX_SOURCE_BYTES:
        raise Hold("pinned Git object unavailable or oversize")
    obj_id = hashlib.sha1(
        b"blob " + str(len(payload)).encode("ascii") + b"\x00" + payload
    ).hexdigest()
    if obj_id != sha:
        raise Hold("pinned Git bytes do not match object ID")
    return payload


def literal_constants(source: bytes, names: set[str]) -> tuple[ast.Module, dict]:
    try:
        module = ast.parse(source.decode("utf-8"))
    except (UnicodeError, SyntaxError, ValueError):
        raise Hold("invalid pinned source code")
    found = {}
    for node in module.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            lhs = node.targets if isinstance(node, ast.Assign) else [node.target]
            for entry in lhs:
                if isinstance(entry, ast.Name) and entry.id in names:
                    if entry.id in found:
                        raise Hold("duplicate source pin constant")
                    try:
                        found[entry.id] = ast.literal_eval(node.value)
                    except (ValueError, TypeError, RecursionError):
                        raise Hold("nonliteral source pin")
    if set(found) != names:
        raise Hold("missing source identity constant")
    return module, found


def function(module: ast.Module, name: str) -> ast.FunctionDef:
    functions = [n for n in module.body
                 if isinstance(n, ast.FunctionDef) and n.name == name]
    if len(functions) != 1:
        raise Hold("source function ambiguous")
    return functions[0]


def references(node: ast.AST, words: set[str]) -> bool:
    used = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
    return words <= used


def r55_contract(r48_source: bytes, r55_source: bytes, v2_source: bytes,
                 prereg_source: bytes) -> None:
    r48, constants = literal_constants(r48_source, {"CANONICAL_TEST_SHA256"})
    if constants["CANONICAL_TEST_SHA256"] != TEST_SHA256:
        raise Hold("canonical Test source digest drift")
    function(r48, "read_gold")
    r55, pins = literal_constants(
        r55_source, {"EXPECTED_PROMPTS_BLOB", "EXPECTED_MANIFEST_BLOB"}
    )
    if pins != {"EXPECTED_PROMPTS_BLOB": PROMPTS_BLOB,
                "EXPECTED_MANIFEST_BLOB": MANIFEST_BLOB}:
        raise Hold("R55 prompt/manifest pins drift")
    loader = function(r55, "load_exact_sources")
    if not references(loader, {"CANONICAL_TEST_SHA256", "EXPECTED_PROMPTS_BLOB",
                               "EXPECTED_MANIFEST_BLOB", "validate_prompts",
                               "read_gold", "check_r47"}):
        raise Hold("R55 source loader missing canonical link")
    if not any(isinstance(n, ast.Attribute) and n.attr == "compiled_test"
               for n in ast.walk(loader)):
        raise Hold("R55 does not reference compiled Test source")
    v2, _ = literal_constants(v2_source, set())
    v2_main = function(v2, "main")
    if not any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        and node.func.attr == "load_exact_sources"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "legacy"
        for node in ast.walk(v2_main)
    ):
        raise Hold("R55 v2 no longer delegates frozen source loader")
    try:
        p = json.loads(prereg_source)
        src = p["source"]
        review = p["review"]
        promotion = p["promotion"]
    except (ValueError, KeyError, TypeError):
        raise Hold("R55 source prereg invalid")
    if (p.get("schema") != "storyforge-r55-exposed20-pairwise-dev-preregistration-v1"
            or src.get("exposed_unique_cases") != 20
            or src.get("worlds") != 2
            or src.get("r47_and_r48_same_20") is not True
            or src.get("fresh_independent_heldout") is not False
            or src.get("prompts_git_blob_sha1") != PROMPTS_BLOB
            or src.get("manifest_git_blob_sha1") != MANIFEST_BLOB
            or review.get("case_count") != 20
            or review.get("not_independent_test") is not True
            or promotion.get("r50_sealed") is not True
            or promotion.get("automatically_permitted") is not False):
        raise Hold("R55 20-case source prereg no longer matches")


def r57_owner_receipt(source: bytes) -> None:
    try:
        p = json.loads(source)
        config = p["config"]
        serious = p["serious_selected_subset"]
        audit = p["audit"]
    except (ValueError, TypeError, KeyError):
        raise Hold("R57 SAFE archive invalid")
    if (p.get("schema") != "storyforge-r57-bprompt-safe-archive-v1"
            or p.get("suite") != "EXPOSED_DEV20_NOT_HELDOUT"
            or p.get("outcome") != "EXPLORATORY_DEV_ONLY_NO_PROMOTION"
            or config.get("stories") != 2 or config.get("pairs") != 20
            or config.get("responses") != 40 or config.get("reviewers") != 3
            or config.get("model_weights_changed") is not False
            or serious.get("cases") != 10
            or serious.get("verdict_slots") != 40
            or serious.get("unbiased_full20_rate") is not False
            or audit.get("independent_original_key_mapping_verified") is not False):
        raise Hold("R57 DEV20/DEV10 reported scope drift")


def summarize(blobs: dict[str, bytes]) -> dict:
    if set(blobs) != set(PINS):
        raise Hold("incomplete pinned source set")
    r55_contract(
        blobs["R48_VALIDATOR"], blobs["R55_GOLD5_BUILDER"],
        blobs["R55_GOLD5_V2_BUILDER"], blobs["R55_DEV20_PREREG"],
    )
    r57_owner_receipt(blobs["R57_BPROMPT_SAFE_RECEIPT"])
    return {
        "schema": SCHEMA,
        "status": "R55_GOLD5_SOURCE_AND_R57_BPROMPT_OWNER_DECLARED_DEV20_PINNED__OTHER_DEV_HOLD",
        "pinned_git_code_blobs_verified": 3,
        "pinned_git_safe_contract_blobs_verified": 2,
        "r55_canonical_v01_test_sha_contract_verified": True,
        "r55_prompt_and_manifest_git_blob_contract_verified": True,
        "r55_v2_uses_v1_frozen_input_loader": True,
        "r55_legacy_dev_worlds": 2,
        "r55_legacy_dev_cases": 20,
        "r57_bprompt_owner_reported_dev_worlds": 2,
        "r57_bprompt_owner_reported_dev_pairs": 20,
        "r57_bprompt_serious_subset_of_owner_reported_dev20_cases": 10,
        "r57_private_per_case_source_mapping_independently_replayed": False,
        "r55_original_input_bytes_reread_or_rehashed_this_step": False,
        "all_other_r55_r57_dev_and_arbitration_worlds_exhausted": False,
        "all_other_reserved_heldout_worlds_exhausted": False,
        "all_actual_historical_parameter_update_job_inputs_proven": False,
        "private_uuid_or_narrative_exported": False,
        "r50_protected_content_accessed": False,
        "no_new_hf_jobs": True,
        "g1_clearance": "HOLD",
        "g2_clearance": "HOLD",
        "train_admitted": 0, "validation_admitted": 0,
        "teacher_admitted": 0, "expansion_allowed": False,
    }


def audit(repo: Path) -> dict:
    branch = subprocess.run(
        ["git", "-C", str(repo), "branch", "--show-current"],
        capture_output=True, text=True, check=True, timeout=8,
    )
    if branch.stdout.strip() != BRANCH:
        raise Hold("incorrect branch")
    return summarize({key: pinned_blob(repo, sha) for key, sha in PINS.items()})


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = p.parse_args()
    try:
        print(json.dumps(audit(args.repo_root.resolve(strict=True)),
                         sort_keys=True, ensure_ascii=False, indent=2))
        return 0
    except Exception:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "PINNED_DEV20_SOURCE_CONTRACT_UNAVAILABLE__G1_HOLD",
            "private_uuid_or_narrative_exported": False,
            "r50_protected_content_accessed": False,
            "no_new_hf_jobs": True,
            "g1_clearance": "HOLD",
            "g2_clearance": "HOLD",
            "train_admitted": 0, "validation_admitted": 0,
            "teacher_admitted": 0, "expansion_allowed": False,
        }, sort_keys=True, ensure_ascii=False, indent=2))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
