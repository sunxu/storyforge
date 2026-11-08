# R60：GPU 5+5 Pilot 后的 Owner 私有配对与严重标记校准

日期：2026-11-08。目标：尽快从“GPU 流程正常”转到“真实高质量历史数据可否用于训练”的判断。**本阶段不运行 GPU、不启动 SFT、不改写原始评审结果。**

## 已核验事实

- A：HF Job `6af056bb0e0338d1bb84ac8a`，Qwen3-32B，5/5 v2 私有 Checkpoint，原始判断 5 REJECT。
- B：HF Job `6af060700e0338d1bb84b025`，GLM-4-32B，5/5 v3 私有 Checkpoint，受控一次性引用纠错 1/1 成功，原始判断 5 REJECT。
- 两槽各五条分别随机抽取于不同乱序输入，**直接两两对比 25 组可见历史+目标全文：共同案例为 0**。因此既没有 5/5 逐案一致，也没有 0/5 逐案不一致可统计。
- 10 条均被模型标记 `serious_player_agency=true`，其中至少存在与玩家自主权评分（≥4）或模型文学说明明显冲突的条目。后验逐条风险分层：4 条 `UNSUPPORTED_SEVERE_SUSPECTED`、4 条 `CONTEXTUAL_AMBIGUITY_HOLD`、2 条 `SAFETY_POLICY_HOLD`。这些**只是非盲后验筛查线索**，不属于有效的 Reviewer C、独立判定或 Quality-v1 准入。
- 公开 SAFE 统计仅存于 [R60_HF_PILOT10_POSTHOC_SEVERE_CALIBRATION_SAFE_20261108.json](evidence/R60_HF_PILOT10_POSTHOC_SEVERE_CALIBRATION_SAFE_20261108.json)。私有故事、原文引用、内部盲 ID、Owner 映射不提交 GitHub。

## 审查准则：先分清谁的行为

1. **玩家自主权（serious_player_agency）**：只对模型擅自替玩家决定、持续控制玩家动作/情绪/对话、执行玩家尚未授权的不可逆选择进行证据化判断。NPC 自己的对话、行为、脾气、情绪、威胁、主导剧情甚至身体接触，并不**自动**等同“AI 替玩家作出选择”。涉及不情愿身体接触时，须另外进行安全、同意和交互边界审查，不能因为排除“代理玩家”就自动放行。
2. **可见硬规则与禁令（hard_fact_or_ban）**：必须引用真实可见的硬规则或事实，再展示与目标的确切冲突。未提供世界卡不能推断“没有违规”，也不能自创一条看不见的禁令来 REJECT，应记证据不足 HOLD。
3. **安全排除（safety_exclusion）**：与文学质量、玩家代理权完全独立。性内容、强迫、潜在年龄背景、伤害等按独立政策审查；没有证据不能轻率安全 PASS，亦不能拿“语言亲密”或普通亲密行为自动作硬排除。
4. **严格逐字引用**只验证引文真实存在，不证明引用内容语义能够支持 flag。B v3 修复只选候选索引，不能让 unsupported flag 变得被证实。
5. 六维评分达到门槛而严重 flag=true，或文学理由整体正面而数个严重 flag=true，列为 `FLAG_SCORE_SEMANTIC_CONFLICT_HOLD`，但不能机械改成 PASS。
6. **来源独立性**：A/B 原本共享评价 Prompt，只是换模型；两模型相同错误仍可能由相同标准的歧义造成。只有严格匹配同一来源后的独立、遮蔽原始评价的语义审查，才有逐案共识/分歧意义。

## 已实现的 Owner-only 只读验证器

`src/storyforge_gold_quality/hf_pilot_pairwise_audit.py` （可通过 `python -m storyforge_gold_quality.hf_pilot_pairwise_audit` 运行）：

- 验证 Owner `stage_manifest.private.json` 内部 receipt SHA、`owner_crosswalk.private.json` schema/pool/pins；
- 验证 A/B 完整 1,000 行原始 source 文件字节 SHA，全部映射 blind_id 唯一及所有 `source_index` 完整覆盖；
- 逐 source_index 检查两槽所有 1,000 个真实可见历史+目标一致、case_key 和来源哈希相同，不把文件行号当身份；
- 独立重算 A v2 及 B v3 的 5+5 个 Checkpoint 规范化 `receipt_sha256` 和逐案 `input_sha256`，验证模型 pin、盲 ID、严谨引用、六维分数；
- SAFE 只返回覆盖数、实际重叠个数、matched decision/flags agreement、逐槽各严重标记计数与 `serious_player_agency=true` 同时 player_agency score ≥ 4 的个数。**不输出任何 case_key、source_index、blind_id、引用、正文、文件路径或逐案数据**；
- 输出采用 `O_EXCL` 私有 `0600` 新文件，错误自动 fail-closed，不覆盖历史。

