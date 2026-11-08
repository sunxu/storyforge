# R60-REAL-01 Owner Mac：真实历史 40 Pair 元数据技术预筛执行令

**主线**：`docs/R60_REAL_HISTORY_SFT_MAINLINE_CN.md`（P0：真实生产 User–Assistant 数据）。  
**入口**：`experiments/r58_quality/r60_real_history_metadata_triage.py`。  
**状态**：代码已提交，Owner Mac 真实执行及新 SAFE 待完成。  
**禁止**：修改 RolePlay、数据库写入/权限/RLS、访问 R50 正文、GPU / HF Jobs、向 GitHub/终端输出真实用户文字。

## 输入和范围

本轮只使用 Owner 明确 G0/G1 授权、已有 G0 实际返回 40 对的**唯一 Story/Session**；不自动将此授权扩展至其他 Story 或用户：

- `R60_G0_G1_SINGLE_PAIR_SCOPE_PRIVATE.json`：已创建的单对授权 Scope（schema `storyforge_r60_single_pair_g0_g1_scope_v1`）；
- `R60_TARGET_PAIR_LOCATORS_PRIVATE.jsonl`：原 40 对定位信息；
- `R60_TARGET_PAIR_SAFE.json`：原 G0 SAFE，包含 `scope_sha256`、原对数和未准入状态。

三份文件都必须位于 `~/.local/share/storyforge/r59/private` 下（文件 0600、父目录 0700），禁止改写原件。程序复核 Scope SHA 与 G0 Receipt、严格最多 40 对、1 个 Story/Session、User/Assistant 原始消息 UUID 和确切轮次；任一不一致 fail closed。

## 本轮 SQL 与分类

使用 `STORYFORGE_SUPABASE_DSN` 指向 `r58_export_reader`。数据库必须 `REPEATABLE READ READ ONLY`、`row_security=on` 且角色无 `BYPASSRLS`、无 `SUPERUSER`。每条定点查询以 `(session_id,story_id,turn_index)` 命中已有索引，取得：

- 数据库实际 User/Assistant 的 ID、role、status、相邻轮次；
- Assistant 正文字数（仅长度，不读原文）；
- 前置 User 去空白长度、`continue` 迹象；
- `finishReason`、编辑元数据键、`parseWarnings` 键、metadata 形态。

不得 SELECT `content`、完整 `metadata`、`user_id` 或当前 `v2_data`。此工具输出的 `TECHNICAL_PRIORITY` 仅表示：Assistant >= 300 字、非空且非 continue 的 User、常见正常 finish、无显式编辑键、无 parseWarnings 键，**不是质量 PASS、权益 PASS、单次 Provider PASS**。

其他记录一律 `MANUAL_REVIEW_HOLD`，并列出技术原因。不能因为没有键就认定不存在隐含处理链。采集内容是最终持久化 Assistant，不宣称 Provider 原始字节或当时 System Prompt。

## 运行

```bash
set -euo pipefail
set +x
umask 077
cd "$HOME/workspace/storyforge-r60-ledger-diagnostics"
git status --short
git fetch origin r60/gold192-history-v3-adapter
git pull --ff-only origin r60/gold192-history-v3-adapter
export PYTHONPATH="$PWD/experiments/r58_quality:$PWD${PYTHONPATH:+:$PYTHONPATH}"
python3 -m pytest -q \
 experiments/r58_quality/test_r60_real_history_metadata_triage.py \
 experiments/r58_quality/test_r60_scoped_target_pairs.py

ROOT="$HOME/.local/share/storyforge/r59/private"
# 下面三个变量必须填入**原先真实生成**的私有文件路径，不得使用示例 ID/凭据。
SCOPE="$ROOT/<实际已有目录>/R60_G0_G1_SINGLE_PAIR_SCOPE_PRIVATE.json"
G0_PAIRS="$ROOT/<实际G0输出目录>/R60_TARGET_PAIR_LOCATORS_PRIVATE.jsonl"
G0_SAFE="$ROOT/<实际G0输出目录>/R60_TARGET_PAIR_SAFE.json"
OUT="$ROOT/r60-real-history-triage-$(date -u +%Y%m%dT%H%M%SZ)-$$"

test -f "$SCOPE" && test -f "$G0_PAIRS" && test -f "$G0_SAFE"
test -n "${STORYFORGE_SUPABASE_DSN:-}"
python3 experiments/r58_quality/r60_real_history_metadata_triage.py \
 --scope "$SCOPE" --target-pairs "$G0_PAIRS" --g0-safe "$G0_SAFE" \
 --output-dir "$OUT"
```

不得直接复制 `<...>` 占位符；Owner Agent 仅从已确认的本机执行报告获取实际路径，避免再次进行大范围扫描。如果已有工作区脏改动，先保护而非覆盖。

输出于私有 `OUT`：
- `R60_REAL_HISTORY_TRIAGE_PRIVATE.jsonl`：逐 Pair 技术分类、原因和**尚未准入状态**；
- `R60_REAL_HISTORY_TRIAGE_SAFE.json`：聚合数量、各异常计数、安全断言，不含任何故事/用户/Session/消息 ID、正文或 Case SHA。

### 验收与继续推进

1. 对已授权的原 40 Pair 逐个验证精确身份；数据发生变化或 RLS/权限不足则立即 HOLD，不自动换用 `supabase_read_only_user`、service role 或其他高权限账号。
2. 返回 SAFE 中 `exact_pairs_revalidated`、`technical_priority`、`manual_review_hold` 和原因统计。
3. 根据技术优先次序，从同一已授权对中**先选择最多 5 条**开展私有 G1 真实文本质量审核（六维），并检查前置上下文是否足以支持目标。不一次性导出 40 条正文；若 Agent 判断 G1 现有授权不足以覆盖新五条，应记录 `G1_REVIEW_SCOPE_HOLD`，不得擅自扩范围。
4. 下一步的私有质量审核要对输入/目标引用保持可追溯，记录真实最终交付回复的标签语义；来源/训练权利、完整 R50 排除、世界隔离仍须单独 PASS 才能冻结训练集。
5. 仅回传 SAFE 聚合与无敏感值的缺口说明，禁止提交私有 JSONL。原 Gold192/R50 保持原样。

**本轮不再讨论是否需要重复 GPU smoke test；唯一目标是把真实 40 Pair 转换为可进行私有质量审核的短名单。**
