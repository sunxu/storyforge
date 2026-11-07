# R60 Owner Mac 单对 G0 + G1 有限授权执行令

状态：`OWNER_G0_G1_AUTHORIZED_ONE_PAIR__R50_AND_TRAINING_HOLD`。适用 Owner 于 2026-11-07 明确授权：对**现有 Owner Locator 三案例所对应的唯一 Story/Session 对**执行 G0 元数据发现及 G1 有限私有内容审核。该授权不证明任何案例的训练使用权、R50 排除、历史 Test 曝光隔离或 Provider 原始请求完整性；不能提升为 SFT 准入。

## 重点变更

此前 R60 入口强制在 Scope 中填写 `r50_protected_scope_excluded=true`，将 G0/G1 候选发现与最终 G2 训练准入混为一谈。现新增 **独立的严格单对 Scope Schema** `storyforge_r60_single_pair_g0_g1_scope_v1`：

- 允许且仅允许一对现有 Story/Session；
- G0/G1 授权以 Owner 本轮明确消息作为唯一明确授权，不代表未知来源 SHA / 训练许可已经通过；
- 强制 `r50_scope_verification=UNKNOWN_HOLD`、`training_rights_verification=UNVERIFIED_HOLD`、`source_version_sha256=null`；
- 强制 `r50_protected_scope_excluded=null`、`training_rights_verified=null`，禁止预填假 PASS；
- 已有 G2 旧 Schema 保留，且仍然要求其严格证据条件，不会由此放宽。

**重要：本代码不在本机自动证明“所填 ID 就是唯一 Owner Locator 对”。Owner Mac Agent 必须在写入任何 Scope 之前，用当前已固定的三条案例 ID / 目标 SHA / 行号 / 证据文件 SHA 重核并锁定一对 Story/Session。不得以随机生产 ID 替代。**

## 执行顺序

1. 同步 `r60/gold192-history-v3-adapter`，保留其他工作区改动，检查 `git status`，执行：
   `python3 -m pytest -q experiments/r58_quality/test_r60_scoped_target_pairs.py`。
2. 从 **已有** 私有 `r60-scope-evidence-20261107T155830Z/R60_SCOPE_CASE_EVIDENCE_PRIVATE.jsonl` 中校验三案与唯一 Story/Session 关系；核对其 SAFE 原件 SHA、行号，不读取 R50 正文；仅按原件确定真实 ID。若仍不确定，停止并报告 `OWNER_LOCATOR_IDENTITY_HOLD`。本轮不再尝试从缺失的 Chat Archive / Backup 获取证据。
3. 创建仅包含这一个真实身份的 `R60_G0_G1_SINGLE_PAIR_SCOPE_PRIVATE.json`（0600，位于 0700 目录）。模板见下方。填写时必须保留所有 UNKNOWN/null 状态。授权引用仅为追踪来源，不能作为案例级训练使用权证明。
4. 验证 `STORYFORGE_SUPABASE_DSN` 对应 `r58_export_reader`，执行新 Scope 下的 `r60_scoped_target_pairs.py`。脚本限定一对、最近最多 80 条消息元数据、5 秒单 SQL 超时、READ ONLY、回滚、不读取正文。若出现角色或 RLS 权限 HOLD，停止，不换用高权限账号。
5. G1 **只针对这一个对与其原有三案**，可先读取 Owner 本机既有已授权的私有 Source Packet / 审核资料，验证目标内容、历史相关段和文档来源。若确实需要从该对的 Supabase 读取有限正文，应通过 Agent 独立写明精确 `story_id+session_id+turn_index` 限制，最多审查 3 个已固定案例、每案例最多必要的一个 User + 一个 Assistant 及有限先前历史；不做整 Session / 全 Story 正文导出。只写 Owner 本机私有报告（0600）。避免打印/上传正文、用户 ID、Case ID、哈希、凭据或私有路径。
6. 如发现授权的 G1 来源包含第三方版权、敏感个人信息或无法确认的真人对话权限，相关内容不作训练候选，记录 HOLD/REJECT；不因本轮 G1 审核授权就认定训练许可。
7. 不用 Session + 相邻时间拼接日志冒充 Request–Response 精确证据；把缺失证据记录为 E2 HOLD。
8. 不读取 R50 正文/题目；未取得已认证完整性与世界组件覆盖的保护集元数据时，继续 `R50_EXCLUSION_UNKNOWN_HOLD`。不能把 `not found` 视为 `excluded`。
9. 最终分别给出 G0 发现与 G1 审核计数、缺口原因和 SAFE。不生成独立 Validation 世界、不标 SFT PASS、不启动 GPU / HF Job。

