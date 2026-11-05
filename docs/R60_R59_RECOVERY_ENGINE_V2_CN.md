# R60 / R59 Historical Recovery Engine v2

日期：2026-11-05  
分支：`r60/gold192-ledger-diagnostics`  
性质：只读历史证据恢复与性能观测；不做 Quality-v1 admission。

## 1. 本轮输入状态

若运行返回：

`GOLD192_HISTORICAL_CONTEXT_HOLD / HISTORY_SUFFIX_NOT_USER`

它只说明对应样本的重建历史未满足“最后一条有效历史消息必须是 user”的硬门槛。不能把当前消息强行作为目标时点历史，也不应因此丢弃其他独立样本。

## 2. v2 改动

### 2.1 按 Session 批量读取目标消息

`recover_cases` 与独立恢复路径按 `(story_id, session_id)` 分组，以一次 `turn_index = ANY(...)` 查询读取该 Session 的多个目标消息，再逐条核对：

- 每个 turn 必须恰好对应一条 Assistant 消息；
- 目标 SHA256 必须精确匹配；
- status 必须为 completed；
- story/session/turn locator 必须一致。

身份失败只 HOLD 对应 Case，不影响同 Session 其他已匹配目标。

### 2.2 Session lineage 缓存

单次只读事务内共享 session node 与 lineage chain 缓存。相同 Session 链不重复查询；缓存只作用于本次调用，不跨数据库事务或运行复用。

### 2.3 Story version 缓存

相同 `(story_id, target_time)` 的版本查询结果在单次调用内复用。不同目标时间仍独立执行时间边界判断。

### 2.4 逐案 HOLD 隔离

`recover_cases_independently` 返回两组结果：

- recovered：通过历史重建硬门槛的私有恢复记录；
- holds：内部逐案原因，SAFE 只输出原因分布，不输出 Case ID、消息 ID、Session ID 或正文。

单条 Case 的 `HISTORY_SUFFIX_NOT_USER`、目标身份不唯一或 Ledger 证据不足，不会中止其他 Case。数据库连接/SQL 执行异常仍作为批次级故障终止，避免把基础设施错误误记成样本质量 HOLD。

SAFE 增加：

- `pilot_recovered`
- `pilot_held`
- `case_hold_reason_counts`
- `performance_metrics.query_classes`

输出状态为 `GOLD192_HISTORICAL_CONTEXT_PARTIAL__NOT_ADMITTED` 或 `GOLD192_HISTORICAL_CONTEXT_RECOVERED__NOT_ADMITTED`。这些状态均不代表训练准入。

## 3. 性能指标

`RecoveryStageCursor` 仅按预定义 SQL 阶段聚合：

- query_count
- execute_ms
- fetch_count
- fetch_ms
- rows_fetched

不保留 SQL 文本或参数。SAFE 汇总总查询数、总 execute/fetch 时间和总读取行数。

这可区分 SQL 执行/网络等待与结果传输，但不是数据库服务器内部 CPU 计时。需要更细的 DB 计划成本时，应另行执行受控只读 EXPLAIN，不在主恢复路径自动启用 EXPLAIN ANALYZE。

## 4. 当前不做的优化

- 不并发拆分同一 Session 的 Ledger 分页。
- 不为不同 Worker 开启独立快照后假定结果一致。
- 不改变 `(recorded_at, id)` 的现有算法，也不把它提升为提交顺序证明。
- 不修改索引、trigger、table、grant、policy。
- 不改变历史恢复规则或训练准入条件。

后续如评估 Session 级并发，必须先证明所有 Worker 共享同一个 PostgreSQL 数据库快照，并对串行/并发结果做确定性一致性比较。

## 5. 安全与准入

本次变更不授权训练。所有输出必须继续保持：

- `quality_v1_admitted=0`
- `training_authorized=false`
- `gpu_started=false`
- `database_modified=false`
- `private_values_emitted=false`
- `ledger_commit_order_verified=false`
- `ledger_trigger_continuity_verified=false`

RECOVERED 仅表示现有机械重建完成；Reviewer 决定、Owner 审批、历史时序认证、Quality-v1 准入是彼此独立的门槛。


### 2.5 LedgerEventIndex：每个 Session 只建立一次事件索引

对同一 Session 的多目标恢复，原逻辑会在每个 Case 重复：

- 遍历 Ledger 事件；
- 按 message_id 分组；
- 对各消息事件排序；
- 查找目标边界之后的首个相关事件。

现在 `LedgerEventIndex` 在每个 Session 的 Ledger 元数据读取后建立一次，缓存 message_id 分组、排序后的事件和排序键。每个目标使用二分定位目标边界之后的位置，再按 turn cutoff 选择首个有效事件。

`_required_event_ids` 与 `reconstruct_history` 复用同一索引；恢复主路径不会为每个 Case 重新分组和排序完整 Ledger。索引只在单次恢复事务/调用内使用，不跨运行持久化。

该优化只改变重复计算方式，不改变 `recorded_at, id` 的比较规则，也不证明跨事务提交顺序。
