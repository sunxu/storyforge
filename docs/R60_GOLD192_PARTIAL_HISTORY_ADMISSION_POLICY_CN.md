# R60 Gold192 部分历史恢复与逐案准入原则

## 决策

Owner 已确认：Gold192 不要求 192 条全部恢复，也不要求 192 条全部通过。目标是从冻结的 192 条候选中，逐案筛选出证据充分、质量合格的训练样本；不设置最低准入数量，不为达到数量目标降低证据标准。

本原则只调整恢复策略和工作排序，不自动改变任何样本的审核决定、Owner 审批或训练准入状态。

## 样本级结果分类

每条样本独立处理，不因其他样本 HOLD 而阻塞。

| 分类 | 含义 | 后续处理 |
|---|---|---|
| `FULL_HISTORY_RECOVERED` | 目标前可用历史按既有恢复规则完整重建，身份、顺序、时间边界和尾部均通过 | 进入后续证据与质量审核 |
| `VERIFIED_WINDOW_RECOVERED` | 完整 Session 历史不可用或不必要，但选定的连续目标前窗口中每条消息均有可验证的历史版本、身份、顺序和时间边界 | 标记截断窗口及长度，进入后续证据与质量审核 |
| `HOLD` | 目标身份、窗口连续性、消息历史版本、时间边界或必要证据无法证明 | 不进入训练候选；保留原因码 |
| `REJECT` | 已有明确审核拒绝证据 | 排除，不因恢复成功而翻转 |

以上是准入策略分类。实现代码、SAFE schema 和测试完成前，不得把尚未实现的 `VERIFIED_WINDOW_RECOVERED` 当作已支持的运行结果。

## 硬性证据门槛

无论完整历史还是有限窗口，进入后续 Quality-v1 审核前都必须满足：

1. **目标身份**：目标 Assistant 消息与冻结候选的精确身份及目标 SHA256 唯一匹配。
2. **目标边界**：所有训练输入消息严格早于目标消息；不得包含目标消息或任何目标之后的信息。
3. **消息身份与顺序**：窗口内每条消息的来源身份、角色、turn 和排序均可验证；不得重复、拼接或跳过窗口内部的缺失消息。
4. **历史版本**：窗口内消息必须是目标时点的版本。若目标之后发生更新，只有存在并通过校验的目标前快照，才可使用该消息的历史正文和字段。
5. **连续窗口**：有限窗口必须是目标前已验证消息的连续尾部窗口。不能跳过无法恢复的消息，再把更早与更晚的消息拼成连续上下文。
6. **对话边界**：窗口末尾必须满足既定对话边界规则（当前要求最后一条历史消息为 User）。
7. **上下文来源声明**：窗口截断必须明确记录窗口长度、截断状态和可验证的起点；不得把当前故事卡、当前 Session 摘要或推测内容冒充目标时点历史。

若上述任何一项无法证明，该样本保持 HOLD。有限窗口不是绕过 Ledger 快照缺失、事件顺序歧义或历史正文不可信的豁免。

## Ledger 事件的处理边界

- `update_before` 和 `delete` 属于可用于恢复历史的快照事件，但仍须逐字段验证其身份、时间、角色、正文、状态及适用的版本字段。
- `insert` 和 `update_after` 是事件标记，不包含可替代旧正文的历史快照。
- 若消息在目标之后有 `update_after`，但不存在目标边界之前可验证的快照，则不能使用当前消息正文声称恢复了目标时点内容。
- 只有当排除不可信消息后，仍能从其他已验证消息构成满足规则的连续尾部窗口，才可能评估有限窗口恢复。
- 若目标前尾部窗口本身受影响或存在缺口，不得跳过受影响消息继续拼接；应 HOLD。

## 各类 PASS 不得合并

SAFE 与审核记录必须分别表达以下状态：

1. Source / target 身份匹配；
2. 历史证据完整性（完整历史或有限窗口）；
3. Reviewer 审核决定；
4. 人工 Owner 审批；
5. Quality-v1 训练准入；
6. 训练授权与 GPU 执行状态。

身份匹配、历史恢复成功、AI Arbitration PASS 或 Reviewer PASS，均不自动等于 Owner 批准或 Quality-v1 准入。AI Arbitration 的 `human_owner_approval=false` 仍然是未获 Owner 批准。

## 工作顺序

