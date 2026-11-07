# R60 Canonical Reviewer A V3 证据绑定修复

日期：2026-11-07  
开发分支：r60/canonical-a-v3-binding  
基线：r60/gold72-disagreement-reviewer-c，提交 e21b9f7a72c8df838a6ddc12106245a87ef032c4

## 1. 修复目的

修复 Gold192 / Gold72 Owner evidence pipeline 对旧 Reviewer A SHA 与旧字段
decision_for_strict_ab_pairing 的依赖。新版只接受冻结的 Canonical Reviewer A V3，
并把逐案评分 PASS 与汇总互补 PASS 明确区分。

本修复不修改 Reviewer A/B、Gold192 packets、11 条 exclusions、Gold72 Stage、
现存 Owner Template / AutoLink 私有文件或 Manifest 历史事件。

## 2. 冻结来源

| 来源 | 固定值 |
|---|---|
| Canonical A V3 schema | r58_gold192_reviewer_a_results_v3_reconciled_private_v1 |
| Canonical A V3 status | V3_SOURCES_NORMALIZED__192_IDENTITIES_VERIFIED__EVIDENCE_GRANULARITY_EXPLICIT |
| Canonical A V3 report SHA256 | b0356782963dd3c4f85c210bf0f1c69dc01211d818011c16754ea95e9a4fbdb8 |
| Reviewer B SHA256 | bdd1980eacf9e21c08fb3e5ada482ea476f35c2018c6120e0f708718eda666e8 |
| 11 exclusions SHA256 | 9ca99432e08b680cb67b5a1f89d172a337cb91c9bd02af70b68356938c6c04ed |
| Gold192 packets SHA256 | ae26a288382939aa79923d4a4c0602b0d575baa63f81c622ab362fbb70d56a5e |

A V3 的固定证据粒度：

| 粒度 | 数量 | 严格 A/B 候选资格 |
|---|---:|---|
| CASE_LEVEL_SCORED_REVIEW | 31 | 只有明确 PASS_ONLY 且 B=PASS、未被 exclusions 排除时可进入 |
| AGGREGATE_COMPLEMENT_ONLY | 109 | 不可进入；没有逐案评分和严格比较决定 |
| CASE_ID_IN_EXPLICIT_HOLD_GROUP | 51 | 不可进入 |
| CASE_ID_IN_EXPLICIT_REJECT_GROUP | 1 | 不可进入 |
| 合计 | 192 | — |

候选数由 31 条逐案评分 PASS 与 178 条 B PASS 的实际交集，再扣除 11 条冻结排除记录决定。
不得硬编码为 72，也不得从 109 条汇总互补 PASS 推导逐案审核结论。实际候选数必须由
Owner 私有文件运行时计算；本文件不声称其交集数量。

## 3. 新版工具与旧版隔离

新版工具：

- experiments/r58_quality/r60_gold192_canonical_a_v3.py：A V3 SHA、schema、
  source pins、192 条唯一身份及四类证据粒度的唯一验证器。
- experiments/r58_quality/r60_gold192_supabase_extract_v3.py：Gold192 有界只读来源提取；
  只为明确逐案 A V3 PASS + B PASS 且未排除的案例恢复上下文。
- experiments/r58_quality/r60_owner_evidence_autolink_v3.py：建立 Canonical A V3、
  Reviewer B 与冻结 Packet 的精确定位符；输出仍不是 Owner attestation。
- experiments/r58_quality/gold_quality_review_bind.py：只接受 A V3 SHA、case-level
  scored PASS，并逐条验证 Owner A/B locator 精确指向当前冻结文件及正确记录序号。
- experiments/r58_quality/r60_reviewer_ab_canonical_crosswalk.py：复用同一 A V3
  验证器，避免交叉审计和 Binder 对粒度的解释漂移。

R59 历史工具 r59_gold192_supabase_extract.py 与 r59_owner_evidence_autolink.py
保持原样，旧版测试也保持原样。R59 旧 SHA 的历史产物不得覆盖、删除或重新标记为 A V3 证据。

Owner 之前验收的旧 AutoLink SAFE / JSONL 保留原位，但其 A locator 使用旧 SHA，
不能作为本修复的 Canonical A V3 证据输入。新版必须使用新的输出目录和文件名：

- OWNER_EVIDENCE_AUTOLINK_V3_SAFE.json
- OWNER_CASE_EVIDENCE_AUTOLINKED_V3_PRIVATE.jsonl

## 4. Owner Mac：只读身份预检

先在现有工作树切换到本 PR 分支并确认工作区干净。不要 reset、force push 或覆盖本地未提交内容。

    set -euo pipefail
    umask 077

    REPO="$HOME/workspace/storyforge-r60-ledger-diagnostics"
    PYTHON="$HOME/.venvs/storyforge-r60/bin/python"
    R58_PRIVATE="$HOME/.local/share/storyforge/r58/private"
    R59_PRIVATE="$HOME/.local/share/storyforge/r59/private"

    A_V3="$R58_PRIVATE/quality-v1/reviewer-a-v3-normalization-20261103/R58_GOLD192_REVIEWER_A_RESULTS_V3_RECONCILED.json"
    B="$R58_PRIVATE/R58_GOLD192_REVIEWER_B_RESULTS_20261102.json"
    EX="$R58_PRIVATE/quality-v1/QUALITY_V1_EXCLUDED_CASES.jsonl"
    PACKETS="$R59_PRIVATE/GOLD192_STORY_REVIEW_PACKETS_PRIVATE.jsonl"

    cd "$REPO"
    test "$(git branch --show-current)" = "r60/canonical-a-v3-binding"
    test -f "$A_V3" && test ! -L "$A_V3"
    test -f "$B" && test ! -L "$B"
    test -f "$EX" && test ! -L "$EX"
    test -f "$PACKETS" && test ! -L "$PACKETS"

    "$PYTHON" experiments/r58_quality/r60_gold192_supabase_extract_v3.py \
      --reviewer-a "$A_V3" \
      --reviewer-b "$B" \
      --exclusions "$EX" \
      --source-packets "$PACKETS" \
      --output-dir "$R59_PRIVATE/r60-source-v3-identity-only-not-created" \
      --identity-only

