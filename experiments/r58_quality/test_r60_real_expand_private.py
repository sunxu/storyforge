"""Synthetic-only coverage for R60 private, resumable candidate expansion."""
from __future__ import annotations

import hashlib
import json
import os

import pytest
import r60_real_expand_private as exp
import r60_real_private_batch as g1


def sample_case(i=1, story=None, assistant=None):
    story = story or f"seed-story-{i}"
    assistant = assistant or f"assistant-id-{i}"
    return g1.parse_rows([(
        story, f"session-{i}", assistant, f"u-{i}", f"pa-{i}", f"pu-{i}", 20,
        "旧玩家消息", "旧 assistant 回复", "新玩家消息", "中文对话" * 80,
    )])[0]


def make_private_home(tmp_path, monkeypatch):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    monkeypatch.setattr(g1, "BASE", root)
    monkeypatch.setattr(exp, "BASE", root)
    seed_dir = root / "g1-pilot-original"
    seed_dir.mkdir(mode=0o700)
    seed = seed_dir / "R60_REAL_G1_CAPTURE_PRIVATE.jsonl"
    data = [sample_case(i) for i in range(6)]
    seed.write_bytes(g1.encode_lines(data))
    os.chmod(seed, 0o600)
    return root, seed


def db_row(story, n, assistant=None):
    key = hashlib.md5(story.encode()).hexdigest()
    return (
        story, f"session-{story}", key, assistant or f"msg-{story}-{n}",
        f"u-{story}-{n}", f"pa-{story}-{n}", f"pu-{story}-{n}",
        20 + n * 2, "先前玩家", "前一个回复", "新的用户行动", "中文互动故事" * 65,
    )


def test_sql_is_paged_root_only_and_bounded():
    query = exp.SQL.lower()
    assert "parent_session_id is null" in query
    assert "forked_from_turn is null" in query
    assert "(md5(story_id),story_id) > (%s,%s)" in query
    assert "limit %s" in query and "offset" not in query
    assert "role='assistant' and status='completed'" in query
    assert "finishreason" in query
    assert "char_length(m.content) between 300 and 1500" in query


def test_init_stores_only_private_seed_reference(tmp_path, monkeypatch):
    root, seed = make_private_home(tmp_path, monkeypatch)
    output = root / "expanded"
    safe = exp.create_config(output, seed, 20, 600)
    assert safe["seed_cases"] == 6
    assert safe["total_candidates"] == 6
    assert safe["train_admitted"] == 0
    assert output.stat().st_mode & 0o777 == 0o700
    assert (output / exp.CONFIG_NAME).stat().st_mode & 0o777 == 0o600
    assert "seed-story" not in json.dumps(safe)
    with pytest.raises(ValueError, match="OUTPUT_EXISTS_HOLD"):
        exp.create_config(output, seed, 20, 600)


def test_init_rejects_seed_outside_private_folder(tmp_path, monkeypatch):
    root, seed = make_private_home(tmp_path, monkeypatch)
    outside = tmp_path / "seed.jsonl"
    outside.write_bytes(seed.read_bytes())
    os.chmod(outside, 0o600)
    with pytest.raises(exp.Hold, match="SEED_PRIVATE_PATH_HOLD"):
        exp.create_config(root / "bad", outside, 20, 600)


def test_parse_empty_story_advances_cursor():
    c = {"page_size": 20}
    empty = db_row("world-new", 0)
    rows = [(*empty[:3], *([None] * 9))]
    stories, cases, cursor = exp.parse_page_rows(rows, ["", ""], c, set(), 50)
    assert len(stories) == 1 and not cases
    assert cursor == [hashlib.md5(b"world-new").hexdigest(), "world-new"]


def test_dedup_against_existing_six_and_ordering():
    c = {"page_size": 20}
    one = db_row("different-story", 1, "assistant-id-1")
    two = db_row("different-story", 0, "unique-second")
    stories, cases, _ = exp.parse_page_rows(
        [one, two], ["", ""], c, {"assistant-id-1"}, 20)
    assert len(stories) == 1
    assert len(cases) == 1
    assert cases[0]["source"]["assistant_message_id"] == "unique-second"


def test_duplicate_story_rows_with_wrong_session_hold():
    c = {"page_size": 20}
    one = db_row("different-story", 1)
    two = list(db_row("different-story", 0))
    two[1] = "wrong-session"
    with pytest.raises(exp.Hold, match="SESSION_ID_MISMATCH_HOLD"):
        exp.parse_page_rows([one, tuple(two)], ["", ""], c, set(), 20)


