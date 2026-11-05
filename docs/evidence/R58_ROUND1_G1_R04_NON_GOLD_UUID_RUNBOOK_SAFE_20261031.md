# StoryForge R58 G1 — R04 非 Gold 两个历史开发来源 UUID 的精确排除（SAFE）

日期：2026-10-31。**G1=HOLD；Train / Validation / Teacher=0；固定五个候选，已经有一条历史 SFT UUID 曝光而排除，剩余四条不得自动准入。** 本工具与之前的 DEV20/R50/Gold195 核验相互补充，不替代完整保护集合和实际 HF 训练输入全集的核验。

## 为什么采用 R04−Gold108

- 原始 `evaluations/v0.2/source-archives/06-15/snapshots/frozen_r04_150.jsonl` 是仓库已冻结、**非 LFS** 的 150 条 R04 开发策展候选；来源归档覆盖 06–15 的 10 个世界，记录中的 Git Blob SHA-1 为 `b580038f6fef2ffb41831b8f5451ddcac5d610c2`，文件 SHA256 为 `8fbd2581b6823882d27e7839238335319202b1d9a726fc25d9aa74fedf5487f1`。
- `evaluations/v0.2/gold-quality-108/gold_quality_accepted_108.jsonl` 是 108 条 Gold108 已双人接受候选；Git Blob SHA-1 `eedb8ff83e6e0629dc2dbc57ee4681fdfde3df90`、文件 SHA256 `27d15b6f8baf7935ee2c48f85558adc3b5b25e3558e127485d0f17b620f80308`。已存在的仓库 `verify_snapshots.py` 要求 Gold108 所有**原始字节行**属于 R04 150；Gold108 共 8 个世界。
- 在 Owner Mac 使用 `git cat-file blob` 加 SHA256 钉死上面两份数据，只从**原始 JSONL 字节**提取结构化 `metadata.story_id` UUID，拒绝不明确的元数据；**不反序列化、输出、上传任何对话正文或目标**。严格检查 150/108 行、10/8 个世界、Gold108 原始行确实是 R04 精确子集，并得到恰好 **2 个 R04−Gold108 的来源世界 UUID**。
- R56 文档将历史 06–15 十个故事中未进入 Gold195 的开发与隔离来源描述为 07（与 04 关联隔离）和 11（KSG，R01/R04 开发策展）。**这份差集程序不能独立证明“07/11 编号→UUID”的对应关系**，因此仅把结果标注为“R04 非 Gold 两个来源世界”，并保留 rank-to-UUID provenance `false`、其他保护集完整性 `false`、G1 HOLD。

## 本次输入、输出和安全规则

输入只有本地 Git 中两份固定的 source Blob，以及已经存在的五项私有 DEV20 隔离账本 `g1_legacy_dev20_uuid_holds_private.json`。必须确认 1 条历史 SFT 排除、剩余四条 R50/Gold195/DEV20 先前检查均无冲突，否则 HOLD。**不会读取 R50 正文、故事原稿压缩包、数据库或 HF Bucket**，也不重复执行已完成的 DEV20 核验。

新私有输出 `g1_r04_non_gold_uuid_holds_private.json` 仅记录五条 UUID 与是否命中，限制为 0600、禁止符号链接重定向、拒绝覆盖已有文件。STDOUT 是无 UUID/路径/正文的聚合 SAFE JSON；私有文件不可分享或提交 GitHub。

测试覆盖：精确行子集、哈希固定、行数/世界数变化、结构化元数据歧义、已有隔离账本一致性、0600、拒绝覆盖与拒绝任意符号链接。本轮**18 项合成测试在隔离环境 PASS**，不代表已经运行 Owner 的真实冻结数据。

## 在 Owner Mac 执行

```bash
cd ~/workspace/storyforge-r58-run
git switch r58/roleplay-sft-skill-v01
git pull --ff-only

python3 -m unittest discover \
  -s experiments/r58_round1 -p 'test_*.py' -v

ROOT="$HOME/.storyforge-r58-private/round1_pilot_20261030"
umask 077
python3 experiments/r58_round1/check_r04_non_gold_uuid.py \
  --repo-root "$PWD" \
  --private-dev20-holds "$ROOT/g1_legacy_dev20_uuid_holds_private.json" \
  --private-output "$ROOT/g1_r04_non_gold_uuid_holds_private.json"
```

