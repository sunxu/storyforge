# StoryForge R55 — 第三位独立证据仲裁（Owner 操作协议）

**状态：工具发布与合成测试通过，不等于真实第三轮已完成。** 严禁读取 R50、重新推理、重新训练、晋升 R54 或修改既有冻结物料。

## 1. 何时执行

第二位仲裁者的结果已经通过原工具验证：

- 原始 76 项 × 两类别；第二次复核 68 个候选 × 两类别 = 136 项。
- 前两位对 44 项类别都判 `CONFIRMED`；33 项均判 `REJECTED`；剩余**59 项类别判定**因前后判断分歧或首位 `HOLD`，需要第三方核查。
- 24 个 `hard_fact_or_ban` 初审 `REJECTED` 在二审为 `CONFIRMED`，这一规则分歧尤其应严格引证。
- 以上数字不代表样本总体违规率、确认事件数量或第三方仲裁结果。

脚本从本地 **原始第一轮冻结材料、第二轮冻结材料、两套真实仲裁裁决** 校验并抽取需要第三方核查的候选。同一候选可能涉及两个分歧类别，故第三位 Reviewer 的**实际候选回复数**需以 `safe` 回执为准；针对每个入选候选必须判定两种类别。为保持第三位 Reviewer 盲态，不能只暴露“有分歧的类别”。

## 2. 安装与验证

在 StoryForge 仓库内运行（必须已经有 `v03_r55_gold5_second_evidence_audit.py` 及其依赖）：

```bash
cd ~/workspace/storyforge
python3 -m unittest discover -s tests -p 'test_v03_r55_gold5_third_evidence_audit.py' -v
```

预期 `Ran 20 tests` / `OK`；这是合成测试，不读取私有样本。

## 3. 只读冻结来源，生成全新盲审包

```bash
set -euo pipefail
umask 077
cd ~/workspace/storyforge

ROOT="$HOME/.local/share/storyforge/r55/gold5-dev20"
THIRD="$ROOT/event-evidence-third-v1"

python3 scripts/v03_r55_gold5_third_evidence_audit.py \
  --mode prepare \
  --first-pack "$ROOT/event-arbitration-v1" \
  --first-decisions "$ROOT/completed/arbitration/R55_GOLD5_ARBITER_DECISIONS_COMPLETED_PRIVATE.json" \
  --first-safe "$ROOT/event-arbitration-validated-v1/R55_GOLD5_ARBITRATION_DECISIONS_SAFE_COUNT_ONLY.json" \
  --second-pack "$ROOT/event-evidence-second-v1" \
  --second-decisions "$ROOT/completed/second-evidence/R55_GOLD5_SECOND_AUDIT_DECISIONS_COMPLETED_PRIVATE.json" \
  --second-validated-dir "$ROOT/event-evidence-second-validated-v1" \
  --out-dir "$THIRD"

cat "$THIRD/safe/R55_GOLD5_THIRD_AUDIT_PREP_SAFE_COUNT_ONLY.json"
```

预期成功：`R55_GOLD5_THIRD_AUDIT_PRIVATE_BLIND_PACK_PREPARED__NO_NEW_VERDICTS__NO_R50`。

该程序再次核对第一轮已冻结原始材料、第二轮的完整裁决、私有身份索引、第二轮私有比对和脱敏回执；第二轮已报告的 **59 项待仲裁类别**须全部匹配。任一输入或 SHA 不一致，停止，不得绕过冻结条件。已有输出目录不会覆盖，若失败不得删除原始冻结目录后重试；可另建 `event-evidence-third-v2`。

## 4. 仅发送给第三位独立 Reviewer 的资料

`$THIRD/reviewers/R55_GOLD5_THIRD_AUDIT_BLIND_ITEMS_PRIVATE.json`

`$THIRD/reviewers/R55_GOLD5_THIRD_AUDIT_DECISIONS_BLANK_PRIVATE.json`

另附 `docs/R55_GOLD5_THIRD_AUDIT_REVIEWER_PROTOCOL_CN.md`。

**严禁发送**：`$THIRD/coordinator/`、第一位和第二位的裁决文件、原始匿名编号、模型身份映射、此前的解盲报告、历史评分或入选原因。第三 Reviewer 必须未接触两位仲裁者结论；远程传输故事材料由 Owner 明确授权。

## 5. 复核完成后，完整、只读验证

将完成文件存为：

`$ROOT/completed/third-evidence/R55_GOLD5_THIRD_AUDIT_DECISIONS_COMPLETED_PRIVATE.json`

执行：

```bash
set -euo pipefail
umask 077
cd ~/workspace/storyforge
ROOT="$HOME/.local/share/storyforge/r55/gold5-dev20"

python3 scripts/v03_r55_gold5_third_evidence_audit.py \
  --mode validate \
  --pack "$ROOT/event-evidence-third-v1" \
  --decisions "$ROOT/completed/third-evidence/R55_GOLD5_THIRD_AUDIT_DECISIONS_COMPLETED_PRIVATE.json" \
  --out-dir "$ROOT/event-evidence-third-validated-v1"

cat "$ROOT/event-evidence-third-validated-v1/R55_GOLD5_THIRD_AUDIT_SAFE_COUNT_ONLY.json"
```

预期：`R55_GOLD5_THIRD_AUDIT_VERDICTS_QUOTATIONS_VALIDATED__NO_AUTO_RESOLUTION__NO_R50`。

结果：

- `R55_GOLD5_THIRD_AUDIT_TRIAGE_COMPARISON_PRIVATE.json` 仅 Owner 可读，包含各类别三位仲裁者原始结论和身份映射；严禁公开或提交 Git。
- `R55_GOLD5_THIRD_AUDIT_SAFE_COUNT_ONLY.json` 仅安全聚合、SHA256、脱敏分歧统计和验证限制，可以发给协调分析助手。

脚本只验证引用存在、模板完整、冻结哈希匹配。**不自动采用 2:1 多数表决**，亦不等价于语义审核已经认证；最终实质违规和 hard_fact/ban 的细分，仍需具备故事知识的 Owner 按逐条证据确认。首轮未覆盖的对象不能按此结果计算全面错误率。R54 v0.3-A 的现有 `NO_GO_FOR_PROTECTED_R50_NOW` 不变。
