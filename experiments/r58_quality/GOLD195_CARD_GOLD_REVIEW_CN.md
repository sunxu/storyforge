# StoryForge R58 — 卡片快照与 Gold195 私有语义审核包

## 目的

按 Owner 确认的 B 路线，将 GitHub `evaluations/v0.2/source-archives` 的 13 份来源世界卡快照与 195 条冻结 Gold 原文组成**逐案内容审核材料**，而不是直接生成 SFT 训练数据。最终目标是中文文笔、角色/规则一致性、NPC 主动推进、玩家自主权、剧情连续性。

此前的来源 SHA256、195/195 目标哈希、13/13 世界 UUID 映射已经验证。导出时快照是**可供选择的离线卡片候选**，并非历史生产 System，也不自动等于可信训练设定。

## Owner Mac：只读预检和私人输出

先同步 R58 分支。上一轮已经生成：

`$HOME/storyforge-review-private/gold195-card-snapshots-v1.json`

这一文件由 `gold195_card_snapshot_candidates.py` 生成，0600 权限；它不是训练卡片 manifest。

运行：

```bash
python3 experiments/r58_quality/gold195_card_gold_review.py \
  --repo-root "$PWD" \
  --private-card-candidates "$HOME/storyforge-review-private/gold195-card-snapshots-v1.json"
```

该命令只输出 SAFE 数量，不创建文件。若需审核包，再添加：

```bash
  --private-review-output "$HOME/storyforge-review-private/gold195-card-gold-review-v1.jsonl"
```

务必把参数写在同一条命令上。目标必须是仓库外新文件，文件夹权限 0700，输出权限 0600，禁止覆盖。**不要上传审核包、卡片、故事正文或逐案 ID。** 终端只分享 SAFE JSON。

## 审核内容

每条私人记录包含源卡片快照、完整原始历史（含可能孤立的首条 Assistant）、当前 User、冻结目标 Assistant 和哈希。审查字段均为 `UNREVIEWED`，包括：人物关系、硬设定/禁令、时间线与未来信息、玩家自主权、中文文学质量/NPC 行动、年龄和安全边界，以及该快照是否适合用作新的离线设定。

以历史 Assistant 开头的 132 条保留完整历史并能进入六维质量审核任务；真实 ms-swift 已证明这种角色顺序兼容训练。新的卡片尚未经语义认可，不生成“已批准的 System”或伪造 Reviewer 分数。可在独立 AI 内容审查后据实标记问题，并由新输入设计明确首轮历史处理策略。

**最终 Quality-v1 准入、Train/Val 世界组件隔离、Qwen 16K Token 和 ms-swift last_round Mask 全部是独立后续步骤。** R50 测试题不读，HF/GPU 不启动，无历史 Provider 精确回放要求。
