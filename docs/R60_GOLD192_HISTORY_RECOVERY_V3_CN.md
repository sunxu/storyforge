# R60 Gold192 Canonical A V3 Ledger 历史恢复适配器

日期：2026-11-07  
分支：`r60/gold192-history-v3-adapter`  
性质：只读 Supabase 历史恢复；不做 Quality-v1 admission，不编译 SFT，不启动 GPU。

## 1. 本轮诊断后的决策

- 排除 89 条未完成空白历史消息的反事实投影，仍有 4/7 Case 存在角色重复；不得改写或删除原始历史。
- Gold192 locator 的精确匹配分布为 180×1、8×2、2×3、2×4，共 192 个 Case、210 条精确匹配记录、12 个多重匹配 Case、18 条额外匹配记录。
- 多重匹配不能凭 SHA256 或任意根 Session 直接准入。恢复适配器会重新查询数据库，要求精确匹配数量不漂移、消息 ID 不重复、Session lineage 完整且无环、唯一根与冻结 locator 的 message/session 完全一致。
- V3 Source Extract 的 `IDENTITY_AMBIGUOUS` locator 保持 HOLD；不会用根节点猜测来补齐缺失 locator。
- 本适配器目前只输出 `FULL_HISTORY_RECOVERED`；`VERIFIED_WINDOW_RECOVERED` 尚未实现，不能伪装成支持。

## 2. 输入

本工具消费同一次 R60 V3 Source Extract 运行的：

- Canonical Reviewer A V3；
- Reviewer B；
- 11 条冻结 exclusions；
- 冻结 Gold192 source packets；
- `R60_SOURCE_LOCATORS_192.jsonl`；
- 对应 `R60_SOURCE_SAFE.json`。

Reviewer A/B、exclusions、packets 继续使用 V3 源码中冻结的 SHA256。Locator 必须与 SAFE receipt 中的记录数和 SHA256 一致。Locator 与 SAFE 必须来自同一输出目录。

所有私有输入必须为普通文件、0600、单硬链接，直接父目录为 0700。输出目录必须不存在，且父目录为 0700。不得把私有 JSONL、故事正文、消息正文、ID 或 DSN 发到聊天或 GitHub。

## 2.1 固定 Worktree 与分支切换

Owner 已有的 R60 工作目录是：

`$HOME/workspace/storyforge-r60-ledger-diagnostics`

不要改用 `$HOME/workspace/storyforge`，也不要重新克隆仓库。先在原工作目录检查工作区干净，然后 fetch 并验证 PR 分支确实是原始 R60 基线的后代：

```bash
cd "$HOME/workspace/storyforge-r60-ledger-diagnostics"
test -z "$(git status --porcelain)"
git fetch origin r60/gold192-history-v3-adapter
git merge-base --is-ancestor \
  c071784b135c934bfe29537761300c14aa2cd818 \
  origin/r60/gold192-history-v3-adapter
```

确认上述命令成功后，在同一目录切换到 PR 分支：

```bash
git switch --track -c r60/gold192-history-v3-adapter \
  origin/r60/gold192-history-v3-adapter
git status --short --branch
git rev-parse HEAD
```

如果本地分支已经存在，不要重复创建；先检查其 upstream 和工作区状态，再使用 `git switch` 与 `git pull --ff-only`。不得强制重置或覆盖未提交工作。

## 3. CPU-only 检查

在仓库根目录执行：

```bash
python3 -m pip install -e ".[dev]"
ruff check \
  experiments/r58_quality/r60_gold192_history_recovery_v3.py \
  experiments/r58_quality/test_r60_gold192_history_recovery_v3.py
pytest -q \
  experiments/r58_quality/test_r60_gold192_history_recovery_v3.py \
  tests/test_message_ledger.py \
  tests/test_history_recovery.py
```

这些测试不需要 DSN，不连接 Supabase，不访问私有 Gold 文件，不启动 HF/GPU。

## 4. Owner 本机运行顺序

先确认下面的 `SOURCE` 指向已成功生成 R60 V3 三个私有 artifact 和 SAFE receipt 的目录。若实际目录名不同，只修改这一行。不要使用 identity-only 输出目录。

