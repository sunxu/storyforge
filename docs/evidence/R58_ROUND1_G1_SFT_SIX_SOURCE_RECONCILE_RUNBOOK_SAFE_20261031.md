# R58 G1 — 六份历史 SFT 冻结来源与 R57 27 UUID 名录对账（SAFE）

日期：2026-10-31。该步骤不重跑 DEV20、不处理 R50 内容、不接触 RolePlay 数据库、不访问 HF / GPU；不改动任何已有 PRIVATE 账本、PR 审核或数据准入状态。上一阶段 Owner Mac `Ran 113 tests`、`OK`；DEV20 20 题 / 2 来源世界均已核实，剩余四个候选无精确命中。

## 为什么需要这一步

R57 私有 29 世界名录宣称 27 个世界已用于历史 v0.1/R46/R54 Train 或 Validation；R56 旧冻结历史元数据另外记录了 R46 49/15 和 R54 31/9 的逐 UUID SHA256 列表。冻结 Git 的 `data/compiled/v0.3/train.jsonl` 和 `validation.jsonl` 分别为 65/15。逐 UUID、逐 split 计数一致，能证明 **这些已知冻结六份数据与 R57 名录口径一致**，但不能证明 HF 所有真实训练 Job 使用过的数据全集恰好等于这些数据，也不能证明新保护世界全部覆盖。

R56 Stage7 旧输入 5 个 UUID 全来自 Gold195，已被 R57 Gold195 13 世界排除范围覆盖。但 R56 故事 07（旧关联隔离）和故事 11（R01/R04 旧开发策展）可能不在这六份 Train/Validation 或 Gold195 元数据中；必须独立获取具有权威来源证明的 **07/11 世界 UUID** 后继续对比。严禁靠文件名、排名序号、故事正文推断它们的 UUID，亦不可凭“没找到”标记为零交集。不要访问 R50 题目正文。

## 使用的固定源与限制

- Git Blob `3e64c9932ca43fefa8ecfb200085fe718581b6f9`: v0.1 Train 65；Git Blob `db0ae8b86038be1b372d547fdb2d6b0b7e33b54e`: v0.1 Validation 15。仅 Owner Mac 本地 `git cat-file`，先固定 Git 对象；只对 JSONL 原始字节读取 metadata.story_id 和样本 id 的结构 token，不将回复、历史或样本文本反序列化/导出。源 token 若有歧义，一律 HOLD。
- 现有且唯一的 `$HOME/.local/share/storyforge/r57/private/R57_G2_WORLD_ALIAS_REVIEW_YYYYMMDD_HHMMSS_PRIVATE.json`。工具要求正则文件名、唯一实例、mode 0600、29 世界 / 27 已曝光、Gold195 13（其中 2 个未被六份历史训练源暴露）。
- Owner 之前 R56 工具使用过的历史曝光元数据文件，默认位置：`$HOME/.local/share/storyforge/r56/owner-full-replay-20261022-v1/toolkit/private/R56_HISTORICAL_EXPOSURE_WORLD_IDS_PRIVATE.json`。其 schema 必须是 `storyforge-r56-source-world-exposure-v1`，四个 split 行数 49/15/31/9，`r50_read=false`；如果 Owner 本机实际位置不同，**只指定另一个现有已冻结的元数据文件**，勿用新的临时推算 JSON 冒充权威源。

工具只输出聚合 SAFE JSON，不输出逐 UUID、逐目标 Hash、私有路径、Train 内容，也不写任何新私有文件。拒绝 0644 或 symlink 输入；R57 roster / R56 manifest 数量或逐故事计数有任何出入直接 HOLD（退出码 42）。本地新合成测试 16/16 PASS，但真实 Owner 数据仍待跑。

## Mac 执行

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only

python3 -m unittest discover \
  -s experiments/r58_round1 \
  -p 'test_*.py' -v

python3 experiments/r58_round1/check_sft_six_source_coverage.py \
  --repo-root "$PWD" \
  --r57-private-root "$HOME/.local/share/storyforge/r57/private" \
  --r56-historical-exposure "$HOME/.local/share/storyforge/r56/owner-full-replay-20261022-v1/toolkit/private/R56_HISTORICAL_EXPOSURE_WORLD_IDS_PRIVATE.json"
```

预计原 R58 113 + 本轮 16 = **129 项测试**（精确数量以实际 `unittest` 输出为准）。第二条命令若历史路径不存在，直接 HOLD；不尝试扫描 `$HOME`，不自动查找其他数据源。只回传测试摘要与 SAFE JSON；不要回传 PRIVATE 文件或位置。

## 该检查永远不会放开的门禁

`remote_trainer_primary_inputs_verified=false`、`all_actual_sft_runs_and_input_sources_proven_complete=false`、`r56_non_gold_other_protected_index_covered=false`、`source_registry_complete=false`、`g1_clearance=HOLD`、`train/validation/teacher=0`、`expansion_allowed=false`。

下一步分别收集已存在的 R56 07/11 UUID 元数据冻结回执，并对 HF 已完成各训练运行使用的确切输入源登记做只读对照。没有元数据就登记 HOLD，不制造“完整”结论。PR #7 继续 Draft，不训练、不扩样、不自动提交任何 paid Job。
