from storyforge_dataset.compiler import assign_story_splits


def test_story_split_is_deterministic_and_isolated():
    stories = [f"story-{i}" for i in range(19)]
    first = assign_story_splits(stories)
    second = assign_story_splits(reversed(stories))
    assert first == second
    assert sum(v == "train" for v in first.values()) == 15
    assert sum(v == "validation" for v in first.values()) == 2
    assert sum(v == "test" for v in first.values()) == 2
    assert set(first) == set(stories)
