# R60 双轨训练：Owner 已授权 Session 的私有 Target Pair 提取（第一批）

日期：2026-11-07。状态：`SCOPED_PAIR_EXTRACTOR_CODE_READY__NO_PRIVATE_SOURCE_RUN`。

## 实际只读发现

2026-11-06 UTC 一天的 `chat_latency_metrics` 内，V2 Chat 共 44,180 日志、36,780 条 HTTP 2xx。35,218 条成功日志有单元素 `initial/success` attempt_trace，1,562 条成功日志的 attempt_trace 含多次尝试。此事实不构成最终 Provider 输出与 DB Assistant 的逐案绑定。

按 **V2 Chat 活跃度** 选取的前 12 个 Session，每 Session 最近最多 30 条已完成 Assistant 消息中，当天创建的回复有 152 条。其全部 152 条的前一轮存在同 Session、同 Story、completed User；在此 cohort 内同时无编辑顶层标记、无 parseWarnings 顶层键、正常 finishReason 的**81 条技术优先候选**属于 7 个 Session（7 个 Story ID）。这些 Session 不是 Owner 已认证使用权范围；**不得自动用于训练**。

RolePlay 源码显示 `v2_chat_messages.metadata` 并未在上述样本中保留直观的 Request ID 顶层字段。输出审核与 fallback 发生在 Assistant 正文最终持久化之前；成功 latency 日志在最终持久化之后写入。Session/time 就近 join 不能替代唯一 Request–Target 证据。

## 新增代码：只读且专注 Owner 批准范围

- `experiments/r58_quality/r60_scoped_target_pairs.py`
- `experiments/r58_quality/test_r60_scoped_target_pairs.py`

输入为**Owner Mac 已有的私有审核材料中确认可用于候选调查**的 1–12 个 Story/Session 精确对，每个最多读取该 Session 按轮次倒序最近 80 条消息的**身份、轮次、角色、状态、创建时间**，绝不读取正文或 JSONB。只挑有前一轮 `user/completed` 的 `assistant/completed`，输出 Owner 私有 Candidate Locator JSONL + SAFE 汇总；没有任何训练准入字段被置为 true。

连接角色必须是用户明确指定的 `supabase_read_only_user`，执行 `REPEATABLE READ READ ONLY` 和 5 秒查询超时。此角色具有 BYPASSRLS，因此 **Story/Session scope 必须由 Owner 从已有已授权私有来源明确指定**，不得从全站任意候选生成 scope。此工具不以 `owner_scope_confirmed=true` 或 `r50_protected_scope_excluded=true` 自行证明权益/隔离；它们是范围选择人的声明，需后续独立核实。

## 本机运行（只对真实 Owner 批准的范围）

先同步 PR #25 的 `r60/gold192-history-v3-adapter`，运行合成测试：

```bash
set -euo pipefail
set +x
umask 077
cd "$HOME/workspace/storyforge-r60-ledger-diagnostics"
git fetch origin r60/gold192-history-v3-adapter
git pull --ff-only origin r60/gold192-history-v3-adapter
export PYTHONPATH="$PWD/experiments/r58_quality:$PWD${PYTHONPATH:+:$PYTHONPATH}"
python3 -m pytest -q experiments/r58_quality/test_r60_scoped_target_pairs.py
```

只在 Owner 本机私有目录写入 `R60_SESSION_SCOPE_PRIVATE.json`（权限 0600、所在目录 0700），格式示意如下；**下面的占位 ID 不能直接拿去运行，也不能从 R50 的内容中推导任何范围**：

```json
{
  "schema": "storyforge_r60_private_session_scope_v1",
  "approved_purpose": "PRIVATE_TRAINING_CANDIDATE_REVIEW_ONLY",
  "sessions": [
    {
      "story_id": "OWNER_APPROVED_REAL_STORY_ID",
      "session_id": "OWNER_APPROVED_REAL_SESSION_ID",
      "owner_scope_confirmed": true,
      "r50_protected_scope_excluded": true
    }
  ]
}
```

如果只具备 Gold192 的原始 Story Locator，可以优先从**非 R50 且已核实权利范围**的原库存选择真实 Story/Session 对；不得把冻结 Gold192 的 192 个 Case 身份和新的实验数据集混为一谈。

然后运行：

```bash
test -n "${STORYFORGE_SUPABASE_DSN:-}"
PRIVATE_BASE="$HOME/.local/share/storyforge/r59/private"
SCOPE="$PRIVATE_BASE/<已有受限目录>/R60_SESSION_SCOPE_PRIVATE.json"
OUT="$PRIVATE_BASE/r60-scoped-pairs-$(date -u +%Y%m%dT%H%M%SZ)"
python3 experiments/r58_quality/r60_scoped_target_pairs.py \
  --scope "$SCOPE" --output-dir "$OUT"
```

只回传 `R60_TARGET_PAIR_SAFE.json` 聚合结果；**不上传** `R60_TARGET_PAIR_LOCATORS_PRIVATE.jsonl`。如果无候选、权限错误或未能确认合法范围，明确 HOLD。

## 准入与下一步

本阶段只输出 `DB_COMPLETED_MESSAGE_PAIR_ONLY`：没有读取正文、无法运行文学审核，也未证明实际 System、记忆版本、请求绑定、单次 Provider Completion、作品合法使用权、Protected Set 完整性或世界组件独立。不能将它改写为 `RECONSTRUCTED_NOT_ACTUAL_SENT` 的已审训练样本。

下一轮对经核证的来源限定执行**私有正文提取 + 质量评分**，同时提供三类硬证据：案例级授权/隐私依据、目标为单次合法监督文本的依据、不同世界及保护集历史曝光核证。严格线和重建实验线必须有各自独立的候选/冻结清单和 Validation 世界，不得互相污染。任何缺口保持 HOLD。

`strict_gold_admitted=0`、`experimental_admitted=0`、`training_authorized=false`、`gpu_started=false`。
