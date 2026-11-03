# R59 Strict28 历史上下文恢复

## 目的与范围

本工具在既有 Strict28 历史曝光审计之后，恢复目标回复时点之前、可由数据库时间和 Session 分叉关系支持的上下文。它是来源证据工具，不是 Quality-v1 准入器、SFT 编译器或训练器。

- 输入仅为 Owner 本机生成的 Strict28 历史曝光私有 ledger，按固定 SHA256 验证。
- 仅查询 ledger 明确列出的 28 个 `story_id / session_id / turn_index` 定位项。
- 通过目标 Assistant 正文 SHA256 再次确认消息身份。
- 恢复当前 Session 和其父 Session 分叉前的消息；父 Session 仅纳入 `forked_from_turn` 及以前的消息。
- 只纳入 `created_at` 严格早于目标消息、状态为 `completed` 的 User / Assistant 消息。失败、流式中断、未来时间、超出分叉边界的消息不进入上下文。
- 不截断历史。超过上限、历史末尾不是 User、身份不唯一、Session 祖先缺失或出现循环时整批 HOLD。

## 可复用实现

- 唯一共享核心：`src/storyforge_gold_quality/history_recovery.py`
- Strict28 薄适配器：`experiments/r58_quality/r59_strict28_history_recovery.py`
- 共享核心合成回归：`tests/test_history_recovery.py`
- 适配器合成回归：`experiments/r58_quality/test_r59_strict28_history_recovery.py`

共享核心只接受调用方提供的数据库 cursor 和已验证 case locator；不创建连接、不读取 DSN、不写文件、不访问网络，也不决定 Quality-v1 准入。其他批次可以复用 `recover_cases()`，由自己的薄适配器负责输入 pin、权限和 SAFE 输出。

## Session summary 使用规则

允许考察的字段：

- `memory_summary`
- `recent_summary`
- `rolling_outline`

只有同时满足以下条件才进入私有恢复结果：

1. Session `updated_at` 严格早于目标 Assistant `created_at`；
2. `last_summary_turn`、`last_extract_turn`、`summary_source_end_index`、`summary_source_dependency_end_index`、`summary_text_end_index`、`summary_legacy_text_end_index` 均为整数；
3. 所有摘要截止位置均不超过该 Session 在目标时点可见的 turn cutoff；父 Session 的 cutoff 为子 Session 的 `forked_from_turn`。

缺少任一时间或 cutoff 证据时，摘要只标记不可验证，不会被使用。当前 Session 行的 `updated_at` 晚于目标时点时，当前摘要一律不作为历史上下文。Volume memory 不在本版本自动纳入。

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

固定 SHA256：

`b20334581981b0affd76e40c1b2dfe02cf4f610f0d13a666279cc805d48f4fbd`

输入文件权限必须为 0600，父目录为 0700。运行示例：

```bash
python3 experiments/r58_quality/r59_strict28_history_recovery.py \
  --strict28-ledger "/private/path/R59_STRICT28_HISTORICAL_EXPOSURE_PRIVATE.jsonl" \
  --output-dir "/private/path/r59-strict28-history-recovery-v1"
```

输出目录必须尚不存在，父目录权限为 0700。输出包含：

- `R59_STRICT28_HISTORICAL_CONTEXT_PRIVATE.jsonl`：逐案消息、Session lineage、已验证摘要及目标时点故事版本；
- `R59_STRICT28_HISTORICAL_CONTEXT_SAFE.json`：仅计数、状态、SHA256 和非授权字段。

## 状态边界

本工具成功只表示历史来源已按上述时间边界恢复，不代表文学质量通过、世界语义隔离完成或可训练。SAFE 必须保持：

- `quality_v1_admitted=0`
- `training_authorized=false`
- `gpu_started=false`
- `r50_accessed=false`
- `private_values_emitted=false`

后续应将私有恢复结果交给独立的 Quality-v1 来源/结构门禁；不得将缺失历史版本、未验证摘要或当前卡片快照自动升级为 PASS。
