# R59 Strict28 历史上下文恢复

## 目的与范围

本工具在既有 Strict28 历史曝光审计之后，恢复目标回复时点之前、可由数据库时间和 Session 分叉关系支持的上下文。它是来源证据工具，不是 Quality-v1 准入器、SFT 编译器或训练器。

- 输入为 Owner 本机同一次 PR #9 审计运行生成的 Strict28 私有 ledger 与 SAFE receipt；适配器从 SAFE receipt 的 `private_ledger.sha256` 读取预期摘要并重新校验 ledger 字节，不硬编码未经 Owner 核验的哈希。
- 仅查询 ledger 明确列出的 28 个 `story_id / session_id / turn_index` 定位项。
- 通过目标 Assistant 正文 SHA256 再次确认消息身份。
- fork/rewind 会把继承消息物化复制到子 Session（生成新的 message ID）。恢复时以目标所在的子 Session 中已物化的历史为准；父 Session 只用于 lineage 证明，不再二次合并父消息，避免重复或误读分叉边界。`forked_from_turn` 存储的是 story-turn 编号，不是消息表的物理 `turn_index`。
- 只纳入 `created_at` 严格早于目标消息、状态为 `completed` 的 User / Assistant 消息。失败、流式中断、未来时间、超出分叉边界的消息不进入上下文。
- 不截断历史。超过上限、历史末尾不是 User、身份不唯一、Session 祖先缺失或出现循环时整批 HOLD。

## 可复用实现

- 唯一共享核心：`src/storyforge_gold_quality/history_recovery.py`
- Strict28 薄适配器：`experiments/r58_quality/r59_strict28_history_recovery.py`
- 共享核心合成回归：`tests/test_history_recovery.py`
- 适配器合成回归：`experiments/r58_quality/test_r59_strict28_history_recovery.py`

共享核心只接受调用方提供的数据库 cursor 和已验证 case locator；不创建连接、不读取 DSN、不写文件、不访问网络，也不决定 Quality-v1 准入。其他批次可以复用 `recover_cases()`，由自己的薄适配器负责输入 pin、权限和 SAFE 输出。

## 稀疏消息账本恢复（本轮新增）

数据库核验确认 `public.v2_chat_message_ledger` 使用以下字段：

- `id`：事件序号；
- `message_id`、`story_id`、`session_id`、`turn_index`：消息定位；
- `operation`：`insert`、`update_before`、`update_after`、`delete`；
- `row_data`：插入/更新后为 `marker_v1` 轻量标记；更新前/删除前为完整旧行快照；
- `recorded_at`：数据库事务时间戳。

该表当前规模很大（2026-11-03 只读统计估算约 4,275 万行、总占用约 102 GB，其中 heap 约 17 GB），禁止全表扫描和全表聚合。共享核心按 `story_id + session_id + turn_index ceiling` 做每 Session 一次有界读取，使用 `(session_id, recorded_at, id)` 索引，并保留完整事件元数据，以便精确核对 `mutation_revision` 与 `update_after` 计数。默认最多 100,000 条，超过上限整批 HOLD；可用 `--max-ledger-events` 显式调整，上限 500,000。

### R59.2 Ledger JSONB 读取优化

首次真实执行在第一条 `MESSAGE_LEDGER_READ` 的 `EXECUTE` 阶段收到 SQLSTATE `57014`（`QueryCanceled`），与 90 秒 statement timeout 相符。检查触发器后确认 `created_at` 和 `recorded_at` 均默认为 `now()`；但简单添加 `recorded_at >= target_created_at` 会跳过目标前 `update_after` 事件，破坏原有的精确 `mutation_revision` 交叉核验，因此**不采用时间下界来缩短元数据范围**。

改为两阶段读取：

1. 第一条查询只读取紧凑元数据：事件 ID、message ID、story/session、role、turn index、operation、recorded_at；不读取任何 `row_data` JSONB。保留目标前后的全部事件，以维持原有 revision 计数核验。
2. 本地根据每个目标边界，只挑出目标 marker 和每条历史消息的第一个 post-target event；仅对这些事件按主键 `id = ANY(...)` 批量读取 `row_data`，每批最多 500 条。其余事件的大型 before-image 不再传输。
3. 对读取到的 marker 仍验证 `marker_v1`；对实际用于恢复的 snapshot 仍执行完整字段、身份、revision 校验。SAFE 增加 `ledger_detail_rows_loaded_total`，只报告加载的 detail 行数，不输出任何正文或 ID。元数据 locator 校验按字段给出不含值的安全原因码（message_id、story_id、session_id、turn_index、operation），不跳过、不规范化、不放宽任何异常事件；缺少任何所需 detail 或发现无效 locator 都整批 HOLD。

