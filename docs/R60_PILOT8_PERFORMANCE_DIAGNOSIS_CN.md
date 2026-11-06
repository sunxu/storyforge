# R60 Pilot8 性能诊断与下一步

日期：2026-11-05  
分支：`r60/gold192-ledger-diagnostics`  
范围：只读性能诊断；未修改 Supabase schema、数据、索引或策略。

## 1. Pilot8 结果

- 请求 8 条；恢复 5 条；HOLD 3 条。
- 3 条 HOLD 原因均为 `HISTORY_SUFFIX_NOT_USER`。
- 4 个候选 Session；4 个恢复 Story。
- 历史消息总数 9,599。
- 整体恢复 wall time 436,740.936 ms。
- SQL execute wall time 435,964.018 ms；fetch wall time 303.250 ms。
- SQL 111 次；返回 659,707 行。
- GPU 未启动、数据库未修改、私有正文未输出、Quality-v1 admitted 为 0。

逐案 HOLD 隔离有效；当前结果不是训练准入。

## 2. 主要耗时

| Query class | 次数 | execute_ms | rows_fetched |
|---|---:|---:|---:|
| LEDGER_METADATA_QUERY | 66 | 328,185.424 | 641,051 |
| LEDGER_DETAIL_QUERY | 16 | 83,135.125 | 6,854 |
| CURRENT_HISTORY_QUERY | 8 | 21,299.892 | 11,708 |
| TARGET_MESSAGE_QUERY | 5 | 1,826.918 | 74 |
| SESSION_LINEAGE_QUERY | 5 | 474.010 | 6 |
| STORY_VERSION_QUERY | 5 | 475.680 | 1 |
| ADMIN_VERSION_QUERY | 5 | 466.161 | 0 |
| OWNER_SCOPE_QUERY | 1 | 100.809 | 13 |

`cursor.execute` 的计时是客户端调用 wall time，包含数据库执行与往返等待；不是 PostgreSQL 内部 CPU 时间。Fetch 计时很短，不能据此断言数据库端没有 I/O 成本。

## 3. SAFE 计数口径澄清

旧字段：

- `ledger_events_read_total`
- `ledger_detail_rows_loaded_total`

是把每条 recovered Case 的 reconstruction 计数相加。同一 Session 的多个 target 会重复归因同一份已加载事件，因此它们不是唯一 SQL 返回行数。

新增明确字段：

- `ledger_events_attributed_to_recovered_cases_total`
- `ledger_detail_rows_attributed_to_recovered_cases_total`
- `ledger_metadata_rows_fetched_total`
- `ledger_detail_rows_fetched_total`

后两项来自 SQL profiler 的实际 fetch 行数。保留旧字段以兼容既有消费者。

## 4. 数据库结构观察

只读查询观察到：

- `v2_chat_message_ledger` 总大小约 102 GB，heap 约 17 GB，索引约 9.5 GB。
- 估计 live tuples 约 43.1M，dead tuples 约 1.08M。
- 当前索引包含 `(session_id, recorded_at, id)`，但没有把恢复查询需要的 `story_id`、`turn_index`、`message_id`、`role`、`operation` 一并覆盖。
- ledger 最近一次 autoanalyze 记录为 2026-10-12，最近一次 autovacuum 记录为 2026-10-07。

对脱敏的占位参数执行了非 ANALYZE 的 EXPLAIN。计划选择 `idx_v2_chat_message_ledger_session`：

- Index Cond：`session_id`；分页时也包含 `(recorded_at, id)` keyset 条件。
- Filter：`turn_index` 范围和 `story_id`。
- 这说明这两个过滤条件没有成为该计划的 index condition。占位参数计划只用于确认访问路径结构，不代表实际 Pilot8 参数的选择性或耗时。

## 5. 下一步优化建议

### P0：先保留基线

Pilot8 SAFE 与私有 artifact SHA256 已记录。不要改写本轮结果，也不要把 3 条 HOLD 变成自动通过。

### P1：确认实际执行计划

由 Owner 在本机私有 DSN 环境下，对一条代表性 Session 的第一页和 keyset 后续页分别运行普通 `EXPLAIN (FORMAT JSON)`，不运行 `EXPLAIN ANALYZE`。只回传脱敏后的 Plan 节点、Index Cond、Filter、估算 rows 和是否 Index Only Scan；不回传 SQL 参数、Session ID 或消息 ID。

普通 EXPLAIN 不执行查询。暂不对 102 GB Ledger 运行全量 ANALYZE，也不做长时间 BUFFERS/ANALYZE 探测。

### P2：评估 covering index，而不是直接创建

候选方向是在现有 session / recorded_at / id 顺序上覆盖恢复元数据字段，以减少 heap fetch，并争取 Index Only Scan。示意设计（仅讨论，不执行）：

`(session_id, recorded_at, id) INCLUDE (story_id, turn_index, message_id, role, operation)`

创建前必须检查：

- 实际计划与 visibility map 状态；
- 额外索引体积和写入放大；
- 是否与现有索引重复；
- Supabase 磁盘空间和写入负载；
- `CREATE INDEX CONCURRENTLY` 的运行窗口与回滚方案。

此处不是 DDL 授权。本分支不创建 migration，不运行 CREATE/DROP/REINDEX/ANALYZE。

### P3：单独评估 Detail batch

Detail 查询 16 次、返回 6,854 行、execute wall time 83.1 秒。现有每批 500 IDs。可以在合成测试上比较 500 / 1,000 / 2,000 的查询数、峰值内存和总耗时；通过后再用小型只读 Pilot 验证。不要直接扩大到 2,000，避免一次传输过大的 JSONB before-image。

### P4：Current history query

8 次查询返回 11,708 行、耗时 21.3 秒。先检查实际计划是否使用合适的 session/turn 索引，再考虑投影或范围查询优化；不可削弱 `story_id`、`session_id`、`turn_index`、`created_at < target_time` 等边界。

## 6. 暂不进行

- 不扩大到 72 条或 192 条。
- 不启用 Session 并发。
- 不修改 Ledger 顺序语义。
- 不放宽 `HISTORY_SUFFIX_NOT_USER`。
- 不改变历史 System Prompt、Summary、Story Version 的证据门槛。
- 不修改数据库 schema、索引、trigger、grant、RLS policy。
- 不启动 GPU 或训练。

## 7. 当前安全状态

`quality_v1_admitted=0`  
`training_authorized=false`  
`gpu_started=false`  
`database_modified=false`  
`ledger_commit_order_verified=false`  
`ledger_trigger_continuity_verified=false`