预期 SAFE 必须包含：

- status=GOLD192_REVIEW_IDENTITY_PASS__NO_DB_ACCESS
- gold192=192
- excluded_disagreements=11
- aggregate_complement_passes_eligible=false
- candidate_policy=EXPLICIT_CASE_LEVEL_SCORED_A_V3_PASS_AND_B_PASS_MINUS_11_EXCLUSIONS
- priority_candidates 为运行时实际值，不要求等于 72
- quality_v1_admitted=0、gpu_started=false、private_values_emitted=false

Identity-only 不连接数据库、不写输出目录、不恢复历史、不启动 HF/GPU。

## 5. 有界只读 Supabase Source Extract

仅在 Identity-only PASS 且 Owner 确认输入文件版本后执行。必须使用只读 DSN；
脚本执行 SET TRANSACTION READ ONLY 并显式 ROLLBACK。不要把 DSN/token 放入命令、
聊天、仓库或 CI。

先做 7 条 Pilot，使用全新目录：

    "$PYTHON" experiments/r58_quality/r60_gold192_supabase_extract_v3.py \
      --reviewer-a "$A_V3" --reviewer-b "$B" --exclusions "$EX" \
      --source-packets "$PACKETS" \
      --output-dir "$R59_PRIVATE/r60-source-v3-pilot7" --pilot 7

检查 R60_SOURCE_SAFE.json 的聚合统计和源匹配分类。只有 Owner 审查 Pilot SAFE
后，才可在另一个全新目录运行全部明确逐案候选：

    "$PYTHON" experiments/r58_quality/r60_gold192_supabase_extract_v3.py \
      --reviewer-a "$A_V3" --reviewer-b "$B" --exclusions "$EX" \
      --source-packets "$PACKETS" \
      --output-dir "$R59_PRIVATE/r60-source-v3-all-explicit-case-scored" --pilot 0

--pilot 0 表示全部运行时合格候选，不代表 72 条。不要覆盖既有 R59 或其他 R60
私有输出目录。历史上下文仍需独立 Ledger 恢复与逐案验证；当前故事卡不是历史快照。

## 6. 五条 Strict READY 的新版 AutoLink

旧 AutoLink 产物已存在且不可覆盖。新版 AutoLink 必须使用新输出目录，输入包括：

- 冻结 Gold192 Packets；
- 当前 Strict Stage JSONL；
- Canonical Reviewer A V3；
- Canonical Reviewer B；
- 现存 Owner Template JSONL（程序只读）。

调用：

    "$PYTHON" experiments/r58_quality/r60_owner_evidence_autolink_v3.py \
      --packet-jsonl "$PACKETS" \
      --staged-jsonl "$STAGED" \
      --reviewer-a "$A_V3" \
      --reviewer-b "$B" \
      --owner-template-jsonl "$OWNER_TEMPLATE" \
      --output-dir "$R59_PRIVATE/owner-autolink-canonical-a-v3-20261107"

STAGED 和 OWNER_TEMPLATE 必须由 Owner 从已有私有目录设置为精确文件路径；
不要猜路径、重新生成 Template 或覆盖旧 AutoLink。输出目录必须不存在，父目录必须为
0700；输入文件必须满足程序规定的私有文件权限。

新版 SAFE 只证明实际 READY 案例的 A V3 / B / Packet 精确定位符。
它不会创建 Owner attestation，也不证明来源版本真实性、历史时间、Reviewer 独立性、
世界隔离、保护集完整性或 Quality-v1 准入。

## 7. Binder 的新增硬约束

Binder 现在要求：

1. A 文件字节 SHA 必须等于 Canonical A V3 SHA；
2. A schema/status/source pins 与 192 条身份及四类粒度分布必须完整匹配；
3. 只有 CASE_LEVEL_SCORED_REVIEW、PASS_ONLY、六维评分完整的 A 记录能提供 A scores；
4. 旧字段 decision_for_strict_ab_pairing 不参与判定；
5. Owner A/B evidence refs 必须精确等于当前 A V3 / B SHA 及目标记录序号；
6. 汇总互补 PASS 即使带有旧字段或 PASS 标签，也不能进入 Quality-v1 候选。

旧 SHA、旧 A locator 或错误记录序号均返回 HOLD。Binder 候选状态仍是
REVIEW_EVIDENCE_BOUND__CANDIDATES_NOT_ADMITTED，Quality-v1 admission 保持 0。

## 8. 永久安全边界

- 不修改原始 A/B、11 条 exclusions、Gold192 packets 或 Gold72 staging；
- 不覆盖既有 Owner Template / AutoLink / Source Extract 私有文件；
- 不触碰 R50，不读取 protected test body；
- 不执行数据库 DDL/DML；
- 不自动裁决、不把 AI Reviewer PASS 转为 Owner PASS；
- quality_v1_admitted=0；
- training_authorized=false；
- gpu_started=false；
- r50_accessed=false；
- private_values_emitted=false。

本修复只校正代码和来源绑定，不替代 Owner 对原始 Gold、世界图谱、Reviewer 执行过程、
split、保护集完整性、严重问题及版权证据的实质核验。
