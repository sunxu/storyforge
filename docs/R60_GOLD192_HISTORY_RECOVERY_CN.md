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

输入 SHA256 沿用 `r59_gold192_supabase_extract.py` 中冻结的 A/B/排除/packets pins。冻结 Source Pack 是 13 条故事级 JSONL 记录，适配器通过共享的 `index_packets()` 展开为 192 条 case 身份；不得把最外层行数误认为 case 数。
Locator 文件必须与 SAFE receipt 中的文件 SHA256 一致。目标必须为 `EXACT_MATCH`，
并具有唯一 message/session locator；无法证明身份的案例 HOLD，不采用“唯一根 Session”
作为身份替代证明。连接数据库后，适配器还会通过 `user_stories.author_id` 核验 Gold192
故事的 Owner 元数据：所有故事必须可见且每个故事均有有效 Owner；允许多个 Owner，SAFE
只报告不同 Owner 数量，不输出 UUID。

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

适配器会从 `user_stories.author_id` 读取 Gold192 13 个故事的 owner UUID，并要求全部故事可见、
每个故事均有有效 owner；允许 13 个故事属于多个 Owner。SAFE 仅报告不同 Owner 数量，不输出 UUID。
这项检查只确认 Gold192 来源故事的元数据完整性，不构成 Owner 审批或训练准入。

权限已按全库只读方案执行并验证：
- 六张表均有 `r58_export_reader` 的 `PERMISSIVE SELECT USING (true)` 策略；
- 六张表均可 SELECT，INSERT / UPDATE / DELETE 均不可用；
- `rolsuper=false`、`rolbypassrls=false`；
- RLS 保持开启。

本次 GitHub 更新记录了 Owner 已确认的权限结果；没有由适配器修改数据库权限。

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

## Owner 本机 Pilot8 命令

必须先执行 Source Extract，再执行 Historical Context Recovery。此前 Pilot-7 曾发生
`OperationalError`，没有确认成功的 Source Extract SAFE；不能把旧的 staging locator
或其他来源文件冒充本流程的 `R59_SOURCE_SAFE.json`。本次使用全新的 `r59-source-pilot8`
输出目录，避免覆盖任何既有私有证据。

在 Owner 的 Mac 本机终端执行。先从本机私有凭据管理器设置
`STORYFORGE_SUPABASE_DSN` 环境变量；不要将 DSN/token 放入命令文本、聊天、仓库或 HF Job。
确保当前连接使用只读账号 `r58_export_reader`。脚本会自行执行
`SET TRANSACTION READ ONLY`、statement timeout 和 lock timeout，并在成功后 ROLLBACK。

```bash
set -euo pipefail
umask 077
cd ~/workspace/storyforge

PRIVATE="$HOME/.local/share/storyforge/r58/private"
R59_PRIVATE="$HOME/.local/share/storyforge/r59/private"
SOURCE="$R59_PRIVATE/r59-source-pilot8"
HISTORY="$R59_PRIVATE/gold192-history-pilot8-v1"

# 防止覆盖已有私有证据。
test ! -e "$SOURCE"
test ! -e "$HISTORY"

# 1. Supabase Source Extract：校验冻结输入，读取 Gold192 全部 192 个 locator，
#    并仅为 8 个优先候选导出历史上下文。不会写数据库。
python3 experiments/r58_quality/r59_gold192_supabase_extract.py \
  --reviewer-a "$PRIVATE/R58_GOLD192_REVIEWER_A_RESULTS_20261102.json" \
  --reviewer-b "$PRIVATE/R58_GOLD192_REVIEWER_B_RESULTS_20261102.json" \
  --exclusions "$PRIVATE/quality-v1/QUALITY_V1_EXCLUDED_CASES.jsonl" \
  --source-packets "$R59_PRIVATE/GOLD192_STORY_REVIEW_PACKETS_PRIVATE.jsonl" \
  --output-dir "$SOURCE" \
  --pilot 8

# 2. 先做无数据库身份诊断：只读本地文件，输出聚合 HOLD 原因；
#    即使全部通过也会在连接数据库前退出。
python3 experiments/r58_quality/r59_gold192_history_recovery.py \
  --reviewer-a "$PRIVATE/R58_GOLD192_REVIEWER_A_RESULTS_20261102.json" \
  --reviewer-b "$PRIVATE/R58_GOLD192_REVIEWER_B_RESULTS_20261102.json" \
  --exclusions "$PRIVATE/quality-v1/QUALITY_V1_EXCLUDED_CASES.jsonl" \
  --source-packets "$R59_PRIVATE/GOLD192_STORY_REVIEW_PACKETS_PRIVATE.jsonl" \
  --source-locators "$SOURCE/R59_SOURCE_LOCATORS_192.jsonl" \
  --source-safe "$SOURCE/R59_SOURCE_SAFE.json" \
  --output-dir "$HISTORY" \
  --pilot 8 \
  --diagnose-source-only

# 3. 只有在无数据库诊断 PASS 后，才执行数据库只读历史恢复。
python3 experiments/r58_quality/r59_gold192_history_recovery.py \
  --reviewer-a "$PRIVATE/R58_GOLD192_REVIEWER_A_RESULTS_20261102.json" \
  --reviewer-b "$PRIVATE/R58_GOLD192_REVIEWER_B_RESULTS_20261102.json" \
  --exclusions "$PRIVATE/quality-v1/QUALITY_V1_EXCLUDED_CASES.jsonl" \
  --source-packets "$R59_PRIVATE/GOLD192_STORY_REVIEW_PACKETS_PRIVATE.jsonl" \
  --source-locators "$SOURCE/R59_SOURCE_LOCATORS_192.jsonl" \
  --source-safe "$SOURCE/R59_SOURCE_SAFE.json" \
  --output-dir "$HISTORY" \
  --pilot 8
```