这保留了原有历史恢复与 revision 检查，不降低准入标准；不增加索引、不修改数据库、不延长 90 秒超时。主键 detail 查询的 EXPLAIN 已确认使用 `v2_chat_message_ledger_pkey`。metadata 查询仍使用 session 索引并过滤 story/turn；真实 session 的执行耗时仍需 Owner 本机复测。

重建规则：

1. 目标 Assistant 必须在账本中存在 `insert` 或 `update_after` 事件，作为该 Session 的目标边界；缺失则 HOLD。
2. 对每条历史消息，找到严格晚于目标边界的第一条事件。
3. 第一条事件为 `update_before` 或 `delete` 时，使用其旧行快照恢复目标时点状态；第一条事件为 `insert` 或 `update_after` 时，说明目标时点该消息尚不存在或尚无业务正文，排除。
4. 没有目标后事件的消息才使用当前行。
5. 对当前行或旧快照，核对 `mutation_revision` 与账本中此前的 `update_after` 数量。数据库的 revision 触发器还会记录 status / partial_content 变化，而稀疏账本触发器不一定为这些变化保存快照；计数不一致时 HOLD，不以当前正文替代历史正文。
6. 历史消息删除、编辑或迁出目标 Session 后，若账本有可验证的目标后旧快照，仍可恢复；新插入、流式完成标记不会被误当成目标前历史。

事件排序使用 `(recorded_at, id)`。注意：`recorded_at` 是事务时间，不是事务提交时间；当前账本没有提交 LSN，因此不能证明并发事务的真实 commit visibility 顺序。SAFE 明确输出 `ledger_commit_order_verified=false`。该限制必须保留，不能宣称为字节级或提交顺序级历史回放。 当前可见的 migration history 也不能证明 ledger trigger 从目标消息创建时起连续启用；虽然目标事件边界、每条消息的 `mutation_revision` 与事件计数会执行交叉核验，但这不是完整 DDL/trigger 连续性审计。SAFE 同时输出 `ledger_trigger_continuity_verified=false`。如果后续需要证明无触发器停用窗口，必须取得独立数据库 DDL/audit 证据，不能从当前表结构推断。

共享实现与测试：

- `src/storyforge_gold_quality/message_ledger.py`
- `tests/test_message_ledger.py`
- `src/storyforge_gold_quality/history_recovery.py` 集成调用
- `tests/test_history_recovery.py` 编辑、删除及未记录 mutation revision 的集成回归

目标回复本身仍须通过当前目标消息的精确 SHA256；若目标回复本身已被修改、删除或移动而无法按当前定位验证，本版本会 HOLD，不擅自从历史快照猜测目标身份。

## OperationalError 安全诊断（R59.1）

首次本机执行返回 `reason_code=OperationalError`，旧版 SAFE 只暴露异常类型，无法区分连接阶段和查询阶段。适配器现将 psycopg 数据库错误转换为不含原始异常消息的安全诊断：

- `database_stage`：`CONNECT`、`SET_READ_ONLY`、`SET_STATEMENT_TIMEOUT`、`SET_LOCK_TIMEOUT`、`RECOVERY_QUERIES` 或 `ROLLBACK`。
- `database_sqlstate`：仅在 PostgreSQL SQLSTATE 满足五位大写字母/数字格式时输出，否则为 null。
- `database_exception_type`：只输出异常类名，不输出异常消息、DSN、主机、用户名或密码。
- 当 `database_stage=RECOVERY_QUERIES` 时，额外输出：
  - `database_operation`：`SESSION_LINEAGE_READ`、`TARGET_MESSAGE_READ`、`MESSAGE_LEDGER_READ`、`MESSAGE_LEDGER_DETAIL_READ`、`CURRENT_HISTORY_READ`、`STORY_CONTENT_VERSION_READ` 或 `STORY_ADMIN_VERSION_READ`；
  - `database_query_ordinal`：本次恢复 cursor 内第几条查询，不包含 Session ID；
  - `database_failure_phase`：`EXECUTE`、`FETCH_ONE` 或 `FETCH_ALL`。
- 不输出 SQL 文本、查询参数、Session ID、Story ID 或原始异常消息。
- `reason_code` 固定为 `DATABASE_OPERATION_FAILED`。

数据库 schema 核验已确认所需的五张表和列存在；只读连接角色对这些表具有 SELECT 权限，且当前会话 `transaction_read_only=on`。这不能证明 Owner Mac 使用的 DSN、账号、网络链路或连接池状态相同，因此不能据此排除本机连接问题。

