# R58 Gold195 — 先审 63 条 User-first 样本（B 路线）

**目标：训练高质量中文互动剧情 LoRA。** 当前已经有 195/195 的来源卡片与 Gold 对照包，但来源卡片只是 GitHub 导出快照，并非经过语义审核的最终 System。本文只负责生成**可交给独立 AI Reviewer 阅读**的私人题目，不得把尚未审阅的题目当作已通过训练的样本。

## 数据处理策略

- 63 条原始历史从 User 开始：构建由 `story.v2_data` 快照序列化得来的**拟议离线 System**、原样历史消息、最后 User 和单独的 Gold Assistant 目标。卡片仍然**未经批准**，每条审核题必须核查设定是否与历史、目标冲突。
- 132 条历史从 Assistant 开始：保持 `LEADING_ASSISTANT_CONTEXT_HOLD`，既不默默删掉开头，也不伪造历史 User。等第一批真实质量审查后再决定是否以明确的上下文截断策略另开实验。
- 六维审核：中文文笔、人物一致、NPC 主动推进、玩家自主权、硬设定/禁令、叙事连续性。两位独立盲审的评分栏保持空白，不伪造人工或 AI 审核。
- 严重问题：侵犯玩家自主权、明确违反硬设定/禁令、安全排除。审核结论必须留有私人原文证据；不能只靠算法结构判断。

## 在 Mac 上生成私人审题（无外部 API 调用）

你已有的私有审核包（0600）：

`$HOME/storyforge-review-private/gold195-card-gold-review-v1.jsonl`

同步代码并运行：

```bash
git pull --ff-only
python3 experiments/r58_quality/gold195_six_dimension_review_tasks.py \
  --repo-root "$PWD" \
  --private-card-gold-review "$HOME/storyforge-review-private/gold195-card-gold-review-v1.jsonl" \
  --private-task-output "$HOME/storyforge-review-private/gold195-review-tasks-user-first-v1.jsonl"
```

输出仅在仓库外、权限 0700 的文件夹中创建 0600 文件；不覆盖、不输出故事正文/人物 ID/任何真实哈希到终端。若需先只读检查，省略 `--private-task-output` 即可。

生成的 JSONL 包含卡片源快照、提议 System、原始输入与目标、两位独立 Reviewer 要核查的六维指标。**没有完成审核、保护世界隔离和实际 Qwen tokenizer/ms-swift last_round 检查，不可用于训练。**

此脚本不请求模型推理、不主动上传私人内容、不启动 HF CPU/GPU，R50 密封评测内容不读取，不要求历史 Provider 请求精确回放。私人题目可以在受控私有模型环境中开展 AI 双审，双方应分别生成不共享彼此结论的独立回执。

## 下一主线

1. 用真实模型审 63 条优先批次：卡片一致性与六维质量；保留原文证据和真实评分。
2. 对 132 条 Assistant-first 单独验证明确的上下文起始策略，先审不改 Gold。
3. 审核通过后进行世界级 Train/Validation/保护集隔离和 Qwen tokenizer / loss mask CPU 实测。
4. 只有在得到明确 GPU 预算授权后才可启动任何 LoRA GPU 训练。
