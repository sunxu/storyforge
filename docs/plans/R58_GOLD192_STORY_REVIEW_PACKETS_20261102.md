# R58 Gold192 按世界分组的 PRIVATE 语义审核包

日期：2026-11-02。使用已经存在的 PRIVATE 六维任务、历史复用队列和 Gold192 范围清单。**不重新提取 Gold，不重建 PRIVATE 范围，不覆盖任何现有文件。**

## 为什么按故事打包

Mac SAFE 分流已确认 Gold192 有 13 个 story UUID，Gold87/Gold108 两批没有交叉故事 UUID；132 条 Assistant-first，60 条 User-first。所有 192 条均有导出时卡片快照，但该快照不是目标时刻请求卡片，也未批准作为 System。

因此把 192 条按 13 个世界分组，每个世界只携带一份卡片快照，组内保留所有样本的完整历史、当前 User 和 Gold Assistant 目标。这样可一次审查同一世界的共同人物设定和硬规则，再逐条检查回复，不必重复读取 13 次相同卡片。

## 审核优先级

- P1：132 条 Assistant-first。必须保留开头 Assistant 历史，不得自动删除；审查它是否有可见前因、是否与当前 User/目标相连、是否包含无法追溯的角色或事实。
- P2：60 条 User-first。检查当前输入、历史、世界卡与 Gold 目标的连续性、人物关系、硬规则、玩家自主权。
- 每个世界的卡片都保持 \`UNAPPROVED_EXPORT_TIME_SNAPSHOT\`。导出快照不证明目标时刻已经存在或有效。
- Gold108：历史双 ACCEPT 基础证据已绑定，但新上下文/六维审核仍需进行。
- Gold87：索引记载双 ACCEPT；README 说明 Reviewer A/B 双 ACCEPT；JSONL metadata 另记 \`independent_gold_review=NOT_RUN\` 及 \`scores_are_subjective_single_review=true\`。这两类审核可能是不同层次，不能混为一谈。原始 A/B 评语尚未逐条绑定。

## 生成 PRIVATE 故事审核包

先拉取代码并跑合成测试与 Ruff：

~~~bash
set -e
git pull --ff-only
python3 -m unittest discover -s experiments/r58_quality -p 'test_gold192_story_review_packets.py' -v
ruff check experiments/r58_quality/gold192_story_review_packets.py experiments/r58_quality/test_gold192_story_review_packets.py
~~~

再生成唯一的新私人文件（不要改名复用旧文件；目标已存在时程序会拒绝覆盖）：

~~~bash
PRIVATE_ROOT="$HOME/.local/share/storyforge/r58"
python3 experiments/r58_quality/gold192_story_review_packets.py \
  --repo-root "$PWD" \
  --private-tasks "$PRIVATE_ROOT/gold195-review-tasks-v1.jsonl" \
  --private-queue "$PRIVATE_ROOT/legacy-reuse-queue-v1.jsonl" \
  --private-scope "$PRIVATE_ROOT/gold192-scope-v1.private.jsonl" \
  --private-output "$PRIVATE_ROOT/gold192-story-review-packets-v1.private.jsonl"
~~~

预期 SAFE 状态：\`GOLD192_PRIVATE_STORY_PACKETS_WRITTEN__SEMANTIC_REVIEW_PENDING\`，13 个故事包，192 个样本（132 P1、60 P2），排除 3 条。输出目录需为 0700，文件为 0600；内容只留在 Mac 私人目录。终端不输出故事 ID、角色名、卡片或目标正文。

## 审核包内容

每个故事包包含一份世界卡、卡片哈希、审核规则和该世界的所有候选；每个样本保留历史消息、当前 User、Gold Assistant、目标 SHA256、Gold87/Gold108 历史证据状态及审核重点。输出仍是审核材料，不是训练数据，也不含任何审核结论。

如需由 ChatGPT 做内容审核，可由 Owner 选择性上传这个 PRIVATE 文件；可按故事逐包审查，审核结果只输出逐案 PASS/HOLD/REJECT 和简短证据，不把原文重新发布到 GitHub。不得将未经审核的卡片自动加入训练 System。

\`quality_v1_admitted=0\`、\`training_authorized=false\`、\`gpu_started=false\` 保持不变。

## Gold87 历史审核层次补充

对冻结 \`gold_quality_accepted_87.jsonl\` 的 87 条 metadata 统计显示：\`independent_gold_review=NOT_RUN\` 87/87、\`scores_are_subjective_single_review=true\` 87/87、Curator 评分及评语存在 87/87。README 与 index 记载的 Reviewer A/B 双 ACCEPT 是另一层选择证据；不能将其与 JSONL 中的 independent Gold review 字段等同。SAFE 统计见 \`docs/evidence/R58_GOLD87_JSONL_METADATA_INVENTORY_SAFE_20261102.json\`。本轮仍不声称原始 A/B 评语已逐条绑定。
