# R58 G1 — GitHub 历史训练来源 Owner Mac 核验回执（SAFE）

日期：2026-10-31。来源为 **Owner 在对话中返回的 Mac stdout**，并非 GitHub CI 或本次会话重新运行 HF 的独立核验。

## 已核验范围

- Owner Mac 回报完整 R58 测试套件：`Ran 299 tests in 0.261s`，`OK`。
- Owner Mac 回报 `verify_github_historical_training_sources.py` 状态 `R58_G1_GITHUB_KNOWN_TRAINING_SOURCES_VERIFIED__REMOTE_AND_OTHER_HOLD`。
- 固定 Git 对象 11 个、六份已知 Train / Validation 来源共 184 条记录位置；v0.1 源数据 SHA256 通过。
- v0.1 65 条 Train 来自 15 个世界，15 条 Validation 来自 2 个世界，两者按 UUID 精确交集为 0。此交集仅针对 v0.1 两个 split。
- R46 报告 / Owner 远端输入回执的哈希契约、R54 Runner / R53 私有发布的哈希契约核对通过。
- 五个已知发生参数更新的 Job 在 GitHub 证据中有记载；**这不是全部历史 Job 训练用途的完整证明**。
- 184 是 split 位置计数，不是去重样本数，也不是每条记录实际产生梯度的证明。此前 Owner 私有六来源对账所得 27 世界结论不在本次公开源码独立重算，也不将其 UUID 发布。

可机读原始 SAFE 回执：`docs/evidence/R58_G1_GITHUB_KNOWN_SOURCES_OWNER_MAC_SAFE_RECEIPT_20261031.json`。

固定引用：

- `docs/evidence/R58_G1_GITHUB_HISTORICAL_TRAINING_SOURCES_SAFE_20261031.json`
- `experiments/r58_round1/verify_github_historical_training_sources.py`
- `docs/evidence/V03_R53_R46_PRIMARY_EXPORT_OWNER_RECEIPT_VERIFIED_20261021.md`
- `docs/evidence/V03_R53_FORMAL_PRIVATE_31_9_RELEASE_OWNER_RECEIPT_ACCEPTED_20261021.md`
- `docs/evidence/V03_R54_TRAINER_STATE_LOSS_SUMMARY_20261022.md`

## 证据缺口与下一步优先级

1. **R46：** 既有 Owner Mac primary-export 回执已核对远端文件哈希及冻源重建结果；如需更高证据等级，仅对同一份远端原始文件作只读、精确哈希复核，并链接原有私有完整运行回执。无需再跑训练。
2. **R54：** GitHub 已锁定 R53 私有 31/9 正式发布的 `train.jsonl` / `validation.jsonl` 哈希和 R54 runner 的训练前输入校验逻辑；如要进一步断言远端运行时字节一致，只读核对现存原始运行报告和原始输入文件。不能仅凭 Runner 代码断言远端实际行为。
3. **v0.1 三个参数更新 Job：** Smoke / Capacity / Baseline 共用数据来源声明，但还需分别明确原始远端输入哈希和可核实的任务归属；不能把已有同一 Git 文件哈希当作三次任务的原始文件证明。
4. **其余历史 Job：** 之前 60 个任务仍未充分分类。若要求严格证明“所有实际历史训练来源完整”，本缺口仍阻止 G1 放行。优先从已有运行产物 / 来源登记核对；不再把无关键词信号作为排除证据。
5. **受保护数据：** R50 密封内容、R58 候选 UUID、私有世界名录与训练正文均未因本轮回执公开。

## 保留门禁

`source_registry_complete=false`、`all_actual_sft_runs_and_input_sources_proven_complete=false`、`G1=HOLD`、Train / Validation / Teacher 准入 `0/0/0`、`expansion_allowed=false`。

此回执 **没有** 启动 HF Job、下载训练正文、打开 R50、放开 G2/G3、合并 PR #7 或授权新增 GPU / 付费 CPU。
