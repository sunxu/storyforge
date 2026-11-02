# R58 Gold192：11 条 A/B 分歧私人仲裁清单

本工具只读分析已恢复的 Owner 私有 Manifest，生成 **11 条需独立裁决的 PRIVATE JSON**，以及不含案例标识/原文的 SAFE 统计。不会进行仲裁、修改已有判定、增加训练准入或启动 GPU。

## 运行

在已有的 `storyforge-gold-quality` Worktree 运行：

```bash
cd ~/workspace/storyforge-gold-quality
git pull --ff-only
source .venv/bin/activate

PRIVATE_DIR="$HOME/.local/share/storyforge/r58/private"
umask 077

python -m storyforge_gold_quality.arbitration_queue \
  --manifest "$PRIVATE_DIR/gold-quality-events.jsonl" \
  --output "$PRIVATE_DIR/gold192-arbitration-11.private.json" \
  --repo-root "$PWD"
```

输出文件只能创建在现有的私有目录之外的 Git 工作树中（建议沿用 `$PRIVATE_DIR`），权限强制为 0600；若文件已存在则拒绝覆盖，不会删除历史私人产物。终端输出仅包含 SAFE 计数。不要把 PRIVATE JSON 提交到 GitHub、贴到公开日志或发给不了解 Reviewer A 判定的 Reviewer B。

## 现有精确分歧范围

- 6 条：A PASS_ONLY / B HOLD。
- 1 条：A PASS_ONLY / B REJECT。
- 4 条：A 历史 REJECT / B PASS，保留无六维评分的事实，不算标准 A/B 六维评分配对。
- 合计 11 条，全部 `PENDING_OWNER_ARBITRATION`、`decision: null`。
- 与此相独立，剩余 110 条缺 Reviewer A 逐案证据；不能用 V6 汇总填补私人评分。

Private JSON 中会保存 Target SHA256、B 匿名 ID、已有双方决策、已有分数和证据摘要。对于四条历史 A REJECT，因恢复证据缺少完整逐案评分/说明，评分与文字摘要为 null，并保留历史证据层级。工具不臆造原始案例 ID，也不自动提出 PASS/REJECT 仲裁结论。

## 后续处理边界

先核查违反玩家明确意愿/称呼禁令/职业边界等严重规则问题，再核查缺少上下文、角色名映射和文学表达差异。仲裁时对照完整私有故事包的必要上下文，不能用两位 AI 的摘要替代原文验证。

仲裁结果应另存为 Owner 私有决策记录，不能直接覆盖 A/B 原始审核事件。没有新授权不得改变 Quality-v1 / GPU / 训练状态，也不访问 R50 保护材料。
