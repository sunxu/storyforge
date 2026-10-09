import csv
import json

import pytest

from scripts.unblind_review_v01 import DIMS, unblind


def test_unblind_mappings_without_leaking_private_key(tmp_path):
    reviews = []
    ids = [f"eval-{i:03d}-hash" for i in range(15)]
    for idx in range(4):
        path = tmp_path / f"review{idx}.csv"
        columns = ["样本编号", "故事背景与系统规则", "历史对话",
                   "当前用户输入", "回复A", "回复B", "整体偏好(A/B/TIE)"]
        columns += [f"{d}·{arm}" for d in DIMS for arm in "AB"]
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=columns)
            w.writeheader()
            for sid in ids:
                row = {"样本编号": sid, "故事背景与系统规则": "story",
                       "历史对话": "history", "当前用户输入": "prompt",
                       "回复A": "A", "回复B": "B", "整体偏好(A/B/TIE)": "A"}
                row.update({f"{d}·{arm}": "4" for d in DIMS for arm in "AB"})
                w.writerow(row)
        reviews.append(path)
    key = tmp_path / "private.json"
    key.write_text(json.dumps([{"sample_id": sid, "a": "adapter", "b": "base"}
                               for sid in ids]))
    report = unblind(reviews, key)
    assert report["raw_votes"]["adapter"] == 60
    assert report["sample_majority"]["adapter"] == 15
    assert report["mean_scores"]["base"]["角色一致性"] == 4
    with pytest.raises(ValueError, match="exactly four"):
        unblind(reviews[:3], key)
