# StoryForge R55 Gold5 v2 — 76 项仲裁的独立二次证据复核（Owner）

**状态：仅代码与合成回归验证完成；必须在 Owner Mac 运行真实源文件。** 该工具只对已暴露的 R55 开发集与冻结的第一次仲裁做只读验证，**不访问 R50、不执行 GPU 推理、不训练、不改变已冻结判定，也不自动晋升模型**。

## 为什么需要此流程

首轮审查 76 个候选×2 类 = 152 项类别裁决；Owner 回执列出 57 `CONFIRMED`、22 `HOLD_INSUFFICIENT_EVIDENCE`、73 `REJECTED`。原校验器证明裁决格式、引用的字面存在，不证明真实违反了规则；Reviewer 独立性也未经技术认证。第二位仲裁者必须重新阅读冻结规则、历史、用户输入、候选回复，不能看首位仲裁者的结论或模型身份。

### 提前固定的抽样协议

- **全收**：第一次 `CONFIRMED` 或 `HOLD_INSUFFICIENT_EVIDENCE` 涉及的所有候选。
- **驳回质控**：按内部 `source_arm_private × category` 的每个组，对第一次 `REJECTED` 使用确定性 SHA256 排序，选择 `ceil(该组驳回数 / 5)`，即各组至少约 20%；其随机样本由被冻结的首次决定 SHA256 派生，Owner 不凭个人喜好挑选。
- **审查粒度**：按 *候选回复* 汇总去重。每个入选候选，无论之前哪个类别被标记，第二位仲裁者必须独立审核 **两个类别**。因此第二轮的类别判定数由生成包后的回执给出，**不保证恰好 79+样本数**。
- **盲态**：新随机化匿名 token、打乱候选顺序，不带首次裁决、原 Reviewer 意见、模型标签、原始仲裁 token 或抽样原因。Owner 的源模型、首次结果、分层抽样原因仅存在 `coordinator/`。
- **解释限制**：即使两位仲裁者均标记 `CONFIRMED`，也只是两个独立判断的*一致类别裁决*，不能自动宣称某模型出现几次独立严重错误事件。由于来自既有旧开发题且是筛选样本，不得报告成无偏模型错误率。

## 1. 安装 Git 补丁与纯合成测试

将下载的补丁保存到 `~/Downloads/StoryForge_R55_GOLD5_SECOND_EVIDENCE_AUDIT_NOJOB_20261023.patch`。

```bash
cd ~/workspace/storyforge

git apply --check \
  ~/Downloads/StoryForge_R55_GOLD5_SECOND_EVIDENCE_AUDIT_NOJOB_20261023.patch

git apply \
  ~/Downloads/StoryForge_R55_GOLD5_SECOND_EVIDENCE_AUDIT_NOJOB_20261023.patch

python3 -m unittest discover \
  -s tests -p 'test_v03_r55_gold5_second_evidence_audit.py' -v
```

提交时只 `git add` 新增的脚本、测试和两份指南，**不要** `git add .` 把私有 JSON 或身份映射带进仓库。

## 2. 在 Mac 本地验证首轮原件并制作第二轮私有盲包

```bash
set -euo pipefail
umask 077
cd ~/workspace/storyforge

ROOT="$HOME/.local/share/storyforge/r55/gold5-dev20"
FIRST="$ROOT/event-arbitration-v1"
SECOND="$ROOT/event-evidence-second-v1"

python3 scripts/v03_r55_gold5_second_evidence_audit.py \
  --mode prepare \
  --pack "$FIRST" \
  --first-decisions "$ROOT/completed/arbitration/R55_GOLD5_ARBITER_DECISIONS_COMPLETED_PRIVATE.json" \
  --first-safe "$ROOT/event-arbitration-validated-v1/R55_GOLD5_ARBITRATION_DECISIONS_SAFE_COUNT_ONLY.json" \
  --out-dir "$SECOND"

cat "$SECOND/safe/R55_GOLD5_SECOND_AUDIT_PREP_SAFE_COUNT_ONLY.json"
```

