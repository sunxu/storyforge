# R60 Base336 组件级精确复用图（SAFE；非独立裁决）

日期：2026-11-19。本报告基于 Owner 提供的 8 组成员级 Card/Opening、冻结 roster、代表性 World 证据及既有 Codex HOLD，未访问数据库或启动模型。所有原始 ID、角色名、逐案路径、原文、私有 SHA 保留于 Owner 私有文件，GitHub 仅保存脱敏的审查聚合。

## 可复核口径

- 按不同 Story（不是同一 Story 的 current/archived 修订记录）归并，比较 `character_PRIVATE`、`characters_PRIVATE`、`opening_PRIVATE`。采用**非通用、长段逐字相同（≥300 字符）或含充分信息的 Card/Opening JSON 完全相同**为“精确复用”下界，不将仅同名、空模板、字段名、头像 URL、不同故事 ID、近似分数判为已证实冲突。
- 同一故事可同时属于不同 World group：现有 roster 中恰有 2 个 Story 的分组分别为 01/06 与 03/06（归档/当前 World 版本造成的多归属）。不按记录数或分组成员数重复统计故事或候选案例。
- 冻结组内来源 59 条 = 38 current + 21 archived，涉及 38 个唯一 Story、82 个候选案例。基于已上传成员文件，只读比较得 **13 对不同故事存在精确内容复用**，其中 **6 对跨 Train/Validation、7 对仅同一拆分内**。所有 13 对关联对应去重 20 Story、41 个候选案例；6 对跨拆分关联对应去重 **11 Story、22 个候选案例**。这 22 个案例是已确认精确复用的**保守下界**，不代表可能语义污染的全部范围。

## 跨 Train/Validation 的直接精确证据

| Group pair | 不同 Story 对 | 去重 Story | 此组对去重候选案例 | 证据类型 | 当前建议 |
|---|---:|---:|---:|---|---|
| 01 ↔ 06 | 1 | 2 | 3 | 最长 672 字符的非模板逐字重合 | CONFLICT_CANDIDATE |
| 02 内 | 1 | 2 | 3 | 最长 2,368 字符的非模板逐字重合 | CONFLICT_CANDIDATE |
| 05 内 | 1 | 2 | 7 | 最长 3,789 字符的非模板逐字重合 | CONFLICT_CANDIDATE |
| 06 内 | 1 | 2 | 4 | 最长 1,492 字符的非模板逐字重合 | CONFLICT_CANDIDATE |
| 08 内 | 2 | 3 | 5 | 至少两对不同 Story 的完整角色卡 JSON 相同；其中有完全一致的 Opening JSON | CONFLICT_CANDIDATE |
| **全局去重** | **6** | **11** | **22** | 不可将组对数字未经去重直接相加 | **HOLD** |

重要：精确文本复用可证明静态当前/历史版本素材关联，**不能证明**该内容在原始历史推理的 actual-sent 版本中被送达，也不能单独替代独立 Reviewer 的世界隔离裁决。

## 非精确证据层（未计入 6 对）

- 02↔03：有明确角色阵容相同的语义候选链接，但不是以本轮“长段逐字重复”标准归入跨组确切边。
- 03 组 Validation 的同一个 Story 同时出现在 06 组 roster；因此“跨组关联”不全是独立 Story 间的相似性，不能重复计入候选数量。
- 05 组有近似改写的人物设定与相同角色名的其他可能边，未通过精确边标准的不得自动升格为事实性冲突。
- 04 组主要存在重复关系/写作指令框架，07 组未发现组内专属实体确切复用；均不能因缺少逐字重复而获得语义隔离 PASS。
- 既有 Codex 八组均为 HOLD；本轮是非独立审查提案，未修改旧 Reviewer 决定或 Owner Freeze。

## 下一步最小动作

1. 将 6 条精确跨拆分不同 Story 边和其他非精确候选纳入 **Owner-local 独立 Reviewer** 包；每条边在私有环境按 Story、revision、字段路径和证据位置追溯。公开 GitHub 不写原文、ID、映射、附件。
2. Reviewer 给出 `SAME_SEMANTIC_COMPONENT` / `INDEPENDENT_TEMPLATE_ONLY` / `INSUFFICIENT_EVIDENCE`，核对剧情事件、角色关系、组织、时间及具体版本，不能只凭精确 World JSON、同名、同人/IP 标签、空模板或模板文字判定。
3. 已确认组件边使用现有 `src/storyforge_dataset/world_isolation.py` 的组件冲突验证函数，不复制另一套隔离逻辑；Owner Freeze 之前冻结数据不变。
4. 保持 actual-sent 版本、R50 完整 metadata-only roster、R47/R48/R55 全量暴露及 Reviewer 独立性为独立 HOLD；不执行 R50 正文访问、HF/GPU/训练、模型生成或 48 条正式提示构造。

```text
BASE336_MEMBER_FILES = VERIFIED_8_OF_8
BASE336_SOURCE_RECORDS = 59
BASE336_DISTINCT_STORIES = 38
BASE336_AFFECTED_CASES = 82
EXACT_REUSE_STORY_PAIRS = 13
EXACT_REUSE_CROSS_SPLIT_PAIRS = 6
EXACT_REUSE_SAME_SPLIT_PAIRS = 7
EXACT_REUSE_CROSS_SPLIT_STORIES = 11
EXACT_REUSE_CROSS_SPLIT_CASES_LOWER_BOUND = 22
INDEPENDENT_REVIEW = PENDING
HISTORICAL_ACTUAL_SENT = NOT_VERIFIED
P2_C = HOLD
P2_B_48_PROMPTS = NOT_GENERATED
TRAIN_ADMITTED = 0
QUALITY_V1_ADMITTED = 0
DATABASE_ACCESSED_THIS_REVIEW = false
GPU_STARTED_THIS_REVIEW = false
```
