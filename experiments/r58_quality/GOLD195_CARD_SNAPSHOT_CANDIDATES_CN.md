# R58 Gold195 — B 路线原始世界卡私人候选提取

GitHub LFS 实体经专项 Actions 实测：早期备份的 5 个故事与 06–15 归档中的 10 个故事均含 `story.v2_data`；Gold195 的 13 个故事、195 条目标全部有 UUID 对应的原始故事卡来源，无源卡版本哈希冲突。

这个工具在来源固定 SHA256 校验后，只从嵌套原始 JSON 的 `story.v2_data` 提取**导出时快照候选**，计算每张卡的 SHA256，标记 `NOT_APPROVED_FOR_SYSTEM`。不把快照直接当作历史真实 Prompt，也不要求历史 Provider 原始请求回放。

默认只读、只输出汇总：

```bash
python3 experiments/r58_quality/gold195_card_snapshot_candidates.py --repo-root "$PWD"
```

若需要在 Mac 离线审阅卡片，先确保两个 Git LFS ZIP 实体已拉取，再把私人候选写到仓库外的权限 0700 目录：

```bash
mkdir -m 700 -p "$HOME/storyforge-review-private"
python3 experiments/r58_quality/gold195_card_snapshot_candidates.py \
  --repo-root "$PWD" \
  --private-candidates-output "$HOME/storyforge-review-private/gold195-card-snapshots-v1.json"
```

输出权限 0600，无法覆盖现有文件，包含真实故事设定，**不得提交 GitHub、上传到公开 CI 或分享原文**。该 JSON 的 schema 与训练卡片准入 manifest 不同，不能直接输入 `gold195_card_first.py`。它用于下一步逐故事审核来源版本、玩家/NPC 关系、内容边界、与 Gold 目标及历史的设定冲突；必须人工/独立 AI 复核才能构建真正的离线 System 卡。

当前训练准入 0，R50 密封题不读，HF/GPU 不启动。
