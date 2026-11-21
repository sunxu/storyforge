# R60 Base336：八组成员级世界语义复核（SAFE；非独立最终裁决）

日期：2026-11-19。Owner 上传八组 Card/Opening、冻结 roster、代表性 World、既有 Codex 决策。共 8 组、38 个不同 Story、59 条 current/archived 记录（current 38、archived 21）、82 个相关候选案例。此前 Owner-local 脚本汇报 8/8 文件、权限 0700/0600、逐条 roster 对齐及 SHA 绑定 PASS。本轮独立检查了上传的代表性 World 文件与 roster 原始字节 SHA 绑定、旧 Codex 文件与 World 文件及 roster 的 SHA 绑定，均一致；既有 Codex 八组决定仍为 HOLD，独立 Reviewer 身份及执行隔离未验证。

原始人物姓名、剧情、标识、版本号、原文引用和私有 SHA 不进入本报告。文本重合指标只是内部检索辅助，不取代独立语义裁决。

## 每组结论

| 组 | 新增成员级事实 | 当前建议 |
|---|---|---|
| 01 | 本组 Train/Validation 人物与场景未发现直接的专属实体对应；但 Train 成员中的特定角色在组 06 的另一拆分中重复，存在跨组关联。 | HOLD：与组 06 联查 |
| 02 | Train/Validation 复用同一组四个具名人物、详细背景和高度接近的开场，存在长段非通用成员内容逐字复用。 | CONCRETE_CROSS_SPLIT_COMPONENT_REUSE_FOUND |
| 03 | Train 与 Validation 的直接人物集不同，World 值属于宽泛模板；但 Train 人物与组 02 对应，Validation 历史修订人物与组 01/06 对应。 | HOLD_WITH_CROSS_GROUP_LINKS |
| 04 | 不同角色和具体场景，但关系/行为指令框架有大量复用；尚未证明同一专属人物、组织或历史事件。 | HOLD__PROMPT_TEMPLATE_REUSE_RISK |
| 05 | Train/Validation 中至少两个不同的具体人物组件高度重复；相关背景/人物描述存在大段完整或近完整复用。 | CONCRETE_CROSS_SPLIT_COMPONENT_REUSE_FOUND |
| 06 | Train/Validation 中至少两个具体人物与剧情组件复用，其中一处人物说明逐字重合，另一处背景和开场几乎相同；另与组 01/03 有跨组人物关联。 | CONCRETE_CROSS_SPLIT_COMPONENT_REUSE_FOUND |
| 07 | 两侧人物、背景与开场不同，未发现直接专属实体对应；共同的架空世界字段是类型模板而非独立性证据。 | HOLD__NO_DIRECT_COMPONENT_MATCH_IN_EXAMINED_FIELDS |
| 08 | Train/Validation 相同的角色组合、世界内地点及叙事起点；至少一对成员版本的 character、characters、opening 三字段完整 JSON 相同。 | CONCRETE_CROSS_SPLIT_COMPONENT_REUSE_FOUND |

## 证据意义

- 旧 Codex 的八组 HOLD 主要来自只检视单一代表 World JSON，缺少成员级 Character/Card/Opening。此次新增材料明确给出组 02、05、06、08 之间的跨拆分实质内容复用迹象，不能再只按 World JSON 模板分类。
- 不应以“相同 World JSON”把组 03 中互不相干的题材全部误连成同一语义世界，也不应忽略不同组间复用的相同人物。应建立**按具体实体/角色/剧情事实**的组件图，并复用仓库唯一的 world isolation conflict helper 做声明后的结构冲突校验。
- “CONCRETE_CROSS_SPLIT_COMPONENT_REUSE_FOUND”是本次内容复核的**风险标记**，不是已经核验历史 actual-sent 的事实，也不是正式独立 Reviewer 决策，不表示需自动删除冻结案例。
- 所有来源文件仍标记 historical_actual_sent_verified=false。实际送达版本、R50 完整 Protected/Reserved metadata-only coverage、完整旧曝光集合、独立 Reviewer 和 Owner freeze 均待核验。

## 当前门禁

```text
BASE336_CARD_OPENING_STRUCTURE = VERIFIED_8_OF_8_AS_OWNER_REPORTED
BASE336_MEMBER_LEVEL_SOURCE_RECORDS = 59
BASE336_CURRENT_RECORDS = 38
BASE336_ARCHIVED_RECORDS = 21
BASE336_AFFECTED_STORIES = 38
BASE336_AFFECTED_CASES = 82
CONCRETE_CROSS_SPLIT_REUSE_GROUPS = 4
CROSS_GROUP_COMPONENT_LINKS_FOUND = true
INDEPENDENT_SEMANTIC_ADJUDICATION = PENDING
HISTORICAL_ACTUAL_SENT = NOT_VERIFIED
R50_FULL_METADATA_ONLY_PROTECTION = HOLD
P2_C = HOLD
P2_B_48_PROMPTS = NOT_GENERATED
TRAIN_ADMITTED = 0
QUALITY_V1_ADMITTED = 0
DATABASE_ACCESSED_THIS_REVIEW = false
GPU_STARTED_THIS_REVIEW = false
MODEL_REQUESTS_THIS_REVIEW = 0
```

隐私：仅报告不含敏感名字、Story ID、文本、引用、私有 SHA 或逐案映射的汇总；Owner 原始文件未写入 GitHub。