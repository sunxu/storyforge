from storyforge_dataset.compiler import _compact_story_payload, assign_story_splits


def test_story_split_is_deterministic_and_isolated():
    stories = [f"story-{i}" for i in range(19)]
    first = assign_story_splits(stories)
    second = assign_story_splits(reversed(stories))
    assert first == second
    assert sum(v == "train" for v in first.values()) == 15
    assert sum(v == "validation" for v in first.values()) == 2
    assert sum(v == "test" for v in first.values()) == 2
    assert set(first) == set(stories)


def test_compact_story_payload_deduplicates_and_bounds_verbose_fields():
    verbose_rules = ["R" * 600 for _ in range(30)]
    card = {
        "title": "demo",
        "description": "demo story",
        "v2_data": {
            "world": {"worldSentence": "world", "visualOnly": "ignore"},
            "character": {
                "id": "c1",
                "name": "A",
                "upbringing": "U" * 5000,
                "relationNodes": [{"label": str(i), "rules": "X" * 900} for i in range(20)],
            },
            "characters": [
                {
                    "id": "c1",
                    "name": "A",
                    "upbringing": "duplicate",
                }
            ],
            "director": {
                "forbiddenRules": verbose_rules,
                "npcs": [{"id": "n1", "name": "N", "identity": "friend", "ui": "ignore"}],
            },
            "visual": {"customCss": "ignore"},
            "components": {"phone": "ignore"},
        },
    }

    payload = _compact_story_payload(card)

    assert len(payload["characters"]) == 1
    assert len(payload["characters"][0]["upbringing"]) <= 1501
    assert len(payload["characters"][0]["relationNodes"]) == 8
    assert len(payload["characters"][0]["relationNodes"][0]["rules"]) <= 501
    assert len(payload["director"]["forbiddenRules"]) == 16
    assert len(payload["director"]["forbiddenRules"][0]) <= 301
    assert payload["director"]["npcs"] == [{"id": "n1", "name": "N", "identity": "friend"}]
    assert "visual" not in payload
    assert "components" not in payload