def test_one_page_continue_then_resume_without_duplicate(tmp_path, monkeypatch):
    root, seed = make_private_home(tmp_path, monkeypatch)
    output = root / "expanded"
    exp.create_config(output, seed, 20, 20)
    stories = ["world-b", "world-a", "world-d", "world-c"]
    stories.sort(key=lambda x: (hashlib.md5(x.encode()).hexdigest(), x))
    batches = [
        [db_row(stories[0], 0), db_row(stories[1], 0)],
        [db_row(stories[2], 0), db_row(stories[3], 0)],
        [],
    ]
    calls = []

    def fake_fetch(dsn, cursor, config):
        calls.append(cursor)
        return batches.pop(0)

    monkeypatch.setattr(exp, "fetch_page", fake_fetch)
    first = exp.advance(output, "not-used", 1)
    assert first["total_candidates"] == 8
    assert first["private_pages"] == 1
    assert first["status"] == "EXPANSION_IN_PROGRESS__NOT_ADMITTED"
    resumed = exp.advance(output, "not-used", 2)
    assert resumed["total_candidates"] == 10
    assert resumed["stories_scanned"] == 4
    assert resumed["status"] == "EXPANSION_EXHAUSTED__NOT_ADMITTED"
    assert len(calls) == 3
    assert len(list(output.glob("R60_EXPAND_PAGE_*_PRIVATE.json"))) == 3
    assert exp.inspect(output)["total_candidates"] == 10
    # No fetch after exhausted.
    assert exp.advance(output, "not-used", 1)["private_pages"] == 3
    assert len(calls) == 3
    assert seed.read_bytes()


def test_page_checksum_tampering_blocks_resume(tmp_path, monkeypatch):
    root, seed = make_private_home(tmp_path, monkeypatch)
    output = root / "expanded"
    exp.create_config(output, seed, 20, 20)
    monkeypatch.setattr(exp, "fetch_page",
                        lambda dsn, cursor, config: [db_row("world-z", 0)])
    exp.advance(output, "not-used", 1)
    path = output / exp.page_name(1)
    payload = json.loads(path.read_bytes())
    payload["cases"][0]["target_text"] = "篡改"
    path.write_bytes(exp.private_bytes(payload))
    with pytest.raises(exp.Hold, match="PAGE_CHECKSUM_OR_FORMAT_HOLD"):
        exp.inspect(output)


def test_target_budget_limits_new_cases(tmp_path, monkeypatch):
    root, seed = make_private_home(tmp_path, monkeypatch)
    output = root / "expanded"
    exp.create_config(output, seed, 20, 20)
    ordered = [f"world-{i}" for i in range(18)]
    ordered.sort(key=lambda x: (hashlib.md5(x.encode()).hexdigest(), x))
    monkeypatch.setattr(exp, "fetch_page", lambda dsn, cursor, config: [
        db_row(story, 0) for story in ordered
    ])
    summary = exp.advance(output, "not-used", 1)
    assert summary["total_candidates"] == 20
    assert summary["new_cases"] == 14
    assert summary["status"] == "EXPANSION_TARGET_REACHED__NOT_ADMITTED"
    assert exp.advance(output, "not-used", 1)["total_candidates"] == 20
    page = json.loads((output / exp.page_name(1)).read_bytes())
    assert len(page["stories"]) == 18
    assert len(page["cases"]) == 14


def test_config_mutation_fails_closed(tmp_path, monkeypatch):
    root, seed = make_private_home(tmp_path, monkeypatch)
    output = root / "expanded"
    exp.create_config(output, seed, 20, 100)
    config_path = output / exp.CONFIG_NAME
    data = json.loads(config_path.read_bytes())
    data["page_size"] = 400
    config_path.write_bytes(exp.private_bytes(data))
    with pytest.raises(exp.Hold, match="CONFIG_VERSION_OR_VALUE_HOLD"):
        exp.inspect(output)


def test_seed_mutation_blocks_resume(tmp_path, monkeypatch):
    root, seed = make_private_home(tmp_path, monkeypatch)
    output = root / "expanded"
    exp.create_config(output, seed, 20, 20)
    seed.write_bytes(seed.read_bytes() + b"\n")
    with pytest.raises(exp.Hold, match="SEED_MUTATED_HOLD"):
        exp.inspect(output)


def test_non_private_directory_blocked(tmp_path, monkeypatch):
    root, seed = make_private_home(tmp_path, monkeypatch)
    output = root / "expanded"
    exp.create_config(output, seed, 20, 20)
    os.chmod(output, 0o755)
    with pytest.raises(ValueError, match="PRIVATE_DIR_GUARD_HOLD"):
        exp.inspect(output)


