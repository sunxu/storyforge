# R60 Reviewer B 来源绑定审计（Owner-only）

日期：2026-11-06

## 目的与结论边界

本审计只回答一个问题：被选定的 Reviewer B 192 条结果，是否能逐案追溯到实际提供给 B 的盲审输入、Owner 私有 blind-ID 映射，以及冻结 Gold192 原始来源包。

它**不证明** Reviewer B 实际运行在一个全新、未参与 Reviewer A 的 AI 会话中；也不证明执行时没有读取 A 的结果。缺少会话/任务/模型元数据和执行转录时，独立性必须继续保持 HOLD。

审计程序只输出聚合 SAFE，不输出 case_id、blind_case_id、原文、历史或映射内容。

## 已核验的来源固定值

| 来源 | SHA256 |
|---|---|
| Reviewer B 盲审输入包 | `39faf3c5980616b1235b511fec54921fa4f87d0bf3ca7b5b7258c13f969efdb5` |
| Owner-only ID Map | `27bce4d9842768aa5cbb7febd963f5247540d6c5806466647802e9a9a2fc6a30` |
| Reviewer B instructions | `9ba2a6fa9ef08c50f65a8dca2a90277521c65f110fd4ab339309e44c29330254` |
| Gold192 source packet bundle | `ae26a288382939aa79923d4a4c0602b0d575baa63f81c622ab362fbb70d56a5e` |
| Canonical Reviewer B result | `bdd1980eacf9e21c08fb3e5ada482ea476f35c2018c6120e0f708718eda666e8` |

Reviewer B canonical SAFE 将上述结果固定为 192 条：178 PASS / 12 HOLD / 2 REJECT；该结果的结构完整性已验证，但原 SAFE 明确将独立语义复核、case-to-Gold192 绑定和 reviewer independence 标为未验证。

## 本轮原始文件核验结果

对原始文件字节执行 SHA256，并逐条连接 blind ID、target SHA256、Owner map 的原始 case ID/story UUID 与 Gold192 source bundle：

- B 输入包：13 个 story packet / 192 cases。
- Owner ID Map：192 条。
- B canonical result：192 条。
- Gold192 source bundle：13 个 story packet / 192 cases。
- 输入 → Owner map：192/192。
- Owner map → Gold192 source：192/192（原始 case ID、target SHA256、story UUID 三项一致）。
- B result → Owner map：192/192。
- B 输入中未发现原始 case ID、cohort 标签或 Reviewer A 字段。
- B 结果六维评分完整：192/192。
- B 决策分布：178 PASS / 12 HOLD / 2 REJECT。

因此，当前可以把**数据来源与案例身份绑定**判为 VERIFIED。原来的 Crosswalk V2 SAFE 不可覆盖；本程序输出的是独立补充 SAFE。

## 为什么 Reviewer B 独立性仍然 HOLD

Owner 的流程意图是把盲审输入包和说明文件交给一个全新、未参与 Reviewer A 的 AI 会话，并且不提供 ID Map。现有文件可以证明盲审包本身不含 A 结果和 Owner ID，但不能证明实际执行时：

1. 使用了全新的独立会话/agent；
2. 该会话未参与 Reviewer A，也未看到 A 的 SAFE、评分或案例结论；
3. 实际提交的附件和提示词与固定 SHA 的输入完全一致；
4. 最终结果由该次执行直接产生，而不是从其他输出转换、修订或重新导出。

目前没有可验证的独立会话 ID、任务 ID、模型标识、输入/提示词执行回执或完整执行转录。因此：

- `reviewer_b_source_binding_verified = true`
- `reviewer_b_separate_session_execution_provenance_verified = false`
- `reviewer_b_independence_verified = false`
- `quality_v1_admitted = 0`
- 不授权训练、不启动 GPU、不访问 R50。

## 本机执行命令

在 Owner 本机、私有文件仍位于 R58 目录时执行。只输出 SAFE 汇总：

```bash
set -euo pipefail
umask 077

R58="$HOME/.local/share/storyforge/r58"
REPO="$HOME/workspace/storyforge"

python "$REPO/experiments/r58_quality/r60_reviewer_b_scope_binding.py" \
  --reviewer-b-blind-jsonl "$R58/R58_GOLD192_REVIEWER_B_BLIND_20261102.jsonl" \
  --reviewer-b-id-map-json "$R58/R58_GOLD192_REVIEWER_B_ID_MAP_PRIVATE_20261102.json" \
  --reviewer-b-instructions "$R58/R58_GOLD192_REVIEWER_B_INSTRUCTIONS_20261102.md" \
  --gold192-source-jsonl "$R58/private/source_packets/GOLD192_STORY_REVIEW_PACKETS_PRIVATE.jsonl" \
  --reviewer-b-results-json "$R58/private/reviewer_b/R58_GOLD192_REVIEWER_B_RESULTS_20261102.json"
```

不要把 ID Map 上传到 Reviewer B 会话或提交到 GitHub。不要覆盖既有 SAFE。

## 后续最短路径

如果要把 B 升级为独立 AI 复核证据，需要补的是**执行来源证明**，不是重新做一次 192 条映射：

- 在全新、未参与 A 的 AI 会话执行；
- 仅提供固定 SHA 的盲审输入包和 instructions；
- 保留会话/任务标识、模型标识、提交附件 SHA、完整提示词/执行转录和结果 SHA；
- Owner-only 复核该会话没有 A 的材料，再把执行证明与本次 192/192 来源绑定 SAFE 关联。

这一步仍是 AI-only 流程，不要求人工逐案审核。若无法恢复 2026-11-02 的执行证据，就将旧 B 结果保留为“来源绑定已验证、独立性未验证”，不要追认其独立盲审身份。
