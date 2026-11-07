# R60 T1：RolePlay V2 消息写入路径与调用链清单（首轮静态审计）

日期：2026-11-07  
性质：只读 GitHub 源码审计；不连接生产数据库、不运行消息写入、不使用 R50、不改变训练准入。

## 审计对象、基线、范围和严格限制

- 历史消费方：`sunxu/storyforge`，分支 `r60/gold192-history-v3-adapter`。
- 消息生产方：`sunxu/RolePlay`，`main` SHA `e9fe29c42434caeb0bac5acc91845ab4741ecb2b`（本报告所检源码基线）。
- 被审计的生产数据表：`public.v2_chat_messages`、`public.v2_chat_message_ledger`；关联 `public.story_v2_sessions`。
- StoryForge 的 `src/storyforge_gold_quality/message_ledger.py`、`history_recovery.py` 和 R59/R60 Source Extract 代码是只读历史消费者；不应与 RolePlay 的生产写路径混淆。
- **本报告是 T1 第一批确证路径，不是 T1 已完成、全仓库写入入口无遗漏或生产部署状态已核实的证据。**
- 只核实选定 GitHub 源码与既有 StoryForge SAFE/审计。**尚未对 RolePlay 全仓所有 TS/SQL 文件进行逐文件匹配；未对生产 `pg_proc`、`pg_trigger`、权限、实际 RPC 调用频次进行只读交叉比对。**
- `ledger_commit_order_verified=false`、`ledger_trigger_continuity_verified=false`；`quality_v1_admitted=0`、`training_authorized=false`、`gpu_started=false`。

## A. 源码已确证的写入路径（不是唯一调用者清单）

