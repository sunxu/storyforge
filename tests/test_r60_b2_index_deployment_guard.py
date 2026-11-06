"""Fail-closed synthetic checks for the manual R60 B2 production index runner.

No database or credentials are used in these tests.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "ops" / "r60" / "build_b2_index_prod.sh"


def test_r60_b2_script_has_valid_bash_syntax():
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr


def test_r60_b2_fails_closed_without_explicit_approvals():
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
    }
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )
    assert result.returncode != 0
    assert "R60_B2_STATUS: HOLD" in result.stderr
    assert "OWNER_CHANGE_APPROVAL_MISSING" in result.stderr
    assert "CREATE_INDEX_CONCURRENTLY" not in result.stdout


def test_r60_b2_has_no_automatic_destructive_or_privilege_actions():
    source = SCRIPT.read_text()
    statements = "\n".join(
        line for line in source.splitlines()
        if not line.lstrip().startswith("#")
    )
    assert "CREATE INDEX CONCURRENTLY idx_v2_chat_message_ledger_r60_b2" in statements
    assert "INCLUDE (turn_index, message_id, role, operation)" in statements
    assert "IF NOT EXISTS" not in statements
    # Ignore explanatory comments when checking for executable SQL actions.
    assert "DROP INDEX" not in statements
    assert "REINDEX" not in statements
    assert "ALTER ROLE" not in statements
    assert "GRANT " not in statements
    assert "R60_B2_DISK_APPROVED" in source
    assert "R60_B2_WAL_APPROVED" in source
    assert "R60_B2_WINDOW_APPROVED" in source
