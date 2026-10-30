# R58 — RolePlay 首批私有重放试点：10 条分层 / 3 条优先（SAFE）

**日期：** 2026-10-30  
**状态：** `PILOT10_METADATA_HISTORY_CHECK_PASS__PRIORITY3_SELECTED__EXACT_RUNTIME_REPLAY_HOLD`

## 范围与边界
- 复用固定种子 `:R58:20261030:pilot2:versioned` 的 24 故事/45 根会话/135 个检查点后 Assistant 位置；对其中 133 个有前序故事版本证据的目标实施只读规则筛查。
- 已有阶段证实 133/133 有生成前的批准提交及结构化故事卡候选快照，旧读者公开投影的 17 个位置也有旧批准卡，而不是以作者当前稿替代。
- 本次 SQL 只返回按证据等级的**聚合统计**。未读取、下载、提交故事卡 JSON、具体故事/用户/消息 ID 或聊天文本，未访问 R50、未执行付费计算或写 Supabase。
- **不是已冻结的物理案例集**：生产库和统计表会变动；在私有工作区固定 message ID、批准 submission ID、来源字节及哈希前，复跑不保证产生同一批记录。

## 1. 133 条证据等级分布

将 **检查点距目标的逻辑轮次**、`v2EventRuntimeBefore` 元数据及附近 30 秒内唯一的成功 V2 请求指标（仅弱关联）组合为下列优先级：

| 等级 | 条数 | 说明 |
|---|---:|---|
| A | **30** | 检查点≤5 轮、事件前状态字段、30 秒内恰有一条成功 V2 推理指标 |
| B | **36** | 检查点≤5 轮、事件前状态字段，缺少唯一推理指标 |
| C | **15** | 检查点≤5 轮，事件前状态字段不齐 |
| D | **47** | 检查点 6–20 轮 |
| E | **5** | 检查点超过 20 轮（其中 3 条约 1957–1959 轮） |
| **合计** | **133** | 所有等级仍是**候选证据等级**，绝非训练质量分数 |

**注意：** A 的时间邻近唯一指标不意味着该指标的 `request_id` 与这条完成回复精确匹配。

## 2. 可复算的 10 条试点（每故事 ID 最多 1 条）

固定 tie-break 种子 `:R58_PRIVATE_REPLAY_PILOT_20261030`，先选择旧公开卡最多 3 条，再选择作者本人路径最多 1 条，最后选择现公开卡最多 6 条。跨这些组排除重复故事 ID：

| 组别 | 选择 | 最近历史检查点 | 带事件前状态的目标 | 有唯一 30 秒成功推理指标 |
|---|---:|---:|---:|---:|
| 读者现公开版本 | 6 | 1 轮 | 6 | 6 |
| 读者历史旧公开版本 | 3 | 1–3 轮 | 3 | 2 |
| 作者本人当前稿路径 | 1 | 1 轮 | 0 | 1 |
| **共计** | **10** | **1–3 轮** | **9** | **9** |

10 个不同 story ID **并不等于** 10 个无语义别名或交叉曝光的独立故事世界。该试点还没有完成任何训练或保护集曝光检查。

执行中的当前数据库窗口检查：
- 10 条目标各能找到 **24 条较小 turn_index 的消息**，合计 240；目前 240/240 为已完成状态，且未见创建时间反而晚于目标的前置消息。**这不能证明当时请求发送了这 24 条**。
- 240 条中的 108 条当前 `mutation_revision>0`；只表明内容、状态或元数据等曾变更，尚不能判定历史正文不一致。
- 9 条目标附近可匹配成功推理指标，指标均记录 `historyMsgCount=11`；另 1 条缺指标。其值与当前 DB 24 条原始消息不能直接比较：`route.ts` 会做有限预取、摘要滑窗、恢复/重生分支与 scrub，并在末尾追加/改写当前用户指令。**不能硬塞 24 条或者把 11 条直接截为最近 11 条冒充历史输入。**

SQL: [10-case selection and history checks](R58_ROLEPLAY_PRIVATE_REPLAY_PILOT10_QUERY_SAFE_20261030.sql)。

## 3. 从 10 条进一步选择 3 条代码时间线更有利的试点

GitHub 源码查询显示关键文件最近一次已知修改：
- `src/app/api/chat/v2/route.ts`：2026-10-19 UTC；
- `src/lib/db/v2-message-service.ts`：2026-10-24 UTC；
- `src/lib/story-v2/context-builder.ts`：2026-10-26 07:05:10 UTC；
- `src/lib/story-v2/prompts/index.ts`：2026-09-29 UTC；
- 本次固定源码提交 `e9fe29c4...`：2026-10-29 UTC。

10 条中，有 **7 条**早于 10 月 26 日记忆构建器源码变更，有 **9 条**早于固定提交。优先取创建时刻不早于 10 月 26 日 07:05:10 UTC 的 3 条：

| 先行私有试点 | 条数 | 近似历史指标 | 检查点间隔 |
|---|---:|---|---|
| 作者稿 | 1 | 附近 `historyMsgCount=11` | 1 轮 |
| 当前读者公开稿 | 1 | 附近 `historyMsgCount=11` | 1 轮 |
| 历史旧公开稿 | 1 | 附近 `historyMsgCount=11` | 3 轮 |

**源码提交时间不等于生产部署时间。** 这些 3 条只是减少了已知代码变更的时间差，未证明完整历史运行时代码与当前 fork 相同，也不能将推理指标的 `request_id` 直接归给完成消息。

SQL: [three-route source-window pilot](R58_ROLEPLAY_PRIORITY3_SOURCE_WINDOW_QUERY_SAFE_20261030.sql)。

## 4. 精确复原仍缺的证据与明确行动

1. 仅在受控私有执行环境生成并冻结 3 条的 `story_id/session_id/message_id`、审核提交 ID、`snapshot.source.v2Data` 源卡字节与 SHA256；先校验完整语义世界与保护集**元数据**，防止访问 R50 正文。
2. 找到目标时间的**真实已部署源码 commit、灰度配置、selectedModel、locale、续写/重生及其它请求参数**。若只能依据当前源码推定，标注 `CODE_VERSION_UNVERIFIED`。
3. 使用检查点和时间线恢复导演、摘要、RAG、记忆事实/实体卡、前后轮状态；尝试基于当时逻辑重建 `llmHistory`，不可把现存 Session 当前字段代入历史。
4. 将重建的 System 和输入消息在**私有**环境冻结，保存 `source_card_hash`、`history_hash`、`reconstructed_prompt_hash`、`code_sha` 与 `runtime_config_hash`。若缺原始实际请求字节或可信请求哈希，只能称 `RECONSTRUCTED_WITH_EVIDENCE`，**不能**自称 `BYTE_EXACT_PASS`。
5. 完成内容双审及独立世界 Train/Val 划分以后，才允许正式 v0.4 准入；Hugging Face CPU 预检和 GPU 训练均属于额外授权门禁。

## 状态和仓库边界

`PILOT10_METADATA_HISTORY_CHECK_PASS__PRIORITY3_SELECTED__NO_EXACT_REPLAY__V04_ADMITTED_0`

本次仅更新 PR #7 的 SAFE 审计查询和报告，**未修改 Skill v0.1**；PR 保持 DRAFT。