如果正式 Recovery 返回 `LEDGER_SESSION_EVENT_LIMIT_EXCEEDED`，
先运行 `--diagnose-ledger-event-counts`。该模式仅对 Pilot8 已选中的 Session
按 Recovery 完全相同的 story/session/positive-turn 范围执行 `COUNT(*)`，
不读取事件 payload，不恢复历史，不写文件。SAFE 输出每个 Session 对应的 Pilot
安全序号、事件数量、当前上限和是否超限。只有明确得到数量后，才决定是否在
CLI 允许范围内调整 `--max-ledger-events`；不得盲目提高上限或截断事件。

```bash
python3 experiments/r58_quality/r59_gold192_history_recovery.py \
  --reviewer-a "$PRIVATE/R58_GOLD192_REVIEWER_A_RESULTS_20261102.json" \
  --reviewer-b "$PRIVATE/R58_GOLD192_REVIEWER_B_RESULTS_20261102.json" \
  --exclusions "$PRIVATE/quality-v1/QUALITY_V1_EXCLUDED_CASES.jsonl" \
  --source-packets "$R59_PRIVATE/GOLD192_STORY_REVIEW_PACKETS_PRIVATE.jsonl" \
  --source-locators "$SOURCE/R59_SOURCE_LOCATORS_192.jsonl" \
  --source-safe "$SOURCE/R59_SOURCE_SAFE.json" \
  --output-dir "$HISTORY" \
  --pilot 8 \
  --diagnose-ledger-event-counts
```

如果 `--diagnose-source-only` 返回 `SOURCE_MATCH_COUNT_NOT_UNIQUE`，
使用下面的定点诊断。它只允许通过本机 DSN 连接 `r58_export_reader`，
并会在连接后强制检查 `transaction_read_only=on`、`row_security=on`、
`rolsuper=false`、`rolbypassrls=false`。若角色不符合要求，立即拒绝查询。
该模式只读取指定 Pilot 序号对应的一组 story/turn 消息与其 Session parent lineage，
不写文件、不恢复历史、不生成训练候选。

```bash
python3 experiments/r58_quality/r59_gold192_history_recovery.py \
  --reviewer-a "$PRIVATE/R58_GOLD192_REVIEWER_A_RESULTS_20261102.json" \
  --reviewer-b "$PRIVATE/R58_GOLD192_REVIEWER_B_RESULTS_20261102.json" \
  --exclusions "$PRIVATE/quality-v1/QUALITY_V1_EXCLUDED_CASES.jsonl" \
  --source-packets "$R59_PRIVATE/GOLD192_STORY_REVIEW_PACKETS_PRIVATE.jsonl" \
  --source-locators "$SOURCE/R59_SOURCE_LOCATORS_192.jsonl" \
  --source-safe "$SOURCE/R59_SOURCE_SAFE.json" \
  --output-dir "$HISTORY" \
  --pilot 8 \
  --diagnose-duplicate-source-index 4
```

这里只允许使用 Owner 本机私有凭据管理器中的 `STORYFORGE_SUPABASE_DSN`，
不得使用具有 `BYPASSRLS` 的 ChatGPT/管理连接。SAFE 只输出 Pilot 序号、匹配数量、
不同消息/Session 数量、根 Session 数量及 lineage 完整性，不输出任何 ID 或正文。
若结果证明唯一根消息且所有重复匹配均位于该根的后代 Session，可进一步评估
Recovery 采用唯一根消息的方案；本诊断本身不改变准入规则，不能直接放行。

执行后只回传各命令的 SAFE stdout（JSON）。不得回传 DSN、私有 JSONL、
故事正文、消息正文、message/session/story ID 或原始数据库日志。若任一步返回 HOLD，
保留私有本地证据并先诊断 reason code；不得直接扩大到 72 条。

Pilot 成功也不构成 Quality-v1 admission、SFT 编译或训练授权。GPU 不启动。
