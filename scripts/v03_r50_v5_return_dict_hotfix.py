#!/usr/bin/env python3
"""Offline source-only conservative v5 return_dict=False compatibility hotfix.

No HF/Transformers imports, no private candidate text, no model execution.
Fails closed except for EXACT one apply_chat_template call and a matching
original source SHA and a known TypeError invalid-encoded-ids source guard.
Always creates a NEW private copy; never edits the original.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

EXPECTED_SOURCE_SHA256 = "235b92a668a1f4f0afbea7cd951df695f9d1a487a659ce46d315938a2880b959"
EXPECTED_ERROR_WORDS = "invalid encoded ids"

class Blocked(Exception):
    pass

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def need(cond: bool, why: str) -> None:
    if not cond:
        raise Blocked(why)

def script_call(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "apply_chat_template"

def patch_bytes(original: bytes, *, required_sha: str = EXPECTED_SOURCE_SHA256) -> tuple[bytes, dict]:
    need(sha(original) == required_sha, "SOURCE_SHA256_NOT_FROZEN")
    old = ast.parse(original, filename="<protected-local-script>")
    need(any(isinstance(n, ast.Constant) and isinstance(n.value, str) and
             EXPECTED_ERROR_WORDS in n.value for n in ast.walk(old)),
         "EXPECTED_ENCODED_IDS_GUARD_NOT_PRESENT")
    calls = [n for n in ast.walk(old) if script_call(n)]
    need(len(calls) == 1, "NOT_EXACTLY_ONE_CHAT_TEMPLATE_CALL")
    call = calls[0]
    kw = {item.arg: item.value for item in call.keywords if item.arg is not None}
    need(all(item.arg is not None for item in call.keywords), "DYNAMIC_KWARGS_NOT_SAFE")
    need("return_dict" not in kw, "RETURN_DICT_ALREADY_SPECIFIED")
    need("return_tensors" not in kw or isinstance(kw["return_tensors"], ast.Constant) and kw["return_tensors"].value is None,
         "RETURN_TENSORS_NOT_SUPPORTED_BY_HOTFIX")
    if "tokenize" in kw:
        need(isinstance(kw["tokenize"], ast.Constant) and kw["tokenize"].value is True,
             "TOKENIZE_NOT_EXPLICIT_TRUE")
    # AST positions use UTF-8 byte column offsets; compute file byte index.
    raw_lines = original.splitlines(keepends=True)
    end = sum(len(x) for x in raw_lines[:call.end_lineno - 1]) + call.end_col_offset
    need(original[end-1:end] == b")", "CALL_CLOSING_PAREN_NOT_FOUND")
    # Insert a keyword at the end of the one explicit call.
    pre = original[:end-1]
    terminator = pre.rstrip()
    separator = b" " if terminator.endswith(b",") else b", "
    patched = original[:end-1] + separator + b"return_dict=False" + original[end-1:]
    try:
        new = ast.parse(patched, filename="<protected-local-script-hotfix>")
    except SyntaxError:
        raise Blocked("PATCHED_SCRIPT_NOT_VALID_PYTHON") from None
    new_calls = [n for n in ast.walk(new) if script_call(n)]
    need(len(new_calls) == 1, "PATCHED_CHAT_TEMPLATE_CALL_COUNT_CHANGED")
    new_kwargs = [k for k in new_calls[0].keywords if k.arg == "return_dict"]
    need(len(new_kwargs) == 1 and isinstance(new_kwargs[0].value, ast.Constant) and
         new_kwargs[0].value.value is False, "RETURN_DICT_FALSE_NOT_VERIFIED")
    # AST equivalence: deleting our single added keyword must produce EXACT original AST.
    new_calls[0].keywords.remove(new_kwargs[0])
    need(ast.dump(new, include_attributes=False) == ast.dump(old, include_attributes=False),
         "PATCH_MODIFIED_OTHER_SCRIPT_SEMANTICS")
    return patched, {
        "schema": "storyforge-r50-v5-chat-template-compat-hotfix-v1",
        "status": "PRIVATE_PREFLIGHT_PATCHED_COPY__NOT_RUN_ON_HF",
        "source_sha256": sha(original),
        "patched_sha256": sha(patched),
        "patch_only": "apply_chat_template(return_dict=False)",
        "original_chat_template_call_count": 1,
        "ast_semantics_unchanged_except_return_dict_false": True,
        "original_private_file_unchanged": True,
        "private_cases_opened": 0,
        "tokenizer_executed": False,
        "huggingface_job_submitted": False,
        "official_heldout_admitted": 0,
        "semantic_world_isolation": "HOLD",
        "final_seal": False,
    }

def check_outside_git(p: Path) -> None:
    for parent in (p.parent, *p.parents):
        need(not (parent / ".git").exists(), "DESTINATION_INSIDE_GIT_REPOSITORY")

def main() -> int:
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        source = args.source.expanduser().resolve(strict=True)
        output = args.output.expanduser().absolute()
        need(source.is_file() and not source.is_symlink(), "SOURCE_NOT_REGULAR_FILE")
        need(not output.exists() and not output.is_symlink(), "OUTPUT_ALREADY_EXISTS")
        need(output.name == "R50_CPU_TOKENIZER_PREFLIGHT_46.py", "OUTPUT_MUST_HAVE_EXPECTED_BASENAME")
        check_outside_git(output)
        patched, receipt = patch_bytes(source.read_bytes())
        # No partially-created output on validation failure.
        output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(output, os.O_CREAT | os.O_WRONLY | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(patched)
        receipt["written_sha256_verified"] = sha(output.read_bytes()) == receipt["patched_sha256"]
        need(receipt["written_sha256_verified"], "WRITTEN_BYTES_MISMATCH")
        print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (Blocked, OSError, SyntaxError) as e:
        reason = str(e) if isinstance(e, Blocked) else type(e).__name__
        print("R50_V5_HOTFIX_HOLD__" + reason, file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