原先 R58 合成测试 129 项，本轮加 18 项，预计 **147 项**。若测试/实际脚本报错，直接报告无隐私字段的测试摘要或固定 `HOLD` 标记；**不要上传原始 frozen_r04/Gold108、私有账本、真实 UUID、世界对照或故事正文**。如果私有输出已存在，不能覆盖重跑，先人工核对已有回执。

## 结果解释与下一步

- `r04_non_gold_exact_uuid_matches_among_remaining_four > 0`：该数量的候选必须保持额外来源隔离，不替换候选、不补选、不扩样。
- `= 0`：剩余四条仅与 **这两个 R04 非 Gold 世界**没有相同 UUID；不代表其他保护/保留世界穷尽、不代表 07/11 rank-to-UUID 独立重放、更不代表历史训练 Job 输入全集已经核验完成。
- 即使 0 命中，`r56_non_gold_r04_metadata_scope_checked=true` 与 `other_protected_uuids_covered=false` 必须并存；`all_actual_sft_runs_and_input_sources_proven_complete=false`、`g1_clearance=HOLD`、`train/validation/teacher=0`、`expansion_allowed=false`。

### 后续历史训练证据缺口

六份已知冻结 Train/Validation 共 **184 条 / 27 世界**已在 Owner Mac 对账通过，这是数据名录一致性；不是“全部实际 HF Job 都只使用此集合”的证明。已有 R46 Owner 机器 7 件 primary export 核验回执、R54 trainer_state 与 GPU 工程报告、v0.1 baseline registry。下一步应以**历史已执行 GPU Job/训练输入清单及其冻结 SHA256、真实远端运行源和训练阶段行为的只读交叉核验**证明不存在其他训练世界；不能凭本轮脚本、HF Job ID 名称或已知六份来源记录自动设为 PASS。任何收费 Job、重新训练、R50 解封、G2/G3、模型晋升和扩样均未授权。

## 2026-10-31 macOS Owner 真实运行：源结构 HOLD 的兼容修订

Owner 反馈：私有 DEV20 账本 `PASS`、两份 Git Blob 读取 `PASS`、R04 与 Gold108 两组结构 `HOLD`、子集阶段 `HOLD`；私有新输出路径 `READY`，**尚未创建私有 R04 账本**。这不代表来源发生实际 UUID 碰撞，不能自动断言哪项结构条件失败。

发现旧 R56 冻结来源读取器兼容 `metadata.story_id` **或** `metadata.source_story_id` 两种字段，上一版 R04 只识别 `story_id`。修订版接受两者，但每行严格只允许出现**恰好一个**可验证 UUID 字段；两者并存、字段重复、UUID 格式不对、来源 SHA256、行数、10/8 世界数或原始字节子集不一致仍然 HOLD。修订程序仍仅读取 Git 对象与元数据 token；**从不 JSON 反序列化故事/对话正文**。

新增聚合诊断模式（不读取任何 PRIVATE 账本，不生成任何文件）：

```bash
cd ~/workspace/storyforge-r58-run
python3 experiments/r58_round1/check_r04_non_gold_uuid.py \
  --repo-root "$PWD" --diagnose-only
```

`diagnose-only` 仅输出固定字段的 SHA256/行数/结构 token/世界数通过标记和行计数，完全不输出真实 UUID、原文、私有路径或逐条记录；即使存在不符仍是 `G1=HOLD`。只有两份来源的 `sha256_pin_verified`、`expected_row_count_verified`、`unique_raw_rows_verified`、`distinct_worlds_expected_verified` 为真，且 `valid_single_uuid_rows` 分别为 150/108 后，再运行原本的 `--private-dev20-holds`、`--private-output` 真正检查；如果任一失败只返回聚合诊断而非强行继续。私有输出一旦成功创建不可覆盖，重跑将 HOLD。

此次新增六项合成测试（之前 18 项变为 **24/24 PASS**），其中包含两种源字段、混用、同一行两个来源字段拒绝、固定来源哈希不一致拒绝及 SAFE 诊断防泄漏；R58 总测试预计为 **153 项**（之前 129+24），以 Owner 真实 `Ran N` 为准。该补丁的完成与测试通过并不代表 Owner 真正冻结数据已核验成功，G1/Trainer/Other protected 保持 HOLD。
