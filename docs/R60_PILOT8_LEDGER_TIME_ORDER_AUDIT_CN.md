# R60 Pilot8 Ledger 时间顺序与历史恢复审计

日期：2026-11-05  
范围：Pilot8 SAFE 汇总、Supabase 只读 catalog / trigger / function 定义核验  
性质：只读审计；不修改数据库、不读取或输出聊天正文、不改变训练准入。

## 1. Pilot8 历史恢复诊断

本轮 SAFE 输出：

| Pilot safe index | 当前历史消息数 | 目标后首个事件分布 | 目标前快照数 | 机械恢复结果 |
|---:|---:|---|---:|---|
| 0 | 27 | update_after 27 | 0 | HOLD |
| 1 | 539 | update_after 1,557 | 1,557 | RECOVERED，时间顺序待认证 |
| 2 | 28 | update_after 28 | 0 | HOLD |
| 3 | 2,560 | update_before 2,560 | 2,560 | RECOVERED，提交顺序待认证 |
| 4 | 259 | update_before 259 | 259 | RECOVERED，提交顺序待认证 |
| 5 | 2,278 | update_before 2,278 | 2,278 | RECOVERED，提交顺序待认证 |
| 6 | 391 | update_after 391 | 0 | HOLD |
| 7 | 3,963 | 无 | 0 | RECOVERED，提交顺序待认证 |

`RECOVERED` 表示现有恢复算法完成机械重建，不代表历史事务提交顺序已经认证，更不代表 Reviewer、Owner 或 Quality-v1 准入。

## 2. Pilot 0、2、6 的有限窗口判断

这三个样本的当前历史消息均有目标之后的 `update_after`，且没有目标前快照。因此当前表中的消息正文无法证明是目标时点版本。

不得直接截取这些当前消息作为有限历史窗口。只有从另一个独立历史来源取得目标前、身份与顺序可验证、连续且无缺口的窗口，才可重新评估。若没有这样的来源，保持 HOLD / 排除。

## 3. Supabase 只读结构核验

已确认：

- `v2_chat_messages` 上启用的 `trg_capture_v2_chat_message_ledger` 为 `AFTER INSERT OR DELETE OR UPDATE`。
- 该触发函数对具有业务内容的 UPDATE，在同一触发器执行中插入 `update_before` 完整 OLD 行快照和 `update_after` 稀疏标记。
- `v2_chat_message_ledger.recorded_at` 默认值为 `now()`。
- `id` 使用 sequence 默认值。
- 当前数据库 `track_commit_timestamp=off`，隔离级别为 `read committed`，默认事务只读设置为 `on`。

PostgreSQL `now()` 表示事务开始时间，并非提交时间。Sequence ID 是分配顺序，不是跨事务提交顺序。若事件与目标边界具有相同 `recorded_at`，单凭 `(recorded_at,id)` 无法普遍证明不同事务之间的提交先后。

特别是 Pilot safe index 1 的 1,557 条快照与目标边界时间戳相同；在没有额外事务证据前，不得把它们升级为已认证的目标前快照。

## 4. Writer-path 锁审计的当前范围

已检查到若干常见写入函数持有 session 行锁，例如：

- `edit_v2_message_with_volume_backfill`
- `mutate_v2_session_messages_atomic`
- `import_v2_session_messages_atomic`
- `bind_v2_message_attempt_operation_checked`

但不能由此推断所有可能影响消息版本的写入路径都使用相同锁策略。`bind_v2_legacy_retry_source` 函数主体未显示显式 session `FOR UPDATE`，其调用的 source-validation helper 尚未完成锁语义审计。

`cancel_v2_chat_reply_job` 和 stale-stream reconciliation 会更新消息状态字段；已检查的 Ledger 捕获触发器业务变更判断不包含 status 单字段变化。该点应与内容/元数据变更分开记录，不能混为同一种 Ledger 版本事件。

## 5. 当前认证结论

当前代码 SAFE 已将以下两项明确标记为 false：

- `ledger_commit_order_verified=false`
- `ledger_trigger_continuity_verified=false`

因此本轮 Pilot8 的机械恢复结果尚不能作为完整的历史时间语义认证。

后续需要：

1. 审计全部相关写入路径及其锁范围，包括调用的 helper。
2. 证明目标边界与每个相关 Ledger 事件的先后关系；不能把事务开始时间或 sequence ID 单独当作提交顺序。
3. 对同时间戳但缺乏事务证明的事件保持 HOLD。
4. 对 Pilot 0、2、6 仅从独立来源寻找可信连续窗口；不得从当前未验证版本拼接窗口。
5. 时间顺序认证通过后，再扩大到 72 条优先样本及 Gold192 逐案认证。

## 6. 安全状态

- `quality_v1_admitted=0`
- `training_authorized=false`
- `gpu_started=false`
- `database_modified=false`
- 无训练、无推理、无 GPU Job。
- 原始 Gold192、Reviewer A/B、V3、Stage72 均未修改。
