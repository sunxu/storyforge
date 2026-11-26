# R58 G1 — 首轮 5 条候选与历史 SFT 世界 UUID 精确曝光核验（SAFE）

日期：2026-10-30。**目标不变：最多 5 个可核验独立世界/20 条候选回复；先排除历史曝光、R50/开发题及世界别名冲突，再做回复重放和独立质量审核。用户正式批准前禁止扩样或训练。**

## 为什么不再继续通用文件名筛选

Owner Mac 已报告 **60/60 合成测试 PASS**，并从 22 条唯一文件路径产生按类别的 29 次候选命中（世界 8、历史曝光 2、开发集 19；R50 与其他类 0）。**文件名匹配不是任何一个世界已经隔离的证据**；自动草稿 5 项为空是多候选歧义，不代表磁盘上没有文件。现在只处理首轮 5 条冻结故事的真实风险，不扩大来源扫描。

## 已有确定格式的历史曝光元数据

R57 的 `scripts/r57_g2_owner_world_review_roster.py` 已定义了私有 `R57_G2_WORLD_ALIAS_REVIEW_YYYYMMDD_HHMMSS_PRIVATE.json` 格式；记录 29 个源故事 UUID，27 个精确历史 Train/Validation 曝光 UUID，且**语义世界别名独立性仍为 HOLD**。这份账本不是原始故事正文或 R50 保护集。已归档的 R57 SAFE 回执仍区分“UUID 级曝光”与“跨 UUID 的真实语义世界”。

## 本轮实际执行（Mac）

新工具 `experiments/r58_round1/check_prior_sft_exact_world_ids.py`：

1. 读取现有 G1 冻结队列，仅 1–5 条，必须五项世界/保护门禁仍全为 false；
2. 读取已生成的私有文件名候选清单；**只选择匹配已知 R57 世界 UUID 名录格式的文件**，且只能在 `$HOME/.local/share/storyforge/r57/private` 内；
3. 有且只有一份时，检查其已知严格元数据 Schema：29 个唯一 UUID、27 个历史曝光标记（没有来源正文、回复、Prompt 字段），只计算当前 5 条候选的精确 UUID 命中数；
4. 仅输出 SAFE 汇总（不会打印 story_id、来源路径、作者或世界卡）。如果缺文件、多版本或 Schema 不符，直接 HOLD；如果命中，报告曝露风险；如果 0 命中，**仍旧 HOLD**，不得认为语义独立。
5. 不读取 R50 原文，不获取候选回复正文，不修改既有队列，不生成训练样本，不更新世界隔离通过标记。

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only

python3 -m unittest discover -s experiments/r58_round1 \
  -p 'test_*.py' -v &&

ROOT="$HOME/.storyforge-r58-private/round1_pilot_20261030"
python3 experiments/r58_round1/check_prior_sft_exact_world_ids.py \
  --private-queue "$ROOT/g1_review_queue_private.csv" \
  --private-discovery "$ROOT/g1_index_candidates_autodiscovered_private.json"
