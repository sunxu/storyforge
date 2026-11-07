# R60 Supabase 只读覆盖率实际核验：2026-11-07

## 范围、执行身份与权限

- 使用已连接的 `supabase_read_only_user`，仅执行 SELECT / EXPLAIN 和 `pg_catalog` 查询；未运行 DDL/DML、未关闭 RLS、未修改权限。
- `transaction_read_only=on`、`row_security=on`，但 `rolbypassrls=true`。故 **RLS 不构成此连接的行级可见范围限制**。本轮不读取聊天正文、用户标识、Story ID/Session ID/Request ID 原值；仅统计聚合。
- 数据来源：2026-11-06T00:00:00Z 至 2026-11-07T00:00:00Z 的 `public.chat_latency_metrics`，再按当日日志量选取最活跃的 12 个 Session，最多取各 Session 最近的 30 条已完成 Assistant 消息（历史跨度可越过该日）。
- **这不是 Owner Rights 已验证的 Story 白名单，也不是代表性随机抽样；任何这 12 个 Session 的数据不得直接进入训练。** 没有跨租户内容导出或样本级身份发布。

## 有界聚合实际结果

| 查询 | 统计 |
|---|---:|
| 时间窗日志事件 | 134,489 |
| 非空 request_id 日志 | 44,194 |
| 非空 relay_request_id 日志 | 0 |
| 不同 story_id（仅日志） | 875 |
| 不同 session_id（仅日志） | 4,105 |
| 抽样 Session（按日志量前 12） | 12 |
| 完成 Assistant 消息（每 Session 最多最近 30 条） | 360 |
| 完成消息涉及不同 Story ID | 12 |
| 360 条中在 11-06 UTC 创建 | 153 |
| 360 条 Assistant 的前一 turn 有 User 消息 | 360 |
| 前一 User 状态为 completed | 360 |
| 前一 User 的 Story ID 与 Assistant 一致 | 360 |
| 12 个 Session 都具有 request_id 日志 | 是 |

`360/360` 是交替消息结构证据，非全部历史时点完整性的证明。Session 级 request 日志存在不等于每条 Assistant 具有唯一 request / attempt / response 链。不同 Story ID 不等于独立 world component。`status='completed'` 不等于原生单次 Provider completion 或 AI 内容无后处理。

## SQL 查询策略

先通过 `EXPLAIN (FORMAT TEXT)` 确认：

- `chat_latency_metrics` 以 `idx_chat_latency_metrics_created` 做日期范围 Index Scan；
- `v2_chat_messages` 以 `uq_v2_msgs_session_turn` 做按 Session、Turn 的反向索引扫描，每 Session `LIMIT 30`；
- 使用在当日日志窗口内聚合后的前 12 个 Session 做受限 join，不做历史全表消息扫描；
- User 前一 Turn 使用同 Session/Turn 定位，只返回 COUNT 聚合。

所有结果均来自只读 SQL 返回，未独立对数据库版本/业务完整性做历史签核。

## 双轨后续准入

- `STRICT_GOLD_QUALITY_V1`：原 Gold192 冻结不变。必须具有 A/B 级实际输入 / 完整可核证重建证据，逐案权益、单次目标、世界隔离与训练曝光、完整 Protected Set 验证。
- `RECONSTRUCTED_CONTEXT_SFT_EXPERIMENTAL`：新候选池独立，不与 Strict Gold 或 R50 Held-out 混淆；必须先证明合法使用范围、目标可以合法监督、世界组件独立并且历史重建边界已完整披露。不得把数据库最终消息冒充真实发送请求。
- 本轮 360 条 `METADATA_ONLY_UNREVIEWED`，不冻结、不下载、不导出正文、不做 Quality-v1 admission。
- 首先对经 Owner 授权的作品/用户范围进行限定，再把本次已验证的 Session/Turn 索引策略应用于其候选。如果来源授权范围不清，保持 HOLD。
- 查询实际 Provider/response 关联前，应核查 RolePlay 消息 metadata / latency attempt 关联的字段语义；`request_id` 存在不等于可信 target mapping。

状态：`AGGREGATE_COVERAGE_PASS__CANDIDATE_ADMISSION_HOLD`。本轮 `strict_gold_admitted=0`、`experimental_admitted=0`、`training_authorized=false`、`gpu_started=false`、`database_modified=false`、`r50_accessed=false`。

注意：Owner 在后续轮次明确授权 `supabase_read_only_user` 执行不涉及修改、权限变更或关闭 RLS 的查询；此前本机工具对 `r58_export_reader` 的强制角色限制属于较早设计，当前连接不可据此直接运行那个工具。对跨所有者业务行数据，仍必须用明确合法的作品范围，而不能依赖 BYPASSRLS 带来的全表访问。
