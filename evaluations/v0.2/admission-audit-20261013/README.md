# StoryForge v0.2｜训练准入门禁审计（2026-10-13）

**状态：`BLOCKED_TRAINING_NOT_APPROVED`。** 本目录只新增审计证据，不改写 01–05 已冻结 87 条、06–15 已冻结 108 条、原始故事或 v0.1 标签。不得将 195 条质量认可样本视为 train.jsonl。

## 已实际完成

- 对完整备份 `StoryForge_v02_06-15_Full_Evidence_20261013.zip`（SHA256 见 `gate_report.json`）进行了离线标准库核验：150 个原始候选、108 个双 ACCEPT、108/108 目标 Assistant 原文与 10 个 raw export 中的原消息相同；ZIP CRC 完整。
- 发现 **3 条**早期记录缺少主 `metadata.story_id`，原始 `source_story_id` 有效，逐条可匹配真实源故事；本目录仅记录补证，不修改原文 metadata。
- 发现 **44 条**当前导出故事卡的 `updated_at` 晚于对应目标回复 `created_at`，其中 08=4、10=19、13=16、15=5。另 64 条未发现此顺序冲突，但**所有 108 条均缺少独立可证的目标时刻故事卡版本**。不要把导出时最终卡片直接注入过去的训练回合。
- 87 与 108 本身故事 UUID 不重合、末轮回复无逐字重复；v0.1 65/15/20 与第二批 108 的故事 UUID 和末轮回复均无精确重复；v0.1 Validation/Test 与第一批 87 也没有故事 UUID 重叠。
- **第一批 87 的 21 条属于 v0.1 旧 Train 中曾见过的同一故事 UUID**（旧 Train 该故事 2 条：sample-000073、sample-000074）；这 21 条不能拿来作为评估 v0.1 已训练模型的独立 held-out 样本。

## 尚未通过的门禁

| 门禁 | 结果 | 必须补充 |
|---|---|---|
| 历史故事卡及长期人设、规则 | BLOCKED | 每个目标时刻对应的可复现角色卡版本，禁止未来信息 |
| 人物年龄、亲密授权及内容边界 | BLOCKED | 目标时刻证据和逐样本人工/独立复审，不得因年龄字段存在就推定通过 |
| 故事 04 ↔ 07 关联隔离 | LIMITED | 本批 07 实际选中 0，不能因此批准未来关联故事混合 |
| v0.2 整故事拆分 Train/Val/Test | NOT RUN | 新版本独立规划、审核后冻结，禁止行级随机拆分 |
| Qwen3.8 16,384-token | NOT RUN | 锁定 tokenizer revision + 目标时刻 system prompt，再按真实 chat template 编码 |
| ms-swift 4.5.3 Loss Mask | NOT RUN | 实际 encode 所有候选，确认系统、用户、历史 Assistant 标签均为 -100，只有最后 Assistant + 合法后缀被监督 |

## 文件说明

- `gate_report.json`：来源校验、数量、审计结果与未通过门禁。
- `card_snapshot_conflicts_44.json`：44 个需要版本化角色卡回溯的候选 ID，外加 3 个经核实的来源 ID fallback。
- `v01_overlap_audit.json`：五个固定 Git Blob 与逐字匹配／故事 UUID 交叉检查的不可变证据。

## 原始证据与复核

- 原始完整 ZIP、回溯脚本：[`../source-archives/06-15/`](../source-archives/06-15/README.md)
- 第二批双评审选择：[`../gold-quality-108/`](../gold-quality-108/README.md)
- 第一批质量冻结：[`../gold-quality-87/`](../gold-quality-87/README.md)
- 仓库的 `scripts/hf_label_mask_audit.py` 与 `scripts/audit_gold_token_lengths.py` 是历史 v0.1 工程核验器；它们的旧 PASS **不代表本批 108 的实际模板已审计**。

**后续实施顺序：补目标时刻角色卡 → 成年及内容边界 → 关联故事隔离 → 整故事拆分方案 → pinned tokenizer → 全样本运行时 Loss Mask → 才能讨论训练。**

本次没有新 GPU/HF 作业、没有生成 B 模型、没有训练，也没有修改 Gold 数据。
