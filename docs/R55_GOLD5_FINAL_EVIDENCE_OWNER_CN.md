# StoryForge R55 Gold5 — Owner 最终证据裁决（不自动多数表决）

## 状态与边界

这是 **Owner Mac 私有、只读来源**的证据卷宗工具，不是第四位 Reviewer，不需要 GPU，不接触 R50，也不自动晋升任何模型。**必须区分：引用和 JSON 格式校验 PASS ≠ 违规语义真实成立。** 原先 20 道题来自两个已曝光开发集世界，因此结果不可以描述为新独立 Held-out 的无偏模型错误率。

### 为什么是 65 + 87，而不是只处理 59 项？

- 76 个首审选中候选 × 2 类 = **152 类别记录**；同一候选可能在两类都有问题，不等于 152 个独立具体事件。
- **P0 65 项必须逐证据优先复核**：59 项“首审 HOLD 或一二审不同” + 6 项“一、二审都 CONFIRMED，第三人 REJECTED”。
- **P1 87 项**：第三轮三人一致 27 项；两人一致但未抽中第三轮 44 项；只有首审 REJECTED、未参与二审 16 项。P1 也须由 Owner 最终核对；不可默认为自动 PASS。
- 原先的 44 项“前两人确认”并非都在第三轮再次审核，不能把 152 项全部说成经过三位独立仲裁者审核。

## 第一步：应用补丁（补丁仅增加三个文件）

确保旧版 `v03_r55_gold5_third_evidence_audit.py` 及全部依赖**在 Mac 本地存在**。下载补丁后：

```bash
cd ~/workspace/storyforge

git apply --check ~/Downloads/StoryForge_R55_GOLD5_FINAL_EVIDENCE_RESOLUTION_NOJOB_20261026.patch
git apply ~/Downloads/StoryForge_R55_GOLD5_FINAL_EVIDENCE_RESOLUTION_NOJOB_20261026.patch

python3 -m unittest discover -s tests -p 'test_v03_r55_gold5_final_evidence_resolution.py' -v
```

预期 15/15 专用合成测试 PASS；既有全部 Gold5 回归共 176 项 PASS。这里**不运行**你的私有故事材料。

## 第二步：只读校验前 3 轮仲裁，制作 Owner 私有卷宗

```bash
umask 077
cd ~/workspace/storyforge
ROOT="$HOME/.local/share/storyforge/r55/gold5-dev20"
FINAL="$ROOT/final-evidence-v1"

python3 scripts/v03_r55_gold5_final_evidence_resolution.py \
  --mode prepare \
  --first-pack "$ROOT/event-arbitration-v1" \
  --first-decisions "$ROOT/completed/arbitration/R55_GOLD5_ARBITER_DECISIONS_COMPLETED_PRIVATE.json" \
  --first-safe "$ROOT/event-arbitration-validated-v1/R55_GOLD5_ARBITRATION_DECISIONS_SAFE_COUNT_ONLY.json" \
  --second-pack "$ROOT/event-evidence-second-v1" \
  --second-decisions "$ROOT/completed/second-evidence/R55_GOLD5_SECOND_AUDIT_DECISIONS_COMPLETED_PRIVATE.json" \
  --second-validated-dir "$ROOT/event-evidence-second-validated-v1" \
  --third-pack "$ROOT/event-evidence-third-v1" \
  --third-decisions "$ROOT/completed/third-evidence/R55_GOLD5_THIRD_AUDIT_DECISIONS_COMPLETED_PRIVATE.json" \
  --third-validated-dir "$ROOT/event-evidence-third-validated-v1" \
  --out-dir "$FINAL"

cat "$FINAL/safe/R55_GOLD5_FINAL_EVIDENCE_PREP_SAFE_COUNT_ONLY.json"
```

期望 `R55_GOLD5_FINAL_EVIDENCE_OWNER_DOCKET_PREPARED__NO_AUTO_DECISION__NO_R50`，并得到 P0=65，P1=87，合计152。若任一冻结来源/第三轮提交的 PIN SHA256 不符会 **HOLD**；不应为通过验证修改原始 SHA 或既有裁决。

输出：

- `$FINAL/owner/R55_GOLD5_FINAL_EVIDENCE_OWNER_DOCKET_PRIVATE.json`：**私有**！76候选的逐字内容、模型身份、一二三轮结论和原始理由，按 P0 优先呈现；**不得**发送给新的盲审者或提交 GitHub。
- `$FINAL/owner/R55_GOLD5_FINAL_EVIDENCE_DECISIONS_BLANK_PRIVATE.json`：**私有**、包含 76 候选×两类别的空白终裁模板。保留原始空白模板不变，复制到私有 completed 目录后填写。
- `$FINAL/safe/R55_GOLD5_FINAL_EVIDENCE_PREP_SAFE_COUNT_ONLY.json`：脱敏计数及哈希，可发给协调助手。

