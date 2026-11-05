# R58 Gold195：保留 Assistant-first 的质量审核试点（13 个来源 UUID）

日期：2026-11-01。状态：**工具完成，合成测试通过；真实双审未执行；训练准入 0。**

## 为什么不再删除首条 Assistant

R58 已在 HF CPU 环境以 Qwen3.8-27B、ms-swift 4.5.3、transformers 5.16.1、`last_round`，对 132/132 条 Assistant-first 冻结历史完成真实 Loss Mask 和 Data Collator 校验；完整历史可编码且历史监督 0 token。原 Gold195 和冻结目标不更改。

旧的 `quality_v1.py`、`gold195_card_first.py`、`gold195_six_dimension_review_tasks.py` 曾把 Assistant-first 当作不兼容：本轮全部修正为允许原样历史并保留严格的交替角色、来源哈希、离线卡快照审查、双审与世界隔离要求。

## 小批量质量审核（先 13 条，不直接审核 195 条）

在 Owner Mac 的 R58 分支，使用已经存在的私人卡片快照候选（**只有候选资格，非可信训练 System**）：

```bash
git switch r58/roleplay-sft-skill-v01
git pull --ff-only

PRIVATE="$HOME/storyforge-review-private"
test -f "$PRIVATE/gold195-card-snapshots-v1.json" || {
  echo '私人卡片快照候选缺失；保持 HOLD' >&2
  exit 42
}
```

先准备 195 条原始 Gold + 原始来源卡片的 PRIVATE 语义审阅数据（如果目标文件已经存在且是本流程生成的版本，保持原样，不覆盖）：

```bash
python3 experiments/r58_quality/gold195_card_gold_review.py \
  --repo-root "$PWD" \
  --private-card-candidates "$PRIVATE/gold195-card-snapshots-v1.json" \
  --private-review-output "$PRIVATE/gold195-card-gold-review-v1.jsonl"
```

然后生成 13 个**来源故事 UUID 各一条**、两位审阅者独立盲号/独立顺序的材料：

```bash
python3 experiments/r58_quality/r58_gold195_blind_quality_pilot13.py \
  --repo-root "$PWD" \
  --private-card-gold-review "$PRIVATE/gold195-card-gold-review-v1.jsonl" \
  --private-output-dir "$PRIVATE/r58-quality-pilot13-$(date -u +%Y%m%dT%H%M%SZ)"
```

所有输出在 Git checkout 外的 0700 目录，PRIVATE 文件 0600；若目标存在即拒绝覆盖。**不要上传两套盲审输入、故事正文、世界卡、Owner crosswalk 到 GitHub 或公开渠道**。未来使用受控的不同 AI 审阅者审核时，A/B 之间不得传递判断、来源身份、既往模型结论。Owner 保存 crosswalk，用于回收审核结果和核对来源。

每份材料必须对中文文笔、人物一致性、NPC 推进、玩家自主、硬规则、剧情连续性独立给出 1–5 分，严重玩家越权/硬事实违例/安全排除显式标注，引用可见原文，确定不了即 HOLD。导出时卡片快照只是供审核的**候选离线设计**，不等于目标时刻的历史 System，也不自动有权进入模型训练。

该 13 条试点按**来源故事 UUID**分层，不代表已经验证 13 个世界在语义上相互独立；R50 和其他密封测试世界的隔离属于后续正式准入条件，不访问其正文。

## 结果合同与下一阶段

正常 SAFE 回执应为：

- `source_rows_checked=195`、`pilot_cases=13`、`reviewer_packets=2`、每位审阅者 13 条；
- `reviewer_decisions_fabricated=false`、`source_cards_semantically_approved=false`；
- `quality_v1_admitted=0`、`training_authorized=false`。

私有目录包含 `reviewer_A.private.jsonl`、`reviewer_B.private.jsonl` 和 `owner_crosswalk.private.json`。新审核的 JSON 不得直接覆盖源 Gold195，也不能将旧五维评分直接填为新六维。完成两份独立审核、世界卡语义校验以及世界级 Train/Validation/R50 隔离之前不进入正式训练。

本轮不进行 HTTP 请求精确回放，不重复 Assistant-first GPU 审核，不创建 GPU Job。


## HOLD 分类诊断（2026-11-01）

旧版 `GOLD195_PILOT13_PRIVATE_SOURCE_OR_OUTPUT_INVALID__HOLD` 将不同错误折叠为一个状态。
现在先更新分支，并在**原命令追加 `--diagnose-only`**。它只读源输入、校验权限与审核任务结构，并输出固定原因代码；**不创建目录、不打印私人文本或身份**。

