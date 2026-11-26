# R58 G1 — R04 非 Gold 2 世界与历史编号 07/11 精确映射核验（SAFE）

日期：2026-10-31。仅本地只读核对固定 Git 对象；不读取 R50，未引用私有候选账本，不重做先前 DEV20/Gold/SFT 对账，不修改或覆盖任何文件，不访问 GPU/HF/RolePlay DB。

## 已确认的输入边界

Owner 先前已运行 `check_r04_non_gold_uuid.py`，SAFE 回执确认：R04 冻结 150 条 / Gold108 冻结 108 条、Gold108 全字节子集校验 PASS、10 与 8 个来源世界、差集 2 个世界、与剩余 4 个候选精确 UUID 交集 0、原有 G1 HOLD；本步骤不重新声称或更改该私人交集结果。

旧 R56 公开记录：故事 07 曾被标为与 04 关联隔离，故事 11 先前有 R01/R04 开发策展；但只是文本记录，缺少来源编号到 story UUID 的直接交叉证明。Git 中存在独立的 10 行来源编号对照：`evaluations/v0.2/admission-audit-20261013/r02-point-in-time-cards/source_story_inventory_10.csv`，Git Blob SHA-1 `1b28b2fa935d6cac5464e62d3eaebb8aed5758b6`。`evaluations/v0.2/source-archives/06-15/source_bundle_manifest.json` 的 Git Blob SHA-1 `d83e609c0b529ad8892200a86a05dbd779e9e9c2`，对每个编号 06–15 给出原始 ZIP SHA256。仓库读取阶段确认 10 行的 raw ZIP SHA256 10/10 与清单匹配；但尚未在 Owner Mac 上验证 R04 两个差集 UUID 恰好对应 07/11。

## 新工具严格检查

`experiments/r58_round1/check_r04_non_gold_rank_provenance.py`：

1. 通过 `git cat-file blob` 读取两个已固定的历史 R04 / Gold108 JSONL Git 对象，用现有的元数据 token 解析器，不 `json.loads` 故事行，也不输出任何 raw 回复。
2. 读取上述 10 行来源清单与 manifest 的固定 Git 对象，检查 Git 对象 SHA1、10 个唯一 UUID/编号和 10 组按原编号严格对应的 raw archive SHA256，以及 `source_json_equals_jsonl=True`。
3. 检查 R04 10 个 UUID 与来源编号清单 10 个 UUID 完全相同，Gold108 8 个 UUID 和 R04 非 Gold 两个 UUID 组成严格分区，且 **R04-Gold108 差集 = 原始编号 07 与 11 的 UUID 集合**。否则 `HOLD` 退出码 42，不默默转为 PASS。
4. 只向标准输出返回聚合 SAFE JSON；任何故事 UUID、角色/对话、候选原文和原始 archive 路径不输出。

## Owner Mac 运行

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only

python3 -m unittest discover \
  -s experiments/r58_round1 -p 'test_*.py' -q

python3 experiments/r58_round1/check_r04_non_gold_rank_provenance.py \
  --repo-root "$PWD"
```

原有测试 156 项，新增本轮 16 项合成测试，预期 **172 项**（真实总数以 Mac 输出为准）。新工具无 `--private-*` 参数、无输出路径，不写文件。若历史 Git 对象缺失，停止并上报统一 HOLD，不要拉取/解封 R50 或改造原有冻结文件。

## 状态解释

成功仅证明 **Git 冻结的 R04 非 Gold 两来源世界 == 06–15 来源清单编号 07/11**，可以结合 Owner 已完成的非 Gold UUID 交集零命中结论，给 R56 07/11 这两个历史来源的“精确 UUID 排除”提供编号证据。此结论不是跨 UUID 语义世界独立、其他历史 protected/heldout 全集覆盖，也不能代替 HF 三轮完成训练的**实际运行输入来源全集**检查。

`G1=HOLD`、`G2/G3` 未启动、Train/Val/Teacher=0、扩样禁用、R50 密封、PR #7 仍 Draft。下一步是逐个 HF 完成任务的 primary input receipt 与所有实际任务记录核对；不能把六份已知 Train/Validation 冻结源的一致性误称全运行证明。