1. 完成 Pilot8 现有 HOLD 的 SAFE 诊断，确认目标后标记、前置快照覆盖和边界顺序；不因追求 8/8 而放宽规则。
2. 对 192 条冻结候选执行逐案历史证据分类；优先评估既有 72 条 Reviewer A/B 双审 PASS 候选，但不得把双审 PASS 直接当作准入。
3. 对完整历史不可用的样本，仅在上述连续窗口门槛可证明时评估有限窗口模式。
4. 汇总 FULL / WINDOW / HOLD / REJECT 数量及原因分布；不设最低通过数量。
5. 对可进入后续审核的样本继续完成世界隔离、质量评分、历史曝光、Owner 审批及其他既有 Quality-v1 检查。
6. 冻结最终 Train / Validation / Test 数据集并完成 CPU Token、Collator、隔离和复现性验证。
7. 只有在用户明确授权后才启动 GPU 训练。

## 当前状态与安全约束

本策略文件不代表任何新增样本已获准入。当前已知状态继续保持：

- `quality_v1_admitted=0`
- `training_authorized=false`
- `gpu_started=false`
- `database_modified=false`
- 不修改冻结 Gold192、Reviewer A/B、V3、Stage72 原始证据。
- 不启动 GPU、不训练、不推理。
- 不因本策略变更生成派生训练候选。

后续每次执行只依据 SAFE 输出更新样本级状态；私人正文、Case ID、消息 ID、故事名及自由文本审核备注不得输出到聊天或公开 CI 日志。


## Pilot8 SAFE 诊断补充（2026-11-05）

本轮 `r59_history_suffix_recovery_diagnostic_safe_v1` 的 SAFE 输出显示：

| Pilot safe index | 当前历史消息数 | 目标后首个事件分布 | 目标前快照数 | 诊断结果 |
|---:|---:|---|---:|---|
| 0 | 27 | update_after 27 | 0 | HOLD |
| 1 | 539 | update_after 1,557 | 1,557 | RECOVERED（时间顺序待认证） |
| 2 | 28 | update_after 28 | 0 | HOLD |
| 3 | 2,560 | update_before 2,560 | 2,560 | RECOVERED（提交顺序仍待认证） |
| 4 | 259 | update_before 259 | 259 | RECOVERED（提交顺序仍待认证） |
| 5 | 2,278 | update_before 2,278 | 2,278 | RECOVERED（提交顺序仍待认证） |
| 6 | 391 | update_after 391 | 0 | HOLD |
| 7 | 3,963 | 无 | 0 | RECOVERED（提交顺序仍待认证） |

### 三条 HOLD 的处理

Pilot safe index 0、2、6 的当前历史消息全部对应目标之后的 `update_after`，且没有目标前快照。当前消息正文不能代表目标时点版本。不得直接使用这些当前消息构造有限窗口；只有另一个独立、可验证的历史来源能提供目标前连续窗口时，才可重新评估。否则保持 HOLD / 排除。

### 额外的 Ledger 时间语义审计

只读数据库核验确认：

- `v2_chat_messages` 上存在已启用的 `AFTER INSERT OR DELETE OR UPDATE` 触发器 `trg_capture_v2_chat_message_ledger`。
- 业务 UPDATE 在旧行存在业务内容时，会在同一触发器执行中写入 `update_before` 完整旧行快照和 `update_after` 稀疏标记。
- Ledger 的 `recorded_at` 默认值为 `now()`。
- 当前数据库 `track_commit_timestamp=off`。

PostgreSQL 的 `now()` 是事务开始时间，不是提交时间；Ledger 的序列 ID 也不是跨事务提交顺序证明。因此，仅凭 `(recorded_at, id)` 排序，不能普遍证明不同事务之间的提交先后。Pilot safe index 1 的 1,557 条快照与目标边界时间戳相同，尤其需要谨慎处理。

当前代码的历史上下文 SAFE 也明确记录 `ledger_commit_order_verified=false` 和 `ledger_trigger_continuity_verified=false`。因此本轮的 `RECOVERED` 仅表示按现有算法完成了机械重建，不等于历史提交顺序认证，也不等于 Quality-v1 训练准入。

### 下一步认证门槛

1. 为目标边界与相关 Ledger 事件建立可验证的事务/提交顺序证据；当前数据库未启用 commit timestamp，不能假设可从该设置直接取证。
2. 在无法证明跨事务顺序时，将受影响的样本保持 HOLD，而不是把序列 ID 当作提交顺序。
3. 对 Pilot 0、2、6，只从独立历史来源寻找目标前连续窗口；若没有则排除。
4. 只有完成历史时间语义认证后，才扩大到 72 条优先样本及 Gold192 逐案审核。

本补充不改变任何原始审核结果或训练准入。当前 `quality_v1_admitted=0`、`training_authorized=false`、`gpu_started=false`、`database_modified=false`。
