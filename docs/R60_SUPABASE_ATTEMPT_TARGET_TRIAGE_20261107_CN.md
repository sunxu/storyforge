# R60 双轨 SFT：Provider Attempt / Assistant 目标元数据有界核验（2026-11-07）

状态：`METADATA_TRACE_TRIAGE_PASS__TARGET_ATTEMPT_LINKAGE_HOLD`

## 范围与权限

本报告为实时只读聚合结果，数据库查询由 `supabase_read_only_user` 执行。确认只读事务 `transaction_read_only=on`、`row_security=on`，**但该角色 `rolbypassrls=true`**。所有业务查询限 2026-11-06 UTC 一天的 `scene='v2-chat'` 日志，或者据此选出的 12 个最活跃 Session 各最多 30 条已完成 Assistant 消息。没有返回用户、Session、Story、请求或消息 ID 值，没有导出正文，没有使用 R50 资料。

此处高活跃样本**未经 Owner 逐作品授权审计，不能用于训练**。查询不是随机采样，不能把其通过率外推到全库或 Gold192。

## 实际证据数据

### A. 2026-11-06T00:00Z 至 2026-11-07T00:00Z 的 V2 Chat

- `v2-chat` 生成日志：**44,180**；44,180 条均有 `request_id`、`session_id`。
- HTTP 2xx：**36,780**；有 `attempt_trace`：**43,696**。
- `request_id` 在这一查询范围内 **44,180 个 distinct / 44,180 行**；重复 Request ID 为 0。这是**日志内唯一性**，不是与 Assistant 的一对一映射。
- `attempt_trace` 是 JSON 数组：单元素 39,913 条、双元素 3,725 条、三元素 57 条、四元素 1 条；其余 484 条 null。
- 在 36,780 条 HTTP 2xx 日志中，**35,218** 条同时满足 `attempt_trace` 仅一元素且为 `initial/success`；**1,562** 条为多尝试。单元素日志仅说明该字段显示的一次初始成功，不排除系统外部隐含重试/后处理/日志漏记。
- HTTP 2xx 内 `finish_reason` 标记 `length/MAX_TOKENS` 8 条，缺失 finish reason 42 条。不能从这些计数推断无后处理比例。
- GitHub RolePlay `src/lib/db/chat-latency-metrics-service.ts` 将 `attempt_trace` 定义为尝试分类、结果、模型和数字等**不包含 Prompt/响应正文**的观测字段。见 `ChatLatencyMetricsInput.attemptTrace`。

### B. 活跃 12 Session × 每 Session 最近 30 条完成消息

- 共 **360** 条、12 个不同 Story ID；其中 **153** 条创建于 2026-11-06 UTC，其他可能是历史回复。
- 360/360 有同 Session 前一 turn 的已完成 User，Story ID 均一致。这个事实不等于目标历史时点世界卡/记忆/System 已复现。
- 360/360 的 Assistant `metadata.finishReason` 为常见正常结束类型；长度终止 0。
- **4/360** 在 Assistant metadata 中有 `editedAt` 或 `originalContent` 标记，应优先排除或人工核证编辑/后处理。
- **103/360** 带 `parseWarnings` 键。键存在不证明存在实际严重错误；先作为可能受结构解析影响的审阅优先级，不直接判 REJECT。
- **0/360** 有检测到的直观请求关联顶层键 `requestId`/`request_id`/`relayRequestId`/`attemptId`。这不是证明全表、其他嵌套键、其他关联表不存在映射，但当前样本**不能直接凭消息 metadata 完成 E2 唯一绑定**。
- 12/12 Session 在此日均有 request ID 日志，但会话级日志存在不等于目标回复级关联。
- 以上统计只检查键名、状态和聚合计数，没有读取/输出私人正文或请求 ID 值。

## 两轨数据决策

### Strict Gold192