| 编号 | 入口/调用链 | 业务表变更 | 源码证据 | Session 锁与结论 |
|---|---|---|---|---|
| W01 | `POST /api/chat/v2` → `V2MessageService.saveMessage` → Supabase `.insert` | User、非流式 Assistant INSERT | [route](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/app/api/chat/v2/route.ts#L3683-L3717)、[service](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/lib/db/v2-message-service.ts#L361-L390) | 直接 INSERT；未在此单条事务中显式锁 Session。上游 claim 与该请求不是同一数据库事务；须继续证明对事件时间顺序的影响。 |
| W02 | `POST /api/chat/v2` → `V2MessageService.insertStreamingAssistantStub` → `prepare_v2_streaming_assistant_stub` RPC | Assistant streaming INSERT 或失败占位复用 UPDATE | [service](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/lib/db/v2-message-service.ts#L1405-L1444)、[RPC](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/supabase/migrations/20261012201000_v2_streaming_stub_session_lock.sql#L5-L41) | RPC 先 `story_v2_sessions FOR UPDATE NOWAIT`，再操作消息；已看到显式 Session 锁。 |
| W03 | `POST /api/chat/v2` → `V2MessageService.updateStreamingPartial` | `partial_content` UPDATE | [service](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/lib/db/v2-message-service.ts#L1446-L1468) | 直接 UPDATE；通常不属于 Ledger 业务语义变化，但对 Streaming 并发状态必须单独认证。 |
| W04 | `POST /api/chat/v2` → `V2MessageService.finalizeStreamingAssistant` | `content/metadata/status/partial_content` UPDATE | [service](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/lib/db/v2-message-service.ts#L1471-L1558) | 直接 UPDATE；本事务未显式先锁 Session；重要正文更新，必须验证先后顺序和 Trigger 连续性。 |
| W05 | Streaming 异常/取消、历史 GET 读时修复 → `markStreamingFailed` / `markSessionStreamingFailed` / `markStaleStreamingFailed` | `status/failure_code` UPDATE | [service](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/lib/db/v2-message-service.ts#L1564-L1641)、[history route](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/app/api/chat/v2/messages/route.ts#L125-L172) | 直接 UPDATE；稀疏 Ledger 一般忽略 status-only；需要明确目标时点可见性证明。 |
| W06 | `PATCH /api/chat/v2/messages` → `updateContentByTurnIndex` → `edit_v2_message_checked` / `edit_v2_message_with_volume_backfill` | `content/metadata` UPDATE | [route](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/app/api/chat/v2/messages/route.ts#L400-L455)、[service](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/lib/db/v2-message-service.ts#L775-L955)、[checked RPC](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/supabase/migrations/20261008150000_v2_checked_message_mutation.sql#L363-L403) | Checked RPC 已看到 Session 行锁；需核查 legacy edit helper 的完整函数定义。 |
| W07 | `DELETE /api/chat/v2/messages` → `deleteCheckedAction` / `mutateSessionMessagesAtomic` → `mutate_v2_session_messages_checked` / `mutate_v2_session_messages_atomic` | DELETE、UPDATE 轮次压缩 | [route](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/app/api/chat/v2/messages/route.ts#L455-L525)、[service](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/lib/db/v2-message-service.ts#L960-L1075)、[checked RPC](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/supabase/migrations/20261008150000_v2_checked_message_mutation.sql#L63-L287)、[atomic RPC](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/supabase/migrations/20261006120000_v2_legacy_orphan_delete_guard.sql) | 部分 RPC 明确先锁 Session；需要对后续 helper / 所有 active overload 逐条核查。 |
| W08 | `POST /api/chat/v2/messages` → `saveBatchMessages` → `import_v2_session_messages_atomic` | 历史批量 INSERT | [route](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/app/api/chat/v2/messages/route.ts#L275-L287)、[service](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/lib/db/v2-message-service.ts#L390-L455)、[RPC](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/supabase/migrations/20260830170000_v2_message_import_session_recovery.sql) | RPC 使用 Session 首锁设计；需确认生产实际采用的函数版本。 |
| W09 | Session restart / hard-delete / purge cron → `hardDeleteSave` → `deleteAllBySessionWithDiagnostics` → Supabase `.delete` | 整 Session 消息 DELETE | [cron](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/app/api/cron/purge-deleted-v2-sessions/route.ts#L70-L88)、[hardDeleteSave](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/lib/db/story-v2-saves.ts#L599-L735)、[message service](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/lib/db/v2-message-service.ts#L1080-L1160) | 多张表并行分批删除；非同一数据库事务，当前消息 DELETE 直接提交，需核查与 Session 锁、异地归档和其他写入的交错。 |
| W10 | Session fork → `execute_v2_chat_fork` RPC | 新 Session 的消息批量 INSERT | [RPC 最新检到的定义](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/supabase/migrations/20261003110000_v2_write_cost_optimization.sql#L11-L150) | 跨 Session 复制，须验证源 Session、目标 Session 的事务锁和 lineage、目标时点。 |
| W11 | 旧重试绑定 → `bind_v2_legacy_retry_source` → `validate_v2_message_action_sources` | User `client_msg_id/status/metadata` UPDATE | [RPC](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/supabase/migrations/20261008150000_v2_checked_message_mutation.sql#L410-L458) | 调用的 validate helper 已看到 Session `FOR UPDATE NOWAIT`；**函数本体没有重复显式加锁不等于无锁**，需在 T2 核证 helper 锁至同事务结束。 |
| W12 | 重试操作绑定 → `bind_v2_message_attempt_operation_checked` | User `metadata` UPDATE | [RPC](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/supabase/migrations/20261012200000_v2_attempt_bind_result.sql#L4-L49) | 已看到 Session `FOR UPDATE NOWAIT`，随后锁目标 User 行。 |
| W13 | 事件 Engine 完成 → `commit_v2_event_turn_claim` | Assistant `metadata` UPDATE | [RPC](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/supabase/migrations/20260908152000_v2_event_turn_claim_expand.sql#L333-L445) | 已看到 Session `FOR UPDATE` 后更新 Assistant；需核查与最终回复入库的跨事务先后。 |
| W14 | Durable Reply Job 接受/重试 → `accept_v2_chat_reply_job` | User/Assistant INSERT、失败回复 UPDATE | [RPC](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/supabase/migrations/20260820213000_v2_durable_reply_jobs.sql#L51-L177) | 已检定义没有显式 Session `FOR UPDATE`（有 Session 查询和消息行锁）；需核实是否仍为生产可达路径及其他包装锁。 |
| W15 | Durable Reply Job 取消 → `cancel_v2_chat_reply_job` | Assistant `status/failure_code` UPDATE | [RPC](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/supabase/migrations/20260820213000_v2_durable_reply_jobs.sql#L283-L314) | 已检定义没有显式 Session 首锁；status-only 与 Ledger 业务快照要分别处理。 |
| W16 | pg_cron → `reconcile_stale_v2_streaming_messages` | Assistant `status/failure_code` UPDATE | [RPC](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/supabase/migrations/20260827130000_v2_stale_streaming_reconciler.sql#L7-L162) | 候选消息 `FOR UPDATE SKIP LOCKED`，已检函数不先锁 Session；需确认生产启用及状态转换影响。 |

以上是**16 类确证或代码定义可达的候选写路径**，不是 16 个唯一物理 SQL 语句，也不表示 16 条都已在生产执行。应用调用已明确的以应用证据标注，只有 SQL 定义证据的需进一步检索 TS/Worker 调用者。

## B. Trigger 链、写入保护及版本边界

- [20260727d_v2_chat_message_ledger.sql](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/supabase/migrations/20260727d_v2_chat_message_ledger.sql)：`AFTER INSERT OR UPDATE OR DELETE ON v2_chat_messages`；早期完整快照，`recorded_at DEFAULT now()`，`id BIGSERIAL`。
- [20260908132000_v2_chat_ledger_sparse_markers.sql](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/supabase/migrations/20260908132000_v2_chat_ledger_sparse_markers.sql)：后续重定义为稀疏 Ledger；`update_before`、`delete` 保存 OLD 全快照，`insert`、`update_after` 为 marker；`status`、`partial_content` 单独变更不视为业务修改。注意部分 Streaming status-only 事件并不入账。
- [20261008150000_v2_checked_message_mutation.sql](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/supabase/migrations/20261008150000_v2_checked_message_mutation.sql)：`BEFORE INSERT OR UPDATE` 维护 `mutation_revision`，还有 history-provenance trigger。不能只验证主 Ledger Trigger 而忽略其他 Trigger 顺序/作用。
- 只有 *源码* 证据，不能证明生产 Trigger 未被 disable、所有函数已按 migration 生效、RLS/ACL 正常。T3/T5 还必须从生产 `pg_catalog` 做独立只读核证。

## C. 具体调用链（静态核对）

```text
/api/chat/v2 POST
 ├─ turn claim / event claim RPC（与后续消息写入可能是不同事务）
 ├─ saveMessage → direct INSERT User
 ├─ insertStreamingAssistantStub → prepare_v2_streaming_assistant_stub RPC
 ├─ updateStreamingPartial → direct UPDATE partial_content
 ├─ finalizeStreamingAssistant → direct UPDATE content/metadata/status
 ├─ persistTurnMessages → saveMessage → direct INSERT Assistant（非 streaming）
 ├─ failure/cancel → markStreamingFailed / markSessionStreamingFailed
 └─ event claim commit → commit_v2_event_turn_claim RPC → metadata UPDATE

/api/chat/v2/messages POST → saveBatchMessages → import_v2_session_messages_atomic RPC
/api/chat/v2/messages PATCH → updateContentByTurnIndex → checked/legacy edit RPC
/api/chat/v2/messages DELETE → deleteCheckedAction / deleteByTurnIndices / deleteFromTurnIndex
                              → checked/atomic mutation RPC → DELETE / compact UPDATE
/api/chat/v2/messages GET → stale read projection → markStaleStreamingFailed → direct UPDATE
/api/chat/v2/saves or legacy sessions restart / cron purge
                         → hardDeleteSave → deleteAllBySessionWithDiagnostics → direct DELETE
/api/chat/v2/sessions/[sessionId]/fork → execute_v2_chat_fork RPC → INSERT copied messages
DB pg_cron → reconcile_stale_v2_streaming_messages → status-only UPDATE
Legacy retry → bind_v2_legacy_retry_source → validate_v2_message_action_sources → UPDATE
Durable worker/job RPCs → accept_v2_chat_reply_job / cancel_v2_chat_reply_job → INSERT/UPDATE
```

## D. T1 尚未完成的必须核证项目

1. **全仓扫描**：覆盖 RolePlay `src/`、`apps/`、`packages/`、`scripts/`、所有 `supabase/migrations/` 中的实际写入（含函数内动态 SQL、未以 `v2_` 命名的 RPC 和单独维护任务）；当前仅部分代表路径完成静态核对。
2. **应用调用者**：为 W10/W11/W13/W14/W15/W16 确认现行 Web、移动端、Worker、cron 的实际调用；区分已定义 / 已引用 / 可达 / 实际部署 / 已启用。
3. **覆盖与覆写**：历史 migration 的 `CREATE OR REPLACE FUNCTION` 不保证生产采用该版本。必须只读检查当前生产 `pg_get_functiondef`、`pg_get_triggerdef`、`pg_proc`、`pg_class`、`pg_roles`、`pg_policies`。
4. **间接写入**：检查 Session/Fork/保存/回退/历史重放 RPC 中的触发器、CASCADE、嵌套函数、后台队列和 cron。
5. **触发器状态**：除 Ledger 外，核对 mutation revision、history provenance、Session event runtime、memory invalidation 的触发顺序与递归写入。
6. **批量清理与归档**：`hardDeleteSave` 跨表多事务、delete-all archive 是辅助路径且允许失败。必须确认与 Ledger 事务原子性/保留策略的区别。
7. **数据边界**：StoryForge 恢复不仅依赖消息顺序，还依赖 Story/Card/System Prompt 的历史版本。此项属于后续独立 T6/T7，不得在 T1 默认已解决。

## E. T1 → T2 的下一步

- 先完成全仓精确扫描，再给每个 Writer Path 分配唯一 `writer_path_id`、调用者、RPC、触发器、所属功能和可达性等级；无证据时标记 `UNVERIFIED`。
- 对每条 Writer Path 核验 `session-row lock first`、锁顺序、是否在同一 SQL 事务中提交及其是否存在跨事务请求链。
- 特别优先核对：W01 直接 INSERT、W04 Finalize、W05/W15/W16 status-only、W09 Delete-all、W11 Legacy retry、W14 Durable RPC、W10 Fork。
- **禁止**根据这份静态清单把 `ledger_commit_order_verified` 或 `ledger_trigger_continuity_verified` 提升为 true。

## F. T1 第二轮增量审计：Checkpoint Rewind 与 RPC 版本覆写（2026-11-07）

本轮补查了消息/Session 相关路由、rewind service，以及多份 SQL migration。新增两个必须独立跟踪的路径：

| 编号 | 静态调用链/代码定义 | 变更 | 状态与后续检查 |
|---|---|---|---|
| W17 | [rewind route](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/app/api/chat/v2/checkpoints/%5BckptId%5D/rewind/route.ts) → [rewindFork](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/lib/story-v2/rewind-service.ts#L50-L76) → `execute_v2_checkpoint_rewind_v2` | 目标 Session 的消息复制 INSERT | 当前 app 调用 **`..._v2`**；已检查的 [SQL](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/supabase/migrations/20260826210000_atomic_checkpoint_rewind_rpc.sql#L33-L60) 定义 **`execute_v2_checkpoint_rewind`**（没有 `_v2`），且其中确实包含 INSERT（约 L248）。两者不能等同；需确认最新同签名定义、部署状态、权限和调用可达性；本项暂标记 `RPC_VERSION_MISMATCH_UNVERIFIED`。 |
| W18 | [reply-job accept migration](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/supabase/migrations/20260913120000_v2_reply_job_accept_conflict_predicate.sql) 再次定义 `accept_v2_chat_reply_job` | User/Assistant INSERT；失败回复 UPDATE | W14 原先引用的 20260820 函数不是最新发现的定义。新迁移仍有约 L50/L77 INSERT 和 L127 UPDATE；必须按 **最新函数定义**审计锁，而不是根据旧迁移给出生产结论。 |

同时核对：

- [`src/app/api/chat/v2/messages/compact/route.ts`](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/app/api/chat/v2/messages/compact/route.ts)：经 `V2MessageService.compactTurnIndices` 路由进入 W07，不是新的直接 SQL 入口，但应登记为 W07 的另一上游调用者。
- [`src/lib/story-v2/events/chat.ts`](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/lib/story-v2/events/chat.ts)：存在 `v2_chat_messages` 表引用，当前查到的为 SELECT；对消息修改的间接 helper 仍需逐层跟踪。
- [`src/app/api/chat/v2/sessions/[sessionId]/fork/route.ts`](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/app/api/chat/v2/sessions/%5BsessionId%5D/fork/route.ts) → `forkFromTurn` → `execute_v2_chat_fork`：补强 W10 的应用调用链。
- SQL migration `20260826210000_atomic_checkpoint_rewind_rpc.sql` 使用源 Session 的 `FOR SHARE`（而非强制 `FOR UPDATE`）；若生产仍运行类似逻辑，必须在 T2 解释其与并发源消息变更的可见性和拷贝一致性关系。
- `20261008150000_v2_checked_message_mutation.sql` 中的 `bind_v2_legacy_retry_source` 调用了 `validate_v2_message_action_sources`，而该 helper 在已核代码中执行 Session `FOR UPDATE NOWAIT`。所以原先“函数体没有显式 Session 锁”只能标为 **间接锁待确认**，不能认定完全无锁。

### T1 进度口径与发现的重要问题

- 已登记 **18 类 Writer Path / 候选 Writer Path**（W01–W18）；其中 W18 是 W14 的新版本定义核查，**不是新的独立业务写入类型**。
- 不把这 18 类称为“全仓所有入口”，也不把旧 migration 函数作为现行生产定义。
- GitHub 代码搜索对该私有仓库没有返回可用匹配，完整扫描需要逐文件源码核对；目前仅覆盖选定的高相关 TS/SQL 文件。
- 从整个 Git tree 确认：RolePlay main 中至少有 **632 个 migration SQL**、**1,515 个 `src/` TS/TSX**、**305 个 `apps/` TS/TSX**、**43 个 `packages/` TS/TSX** 和 **457 个 `scripts/` TS/TSX/SQL/Python**。仅目录和扩展名计数，不表示都引用消息表；T1 要证明完整性，必须进行自动化扫描并记录跳过/失败文件。
- 下一步先做全仓静态扫描，重点 `execute_v2_checkpoint_rewind_v2` 的定义来源、所有 `CREATE OR REPLACE FUNCTION` 覆写链、动态 SQL、直接写入、触发器写入和定时任务引用；之后做生产 catalog **只读**核验。
- **当前仍然不证明**任意 Session 的最终提交顺序/Trigger 连续性；StoryForge V3 Full Recovery 保持 fail-closed。


## G. 可复现的只读全仓扫描器（代码已提交，待 Owner 本地运行）

新增：

- [`experiments/r58_quality/r60_roleplay_writer_inventory.py`](https://github.com/sunxu/storyforge/blob/r60/gold192-history-v3-adapter/experiments/r58_quality/r60_roleplay_writer_inventory.py)
- [合成测试](https://github.com/sunxu/storyforge/blob/r60/gold192-history-v3-adapter/experiments/r58_quality/test_r60_roleplay_writer_inventory.py)

扫描器使用 `git ls-files` 读取本地 RolePlay Worktree 中的 `src/`、`apps/`、`packages/`、`scripts/`、`supabase/`、`workers/` 下已跟踪的 TS/JS/Python/SQL，输出：

1. 直接 SQL `INSERT/UPDATE/DELETE/MERGE/TRUNCATE v2_chat_messages` 位置；
2. Supabase `.from('v2_chat_messages')` 和相邻写入方法候选；
3. 相关 `.rpc('...')` 调用；
4. 相关 SQL 函数定义及潜在覆写链；
5. 相关 Trigger 定义候选与动态 SQL 待核项；
6. 每个发现的相对路径、行号、分类，以及 skipped 文件记录、仓库 HEAD SHA。

不输出文件正文、消息文本、用户 ID、数据库连接串或 token；不访问网络或数据库，不执行被扫描项目的代码。现阶段是正则扫描工具，**存在误报和漏报可能**（比如动态生成函数名、多行拼接、间接数据库写入、第三方运行时代码），必须人工/AST 复核，不能仅凭 `STATIC_SCAN_COMPLETE_NOT_CERTIFIED` 宣告 T1 完成。

在 Owner 原 StoryForge Worktree 运行（RolePlay 目录必须由 Owner 指向实际已有的本地 clone，不假设 `~/workspace/RolePlay` 存在）：

```bash
set -euo pipefail
cd "$HOME/workspace/storyforge-r60-ledger-diagnostics"
git pull --ff-only origin r60/gold192-history-v3-adapter

# 按实际情况设置；目录必须是 sunxu/RolePlay 的本地 git 仓库根目录
: "${ROLEPLAY_REPO:?请先设置本机 RolePlay 仓库绝对路径}"
ROLEPLAY_REPO="$(cd "$ROLEPLAY_REPO" && pwd -P)"
git -C "$ROLEPLAY_REPO" remote -v
git -C "$ROLEPLAY_REPO" rev-parse HEAD

# 保存到 Owner 私有目录；不要将完整 scan report 自动提交 GitHub
umask 077
OUT="$HOME/.local/share/storyforge/r59/private/R60_T1_ROLEPLAY_WRITER_SCAN_SAFE_$(date -u +%Y%m%dT%H%M%SZ).json"
test ! -e "$OUT"
python3 experiments/r58_quality/r60_roleplay_writer_inventory.py \
  --roleplay-repo "$ROLEPLAY_REPO" \
  --output "$OUT"
shasum -a 256 "$OUT"
```

输出的 CLI SAFE 摘要可用于回传；完整 JSON 包含可公开的代码路径/函数名，但仍建议先留 Owner 本机，复核后只提交适当聚合统计。当前还没有执行实际 Owner RolePlay clone 的全仓扫描。

### T1 剩余判定

完成真正的 T1 需要：全仓零未解释的 skip、动态 SQL/间接调用的人工覆盖、最新 RPC 函数版本核对、所有写路径 reachability 分类，并进行生产目录只读交叉比对。随后才能进入 T2 的 lock-order 审计。


## H. Owner 本地 RolePlay 全仓静态扫描 SAFE 回执（2026-11-07）

Owner 已在本机执行 `r60_roleplay_writer_inventory.py`，并提供终端 SAFE 摘要：

| 字段 | 数值 |
|---|---:|
| `status` | `STATIC_SCAN_COMPLETE_NOT_CERTIFIED` |
| `head_sha` | `ccdf2e8dc2723f481cd0392883bc359e9e341c66` |
| `tracked_source_files_scanned` | 3466 |
| `skipped_count` | 0 |
| `SQL_MESSAGE_WRITE` | 291 |
| `SUPABASE_MESSAGE_TABLE` | 106 |
| `RPC_CALL_CANDIDATE` | 98 |
| `SQL_FUNCTION_DEFINITION` | 339 |
| `TRIGGER_DEFINITION_CANDIDATE` | 26 |
| `DYNAMIC_SQL_REVIEW_REQUIRED` | 89 |

Owner 报告的 SHA256：`d657f54601ebf7e63a2be5665c14e3856f6a470bf810c7f725091a18f919a3e1`。

**证据边界：**本报告只是复录 Owner 提供的 SAFE 输出；GitHub 审计端未读取或独立验算本地完整 JSON 文件字节，因此不能声称二次复核了 SHA256。也不能据此确认 `RolePlay` Worktree 干净、扫描结果完整覆盖动态构造/被忽略的目录、以及所有发现均为生产可达写入。扫描器的 `STATIC_SCAN_COMPLETE_NOT_CERTIFIED` 仅意味着所选择的已跟踪源码无 skipped/dirty，并不是代码正确性或生产数据库认证。

**数值不可直接当作独立写路径数：**
- 291 为 SQL 写入语法的正则命中，包含历史覆写、可能废弃的函数或重复定义；
- 106 为 TS/JS 对表的引用匹配，其中可能有 READ；
- 98 是相关 RPC 调用候选，不都写入消息表；
- 339 是按名称过滤的 SQL 函数定义，不都直接/间接写入消息表；
- 26 为 Trigger 定义候选，非现行启用 Trigger 的数量；
- 89 是“文件内同时发现 `EXECUTE` 和表名”的保守待核标签，不证明全部为动态 SQL 消息写入。

**与此前源码版本的差异：**首次人工审计用 `e9fe29c42434caeb0bac5acc91845ab4741ecb2b`，本次 Owner 扫描使用 `ccdf2e8dc2723f481cd0392883bc359e9e341c66`。需按扫描 HEAD 重新确认历史函数覆写和应用调用者，不直接将两个版本认作完全一致。

### 下一步：先做去重与分类，后做人工代码审查

1. 从 Owner 本地完整 SAFE JSON 按 **`path`、`line`、`kind`、`function`** 聚合；优先列出 `SQL_MESSAGE_WRITE` 与 `SUPABASE_MESSAGE_TABLE` 的真实路径，并分类写、读、误报。
2. 按函数名与 migration 日期查找同名 `CREATE OR REPLACE FUNCTION` 的覆写链，找到扫描 HEAD 的最后定义；再与生产 catalog（仅只读）比对。
3. 对 89 个动态 SQL 标签进行逐文件复核，标记真动态写入、只读或误报。
4. 将每条 **独立、已确证** Writer Path 连接至上游 Route/Worker/cron/RPC 和实际 Trigger；分离“代码定义、调用可达、生产启用”三层状态。
5. 新增 W17 Checkpoint Rewind 的 `_v2` RPC 定义来源优先核实；不可自动归并到旧函数。
6. 形成最终 T1 覆盖矩阵，才进入 T2；仍不得把 Ledger commit-order/trigger-continuity 标记为 true。


## I. Owner T1 聚合结果与重点复核（2026-11-07）

Owner 基于同一份本地 SAFE JSON 提供的聚合输出：SQL_MESSAGE_WRITE 291 次、65 个文件；SUPABASE_MESSAGE_TABLE 106 次、49 个文件；DYNAMIC_SQL_REVIEW_REQUIRED 89 次、89 个文件；SQL_FUNCTION_DEFINITION 按名称去重为 199 个函数名，其中 77 个函数名在不同文件重复定义。

**解释边界**：上述只是静态匹配计数。65 个 SQL 文件中包括大量 supabase/tests、scripts/check-* 和早期 migration；106 次表引用既包括 SELECT，也包括 INSERT/UPDATE/DELETE；89 个动态 SQL 待核仅表示扫描启发式命中，不等于 89 处真实动态写入。77 个重定义函数名未按参数类型区分 overload，也不代表全部为生产有效函数。

### I.1 需要优先追踪最终定义的函数

| 函数 | 涉及文件数 | 审计重点 |
|---|---:|---|
| mutate_v2_session_messages_atomic | 9 | 删除/压缩、Session 锁、最新签名及迁移覆写 |
| claim_v2_session_turn | 5 | 轮次分配与并发 |
| capture_v2_chat_message_ledger | 4 | OLD 快照、marker、trigger 实际定义 |
| execute_v2_chat_fork | 3 | 来源/目标 Session 的历史边界 |
| execute_v2_checkpoint_rewind_v2 | 2 | 先前待查的 _v2 RPC 确实有重定义候选，仍需核对具体文件和签名 |
| accept_v2_chat_reply_job | 2 | 接收、重试及最新写入事务 |
| import_v2_session_messages_atomic | 2 | 历史批量导入 |
| commit_v2_event_turn_claim | 2 | 元数据写入 |
| cleanup_v2_chat_message_ledger | 3 | 账本清理/保留 |

### I.2 直接核实的非 Web 写入路径

1. [execute-v2-session-watermark-recovery.mjs](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/scripts/execute-v2-session-watermark-recovery.mjs#L193-L230)：显式执行模式下分批直接 INSERT 消息，再调用 publish_history_recovery_save；需要核对跨 PostgREST 事务的恢复边界，不能因为它不是在线 API 就忽略。
2. [cleanup-deleted-history-recovery-20260825.mjs](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/scripts/cleanup-deleted-history-recovery-20260825.mjs#L95-L116)：显式执行模式下逐条直接 DELETE 消息；必须确认 Ledger 删除前快照及脚本实际运行情况。
3. [repair-turncap-damaged-sessions-0714.mjs](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/scripts/repair-turncap-damaged-sessions-0714.mjs#L35-L88)：消息表为 SELECT；带 --apply 时修改 story_v2_sessions.total_turns，而不是直接修改消息表。应登记为 SESSION_BOUNDARY_WRITER，避免误计入消息写入。
4. [v2-message-service.ts](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/src/lib/db/v2-message-service.ts#L1471-L1545)：finalizeStreamingAssistant 有 status='streaming' CAS、零行处理和相同正文重试幂等判断；不能误称完全没有并发保护，仍需审计 Session 级事务顺序。
5. [v2-message-service.ts](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/src/lib/db/v2-message-service.ts#L361-L390)：saveMessage 直接 INSERT；需继续追踪 claim RPC 与 INSERT 是否跨事务及有无统一排序依据。

**这些脚本含有写入语句，并不证明它们已经在生产执行。** 所有结论须区分 CODE_DEFINED、CALLABLE、PRODUCTION_ENABLED、EXECUTED。

### I.3 下一步

将所有命中以代码文件、行号、操作、函数签名去重；把 TEST_FIXTURE、HISTORICAL_MIGRATION、LIVE_API_WRITE、WORKER_CRON_WRITE、MANUAL_SCRIPT_WRITE、READ_ONLY 分类。对 9/4/2 个重点重定义组核实最终签名，并与实际数据库 catalog 只读对照。T1 仍未达到完整认证，T2 的 Session 锁审计仅能针对已验证路径先行。

## J. T1 三组关键函数的源码覆写与调用链复核（2026-11-07）

本节锁定 RolePlay 源码 Commit `ccdf2e8dc2723f481cd0392883bc359e9e341c66`，检查最新检出的 SQL 定义；属于代码静态证据，**尚非生产 pg_proc / pg_trigger 实际定义证明**。各函数按函数名和明确的参数类型定位；所有同名不同签名 overload 仍须 catalog 复核。

### J.1 mutate_v2_session_messages_atomic：重点是 10 月 7 日版本

- Owner 聚合清单：同名函数出现在 9 个 SQL 文件中。
- [2026-10-06 migration](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/supabase/migrations/20261006120000_v2_legacy_orphan_delete_guard.sql#L5) 有该函数定义，但并非最后已核实的代码版本。
- [2026-10-07 migration](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/supabase/migrations/20261007100000_v2_memory_summary_continuity.sql#L144-L205) 再次 `CREATE OR REPLACE FUNCTION public.mutate_v2_session_messages_atomic(p_session_id text, p_user_id uuid, p_mode text, p_turn_indices integer[], p_role text, p_truncate_from integer)`；它在 L188–195 明确先锁 `story_v2_sessions FOR UPDATE`。
- 同一 10 月 7 日函数还有多个针对 `v2_chat_messages` 的 DELETE（约 L372/400/467）及 UPDATE（约 L498/506），与 Session 首锁位于一个 PostgreSQL RPC 调用事务；需要进一步比较被调用的所有 helper 和触发器。
- **T1 判定：**上游消息删除/压缩调用链找到较新函数实现，标记 `SOURCE_DEFINITION_FOUND_PROD_UNVERIFIED`；不再用 10 月 6 日定义代表最终代码。

### J.2 capture_v2_chat_message_ledger：稀疏快照实现明确，生产状态未认证

- Owner 聚合清单：同名函数在 4 个文件中出现。
- [2026-07-27 初版](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/supabase/migrations/20260727d_v2_chat_message_ledger.sql#L30-L77) 建立 Ledger Trigger，记录 `recorded_at DEFAULT now()`，对 `v2_chat_messages` `AFTER INSERT OR UPDATE OR DELETE`；该初版授予 `service_role` 直接 INSERT Ledger 的权限（需要检查后续 revoke 和生产实际 ACL）。
- [2026-08-12 业务语义版本](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/supabase/migrations/20260812160000_v2_chat_ledger_semantic_versions.sql#L12-L85) 重新定义业务版本记录规则。
- [2026-09-08 稀疏标记版本](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/supabase/migrations/20260908132000_v2_chat_ledger_sparse_markers.sql#L6-L105) 重定义：业务 INSERT 与 UPDATE_AFTER 写 marker，业务 UPDATE_BEFORE / DELETE 写 OLD 完整快照；**status-only、partial_content-only 更新不会写业务 Ledger**。
- 这意味着 Ledger 对可恢复正文的记录规则可描述，但不保证所有运行状态转换或目标时点消息有效性已记录。第四处函数定义尚未由本轮人工源码定位和复核，不能宣布全部覆写链已核清。
- **T1 判定：**已发现主 Trigger 和关键版本行为，标记 `SOURCE_TRIGGER_BEHAVIOR_PARTIAL_PROD_UNVERIFIED`，保留目标历史时间语义 HOLD。

### J.3 execute_v2_checkpoint_rewind_v2：之前的版本缺失疑问已消除

- [应用调用](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/src/lib/story-v2/rewind-service.ts#L50-L72) 确认 `rewindFork` → `execute_v2_checkpoint_rewind_v2`。
- [2026-08-26 的 v2 定义](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/supabase/migrations/20260826220000_checkpoint_full_state_snapshot.sql#L343-L385) 以及 [2026-10-07 再定义](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/supabase/migrations/20261007100000_v2_memory_summary_continuity.sql#L859-L900) 均明确存在；两者同名、形参为 `(UUID, UUID, TEXT, TEXT)`。
- v2 包装函数调用 [基础 `execute_v2_checkpoint_rewind`](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/supabase/migrations/20260826210000_atomic_checkpoint_rewind_rpc.sql#L33-L95)（此函数执行跨表复制，包含约 L248 的消息 INSERT），然后读取 rewind job / checkpoint、恢复目标 Session 的其他状态。
- 基础函数对源 checkpoint / session 使用 `FOR SHARE`，并非简单的 Session `FOR UPDATE` 独占锁；在 T2 需判断与源 Session 并发写入的关系，以及快照读取时点。包装函数整体处于单个 RPC 事务的初步代码结构，仍需确认异常分支、隔离级别及生产定义。
- **T1 判定：**原先 `RPC_VERSION_MISMATCH_UNVERIFIED` 应细化为 `SOURCE_WRAPPER_CHAIN_RESOLVED_PROD_UNVERIFIED`。`_v2` 并非找不到定义，真正待核是当前生产所部署的确切 SQL 及全链事务语义。

### J.4 下游 T2 与生产只读核验

| 优先级 | 审计项 | 只读证据要求 |
|---|---|---|
| P0 | `mutate_v2_session_messages_atomic` | 生产 `pg_get_functiondef` 的同签名函数、Session/消息锁顺序、所有 Helper |
| P0 | `capture_v2_chat_message_ledger` | 生产 `pg_trigger.tgenabled`、`pg_get_triggerdef`、最终 `pg_get_functiondef`、Ledger ACL |
| P0 | `execute_v2_checkpoint_rewind_v2` 与基础函数 | 两个函数定义、调用是否同事务、源/目标锁与版本边界 |
| P0 | 直接 INSERT/Finalize/脚本写入 | 单次 HTTP/RPC 的事务范围、CAS、Session 锁、是否纳入 Trigger |
| P1 | runtime status-only 操作 | 是否影响训练目标的可见性或有效状态；不能默认 Ledger 有记录 |

**安全结论：** 本轮没有生产数据库连接或验证；未进行 DML/DDL，未运行训练或历史恢复。`ledger_commit_order_verified=false`、`ledger_trigger_continuity_verified=false`、`quality_v1_admitted=0`、`training_authorized=false`、`gpu_started=false`。
