# R58 — Assistant-first 全量 132 条离线语义审核任务

## 范围和边界

Owner 明确要求从先前的 10 条试点扩大到 **132/132** 条 Assistant-first 历史。此前私人比较文件已经验证 132/132 的角色形状：删除历史的第一条 Assistant 后，余下历史以 User 开始并保持交替，但这**不是语义批准**。本轮仅扩大**本地审核任务覆盖范围**，不扩大向 Grok 等外部服务发送故事正文的授权，不启动 HF/GPU，不改 Gold 目标或任何冻结来源。

旧有 10 条试点、裁定模板保持原样；新全量文件使用独立文件名，保持 132 条来源文件原始顺序，所有 132 个世界/案例 ID、Gold、世界卡只保存在 Mac 私有文件夹里。

## 第一步：批量生成 132 条私人审核任务

从 StoryForge Git 工作区 R58 分支根目录执行：

~~~bash
git pull --ff-only
R58_PRIVATE="$HOME/.local/share/storyforge/r58"

python3 experiments/r58_quality/gold195_assistant_first_full132.py \
  --repo-root "$PWD" \
  --private-comparison-input "$R58_PRIVATE/gold195-assistant-first-comparisons-v1.jsonl" \
  --private-task-output "$R58_PRIVATE/gold195-assistant-first-review132-v1.jsonl"
~~~

预期 SAFE `FULL132_CONTEXT_REVIEW_TASKS_EXPORTED__UNREVIEWED`，`source_comparisons_verified=132`、`review_tasks=132`、`semantic_reviews_completed=0`、`quality_v1_admitted=0`。输出文件不能已存在；程序禁止覆盖源文件和此前 10 条试点。输入、输出文件要求权限 0600，私人目录 0700。

每条审核任务含原始 Assistant-first 历史、建议删除首条的上下文视图、冻结当前 User 和 Gold、世界卡快照、源哈希、六类语义检查问题，全部为 `UNREVIEWED`，不直接生成训练 messages。

## 第二步：生成 132 条私人审阅结果模板

~~~bash
python3 experiments/r58_quality/gold195_assistant_first_full132_decisions.py \
  --repo-root "$PWD" \
  --private-comparison-input "$R58_PRIVATE/gold195-assistant-first-comparisons-v1.jsonl" \
  --private-full-tasks "$R58_PRIVATE/gold195-assistant-first-review132-v1.jsonl" \
  --private-blank-decisions-output "$R58_PRIVATE/gold195-assistant-first-decisions132-v1.jsonl"
~~~

预期 `FULL132_SEMANTIC_DECISION_TEMPLATES_READY__UNREVIEWED`、`unreviewed_cases=132`、`reviewed_cases=0`。每条裁定初始均为 `UNREVIEWED`，不自动把结构通过视为人工或 AI 审核结论。

实际审阅者须阅读每条任务，逐项判断首条 Assistant 是否携带不可丢弃的身份/关系、事件、硬规则、玩家自主信息；这些事实是否已在后文重建，以及世界卡能否在不泄漏未来信息的情况下弥补。 `CONSIDER_DROP_ONLY_AFTER_EXPLICIT_FACT_REVIEW` 需要六项结论齐全且达最低结构要求、逐字引用首条 Assistant 内容和具体解释。建议保留首条或无法判断时选择 `PRESERVE_LEADING_ASSISTANT_IF_RUNTIME_SUPPORTS` 或 `HOLD_CONTEXT_UNRECOVERABLE`。**真实复核结果未生成之前，不得替审阅者填写分数或虚构证据。**

## 第三步：实际填写后，只读校验

~~~bash
python3 experiments/r58_quality/gold195_assistant_first_full132_decisions.py \
  --repo-root "$PWD" \
  --private-comparison-input "$R58_PRIVATE/gold195-assistant-first-comparisons-v1.jsonl" \
  --private-full-tasks "$R58_PRIVATE/gold195-assistant-first-review132-v1.jsonl" \
  --private-filled-decisions-input "$R58_PRIVATE/gold195-assistant-first-decisions132-v1.jsonl"
~~~

校验器逐条核对与原始 132 对照记录完全一致的任务正文、哈希、固定标签及已填写的结论格式/逐字引用，终端只输出 SAFE 统计。软件仍无法独立证明语义判断准确、审阅者独立或世界卡事实真伪。所有自动审核通过都仅代表**结构及证据引用形式核验**；`history_truncation_approved=false`、`quality_v1_admitted=0`。

已有 10 条试点不被此次新脚本重写或重新生成；R50 测试文件不读，GitHub 不接收任何私人故事文本。世界组件隔离、中文文学与角色安全的正式质量批准、Qwen/ms-swift CPU collator、GPU 授权全部为独立后续门槛。
