# R60 Gold192 历史上下文恢复适配器

## 状态

本分支 `r60/gold192-ledger-history` 基于 `r60/hf-jobs-runtime`。本变更选择性移植
`r59/shared-history-recovery` 的共享恢复核心，不合并整个 R59 分支。

当前交付：
- `src/storyforge_gold_quality/message_ledger.py`
- `src/storyforge_gold_quality/history_recovery.py`
- 两个共享核心合成测试
- `experiments/r58_quality/r59_gold192_history_recovery.py`
- `experiments/r58_quality/test_r59_gold192_history_recovery.py`

这是只读来源恢复工具，不是 Quality-v1 准入器、SFT 编译器或训练器。
默认 Pilot 为 8 条；`--pilot 0` 表示 72 条双审 PASS 优先候选。扩大范围前应先审查 Pilot SAFE。

## 输入

适配器要求同一次既有 Gold192 Source Extract 运行的以下文件：
- Reviewer A 结果
- Reviewer B 结果
- 11 条争议排除 JSONL
- 冻结 Gold192 source packets
- `R59_SOURCE_LOCATORS_192.jsonl`
- 对应 `R59_SOURCE_SAFE.json`

输入 SHA256 沿用 `r59_gold192_supabase_extract.py` 中冻结的 A/B/排除/packets pins。
Locator 文件必须与 SAFE receipt 中的文件 SHA256 一致。目标必须为 `EXACT_MATCH`，
并具有唯一 message/session locator；无法证明身份的案例 HOLD，不采用“唯一根 Session”
作为身份替代证明。连接数据库后，适配器还会读取 13 个 story 的 owner `user_id`，要求全部可见且
属于同一个 UUID；缺失或多 owner 一律 HOLD。

所有输入文件必须是普通文件、权限 0600，直接父目录权限 0700。私有正文、ID 和哈希
不得回传聊天、提交 GitHub 或写入 Actions 日志。

## 只读与历史边界

数据库连接通过 `STORYFORGE_SUPABASE_DSN` 环境变量提供。脚本执行：
- `SET TRANSACTION READ ONLY`
- `statement_timeout = 90000ms`
- `lock_timeout = 1000ms`
- 成功后显式 ROLLBACK

恢复调用 `storyforge_gold_quality.history_recovery.recover_cases()`，并复用稀疏 Ledger
两阶段读取。默认最多 100,000 个 Session Ledger 事件、最多 20,000 条历史消息、
最多 16 层 Session lineage。超限或证据不完整时整批 HOLD，不静默截断。

SAFE 固定保留以下限制：
- `ledger_commit_order_verified=false`
- `ledger_trigger_continuity_verified=false`
- `historical_system_prompt_verified=false`
- `quality_v1_admitted=0`
- `training_authorized=false`
- `gpu_started=false`
- `database_modified=false`

当前故事卡快照不被当作目标时点历史配置。该适配器不恢复精确 Provider System Prompt，
也不证明历史模型配置或原始请求字节。

## RLS / 数据库权限注意事项

Owner 已决定采用简化的全库只读模型：`r58_export_reader` 对共享恢复所需六张表读取所有故事、
所有 Owner 的记录，不再使用逐故事 allowlist 或单一 Owner 限制。

2026-11-05 已由 Owner 执行权限配置，并回传验证结果：
- 六张表均存在 `r58_export_reader` 的 PERMISSIVE SELECT 策略，`USING (true)`；
- 六张表均有 SELECT 权限；
- 六张表 INSERT、UPDATE、DELETE 均为 false；
- 角色 `rolsuper=false`、`rolbypassrls=false`；
- 没有授予 `service_role`，没有关闭 RLS。

该设计明确允许该角色读取六张表内所有故事和所有 Owner 的记录。它是受信任数据处理环境的广范围只读凭据，
不是用户级隔离凭据。不得将 DSN 暴露给客户端、HF 训练容器或不受信任的第三方；只能在 Owner 控制的
Source Recovery 环境使用。未来增加故事不需要修改这六张表的权限。

权限与训练准入仍然独立：全库可读不意味着任何记录自动获得 Quality-v1 admission。
每条候选仍需来源身份认证、历史恢复、审核和独立训练准入。

后续连接必须继续使用 `SET TRANSACTION READ ONLY`、statement timeout 和 lock timeout。
不得授予 `BYPASSRLS`、`service_role`、superuser 或任何写权限。

## 2026-11-05 schema / RLS 核验补充

