from storyforge_dataset.analyze import _percentile


def test_percentile_interpolates():
    values = [100, 200, 300, 400]
    assert _percentile(values, 0.50) == 250
    assert _percentile(values, 0.95) == 385


def test_percentile_empty():
    assert _percentile([], 0.95) == 0
