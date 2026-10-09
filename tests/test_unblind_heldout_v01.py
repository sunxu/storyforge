import csv
import json

import pytest

from scripts.unblind_heldout_v01 import DIMS, summarize


def test_final_heldout_unblinding_and_arbitration(tmp_path):
    ids = [f"eval-{i:03d}-hash{i}" for i in range(20)]
    review_paths = []
    for reviewer in range(4):
        path = tmp_path / f"review{reviewer}.csv"
        fields = ["样本编号", "故事背景与系统规则", "历史对话",
                  "当前用户输入", "回复A", "回复B", "整体偏好(A/B/TIE)"]
        fields += [f"{d}·{arm}" for d in DIMS for arm in "AB"]
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for index, sid in enumerate(ids):
                pref = "A"
                if index in (1, 2, 12, 18):
                    pref = "A" if reviewer < 2 else "B"
                row = {"样本编号": sid, "故事背景与系统规则": "background",
                       "历史对话": "history", "当前用户输入": "user",
                       "回复A": "text A", "回复B": "text B",
                       "整体偏好(A/B/TIE)": pref}
                row.update({f"{d}·{arm}": "4" for d in DIMS for arm in "AB"})
                writer.writerow(row)
        review_paths.append(path)
    key = tmp_path / "private-key.json"
    key.write_text(json.dumps([{"sample_id": sid, "a": "adapter", "b": "base"} for sid in ids]))
    result = summarize(review_paths, key)
    assert result["samples"] == 20
    assert result["sample_majority"] == {"adapter": 17, "base": 3}
    assert result["raw_votes"] == {"base": 8, "adapter": 72, "tie": 0}
    assert result["mean_scores"]["adapter"]["角色一致性"] == 4
    with pytest.raises(ValueError, match="exactly four"):
        summarize(review_paths[:3], key)
