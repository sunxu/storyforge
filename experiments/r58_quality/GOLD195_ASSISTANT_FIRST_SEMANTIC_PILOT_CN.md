# R58 — Assistant-first 132 条中抽取 10 条跨世界离线复核试点

## 已确认的诊断状态

Owner Mac 的 SAFE 回执：Gold195 共 195 条；63 条历史以 User 开始；132 条历史以 Assistant 开始。132 条在移除第一条 Assistant 后都能满足角色交替结构，且仍有其他历史消息。但**这一结果不能证明丢掉开头回复不损失人物、剧情或规则事实**。

本流程只准备最多 10 条跨不同来源世界的*私人*复核任务；按 132 条原始记录顺序，优先每个不同 `story_uuid` 各选一条，再按原始顺序补足。不是随机样本，也不能用于统计推断所有 132 条的通过率。相同世界的相关候选仍需后来集中检查。

## Mac 执行

已将私有目录迁至 `$HOME/.local/share/storyforge/r58`，请在 StoryForge 的 R58 Git 仓库根目录执行：

~~~bash
git pull --ff-only

R58_PRIVATE="$HOME/.local/share/storyforge/r58"

python3 -m unittest discover -s experiments/r58_quality \
  -p 'test_gold195_assistant_first_semantic_pilot.py' -v

python3 experiments/r58_quality/gold195_assistant_first_semantic_pilot.py \
  --repo-root "$PWD" \
  --private-comparison-input "$R58_PRIVATE/gold195-assistant-first-comparisons-v1.jsonl" \
  --private-task-output "$R58_PRIVATE/gold195-assistant-first-semantic-pilot10-v1.jsonl"
~~~

输出文件必须原先不存在；命令是只读源文件和创建新本地文件，不覆盖源文件、不写入 Git 仓库。输入输出权限 `0600`，私有文件夹 `0700`。

## 十份私有审核题要判断什么？

每条包含原始 Assistant-first 历史、拟议截断视图、首条 Assistant 原文、当前 User、冻结 Gold 目标、来源世界卡快照与绑定哈希。审核人员重点核实：

1. 移除首条 Assistant 是否损失人物身份、关系、态度或口吻；
2. 是否损失关键历史事件、因果关系或时间顺序；
3. 是否损失硬事实、禁止行为、安全约束或隐含玩家决定；
4. 后续历史是否确实重新叙述了这些事实，而不是审核者自行脑补；
5. 来源世界卡是否能够补足信息，是否引入目标时间点之后的信息；
6. 如果无法无损截断，能否在经过 CPU tokenizer/collator 验证后保留 Assistant-first 完整历史，或继续 HOLD。

建议策略标记：

- `PRESERVE_LEADING_ASSISTANT_IF_RUNTIME_SUPPORTS`：保留完整上下文的实验路线，仅表示值得 CPU 技术验证；
- `CONSIDER_DROP_ONLY_AFTER_EXPLICIT_FACT_REVIEW`：有原文证据支持丢弃开头 Assistant，但**依然不是训练准入**；
- `HOLD_CONTEXT_UNRECOVERABLE`：信息缺失或事实无法确证，继续 HOLD。

所有新文件中的 `review_status` 初始为 `UNREVIEWED`，`recommended_policy` 为 `HOLD_PENDING_SEMANTIC_REVIEW`，`training_candidate_messages=null`，`quality_v1_admitted=false`。**脚本没有作任何 AI 内容审查，也没有授权发送给 Grok 或其他第三方网站。** 私人故事正文、真实 UUID、逐案 ID 均不发送到 stdout、GitHub 或 CI。

## 后续门槛

等这 10 条真实语义审核完成后，再决定对完整 132 条采取哪种分流、是否需要特定世界卡修复以及是否做 CPU tokenizer/collator 技术预检。R50 继续封存，Quality-v1 准入仍为 0，GPU/HF 不启动。