```bash
set -euo pipefail
umask 077
cd "$HOME/workspace/storyforge-r60-ledger-diagnostics"

PRIVATE="$HOME/.local/share/storyforge/r58/private"
R59_PRIVATE="$HOME/.local/share/storyforge/r59/private"
SOURCE="$R59_PRIVATE/r60-source-v3-pilot7-verified-20261107"
HISTORY="$R59_PRIVATE/r60-history-v3-pilot7-20261107"

A="$PRIVATE/quality-v1/reviewer-a-v3-normalization-20261103/R58_GOLD192_REVIEWER_A_RESULTS_V3_RECONCILED.json"
B="$PRIVATE/R58_GOLD192_REVIEWER_B_RESULTS_20261102.json"
EX="$R59_PRIVATE/quality-v1/QUALITY_V1_EXCLUDED_CASES.jsonl"
PACKETS="$R59_PRIVATE/GOLD192_STORY_REVIEW_PACKETS_PRIVATE.jsonl"
LOCATORS="$SOURCE/R60_SOURCE_LOCATORS_192.jsonl"
SOURCE_SAFE="$SOURCE/R60_SOURCE_SAFE.json"

# 1. 本地 source identity preflight，不连接数据库。
python3 experiments/r58_quality/r60_gold192_history_recovery_v3.py \
  --reviewer-a "$A" \
  --reviewer-b "$B" \
  --exclusions "$EX" \
  --source-packets "$PACKETS" \
  --source-locators "$LOCATORS" \
  --source-safe "$SOURCE_SAFE" \
  --pilot 7 \
  --diagnose-source-only

# 2. 只读数据库事件计数；会重新验证 Pilot 内多重匹配的唯一根身份。
#    不读取 Ledger payload、不恢复历史、不写文件。
python3 experiments/r58_quality/r60_gold192_history_recovery_v3.py \
  --reviewer-a "$A" \
  --reviewer-b "$B" \
  --exclusions "$EX" \
  --source-packets "$PACKETS" \
  --source-locators "$LOCATORS" \
  --source-safe "$SOURCE_SAFE" \
  --pilot 7 \
  --diagnose-ledger-event-counts

# 3. 仅当上一步所有 Session 均在 100000 默认上限内，执行完整历史恢复。
#    如超限，先按 SAFE 中实际计数设置有限的 --max-ledger-events；
#    上限不得超过 1000000，不得截断 Ledger 事件。
test ! -e "$HISTORY"
python3 experiments/r58_quality/r60_gold192_history_recovery_v3.py \
  --reviewer-a "$A" \
  --reviewer-b "$B" \
  --exclusions "$EX" \
  --source-packets "$PACKETS" \
  --source-locators "$LOCATORS" \
  --source-safe "$SOURCE_SAFE" \
  --output-dir "$HISTORY" \
  --pilot 7 \
  --max-ledger-events 100000
```

### 数据库连接要求

从本机私有凭据管理器设置 `STORYFORGE_SUPABASE_DSN`。只允许 `r58_export_reader`。脚本会验证：

- 当前角色严格为 `r58_export_reader`；
- `transaction_read_only=on`；
- `row_security=on`；
- `rolsuper=false`；
- `rolbypassrls=false`；
- `statement_timeout=90000ms`；
- `lock_timeout=1000ms`；
- 每次运行使用 `REPEATABLE READ, READ ONLY`，结束显式 ROLLBACK。

## 5. 输出与边界

完整恢复输出在 Owner 本机私有目录：

- `R60_HISTORY_CONTEXT_PRIVATE.jsonl`：恢复后的历史、目标元数据及冻结目标文本；
- `R60_HISTORY_HOLDS_PRIVATE.jsonl`：逐案 HOLD 原因；
- `R60_HISTORY_SAFE.json`：只含聚合统计、原因分布、性能统计及安全状态。

SAFE stdout 可以回传聊天。不要回传任何私有 JSONL 或数据库日志。

以下字段必须继续保持：

- `quality_v1_admitted=0`
- `training_authorized=false`
- `gpu_started=false`
- `database_modified=false`
- `private_values_emitted=false`
- `ledger_commit_order_verified=false`
- `ledger_trigger_continuity_verified=false`
- `historical_system_prompt_verified=false`

历史恢复 PASS 仅表示机械历史证据通过，不代表 Reviewer 决定、Owner 审批、Quality-v1 准入或训练授权。R50 不访问。