## 第三步：Owner 按原文完成独立证据核对

每个候选的 `agency` 与 `hard_fact_or_ban` 都要分别裁决，不能照搬“多数票”。填写：

- `final_verdict`：`CONFIRMED` / `REJECTED` / `HOLD_INSUFFICIENT_EVIDENCE`。
- `rationale`：至少24字符，必须解释可见规则如何支持结论；不能仅写“三人中两人赞同”。
- `final_decider_id`：Owner 私有的本次最终裁决人员或审议小组标识，至少3字符。
- `CONFIRMED` 必须有候选和可见上下文两份**逐字引用**：`candidate_quote`、`context_quote`。仅校验引用存在，不能代替语义核验。
- 只有 `hard_fact_or_ban` 判 `CONFIRMED` 时，`issue_subtype` 从 `explicit_banned_phrase`、`hard_fact_mismatch`、`both` 中选择。玩家自主权的 `issue_subtype=not_applicable`。
- `HOLD_INSUFFICIENT_EVIDENCE` 时 `issue_subtype=undetermined`，`evidence_gap` 必须写清仍缺少的证据（不少于16字符），不能硬性确认或驳回。
- `REJECTED` 的 `issue_subtype=not_applicable`，并解释不存在指定违规的原因。

**初步任务**：先填写所有 P0 65 项；P1 87 项可保持空白，按以下命令验证优先任务。为避免误操作，完成版保存在新目录，绝不修改 $FINAL/owner 下的空白模板。

```bash
mkdir -p "$ROOT/completed/final-evidence"
cp -n \
  "$FINAL/owner/R55_GOLD5_FINAL_EVIDENCE_DECISIONS_BLANK_PRIVATE.json" \
  "$ROOT/completed/final-evidence/R55_GOLD5_FINAL_EVIDENCE_DECISIONS_WORKING_PRIVATE.json"
# 使用本地私有编辑器填写 WORKING_PRIVATE.json 的 P0 两个类别。
```

**P0 格式和原文引用校验**：

```bash
python3 scripts/v03_r55_gold5_final_evidence_resolution.py \
  --mode validate-priority \
  --pack "$FINAL" \
  --decisions "$ROOT/completed/final-evidence/R55_GOLD5_FINAL_EVIDENCE_DECISIONS_WORKING_PRIVATE.json" \
  --out-dir "$ROOT/final-evidence-priority-verified-v1"

cat "$ROOT/final-evidence-priority-verified-v1/R55_GOLD5_FINAL_EVIDENCE_SAFE_COUNT_ONLY.json"
```

期望 `R55_GOLD5_FINAL_EVIDENCE_PRIORITY_65_FORMAT_VERIFIED__NOT_FINAL__NO_R50`。**不要把 P0 PASS 说成全体 152 项终裁 PASS**。

## 第四步：P1 87 项补充核对，完整归档

核对三轮一致 27、双人一致但第三轮未审 44、仅一审 16，共 P1=87。填齐全部152项后执行：

```bash
python3 scripts/v03_r55_gold5_final_evidence_resolution.py \
  --mode validate-all \
  --pack "$FINAL" \
  --decisions "$ROOT/completed/final-evidence/R55_GOLD5_FINAL_EVIDENCE_DECISIONS_WORKING_PRIVATE.json" \
  --out-dir "$ROOT/final-evidence-all-verified-v1"

cat "$ROOT/final-evidence-all-verified-v1/R55_GOLD5_FINAL_EVIDENCE_SAFE_COUNT_ONLY.json"
```

期望 `R55_GOLD5_FINAL_EVIDENCE_ALL_152_FORMAT_VERIFIED__NOT_SEMANTIC_CERTIFIED__NO_R50`。如果仍有 HOLD，脱敏回执会保留未解决数。计数分母仅限**原始被标记的76个候选、20道旧开发题**；未经复核的24个原始未标记候选不能假定0错误。一次“类别成立”也不等于一个唯一具体事件。

## GitHub 与隐私

只提交三个新增脚本/测试/指南，及手工脱敏的计数结论。绝对不提交任何 `$ROOT`、`completed/`、`owner/`、候选回复、Reviewer 原文证据、映射、私有 SHA-到具体故事索引、HF/GitHub 凭证。这个工具本身**不会提交 Git、发起 HF 任务或动 R50**。R54 v0.3-A 保持 NO-GO，R46 v0.2 仍为开发基线。
