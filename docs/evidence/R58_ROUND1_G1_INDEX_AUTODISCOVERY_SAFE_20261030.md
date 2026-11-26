# R58 G1 — 不再让 Owner 逐个找文件：自动元数据索引线索发现（SAFE）

**日期**：2026-10-30。

Owner 不需要手工查找五个目录、逐行填写索引文件名。工具 `experiments/r58_round1/autodiscover_g1_index_candidates.py` 仅按既定路径、文件名特征和文件属性找出**可能是元数据索引的文件**，输出私有的候选路径列表和五行清单草稿。没有找到时也明确标记待核验，不允许猜测覆盖完整。

## 自动扫描的严格边界

只在 `$HOME/.local/share/storyforge` 下这些已知路径中扫描，最多深入两层子目录：

- `r52/world_isolation`
- `r52/world_review`
- `r52/history_exposure_with_r45`
- `r57/private`

**不扫描 R50**，不沿符号链接，不读取文件内容，不检查任何 JSONL、ZIP、原始故事/消息/Prompt 文件，亦不打开 R55/R57 仲裁原文。每个搜索根有枚举上限，超限 HOLD；所有具体私有路径只保存在 Owner 的 0600 文件中，不进入标准输出、GitHub 或聊天。

文件名含 `world/alias/graph/identity/lineage` 等，可能是世界图线索；含 `exposure/r45/r46/r54/sft` 等，可能是历史训练曝光线索；含 `r55/r57/dev` 可能是开发集线索。这些都是**搜索提示**，并不能确认文件内容是什么，甚至不一定是元数据文件。

## Mac 本地执行一次

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only

python3 -m unittest discover \
  -s experiments/r58_round1 \
  -p 'test_*.py' -v

ROOT="$HOME/.storyforge-r58-private/round1_pilot_20261030"
umask 077

python3 experiments/r58_round1/autodiscover_g1_index_candidates.py \
  --private-candidates "$ROOT/g1_index_candidates_autodiscovered_private.json" \
  --private-draft "$ROOT/g1_evidence_inventory_autodraft_private.csv"
```

新增 10 项纯合成测试；**本轮应为 60 项，Owner Mac 运行结果待回报**。工具产生两个新文件：

1. `g1_index_candidates_autodiscovered_private.json`：每类可能相关的候选**路径清单**。这仍是文件名猜测，绝不代表已经确认其为安全元数据。
2. `g1_evidence_inventory_autodraft_private.csv`：五行证据草稿。仅在某分类找到**唯一一个**候选路径时自动填路径；多个候选或零候选时留空。所有 `coverage_status` 继续 `UNKNOWN`、`independent_review_status=PENDING`，不填写来源版本，不改变原 `g1_evidence_inventory_private.csv`。

只向聊天贴工具输出的**聚合 SAFE JSON**和测试摘要，不提交任何一个生成文件。脚本已避免 R50 文件名和 R50 目录；`r50_protected_worlds` 分类自动发现结果保持 0，是**故意保护隔离**，不能据此断言 R50 元数据不存在。

### 何时需要 Owner 人工确认？

1. **某类别存在多个命名候选**：只在 Mac 本机从候选文件名判断哪一个才是**允许读取的元数据索引**。不要求上传全部文件。如果没有受许可的元数据专用源，就维持缺失。
2. **索引覆盖范围/版本不清**：Owner 需要指向已经存在的 freeze、SHA 和覆盖记录；自动文件名扫描无法推断文件覆盖全集。
3. **世界语义独立**：别名、改编、派生、跨故事连通关系必须由独立 Reviewer 复核，不能用 story UUID、标题、零精确碰撞当 PASS。
4. **R50**：必须通过已有**授权的保护世界元数据登记**，不能扫描 R50 测试题或由助手读取保护集；找不到就保持 HOLD。

这一步只是减少文件定位的人力，不是解除 G1。五条 G1 队列冻结，R50 不读、候选正文不读、Train/Val/Teacher 0、扩样仍禁止、PR #7 Draft。