def test_call_bounds_and_no_private_identifiers_in_safe(tmp_path, monkeypatch):
    root, seed = make_private_home(tmp_path, monkeypatch)
    output = root / "expanded"
    exp.create_config(output, seed, 20, 20)
    with pytest.raises(exp.Hold, match="PAGE_CALL_LIMIT_HOLD"):
        exp.advance(output, "unused", 6)
    safe = exp.inspect(output)
    for marker in ("seed-story-", "session-", "assistant-id-", "seed_sha256"):
        assert marker not in json.dumps(safe)
    assert safe["gpu_started"] is False
    assert safe["r50_complete_exclusion_verified"] is False

def test_immutable_shard_writer_supports_real_batch_over_200kb(tmp_path):
    folder = tmp_path / "private"
    folder.mkdir(mode=0o700)
    content = {"schema": exp.PAGE_SCHEMA, "synthetic_payload": "x" * 240_000}
    exp.immutable_page(folder, 1, content)
    path = folder / exp.page_name(1)
    assert len(path.read_bytes()) > g1.MAX_CAPTURE_BYTES
    assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(exp.Hold, match="PAGE_ALREADY_EXISTS"):
        exp.immutable_page(folder, 1, content)


def test_auto_seed_find_single_valid_capture(tmp_path, monkeypatch):
    root, seed = make_private_home(tmp_path, monkeypatch)
    assert exp.discover_seed() == seed
    safe = exp.create_config(root / "expanded", exp.Path("auto"), 20, 600)
    assert safe["seed_cases"] == 6
    assert safe["target_total"] == 600
    assert safe["total_candidates"] == 6


def test_missing_seed_returns_explicit_reason(tmp_path, monkeypatch):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    monkeypatch.setattr(g1, "BASE", root)
    monkeypatch.setattr(exp, "BASE", root)
    with pytest.raises(exp.Hold, match="SEED_CAPTURE_NOT_FOUND"):
        exp.discover_seed()
    with pytest.raises(exp.Hold, match="SEED_CAPTURE_NOT_FOUND"):
        exp.check_seed(root / "g1-pilot-sample" /
                       "R60_REAL_G1_CAPTURE_PRIVATE.jsonl")


def test_multiple_auto_seed_matches_fail_instead_of_guess(tmp_path, monkeypatch):
    root, seed = make_private_home(tmp_path, monkeypatch)
    alternate = root / "g1-pilot-another"
    alternate.mkdir(mode=0o700)
    another_seed = alternate / seed.name
    another_seed.write_bytes(seed.read_bytes())
    os.chmod(another_seed, 0o600)
    with pytest.raises(exp.Hold, match="MULTIPLE_VALID_SEEDS_SPECIFY_PATH"):
        exp.discover_seed()


def test_advance_uninitialized_is_actionable_error(tmp_path, monkeypatch, capsys):
    root, _seed = make_private_home(tmp_path, monkeypatch)
    folder = root / "not-yet-created"
    with pytest.raises(exp.Hold, match="EXPANSION_NOT_INITIALIZED"):
        exp.advance(folder, "fake", 1)
    monkeypatch.setenv("STORYFORGE_SUPABASE_DSN", "fake")
    monkeypatch.setattr(exp.sys, "argv", [
        "r60_real_expand_private.py", "advance",
        "--output-dir", str(folder), "--max-pages", "5",
    ])
    assert exp.main() == 2
    result = json.loads(capsys.readouterr().err.strip())
    assert result["reason_code"] == "EXPANSION_NOT_INITIALIZED"
    assert result["train_admitted"] == 0


def test_init_cli_missing_seed_does_not_expose_private_path(
        tmp_path, monkeypatch, capsys):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    monkeypatch.setattr(g1, "BASE", root)
    monkeypatch.setattr(exp, "BASE", root)
    monkeypatch.setattr(exp.sys, "argv", [
        "r60_real_expand_private.py", "init",
        "--output-dir", str(root / "new-expansion"),
        "--seed-capture", str(root / "bogus" /
                               "R60_REAL_G1_CAPTURE_PRIVATE.jsonl"),
    ])
    assert exp.main() == 2
    error = capsys.readouterr().err.strip()
    result = json.loads(error)
    assert result["reason_code"] == "SEED_CAPTURE_NOT_FOUND"
    assert "bogus" not in error
    assert "train_admitted" in result
    assert not (root / "new-expansion").exists()
