# StoryForge v0.2 — 87 条 Gold 质量认可集（2026-10-12）

**项目负责人选择策略：保留 Reviewer A/B 双 ACCEPT、五维各项≥4、无严重错误代码的 87 条原候选；其余 25 条不再开展追加评审。** 旧排除对照 10 条不纳入本次 Gold，即使其中 3 条有 A/B/C 全通过。

## 唯一权威口径

- 内容质量决策：`GOLD_QUALITY_ACCEPTED_BY_OWNER`（87 条）。这里的 Gold 是**内容质量已认可的训练候选池**。
- 工程训练准入：**`PENDING_NOT_APPROVED`**。严禁把 `gold_quality_accepted_87.jsonl` 当成已完成全部门禁的 `train.jsonl`。
- 数据拆分：尚无 train/validation/test；只能按整个 `story_id` 单元划分，并先核查 v0.1 旧故事/旧盲审的重叠。
- 训练目标：仅最终 Assistant 回复。历史 Assistant 必须 mask；原记录没有被改变。
- Reviewer A 的补正：7 条涉及这 87 条，SF2-073 尚有严格逐字引文格式异常（正文实际可拆分定位）；为尊重本次停审决策，本次只记账不请求继续更正。
- 故事 04 年龄字段未核实，非露骨局部原文候选不等同全故事内容安全准入。
- 三组《战争与血》同场景二选一建议在 87 条中自然满足；没有仍同时保留的硬重复组，但主题相关性仍然存在。

## 精确数量

| 故事 | 内容质量认可 | 仅本轮选入 |
|---|---:|---|
| 01 京圈的灯火与暗流 | 21 | 是 |
| 02 如何攻略仙尊 | 24 | 是 |
| 03 雪停之前重逢 | 14 | 是 |
| 04 处女之死 | 10 | 是 |
| 05 战争与血 | 18 | 是 |
| **合计** | **87** | |

其他原候选 25 条（19 HOLD_CONTEXT、6 原仲裁组，其中 C 后 5 仍有分歧、1 建议排除）全部 **NOT_SELECTED_THIS_RELEASE**，不再开展本阶段审查，但保留在 `other_25_closed_without_gold.csv` 供历史审计。10 条隐藏对照从未进入 112 原候选，也不进入 Gold。

## 文件

- `gold_quality_accepted_87.jsonl`：严格复制五个最新版本已有候选记录的整行字节内容。未经任何模型重写/补造，也没有修改原始 metadata 里的 `training_admission=PENDING_NOT_APPROVED` 与 `split=null`。
- `gold_87_index.csv`：匿名 ID 到实际原文目标 ID 的来源清单、双评审通过状态和引文状态。
- `other_25_closed_without_gold.csv`：本次不选的 25 条状态快照，不包含对照。
- `selection_manifest.json`：机器可读版本、文件摘要、审批层级和工程待办。
- `scene_overlap_hard_groups.json`：原建议同场景二选一的三组，在 87 条中实际保留内容。
- `build_storyforge_gold87.py`：从既有五故事原始证据重新构建选择清单。
- `verify_gold87.py`：独立检查87条与来源的逐行字节、评分门禁、排除名单和哈希。
- `verification_report.json`：本次核验输出。
- `selftest_gold87.py`：篡改目标、划分及匿名身份的拒绝路径测试。
- `SHA256SUMS.txt`：其他交付文件完整性校验（不包含本文件）。

## 复现说明

从原始 5 份 JSONL、5 份最新 Gold 累计包、A/B 汇总、C 状态覆盖表及 A 补正清单执行 `python3 build_storyforge_gold87.py --root /mnt/data --out /mnt/data/另一个输出目录`；绝不可用本选择结果反过来改写 v0.1 冻结证据或覆盖 R01–R05 原文件。

所有决策均为**用户的质量名单截断策略**，不是对全部历史事实/医疗判断/内容门禁的重新独立审查；没有新增人类或模型打分，没有 HF Job/GPU/训练，也没有 GitHub 写入。
