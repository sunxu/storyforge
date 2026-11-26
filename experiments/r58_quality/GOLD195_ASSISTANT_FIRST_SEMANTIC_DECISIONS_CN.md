# R58 Assistant-first 跨世界 Pilot10：私人语义裁定模板

先前 SAFE 回执已确认：132 条 Assistant-first 的比较文件通过结构校验，试点选出 10 条、分别来自 10 个世界，尚无人/模型进行内容判断。**不把结构通过当作安全截断的证据。**

## 第一步：创建 10 条独立裁定模板

在 StoryForge R58 Git 仓库根目录：

~~~bash
git pull --ff-only
R58_PRIVATE="$HOME/.local/share/storyforge/r58"

python3 experiments/r58_quality/gold195_assistant_first_semantic_decisions.py \
  --repo-root "$PWD" \
  --private-pilot-tasks "$R58_PRIVATE/gold195-assistant-first-semantic-pilot10-v1.jsonl" \
  --private-blank-decisions-output "$R58_PRIVATE/gold195-assistant-first-semantic-decisions10-v1.jsonl"
~~~

仅新建本地 `0600` 文件。若已存在，不会覆盖；不得把真实故事、审查题、裁定 JSONL 上传 GitHub/公共 CI。只把终端 SAFE 统计发回本对话。

## 第二步：实际审核内容

本地读取 `gold195-assistant-first-semantic-pilot10-v1.jsonl` 的每条原始历史、拟议删首条视图、来源世界卡、当前 User 和冻结 Gold。对应裁定文件每条 JSON 的 `pilot_label` 固定 `pilot01`—`pilot10`，不能改变源哈希。

每条须有真实审阅者独立判断六项：首条 Assistant 的人物/关系、事件/时间、禁令规则、玩家自主历史是否丢失；被丢信息是否在后续历史被明确重述；卡片是否能补足且不泄漏未来设定。填 `judgments` 的 YES / NO / UNCERTAIN，并在 `leading_assistant_exact_quotes` 摘取原文证据，写 `reasoning` 与真实 `reviewer_label`，完成时置 `review_completed=true`。

`policy` 只能选择 `PRESERVE_LEADING_ASSISTANT_IF_RUNTIME_SUPPORTS`、`CONSIDER_DROP_ONLY_AFTER_EXPLICIT_FACT_REVIEW` 或 `HOLD_CONTEXT_UNRECOVERABLE`。若缺证据，保持 `UNREVIEWED` 且 `review_completed=false`。不能为了通过而编造依据。

即便填写“考虑截断”，校验器也要求四类事实损失均为 NO、信息在后文确有补足 YES、卡片充分且无未来泄漏 YES；但这仍**只是记录审阅者判断，程序无法独立证明事实真实**。原始审核题仍保持只读。

## 第三步：本地只读验证

~~~bash
python3 experiments/r58_quality/gold195_assistant_first_semantic_decisions.py \
  --repo-root "$PWD" \
  --private-pilot-tasks "$R58_PRIVATE/gold195-assistant-first-semantic-pilot10-v1.jsonl" \
  --private-filled-decisions-input "$R58_PRIVATE/gold195-assistant-first-semantic-decisions10-v1.jsonl"
~~~

输出仅 SAFE 的状态数量，不输出 case ID、故事文本或证据片段。

**边界：** 这不是 AI 自动审核器，不会自动填写审核决定；不外发给 Grok 或第三方，不解决世界卡认证、Qwen/ms-swift 运行时 Assistant-first 兼容性、CPU collator last_round 掩码或 R50 测试隔离。全部 `history_truncation_approved=false`、`quality_v1_admitted=0`，不启动 HF/GPU。用户未授权扩大 Grok 审查范围。
