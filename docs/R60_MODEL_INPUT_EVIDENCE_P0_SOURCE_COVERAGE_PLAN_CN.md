# R60 P0：Gold192 模型输入证据来源覆盖率首轮核查（只读）

日期：2026-11-07
状态：待执行。**此计划没有执行行级查询，也没有把任何候选样本升级到 A/B/C/D。**

## 0. 已收到 Owner 证据槽位初始化 SAFE

- schema: `r60_model_input_evidence_seed_safe_v1`
- status: `EVIDENCE_SLOTS_SEEDED_NOT_REVIEWED`
- Gold192 总数: 192；`UNKNOWN_NOT_REVIEWED=192`
- A/B/C/D: null，代表**尚未核实**，不是 0
- source locator SHA256: `eb2b186b03ffc31585c224ac75cbfd7dd20c8d762887a6463c85bc5090ae9739`
- private slots SHA256: `69e83d6c61a6be5eb1516d3fd2987fc086259597fd8f900cc02c445debb9a5e9`
- `evidence_review_started=false`、`quality_v1_admitted=0`、`training_authorized=false`、`gpu_started=false`、`database_modified=false`、`r50_accessed=false`、`private_values_emitted=false`。

这些哈希由 Owner 的 SAFE 回执提供，尚未从本环境读取并独立计算本机私有文件字节。该回执只证明槽位初始化程序返回预期状态，不证明已查到任何真实 Provider 请求。

## 1. 已确认的证据容器（仅 Catalog 元数据）

对已连接 Supabase 只读 Catalog 做过 `pg_catalog` 查询，确认：

| 表 | 相关字段 | 对 Gold192 的作用 |
|---|---|---|
| `public.v2_chat_reply_jobs` | `request_envelope`、`model_id`、`attempt_count`、`session_id`、`assistant_turn`、`client_msg_id` | 生成任务关联候选，**并非发送态完整请求证明** |
| `public.chat_abnormal_snapshot` | `request_id`、`relay_request_id`、`conversation_context`、`history_preview`、`memory_injection`、`continuation_attempts`、`expires_at` | 失败、重试等异常的部分输入/尝试证据；经常截断 |
| `public.chat_latency_metrics` | `request_id`、`relay_request_id`、`relay_trace_id`、`attempt_trace`、`model` | 尝试关联候选，非原始请求体 |

**当前连接角色为 `supabase_read_only_user`**，不是 R60 私有恢复基线的 `r58_export_reader`。因此前一步只查询表/列定义，未查实际生产用户数据。后续任何聚合或 Gold192 局部证据验证，都须通过 Owner 已验证的受限凭据/权限执行，确认 RLS、只读事务和超时设置。

此外，异常表名必须是 `chat_abnormal_snapshot`（单数），不能使用 `chat_abnormal_snapshots`。

## 2. 第一轮只读聚合的先决条件

1. 连接角色必须满足最小权限，且可观察到的行集满足本项目的业务授权。绝不为提升覆盖率使用 service_role 或 RLS bypass。
2. 在 `BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY` 后确认 `current_user`、`transaction_read_only`、`row_security`、`statement_timeout` 和 `lock_timeout`；未满足立即停止。
3. **首先只查询 Catalog**：三个候选表的 relkind、估算行数、索引列、RLS 与关键字段；确认预期索引可支持有界时间窗才执行真实聚合。
4. 对经确认授权且范围有界的查询，仅输出：覆盖时间窗、行数分桶、关键 linkage 字段非空率、请求重试/模型路由计数的整数；不输出任何 user_id、session_id、request_id、message_id、故事名、prompt、JSON payload。
5. 若读取 `request_envelope` 或 `conversation_context`，**只做 SQL 侧类型、键存在、长度和截断标识的聚合**；不返回内容。不能认为某 JSON key 存在即完整输入可证明。
6. 若存在留存清理或事件覆盖缺失，只标记 `EVIDENCE_SOURCE_COVERAGE_UNKNOWN_OR_MISSING`，不把受影响 Case 判 D。
7. Gold192 Case 关联是单独第二阶段：只能在 Owner 本地用原始冻结 locator 做受控 JOIN，输出 Case 级结果到 0700/0600 私有文件，并只打印聚合 SAFE。没有此步不得给出 A/B/C/D 统计。

## 3. 针对性分期核查

### S1：有无实际可查记录（表级）

- `v2_chat_reply_jobs`：状态和 created_at 年月分桶；含输入信封的 JSON 类型，但绝不读取原值到客户端。
- `chat_abnormal_snapshot`：异常类型/保留时间窗；request_id / relay_request_id 非空率；history/context 是否被截断的元数据。
- `chat_latency_metrics`：日期/模型通道分桶、request_id 与 relay_request_id 非空率；仅计数。
- 归档文件/Relay 外部存储：请 RolePlay 项目方核实**是否启用、旧数据保存多久、是否存在请求正文、是否能与最终回复绑定**。不可仅依赖数据库目录猜测。

### S2：Gold192 Target—Attempt 关联（私有）

严格使用冻结 locator 中可验证的 message/session/turn 身份，核实：

- 有无对应 reply_job、latency request ID、异常快照，是否出现多对一或一对多；
- 生成尝试之间是否发生降密重试、validation_retry、auto_continue、模型 fallback；
- 最终 Assistant 可能是多个分段拼接或 moderation 替换，必须单独标记；
- 只有模型输入证据原始留证完整且可追溯时，才考虑 A / B。

### S3：逐案证据判定

- `A`：实际最终发送请求和目标生成尝试完整关联（需考虑 Provider 出站转换）。
- `B`：完整且可独立验证的确定性输入重建（所有运行时依赖和后处理可验证）。
- `C`：部分旁证、缺少关键输入或关联，保持 HOLD。
- `D`：经过可解释的独立来源核查，确属不可验证，不能因为表中查不到就自动标 D。
- `UNKNOWN_NOT_REVIEWED`：尚未逐案完成上述流程。

所有级别与 `Quality-v1`、Reviewer、Owner 授权、Train/Validation/Test 隔离、R50 Held-out 隔离独立；`admitted=0` 不变。

## 4. 本阶段禁止事项

不运行数据库 DML/DDL，不访问 R50，不导出聊天/Prompt 原文至聊天或 GitHub，不读生产 JSONB 全文，不允许绕过 `LEDGER_TEMPORAL_ORDER_AUDIT_REQUIRED`，不生成训练候选，不启动 GPU。

T1 Ledger Writer Path 审计保留为 RolePlay P1 的数据可靠性治理以及必要个案的支持任务，不作为 P0 输入证据调查的统一硬门槛。