重新运行前先更新到最新诊断提交，并确认上一次失败没有留下输出目录；使用新的、从未存在过的输出目录。保留原始只读 DSN，不要将其贴到聊天。将新 SAFE 中的 `database_stage`、`database_operation`、`database_query_ordinal`、`database_failure_phase` 和 `database_sqlstate` 返回即可。



## Session summary 使用规则

允许考察的字段：

- `memory_summary`
- `recent_summary`
- `rolling_outline`

只有同时满足以下条件才进入私有恢复结果：

1. Session `updated_at` 严格早于目标 Assistant `created_at`；
2. `last_summary_turn`、`last_extract_turn` 必须是 story-turn 整数；`summary_source_end_index`、`summary_source_dependency_end_index`、`summary_text_end_index`、`summary_legacy_text_end_index` 是物理消息 `turn_index`；
3. story-turn 截止按 `(target_turn_index - 1) // 2` 计算；物理索引截止为 `target_turn_index - 1`。虽然数据库存在 `last_summary_turn * 2` 的旧兼容回退，但本恢复门禁不接受空的 source/text/legacy 索引；只有显式索引全部可验证时才使用摘要。dependency 索引可以为空；非空时必须在物理截止内。

缺少更新时间、story-turn 或物理索引证据时，摘要只标记不可验证，不会被使用。当前子 Session 行的 `updated_at` 晚于目标时点时，当前摘要一律不作为历史上下文；父 Session 摘要不与子 Session 历史重复拼接。Volume memory 不在本版本自动纳入。

## 历史故事版本

### `story_content_versions`

仅选择 `source_updated_at` 和 `archived_at` 均严格早于目标消息的最新版本，按 source update time、content revision 和版本 ID 排序。没有满足条件的版本时，标记 `NO_PRETARGET_VERSION_FOUND`，不得回退到当前 `user_stories.v2_data`。

### `story_admin_versions`

只有 `created_at` 和 `updated_at` 均严格早于目标消息时才纳入。该表当前按 story_id 唯一，不是完整版本历史；晚于目标时点的当前行不能证明目标时点配置。

即使找到目标时点前的故事卡/管理版本，也**不证明历史 Provider System Prompt、模型配置或原始请求字节**。输出固定标记 `historical_system_prompt_verified=false`，不得把卡片快照伪装成历史 System Prompt。

## 本机执行

使用项目目录 Python 环境，不使用私人目录下的 venv：

```bash
python3 -m pip install 'psycopg[binary]'
```

将本机私有凭据管理器中的只读 DSN 放入环境变量 `STORYFORGE_SUPABASE_DSN`。不要把 DSN、密码或 token 写入聊天、仓库、命令历史或 CI。连接必须只读；脚本会执行：

- `SET TRANSACTION READ ONLY`
- `SET LOCAL statement_timeout = '90000ms'`
- `SET LOCAL lock_timeout = '1000ms'`

输入文件为此前 Strict28 审计生成的：

`R59_STRICT28_HISTORICAL_EXPOSURE_PRIVATE.jsonl`

ledger 与 SAFE receipt 必须来自同一次 PR #9 运行、位于同一私有输出目录；SAFE receipt 必须为预期 Schema / 状态，28 条上下文核验通过、源字节 pin 已验证且训练未授权。适配器校验 receipt 内的 ledger SHA256 与实际字节。两个文件权限均为 0600，父目录为 0700。运行示例：

```bash
python3 experiments/r58_quality/r59_strict28_history_recovery.py \
  --strict28-ledger "/private/path/R59_STRICT28_HISTORICAL_EXPOSURE_PRIVATE.jsonl" \
  --safe-report "/private/path/R59_STRICT28_HISTORICAL_EXPOSURE_SAFE.json" \
  --output-dir "/private/path/r59-strict28-history-recovery-v1"
```

输出目录必须尚不存在，父目录权限为 0700。输出包含：

- `R59_STRICT28_HISTORICAL_CONTEXT_PRIVATE.jsonl`：逐案消息、Session lineage、已验证摘要及目标时点故事版本；
- `R59_STRICT28_HISTORICAL_CONTEXT_SAFE.json`：仅计数、状态和非授权字段；不包含逐案 ID、私有正文、目标哈希或私有文件哈希。SAFE 文件自身的 SHA256 可在本机单独计算。

## 状态边界

本工具成功只表示历史来源已按上述时间边界恢复，不代表文学质量通过、世界语义隔离完成或可训练。SAFE 必须保持：

- `quality_v1_admitted=0`
- `training_authorized=false`
- `gpu_started=false`
- `r50_accessed=false`
- `private_values_emitted=false`

后续应将私有恢复结果交给独立的 Quality-v1 来源/结构门禁；不得将缺失历史版本、未验证摘要或当前卡片快照自动升级为 PASS。