成功状态应是：
`R55_GOLD5_SECOND_AUDIT_BLIND_PACK_PREPARED__NO_NEW_JUDGMENTS__NO_R50`

程序会拒绝首轮原始盲包、首轮协调员私有索引、首轮已填写决策 SHA256 与此前 Owner 回执不符的输入。固定原文锚点：`b97e743ba3901561dc5745f9f50a47e52d1199c7c60f106ad9d011604c741f65`；索引 `3b0400a5629b6673c2317248f061b63e1a30c26d6486da81f7eb0636d7638e9a`；首次决策 `ee573b1d86d5ad2c8e807f69306006addc86d968ad85e1918d524de0d9b7d621`。真实私有 SHA 不应在新 Reviewer 会话里展示。

**新目录不能已经存在，也不能在 Git 仓库内。** 如果拒绝，不要擅自改动旧决定或锚定 SHA；排查真实路径与输入原件。

## 3. 对新独立仲裁者仅发送三个东西

1. `$SECOND/reviewers/R55_GOLD5_SECOND_AUDIT_BLIND_ITEMS_PRIVATE.json` — 匿名候选、原始规则和上下文。
2. `$SECOND/reviewers/R55_GOLD5_SECOND_AUDIT_DECISIONS_BLANK_PRIVATE.json` — 仅需要填写的第二轮判定模板。
3. `docs/R55_GOLD5_SECOND_AUDIT_REVIEWER_PROTOCOL_CN.md` — 不包含首审答案的中立说明。

**禁止发送** `$SECOND/coordinator/`、首次仲裁者的已完成 JSON、首次裁决统计、任何模型身份映射、任何以前的评分或模型胜负信息；第二次审核应由没有见过第一次裁决的独立人员/会话完成。若使用远端 AI，Owner 需独立决定授权私有小说数据外传。

## 4. 回收第二次判定并校验/生成差异表

保存成 `$ROOT/completed/second-evidence/R55_GOLD5_SECOND_AUDIT_DECISIONS_COMPLETED_PRIVATE.json`，不要覆盖空白模板。

```bash
RESULT2="$ROOT/event-evidence-second-validated-v1"
python3 scripts/v03_r55_gold5_second_evidence_audit.py \
  --mode validate \
  --pack "$SECOND" \
  --decisions "$ROOT/completed/second-evidence/R55_GOLD5_SECOND_AUDIT_DECISIONS_COMPLETED_PRIVATE.json" \
  --out-dir "$RESULT2"

cat "$RESULT2/R55_GOLD5_SECOND_AUDIT_SAFE_COUNT_ONLY.json"
```

成功状态：`R55_GOLD5_SECOND_AUDIT_VERDICTS_VALIDATED__NO_AUTO_PROMOTION__NO_R50`。

- `R55_GOLD5_SECOND_AUDIT_SAFE_COUNT_ONLY.json`：只有计数、SHA、各模型类别统计、首次/二次结论变化，不含原文与个案 ID；可以发回 Owner 主会话继续分析。
- `R55_GOLD5_SECOND_AUDIT_COMPARISON_PRIVATE.json`：含两位仲裁者结果关联、匿名 token 和模型身份，**只在 Owner 私有目录查看**；不得送第二位仲裁者或提交 Git。
- 首审 `HOLD` 即便二审做出了裁决，也需保留原有证据不充分事实；任何不一致或涉及 `HOLD` 的类别均进入第三方/补证待定清单。**不得自动覆盖首次裁决**。

## 5. 复核结束后的质量门禁

聚合统计必须分别报告 (a) 57 项首轮成立的二次确认比例，(b) 22 项 HOLD 的证据去向，(c) 73 项 REJECTED 中被抽到的质控样本、出现多少初审漏判。(d) 逐模型、逐题+候选+类别的去重情况。未复核的 REJECTED 属于未二审，不能报告为两位裁决一致。若需要正式确认严重“事件数”，下一步再由第三位独立仲裁者从原文构建 *distinct event* 清单。

**本轮仍只有 20 道旧开发题、2 个历史世界。R54 v0.3-A 原 NO-GO、R50 保护边界继续有效。**
