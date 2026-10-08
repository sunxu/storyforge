from storyforge_dataset.analyze import _percentile


def test_percentile_interpolates():
    values = [100, 200, 300, 400]
    assert _percentile(values, 0.50) == 250
    assert _percentile(values, 0.95) == 385


def test_percentile_empty():
    assert _percentile([], 0.95) == 0


class _FakeTokenizer:
    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=False):
        assert tokenize is False
        assert add_generation_prompt is False
        return "<s>user:hi</s>"

    def __call__(self, text, add_special_tokens=False):
        assert text == "<s>user:hi</s>"
        assert add_special_tokens is False
        return {"input_ids": [10, 11, 12, 13]}


def test_encode_chat_counts_token_ids_not_mapping_keys():
    from storyforge_dataset.analyze import _encode_chat

    assert _encode_chat(_FakeTokenizer(), [{"role": "user", "content": "hi"}]) == [10, 11, 12, 13]