### Owner Mac 单次操作

请在已同步本分支并已安装开发环境的 Mac 上运行；只需要 **CPU 本机读文件和小量 HF Bucket 下载，不需要 GPU Job**。本地 Owner Stage 路径可在既有 `~/.local/share/storyforge` 私有档案中查找 `owner_crosswalk.private.json`，必须与同目录的 `stage_manifest.private.json` 及 `input_A/source.private.jsonl` / B 同根、case count 1,000。**如有多个匹配 Stage 则停止并人工确认，不自动选择。**

~~~bash
set -euo pipefail
set +x
umask 077
REPO="$HOME/workspace/storyforge"
cd "$REPO"
git fetch origin r60/gold192-history-v3-adapter
git switch r60/gold192-history-v3-adapter
git pull --ff-only origin r60/gold192-history-v3-adapter

PYTHONPATH=src python3 -m pytest tests/test_hf_pilot_pairwise_audit.py -q

# 只寻找现有 1000 例 Owner Stage；不要重新生成/重新随机化。
find "$HOME/.local/share/storyforge" -name owner_crosswalk.private.json -type f -print
# 确认后，将下行 STAGE 改为真实 Stage 根：
STAGE="/ABSOLUTE/PATH/TO/FROZEN_STAGE_ROOT"
test -f "$STAGE/owner/owner_crosswalk.private.json"
test -f "$STAGE/owner/stage_manifest.private.json"

OUT="$HOME/.local/share/storyforge/r60/private/hf-pilot10-owner-audit-20261108"
mkdir -p "$OUT/A" "$OUT/B"
chmod 700 "$OUT" "$OUT/A" "$OUT/B"
BUCKET="hf://buckets/adradar/storyforge-training/quality-review/r60/r60-quality-cpu-20261108T082545Z"
for n in 1 2 3 4 5; do
  f="$(printf 'review_%04d.private.json' "$n")"
  hf buckets cp "$BUCKET/gpu-review-output-A-pilot5-v2-01/$f" "$OUT/A/$f"
  hf buckets cp "$BUCKET/gpu-review-output-B-pilot5-v3-01/$f" "$OUT/B/$f"
done
chmod 600 "$OUT"/A/*.json "$OUT"/B/*.json
test ! -e "$OUT/R60_OWNER_PAIRWISE_PILOT10_SAFE.json"
PYTHONPATH=src python3 -m storyforge_gold_quality.hf_pilot_pairwise_audit \
  --stage-root "$STAGE" \
  --review-a-dir "$OUT/A" \
  --review-b-dir "$OUT/B" \
  --safe-output "$OUT/R60_OWNER_PAIRWISE_PILOT10_SAFE.json"
~~~

上面的 `STAGE` 是刻意显式确认的唯一输入，不应根据陌生目录名猜测。在目前 ChatGPT 的 HF 读取权限范围内，没有 Owner Mac 文件系统访问权，所以**尚不能声称 Owner Stage 的 1,000 条映射已经由上述脚本实际验收**；当前仅能证明本次 5×5 文本完全无重叠。此脚本输出交回 ChatGPT 的 SAFE JSON，即可直接评估是否有真正可配对案例。不要上传 `owner_crosswalk.private.json`、`source.private.jsonl` 或私有 Checkpoint 到 GitHub。

## 训练主线下一决策

通过 Owner 身份和摘要检查后，**暂不扩大双 Reviewer 1000 案 GPU**，先对严重标记歧义提出独立 AI 语义评审协议：给第三方审阅者仅看用户最后一句、少量有界历史和目标；不提前提供 A/B 的 `decision`、severity flags 或分数；逐条指出具体的玩家新增动作/选择、可见硬规则引用或安全政策条款，并给证据足不足三态（SUPPORTED / UNSUPPORTED / INSUFFICIENT）。对安全/年龄语境不清的实例 HOLD。首次验证样本采用 A 5 + B 5 的 10 个**互不重叠**案例；在误报门槛得到证实后，才考虑有成本上限的分批评审和早期 Quality-v1 候选准备。正式训练仍须单独授权。
