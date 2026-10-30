# StoryForge R58 — 133 条候选的历史公开故事卡溯源（SAFE，2026-10-30）

## 状态

**HISTORICAL_APPROVED_STORY_CARD_SNAPSHOT_LOCATED_133_OF_133__EXACT_RUNTIME_INPUT_HOLD_0_OF_133**

本轮针对前次确定的 24 个故事、45 个已持久化根会话、135 个检查点后 Assistant 位置，重点分析已有较早版本证据的 133 条。查询使用固定种子、**生产库动态即时数据**，尚未冻结物理 case ID；统计重复执行可能变化。

- RolePlay 源码 pin：`sunxu/RolePlay@e9fe29c42434caeb0bac5acc91845ab4741ecb2b`。
- Supabase 只读 `SELECT`，全部返回都是**汇总计数**，审核快照 JSON 仅在 PostgreSQL 内部用于结构类型检查及 JSONB 相等比较；没有导出故事 ID、用户 ID、原文或逐案故事卡。
- Skill v0.1 仍保持原样；没有读取 R50、启动 Teacher / HF Job 或批准 v0.4 训练。

## 一、重大突破：17 条旧公开卡可以从历史批准提交中找到

数据库 `story_moderation_submissions.snapshot.source.v2Data` 保存**结构化完整 V2 故事配置 JSON 对象**（注意字段名 camelCase `v2Data`，不是 `v2_data`）。`story_moderation_action_logs` 中 `to_state IN ('ai_approved','human_approved')` 且 `to_visibility='public'` 的审核通过事件，可以与 `submission_id` 相联。数据库触发器 `maintain_story_public_version_projection()` 将批准时的 `NEW.v2_data` 晋升到读者实际读取的 `public_v2_data`；`finalize_story_moderation_ai_core()` 要求审核仍绑定当前 submission 和 content revision，防止过期审核写回不同稿件。数据库已有函数 `read_story_moderation_approved_baseline()` 也依赖批准提交与 revision 的关联。

本轮的每条目标都找到其**生成前最近一次批准公开的提交**；每条提交快照都有 `snapshot.source.v2Data` JSON 对象，并检查批准之后到目标回复之间是否存在审核降级或转私有状态日志——133/133 未见。

| 目标时点配置路径 | 位置 | 公开版本证据 |
|---|---:|---|
| 作者本人使用当前作者稿 | 3 | 以前的批准快照也存在，当前公开配置与提交快照相同；但作者实际走 `user_stories.v2_data` |
| 读者：当前公开卡时间戳不晚于回复 | 113 | 113/113：最近批准快照 JSONB 与当前 `public_v2_data` 相等 |
| 读者：当前公开卡晚于回复、曾被更新 | 17 | 17/17：最近批准快照的 `v2Data` 与当前 `public_v2_data` 不同；对应 4 个独立的历史批准提交 |
| **总计** | **133** | **133/133 有早于目标的完整批准故事配置 JSON 证据** |

**重要限定：** 已找到能够恢复目标时点**原始批准故事配置的候选快照**，不是已证明当时完整 Runtime Prompt 或字节相同的模型实际请求。旧版源码和当时发布顺序、翻译与缓存投影仍需核查；PostgreSQL JSONB 相等也不是原始 HTTP 请求字节相等。此前针对 17 条的 `HOLD_OLD_PUBLIC_PROJECTION_MISSING` 可更精确地更名为 `OLD_PUBLIC_APPROVAL_SNAPSHOT_FOUND__RUNTIME_PROJECTION_UNVERIFIED`，**不是整体 PASS**。

复核 SQL：[历史批准公开卡源核查](R58_ROLEPLAY_APPROVED_PUBLIC_CARD_REPLAY_QUERY_SAFE_20261030.sql)，与本报告一起归档。

## 二、动态语言、缓存、会话状态仍然无法倒推

- `localizeStoryForReader()` 对非 `zh-Hans` 可以选择 `story_content_translations` 缓存，并在过期期间继续使用旧版完整译文。**无法仅凭存在译文缓存推断目标回复使用的 locale/翻译内容**。
- 133 条中有 87 条的同故事至少一个当前译文缓存行创建于其目标时间之前：作者 3、读者当前公开卡 73、读者旧公开卡 11。这只是**故事层缓存存在性**，不是请求使用译文的数量。用户请求 locale 没有在目标消息 metadata 中直接落成可用字段。
- 133 条对应的现存 `story_v2_sessions.updated_at` 都晚于其目标回复，不能把当下 `memory_summary`、`rolling_outline`、`pending_directive` 当成目标时点值。
- 在目标消息的 metadata 里有 106 条 `v2EventRuntimeBefore/After` 字段，有助于局部状态核验；此前检查点 133/133 均包含历史 V2 状态，但缺完整 system 和消息列表。
- `chat_latency_metrics` 使用同用户+故事+会话+回复时间前后 30 秒的启发式关联：67/133 能找到成功 V2 指标，其中 60 个仅一条、7 个多条；这 67 个最近指标均报告 `runtimeBase.mode='native'`、`promptVersion=21`，其余 66 条在该窗口无成功指标。**这不是精确请求 ID 关联**，不能认定 67 条已完成 Prompt 版本归因。
- 133 个目标创建时间范围：2026-10-01 01:59:41 UTC 至 2026-10-30 05:07:42 UTC；**106 条早于本次源码 pin 的 2026-10-29 commit**。它们可能使用旧的线上部署，不能用当前 Git HEAD 自动重放。

## 三、下一道可执行门禁

1. 从本轮历史批准提交建立 **私有源卡清单**，按候选目标生成 `source_approved_submission_id`、`source_content_revision`、`source_v2_data_sha256` 和时间关系证据。不得把清单或敏感映射提交公开/普通 Git。
2. 以实际部署 commit（或其他可靠的请求时 Prompt 版本与运行配置）复原 base mode、输出语言、开场选择、角色身份、硬约束，以及是否生效的事件/反复读/重试尾部注入。
3. 对历史检查点及其后的增量消息、摘要、记忆检索、导演状态执行时间线重建。不得用会话现值倒灌旧回复。优先选择**检查点近、无复杂分支、独立世界已审核**的少量样本做端到端校验。
4. 若无法取得当时真实请求内容/可信请求哈希，则仅能达成 `RECONSTRUCTED_WITH_EVIDENCE`，**不能宣称 `BYTE_EXACT_PASS`**。无证据项必须 HOLD。
5. 训练/验证世界隔离、R50 保护集元数据重叠核查、双 Reviewer、Owner 批准及 HF CPU Collator 预检是后续独立门禁。

**准入：Train 0、Validation 0；Skill v0.1 未改，PR #7 保持 Draft。**
