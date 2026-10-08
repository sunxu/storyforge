from storyforge_dataset.budget import _trim_sample


class _FakeTokenizer:
    name_or_path = "fake"

    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=False):
        assert tokenize is False
        return "|".join(message["content"] for message in messages)

    def __call__(self, text, add_special_tokens=False):
        # One character equals one token for deterministic tests.
        return {"input_ids": list(range(len(text)))}


def test_trim_sample_drops_oldest_history_and_preserves_target():
    sample = {
        "id": "s1",
        "messages": [
            {"role": "system", "content": "SYS"},
            {"role": "user", "content": "old-user-1"},
            {"role": "assistant", "content": "old-assistant-1"},
            {"role": "user", "content": "old-user-2"},
            {"role": "assistant", "content": "old-assistant-2"},
            {"role": "user", "content": "CURRENT"},
            {"role": "assistant", "content": "TARGET"},
        ],
        "metadata": {"split": "train", "story_id": "story-1"},
    }

    trimmed, report = _trim_sample(_FakeTokenizer(), sample, max_length=36)

    assert trimmed["messages"][0] == {"role": "system", "content": "SYS"}
    assert trimmed["messages"][-2] == {"role": "user", "content": "CURRENT"}
    assert trimmed["messages"][-1] == {"role": "assistant", "content": "TARGET"}
    assert report["removed_history_messages"] > 0
    assert report["fits"] is True
