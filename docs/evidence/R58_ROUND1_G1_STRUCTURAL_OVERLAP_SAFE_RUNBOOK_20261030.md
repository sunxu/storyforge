# R58 G1 第二步：5 个私有候选的结构性重叠信号（SAFE）

日期：2026-10-30。Owner Mac 实测：`30/30` 合成测试通过、G1 私有队列 `5` 条（original 3 / dice_cocreate 1 / ai_assisted 1）；**当前真实世界核验 0，所有五种排除门禁仍为 false**。

## 范围和禁止的推论

本工具 `experiments/r58_round1/audit_g1_structural_overlap.py` 只面向 Owner 之前冻结在 Mac 的 **这 5 条** `g1_review_queue_private.csv`，使用已验证的 `r58_export_reader` 数据库只读账户，在数据库侧做成对结构性比较。它不会读取会话/回复正文、R50 测试题或其他保护集原文，也不会在聊天/GitHub 输出故事 ID、作者 ID、标题、世界设定或内容哈希。

- `same_author_pairs`：两故事的当前作者 ID 相同。**相同作者不代表同一世界，不同作者不证明世界独立。**
- `same_title_pairs`：非空标题去空格转小写后完全相等。**只是疑似关联**。
- `same_world_setting_pairs`：非空顶层世界设定原文字段完全一致。只返回相等的故事对数，不返回文字。
- `same_v2_world_exact_pairs`：非空 `v2_data.world` JSONB 结构完全一致的故事对数（空对象不算）。**相等是强重叠警示；不相等不代表不同语义世界**。

上述数字**只是 G1 的弱/中等强度结构碰撞诊断**，不是世界图核验；SQL 比较的是当前故事结构，不代表历史目标时点快照。若全部为 0，仍不能证明五个候选独立，也不能解除 `r50_protected_clear`、`prior_sft_clear`、`r55_r57_dev_clear`、`other_protected_clear`。不得用这些计数填补真实保护集元数据索引缺失。

## Owner Mac 本地执行

先使用最新 GitHub 分支（不更动原私有队列）：

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only
python3 -m unittest discover -s experiments/r58_round1 \
  -p 'test_*.py' -v
```

预期原有 30 项 + 新增 11 项，共 `Ran 41 tests / OK`（Mac 运行结果尚待 Owner 回报）。先做本地校验，不接触数据库：

```bash
G1="$HOME/.storyforge-r58-private/round1_pilot_20261030/g1_review_queue_private.csv"

python3 experiments/r58_round1/audit_g1_structural_overlap.py \
  --private-queue "$G1" --plan-only
```

已有专用 PG 只读环境变量 `PGHOST/PGUSER/PGPASSWORD`（或已配置的安全凭据）后：

```bash
python3 experiments/r58_round1/audit_g1_structural_overlap.py \
  --private-queue "$G1"
```

运行要求：`PGUSER` 是 `r58_export_reader.<project_ref>`，实际 SQL 的 `current_user` 必须为 `r58_export_reader`，`transaction_read_only=on`；脚本把至多 5 个本机故事 ID **仅经本机 psql stdin** 发往受控数据库，禁用 SQL 出错时回显，返回单条 SAFE JSON 聚合。脚本要求队列五项保护门禁仍 false、私有文件 0600；若这些状态已经被人工填写过，则停止用该探针，按已有 G1 复核材料处理，不应清空原证据以重跑。

请只回报 `Ran 41 tests / OK` 和工具的 SAFE JSON。绝不发布 `g1_review_queue_private.csv`、可识别作者 ID、原始查询文本或完整世界卡。

## 后续真正的 G1 清关

无论碰撞数结果如何，接下来仍需 Owner 本地取得 **可信来源、完整覆盖范围和版本/时点** 的元数据证明，再逐项复核：
1. 原始故事间同一语义世界、译名/别名、改编派生与作者独立性图；
2. R50 保护世界 **metadata-only** 排除证明（不读取保护题正文）；
3. 既有训练集/开发集世界曝光元数据；
4. R55/R57 开发题与其他冻结/保留世界的排除。
缺少任何一项，目标依然 `G1_HOLD`，不得提取回复正文。

**本轮仍在最多 5 个世界、20 条候选回复上限内；Train/Val/Teacher 全 0；PR #7 Draft；首轮完成提醒继续监测，未完成不触发，未经 Owner 明确批准禁止扩样。**