Owner 提供的元数据结果确认：
- `user_stories.id` 为 TEXT，owner 字段是 UUID `author_id`，不是 `user_id`；
- `story_v2_sessions`、`v2_chat_messages`、`v2_chat_message_ledger` 使用 UUID `user_id`；
- `story_content_versions` 使用 UUID `author_id`，`story_id` 为 TEXT；
- 已有策略中，`v2_chat_messages` 与 `story_v2_sessions` 的用户策略只面向 `authenticated`；
- `v2_chat_message_ledger` 与 `story_content_versions` 的策略查询结果没有列出任何策略；
- `story_admin_versions` 只列出 service_role 策略，且本次 information_schema.columns 输出没有返回它的列定义，必须单独确认；
- `user_stories` 存在 PUBLIC permissive `true` 策略；另有面向 anon/authenticated 的 restrictive moderation guard。自定义导出角色不能假定受该 guard 约束。

适配器 owner 预检已修正为从 `user_stories.author_id` 读取 owner UUID，保留 story ID TEXT 的比较方式。
权限设计（待执行，尚未变更）：
- `user_stories`：已有 PUBLIC permissive `true`，必须给 `r58_export_reader` 增加
  RESTRICTIVE SELECT 策略，条件为固定 owner `author_id` 与 13 个 story ID 的交集。
  仅增加 permissive 策略不能收窄 PUBLIC 的 `true`。
- `story_v2_sessions`：新增针对导出角色的 SELECT permissive 策略，
  同时匹配 `user_id`、`story_id`。
- `v2_chat_messages`、`v2_chat_message_ledger`：同样同时匹配 `user_id`、`story_id`。
- `story_content_versions`：匹配 `author_id` 与 `story_id`。
- `story_admin_versions`：表无 owner 列，只能通过精确 `story_id` allowlist，
  并以 `EXISTS` 关联 `user_stories(id, author_id)` 验证固定 owner。
- 仅 `story_admin_versions` 需要新增 SELECT GRANT；其余五张表已具备 SQL SELECT 权限。

所有 allowlist 值必须由 Owner 在本机从冻结 packets 取得，owner UUID 必须与数据库查询核对；
不得把这些私有标识提交 GitHub 或粘贴到聊天。创建策略前还应确认没有同名策略，并在事务中
执行后检查 `pg_policies`、`has_table_privilege`、角色属性和策略定义。
本次只修改 GitHub 分支代码与测试，不执行数据库权限变更。

## CPU 合成测试

```bash
python3 -m pip install -e ".[dev]"
ruff check src/storyforge_gold_quality/message_ledger.py \
  src/storyforge_gold_quality/history_recovery.py \
  tests/test_message_ledger.py tests/test_history_recovery.py \
  experiments/r58_quality/r59_gold192_history_recovery.py \
  experiments/r58_quality/test_r59_gold192_history_recovery.py
pytest -q tests/test_message_ledger.py tests/test_history_recovery.py \
  experiments/r58_quality/test_r59_gold192_history_recovery.py
```

以上测试不需要 DSN，不连接 Supabase，不读取 Gold192 私有文件，不启动 HF/GPU。

## Owner 本机 Pilot 命令

```bash
set -euo pipefail
cd ~/workspace/storyforge

PRIVATE="$HOME/.local/share/storyforge/r58/private"
R59_PRIVATE="$HOME/.local/share/storyforge/r59/private"
SOURCE="$R59_PRIVATE/r59-source-pilot7"

python3 experiments/r58_quality/r59_gold192_history_recovery.py \
  --reviewer-a "$PRIVATE/R58_GOLD192_REVIEWER_A_RESULTS_20261102.json" \
  --reviewer-b "$PRIVATE/R58_GOLD192_REVIEWER_B_RESULTS_20261102.json" \
  --exclusions "$PRIVATE/quality-v1/QUALITY_V1_EXCLUDED_CASES.jsonl" \
  --source-packets "$R59_PRIVATE/GOLD192_STORY_REVIEW_PACKETS_PRIVATE.jsonl" \
  --source-locators "$SOURCE/R59_SOURCE_LOCATORS_192.jsonl" \
  --source-safe "$SOURCE/R59_SOURCE_SAFE.json" \
  --output-dir "$R59_PRIVATE/gold192-history-pilot8-v1" \
  --pilot 8
```

仅回传 SAFE stdout，不回传 PRIVATE JSONL。Pilot 成功也不构成训练授权。
