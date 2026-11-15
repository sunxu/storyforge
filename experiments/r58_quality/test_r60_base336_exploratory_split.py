"""336-only exploratory publisher: synthetic test cases, no private/network/GPU."""
import json
import stat

import pytest
import r60_base336_exploratory_split as target


def synthetic(monkeypatch):
    cases = [{"source": {"story_id": "unscoped"}} for _ in range(1000)]
    frozen = {"remaining_full_r50_hold": [], "excluded_known5": []}
    story_pos = {}
    pos = 0
    for number in range(172):
        # First 38 stories have 82 cases. Remaining 134 have 254.
        count = (3 if number < 6 else 2) if number < 38 else (
            2 if number < 158 else 1)
        story = f"fictional-story-{number:03d}"
        story_pos[story] = []
        for _ in range(count):
            pos += 1
            cases[pos - 1] = {"source": {"story_id": story}}
            frozen["remaining_full_r50_hold"].append({"position": pos})
            story_pos[story].append(pos)
    assert pos == 336
    frozen["excluded_known5"] = [{"position": p} for p in (337, 338, 339)]

    def side(story):
        value = int.from_bytes(
            target.hashlib.sha256(
                target.preview.SALT + story.encode()).digest()[:8], "big",
        ) % 100
        return "validation" if value < target.preview.VAL_PERCENT else "train"

    groups = []
    affected = list(story_pos)[:38]
    indices = [affected[i:i + 5] for i in range(0, 30, 5)]
    indices += [affected[30:34], affected[34:38]]
    for i, members in enumerate(indices, start=1):
        groups.append({
            "group_ordinal": i,
            "members_PRIVATE": [{
                "story_id_PRIVATE": story,
                "candidate_positions_1based_PRIVATE": story_pos[story],
                "split": side(story),
            } for story in members],
        })
    document = {
        "schema": target.roster.SCHEMA,
        "semantic_review_completed": False,
        "train_admitted": 0,
        "scope": "FROZEN_336_CASES_172_STORIES__8_CROSSING_WORLD_JSON_VALUES",
        "groups_PRIVATE": groups,
    }
    monkeypatch.setattr(target.preview, "preview", lambda c, f: {
        "held_candidate_cases": 336, "held_candidate_worlds": 172,
        "provisional_train_cases": 276,
        "provisional_validation_cases": 60,
    })
    monkeypatch.setattr(target.audit, "prepare", lambda c, f: [
        {"messages": [{"role": "user", "content": f"fictional-{i}"}]}
        for i in range(336)
    ])
    return cases, frozen, document, story_pos


def test_all_336_preserved_and_known_world_groups_not_crossing(monkeypatch):
    cases, frozen, document, stories = synthetic(monkeypatch)
    payload, stats = target.split(cases, frozen, document)
    assert sum(stats["rows"].values()) == 336
    assert sum(stats["stories"].values()) == 172
    assert stats["known_world_affected_cases"] == 82
    assert stats["known_world_affected_stories"] == 38
    assert stats["crossing_known_world_groups_after_split"] == 0
    assert stats["excluded_known5"] == 3
    assert stats["input_contract"] == "THREE_PERSISTED_MESSAGES_NO_SYSTEM"
    train = [json.loads(v) for v in payload["train"].splitlines()]
    val = [json.loads(v) for v in payload["validation"].splitlines()]
    assert len(train) == stats["rows"]["train"]
    assert len(val) == stats["rows"]["validation"]
    assert (set(row["messages"][0]["content"] for row in train)
            .isdisjoint(row["messages"][0]["content"] for row in val))
    assert all(len(v) > 0 for v in payload.values())
    assert not stats["r50_semantic_isolation_verified"]


def test_altered_roster_membership_fails_closed(monkeypatch):
    cases, frozen, document, stories = synthetic(monkeypatch)
    document["groups_PRIVATE"][0]["members_PRIVATE"][0][
        "candidate_positions_1based_PRIVATE"] = [1000]
    with pytest.raises(target.Hold, match="WORLD_ROSTER_SOURCE_BINDING_HOLD"):
        target.split(cases, frozen, document)


def test_missing_roster_group_fails(monkeypatch):
    cases, frozen, document, stories = synthetic(monkeypatch)
    document["groups_PRIVATE"].pop()
    with pytest.raises(target.Hold, match="WORLD_ROSTER_COUNT_HOLD"):
        target.split(cases, frozen, document)


def test_known5_overlap_fails(monkeypatch):
    cases, frozen, document, stories = synthetic(monkeypatch)
    frozen["excluded_known5"].append({"position": 1})
    with pytest.raises(target.Hold, match="KNOWN5_SCOPE_HOLD"):
        target.split(cases, frozen, document)


def test_private_new_file_is_exclusive(tmp_path):
    target_file = tmp_path / "receipt.json"
    target.private.write_new(target_file, b"frozen\n")
    assert stat.S_IMODE(target_file.stat().st_mode) == 0o600
    with pytest.raises(FileExistsError):
        target.private.write_new(target_file, b"tamper\n")