维持冻结 192、原 A/B 审核选择 28、已有三案语义 PASS。旧归档/备份已由 Owner 证实不存在；不能使用这份近期统计为历史 Gold192 提供实际输入证据。A/B 证据、Owner 审核、E0–E3/世界保护集仍为 HOLD。

### Experimental reconstructed-context

下一步仅在 Owner 已批准的作品/用户范围内执行候选级私有关联和权益筛查，并从可验证的不同世界选择数据。高价值候选的**优先级**可设为：完成的 Assistant、紧邻已完成 User、无编辑痕迹、无明显长度终止、无可能影响目标的 parseWarnings、相关请求日志显示一次 initial-success。单次请求日志如何与目标消息唯一关联仍未证明，必须有合法、可复核的对应证据才能进入 E2；不能用时间最近似关联冒充精确匹配。

严格与实验线的 dataset ID、候选清单、来源标注、split、验证世界、审核和 SAFE 统计必须分开。实验线可标注 `RECONSTRUCTED_NOT_ACTUAL_SENT`，不得将其提升为 Provider 真实发送载荷。

## 进一步调查的最小任务

1. 在 RolePlay 历史代码中确认 `request_id` 由哪个请求层创建、记录于何处、最终 Assistant Metadata 是否有独立的 operation / receipt 关联通路。先代码核对，避免因相同 Session/时间而错误 join。
2. 只对确认有合法使用权的来源进行 Owner 私有的 target–attempt 精确关联与有限上下文恢复；若无唯一映射即 HOLD，不做大规模正文导出。
3. 世界图/训练历史曝光/Protected Set 完整性仍需独立核验；12 Story ID 不等于 12 个世界。
4. 数据集与 GPU 都不启动；本轮 `strict_gold_admitted=0`、`experimental_admitted=0`、`training_authorized=false`、`gpu_started=false`、`database_modified=false`、`r50_accessed=false`。

本报告仅记录聚合与来源代码线索，既不冻结训练集，也不构成授权状态或训练准入决定。

## C. 同日 V2 Chat 活跃 Session 的高优先级元数据候选

后续采用 **仅 `scene='v2-chat'`** 的 12 个最活跃 Session，区别于上一份覆盖率报告中的**全场景** 12 Session。两组抽样标准不同，前者同日完成消息为 **152**，后者为 **153**；不得将两个 cohort 的计数合并或把 1 条差异视为数据丢失。

在 `scene='v2-chat'` 12 Session 各最近 30 条完成 Assistant 中，仅统计当天创建的消息：

- 2026-11-06 UTC 创建并完成的 Assistant：**152**。
- 不带 `editedAt` / `originalContent` 顶层编辑标记：**148**。
- 不带 `parseWarnings` 顶层键：**85**。
- 同时无上述编辑标记、无 `parseWarnings` 键、具有常见正常结束 `finishReason`：**81**。
- 81 条属于 **7 个不同 Story ID**，不是 7 个独立 world component；目前没有任何一条通过来源权益 / 世界隔离审核。

**代码级发现：** RolePlay `src/app/api/chat/v2/route.ts` 的成功流式生成路径先 `moderateOutput`，在阻断时可能把 `outputContent` 改为 fallback，然后经 `persistTurnMessages` 保存目标，才调用 `ChatLatencyMetricsService.record` 写 `requestId: logger.ctx.requestId` 与 `attemptTrace`（约第 5030–5200 行）。因此请求日志的完成状态仅说明应用成功流的后置指标，不证明其文本和原始 Provider Completion 完全一致。消息 metadata 抽样没有直观 requestId 顶层键；不得依靠 Session + 近邻时间做唯一匹配。

**下一次优先行动**：在 Owner 已认证使用权的作品中识别同等筛选条件下的少量候选，寻找真实可信的 target–attempt 关联和处理链，并区分原生单次响应与 moderation/重试/拼接/编辑。不要把这 81 条写入训练集，不准按结果推断可用率。