```bash
git pull --ff-only
PRIVATE="$HOME/storyforge-review-private"
python3 experiments/r58_quality/r58_gold195_blind_quality_pilot13.py \
  --repo-root "$PWD" \
  --private-card-gold-review "$PRIVATE/gold195-card-gold-review-v1.jsonl" \
  --private-output-dir "$PRIVATE/r58-quality-pilot13-$(date -u +%Y%m%dT%H%M%SZ)" \
  --diagnose-only
```

`reason_code=READY` 表示可以去掉 `--diagnose-only`、用**新的**目录路径正式生成包；`PRIVATE_INPUT_NOT_FOUND_OR_PATH_INVALID` 检查第一步审核包是否创建；`PRIVATE_INPUT_PERMISSIONS_INVALID` 检查文件 0600；`OUTPUT_PARENT_NOT_PRIVATE_0700` 检查输出父目录 0700；`OUTPUT_ALREADY_EXISTS` 使用全新的目录名（不要覆盖旧结果）；`REVIEW_TASKS_INCOMPLETE` 检查 `review_tasks_prepared`、`history_shape_hold`；`WORLD_COUNT_NOT_13` 需要检查来源故事 ID 绑定，不能编造或强行凑数；`PRIVATE_SOURCE_SCHEMA_OR_CARD_HASH_INVALID` 需要重新检查私有来源的构造与卡片哈希，而不是跳过验证。只共享 SAFE 回执。


## A/B AI 审核结果回收及验证（2026-11-01）

当 `GOLD195_BLIND_PILOT13_PREPARED__REVIEWS_NOT_PERFORMED` 返回成功时，**勿重新运行准备命令**。保留已经生成的试点目录，里面应包含：

- `reviewer_A.private.jsonl`：仅交给评审 A
- `reviewer_B.private.jsonl`：仅交给评审 B
- `owner_crosswalk.private.json`：只由 Owner 保存，严禁交给评审 A/B

使用两个独立 AI 对话或隔离的评审执行环境，各自独立阅读 13 条，**不共享评分、结论、身份对应表或另一份盲审包**。每位评审保留原始 JSONL 除 `response` 以外所有字段，在新文件 `reviewer_A.completed.private.jsonl` / `reviewer_B.completed.private.jsonl` 中填写本人的 `response`：`decision` 为 `PASS`、`HOLD` 或 `REJECT`，六维 `scores` 为 1–5；三项 `severe_flags` 明确标记；卡片是否适用、与历史冲突分别给出判断；`specific_source_quotes` 必须来自实际历史 User/Assistant 消息（不能只来自未批准的 System 卡），`specific_target_quotes` 必须来自目标回复；给出文学质量理由与不确定性。来源不充分时允许 HOLD，不得编造证据。

**A/B 的完成文件必须分开保存，不要覆盖原始文件。** Owner 仅在两个评审全部冻结后用以下命令验证：

```bash
RUN_DIR="/ABSOLUTE/PATH/TO/EXISTING/r58-quality-pilot13-YYYYMMDDTHHMMSSZ"
python3 experiments/r58_quality/r58_gold195_pilot13_dual_review_validate.py \
  --reviewer-a-source "$RUN_DIR/reviewer_A.private.jsonl" \
  --reviewer-a-completed "$RUN_DIR/reviewer_A.completed.private.jsonl" \
  --reviewer-b-source "$RUN_DIR/reviewer_B.private.jsonl" \
  --reviewer-b-completed "$RUN_DIR/reviewer_B.completed.private.jsonl" \
  --owner-crosswalk "$RUN_DIR/owner_crosswalk.private.json"
```

要求 PRIVATE 完成文件为 0600 普通文件，不能是符号链接，不得上传到 GitHub。验证器检查 13/13 完整性、盲号交叉绑定、源记录未被改写、可见历史与目标逐字引用、评分范围、严重问题标记及 PASS 六维最低门槛，仅输出 SAFE 聚合计数与分歧总数。两位评审的独立性和审阅内容真伪**无法仅由脚本证明**。

验证器始终返回 `quality_v1_admitted=0`、`training_authorized=false`；即使 13/13 双方均 PASS，也仍需卡片语义可信度、Protected/R50 世界隔离、Owner 最终确认和正式数据集冻结，才可考虑 SFT。
