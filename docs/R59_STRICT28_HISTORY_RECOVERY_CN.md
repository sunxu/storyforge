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