```

预期纯合成测试 **69 项**（原 60 + 新增 9）；真实 Mac 测试及结果仍待 Owner 报告。仅分享测试摘要及第二个命令的 SAFE JSON。禁止分享原始私有来源路径、故事 UUID、名单或保护题数据。

## 结果及动作

| 返回值 | 意义 | 动作 |
|---|---|---|
| `R58_G1_PRIOR_SFT_EXACT_UUID_OVERLAP_FOUND__HOLD` | 现有 5 条至少一条与旧 27 个训练世界 UUID 精确命中 | 受影响项必须冻结并在本地标注曝光；其他仍待 R50/世界图验证 |
| `R58_G1_NO_EXACT_UUID_OVERLAP__SEMANTIC_NAMESPACE_HOLD` | 旧 R57 名录没有同 UUID 命中 | **不能证明无世界同源/别名**；下一步独立世界元数据对照 |
| `R58_G1_R57_ROSTER_MISSING__HOLD` | 已发现候选索引中不存在该精确格式的名录 | 不能使用 R57 UUID 路径进行清关；继续 G1，勿擅自补造来源 |
| `R58_G1_R57_ROSTER_AMBIGUOUS__HOLD` | 多个 R57 版本存在 | 保持 HOLD，先确定经冻结证明的源版本 |
| CLI 退出 42 | 输入权限、格式、计数、路径不可信 | 保持 HOLD，不上传私有文件或报错堆栈 |

**注意**：R57 训练世界 UUID 的标识空间与 RolePlay `user_stories.id` 是否真正一致，目前没有证明。即使 0 精确匹配，`candidate_id_namespace=UNVERIFIED`；不同项目的不同 ID 不是无曝光证据。

R50 保护、R55/R57 开发题、其他保护世界以及五候选语义连通图仍未完成，所以 G1 整体 HOLD，G2/G3 不能提前开始。Train/Val/Teacher=0，Skill v0.1 不变，PR #7 Draft，首轮完整回执尚未出现，扩样前提醒继续等待。

## 2026-10-30 额外的纯聚合格式验证

单独使用 RolePlay 生产数据库**只读聚合**复核与本轮发现条件相同的 1280 条故事：`uuid_formatted_story_ids=1280`、`non_uuid_story_ids=0`，ID 长度最小/最大均 36。查询没有返回任何故事 UUID、作者信息或正文。因此，本轮五条队列可以进行精确 UUID 比较，但**仅确认格式相容，没有确认两个数据源的 ID 命名空间和语义世界可互认**。即使工具发现 0 个交叉，G1 仍 HOLD。

## 2026-10-30 Owner 真值回执：5 条中的 1 条与 R57 已曝光 UUID 精确命中

Owner Mac 实测 69/69 合成测试 PASS（0.040s）；五条冻结候选与本地唯一 R57 私有世界名录对比：27 个历史曝光 UUID，命中 **1**、未精确命中 **4**，所有五条满足 UUID 格式；R57 名录 schema 检查 PASS。此发现明确高风险，**不是语义世界同一性或命名空间一致性的独立签核**。

已经在原有 `check_prior_sft_exact_world_ids.py` 添加一个**可选的 Owner 私有逐条 HOLD 清单**，而不是产生新筛选结果。不会修改已经冻结的五条队列：

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only

python3 -m unittest discover \
  -s experiments/r58_round1 -p 'test_*.py' -v &&

ROOT="$HOME/.storyforge-r58-private/round1_pilot_20261030"
python3 experiments/r58_round1/check_prior_sft_exact_world_ids.py \
  --private-queue "$ROOT/g1_review_queue_private.csv" \
  --private-discovery "$ROOT/g1_index_candidates_autodiscovered_private.json" \
  --private-hold-output "$ROOT/g1_prior_sft_exact_id_holds_private.json"
```

新增 4 项纯合成测试，预期总数 **73**（Owner Mac 新测试待验证）。本地 ledger 只有五条，分别为：
- 已精确命中的 1 条：`HOLD_PRIOR_SFT_EXACT_ID_OVERLAP__NAMESPACE_UNVERIFIED`
- 其余 4 条：`HOLD_NO_EXACT_ID_MATCH__SEMANTIC_AND_PROTECTION_PENDING`

另含 R57 私有名录字节 SHA256 以便 Owner 本地追溯，但**不要外传该文件、真实 ID、SHA 或来源路径**。本地文件一旦存在，不允许覆盖；不改变 R58 世界隔离 guard flags，Train/Val/Teacher 保持 0，PR #7 Draft。

**后续真正门禁**：先检验 R57 UUID 与 RolePlay UUID 的身份映射来源证明，并对其他四条作 metadata-only 世界语义与 R50、R55/R57 Dev 和其他保护世界的交叉复核。不得把这四条直接晋级，更不能替换高风险候选后继续读回复正文；首轮仍不得扩大。