### Scope 文件内容（ID 仅示意，实际应从已有 Owner Locator 私有证据原件填写）

```json
{
  "schema": "storyforge_r60_single_pair_g0_g1_scope_v1",
  "approved_purpose": "G0_DISCOVERY_G1_LIMITED_PRIVATE_REVIEW",
  "owner_authorization_ref": "OWNER_CHAT_2026-11-07_G0_G1_SINGLE_PAIR",
  "scope_pair_provenance": "R60_OWNER_LOCATOR_THREE_CASES_ONE_PAIR",
  "r50_scope_verification": "UNKNOWN_HOLD",
  "training_rights_verification": "UNVERIFIED_HOLD",
  "source_version_sha256": null,
  "sessions": [
    {
      "story_id": "<仅使用现有 Owner Locator 已固定的实际值>",
      "session_id": "<仅使用同一记录的实际值>",
      "g0_g1_scope_authorized": true,
      "r50_protected_scope_excluded": null,
      "training_rights_verified": null
    }
  ]
}
```

### 安全执行命令

```bash
set -euo pipefail
set +x
umask 077
cd "$HOME/workspace/storyforge-r60-ledger-diagnostics"
git status --short
git fetch origin r60/gold192-history-v3-adapter
git pull --ff-only origin r60/gold192-history-v3-adapter
export PYTHONPATH="$PWD/experiments/r58_quality:$PWD${PYTHONPATH:+:$PYTHONPATH}"
python3 -m pytest -q experiments/r58_quality/test_r60_scoped_target_pairs.py

BASE="$HOME/.local/share/storyforge/r59/private"
SCOPE="$BASE/<已有0700私有目录>/R60_G0_G1_SINGLE_PAIR_SCOPE_PRIVATE.json"
OUT="$BASE/r60-g0-g1-single-$(date -u +%Y%m%dT%H%M%SZ)"
test -f "$SCOPE"
test -n "${STORYFORGE_SUPABASE_DSN:-}"
python3 experiments/r58_quality/r60_scoped_target_pairs.py --scope "$SCOPE" --output-dir "$OUT"
```

**不得照抄占位符执行。** `SCOPE` 由 Agent 在完成原始证据身份校验后安全创建。

## 私有交付物

- `R60_G0_G1_SINGLE_PAIR_SCOPE_PRIVATE.json`：限定一对、附授权追踪字段。
- `R60_TARGET_PAIR_LOCATORS_PRIVATE.jsonl` + `R60_TARGET_PAIR_SAFE.json`：G0 候选定位输出。
- `R60_G1_THREE_CASE_REVIEW_PRIVATE.jsonl`：只针对既有三案的有限来源/监督目标核验、原件引用与未证实项。
- `R60_G0_G1_LIMITED_REVIEW_SAFE.json`：仅聚合的 G0 数量、G1 审核数量和证据缺口。
- `R60_G0_G1_LIMITED_REVIEW_PRIVATE.md`：Owner 本机中文私有审核报告。

所有报告必须分别记录：
`g0_discovery_authorized=true`（仅这一对）、`g1_limited_review_authorized=true`（仅这一对）、`training_rights_verified=false`、`r50_exclusion_verified=false`、`strict_gold_admitted=0`、`experimental_admitted=0`、`gpu_started=false`、`database_modified=false`、`r50_content_accessed=false`。

若因缺少证据、SQL 权限或私有文件而无法完成 G0/G1，仍提供可核验的部分结果和具体 HOLD 原因，不重复生成大范围归档扫描或改变既有冻结材料。
