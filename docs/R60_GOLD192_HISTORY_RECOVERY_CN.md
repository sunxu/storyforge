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
作为身份替代证明。

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

`r58_export_reader` 已具有两张消息表的 SELECT SQL 权限，但这不代表 RLS 允许读取行。
已知核验显示：
- `v2_chat_messages` 开启 RLS，现有策略只面向 `authenticated` 和 `service_role`；
- `v2_chat_message_ledger` 开启 RLS，已核验输出未显示适用于 `r58_export_reader` 的策略；
- `r58_export_reader` 没有 `BYPASSRLS`，不是 superuser，也未继承其他角色；
- 该角色没有 JWT subject，且直接调用 `auth.uid()` 会触发 `permission denied for schema auth`。

**不要授予 `BYPASSRLS`，不要授予 `service_role`，不要将只读导出账号改成 superuser。**
也不要通过 `SET request.jwt.claim.sub` 让数据库角色冒充任意用户；这会把 RLS 保护变成可自行伪造的身份声明。

权限调整前，必须以 `r58_export_reader` 执行以下只读预检，覆盖共享恢复核心实际读取的全部表；
不能只检查两张消息表：

```sql
WITH required(table_name) AS (
  VALUES
    ('v2_chat_messages'),
    ('v2_chat_message_ledger'),
    ('story_v2_sessions'),
    ('story_content_versions'),
    ('story_admin_versions'),
    ('user_stories')
)
SELECT r.table_name,
       c.relrowsecurity AS rls_enabled,
       c.relforcerowsecurity AS rls_forced,
       has_table_privilege(current_user, format('public.%I', r.table_name), 'SELECT')
         AS can_select
FROM required r
LEFT JOIN pg_class c
  ON c.relnamespace = 'public'::regnamespace
 AND c.relname = r.table_name
 AND c.relkind IN ('r', 'p')
ORDER BY r.table_name;

SELECT tablename, policyname, roles, cmd, qual, with_check
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN (
    'v2_chat_messages', 'v2_chat_message_ledger', 'story_v2_sessions',
    'story_content_versions', 'story_admin_versions', 'user_stories'
  )
ORDER BY tablename, policyname;

SELECT rolname, rolsuper, rolbypassrls
FROM pg_roles
WHERE rolname = current_user;
```

若表缺少 SELECT 权限，只能在确认确有需要后授予该角色 SELECT；不得授予写权限。
若 RLS 对该角色无适用策略，需逐表检查实际列、现有策略和 owner 关系，再设计最小范围策略。
不能假定另外四张表具有与消息表相同的 `user_id` 列或相同 RLS 模型。

如果实际 Pilot 因 RLS 返回零行，建议先只读确认 Gold192 的 13 个 story 是否全部属于同一个 owner `user_id`。
只有 Owner 在 Supabase SQL Editor 中确认唯一 owner UUID 后，才考虑创建两条专用、SELECT-only、绑定固定 UUID 的策略，例如：

```sql
-- OWNER_UUID 必须由 Owner 在受信任环境核实；不可使用聊天中猜测的值。
CREATE POLICY r58_gold192_reader_own_messages
ON public.v2_chat_messages
FOR SELECT TO r58_export_reader
USING (user_id = 'OWNER_UUID'::uuid);

CREATE POLICY r58_gold192_reader_own_ledger
ON public.v2_chat_message_ledger
FOR SELECT TO r58_export_reader
USING (user_id = 'OWNER_UUID'::uuid);
```

这只是待 Owner 核验后的策略模板，不是已执行的数据库变更。策略只允许读取固定 owner 的行，
不授予 INSERT/UPDATE/DELETE，也不绕过 RLS。执行前必须验证所有 13 个 story 的 `user_id`
一致；若不一致，不得使用该模板，应按明确的最小故事范围重新设计并审核策略。

策略变更后先重新检查 `pg_policies`、`has_table_privilege`、`rolbypassrls`、
`rolsuper`，再以 `r58_export_reader` 执行小批量 Pilot。不得在权限验证前运行 72 条。

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
