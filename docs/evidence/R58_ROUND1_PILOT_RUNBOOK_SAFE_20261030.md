# R58 首轮正式候选试点（Round 1）执行书 · SAFE

日期：2026-10-30。**本轮已完成元数据规模盘点和工具开发；私有故事 ID 选取、回复正文审核、最终审查回执尚未执行。** 不要将准备阶段的结果写成“首轮正式筛选完成”。

## 1. 范围与边界（先做小规模）

- 最多 **5 个经过独立世界图核验的语义世界**，最多 **20 条候选 Assistant 回复**。达到任一上限即停止，本轮不得扩大。
- 暂定 3 个 `original`、1 个 `dice_cocreate`、1 个 `ai_assisted` 来源类型配额；若隔离证明不足，可少于上限，**不允许补选未核验世界填满配额**。
- 每个故事至少 50 条已完成 Assistant 回复、至少 2 个历史会话、已审核且未删除，V2 schema 有 world/character/opening 结构字段。
- RolePlay 的 `genre` 列在此次合格汇总池中全部未填写，不以此捏造题材分层；`source_type` 是创作来源类别，不等同故事语义世界。
- 只读 SQL 和私有 CSV 只放 Owner 私有目录；R50 保护题/世界、既有 SFT 曝光世界、R55/R57 开发题和其他保护世界必须在读正文**之前**由私有元数据证明排除。
- 第一期原有 Priority3 3 案例不会重复选取或覆盖；其请求身份及 Runtime 字节级重建仍 HOLD。

## 2. 元数据只读盘点已通过

2026-10-30 汇总刷新时间约 09:34 UTC：已审核且有效 V2 故事 1532；拥有 ≥50 条完成回复 1284；其中拥有 ≥2 会话 1280、≥5 会话 1234、≥200 完成回复且 ≥5 会话 1034。来源类型分别为 original 1108、dice_cocreate 91、ai_assisted 85；三个来源组在 ≥5 会话时分别为 1083、82、69。整个查询仅返回聚合数，不带故事标识或正文。

## 3. Owner 本地运行：先只做无正文发现池

旧的 Skill 查询可直接使用：
`skills/storyforge-roleplay-sft/queries/02_story_shortlist.sql`。

在**仅 Owner 可读**的本地目录中执行该 SELECT，将返回的故事级记录保存为 `stories_private.csv`，**禁止发布到 GitHub、聊天、公共 CI 日志或普通可访问存储**。它包含 story_id。

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only
python3 -m unittest discover -s experiments/r58_round1 \
  -p 'test_pilot_round1_shortlist.py' -v

ROUND1="$HOME/.storyforge-r58-private/round1_pilot_20261030"
mkdir -p "$ROUND1"
chmod 700 "$ROUND1"

# 确认 Owner 已把元数据 SELECT 的 CSV 存成这个路径（不要复制到对话）：
python3 experiments/r58_round1/pilot_round1_shortlist.py \
  --inventory "$ROUND1/stories_private.csv"
```

这一模式只回传元数据数量和来源类别，永远不会宣布 G1 训练准入。**不要为了运行测试而尝试访问保护集正文。**

## 4. 独立世界隔离登记后，才允许私有 shortlist

Owner 仅在本地创建 `world_guards_private.csv`，字段：

```csv
story_id,world_component,owner_world_graph_reviewed,r50_protected_clear,prior_sft_clear,r55_r57_dev_clear,other_protected_clear,evidence_reference
```

各字段语义：
- `world_component` 是真实的语义世界连通分量 ID，不是不同故事 UUID 的伪独立性。
- 五个布尔门禁来自有追踪证据的私有元数据审查；**未知必须 false，不得编造 true**。`evidence_reference` 应指向 Owner 本地可复查的证明；无需把它传到聊天。
- `r50_protected_clear` 只使用已批准的保护世界元数据，**禁止查看 R50 原始题或正文**。
- 与既有 SFT 曝光世界、R55/R57 Dev 及其他保护世界有世界重叠的一律 BLOCK；同一连通分量本轮最多选 1 个故事。
- 此 registry 只是 Owner 自报清关记录；程序并不验证其世界语义正确性，后续还须独立世界图审查，不得把它当作自动 PASS。

随后（只有 registry 有充分证据时）执行：

```bash
python3 experiments/r58_round1/pilot_round1_shortlist.py \
  --inventory "$ROUND1/stories_private.csv" \
  --guards "$ROUND1/world_guards_private.csv" \
  --private-output "$ROUND1/selected_round1_private.json"
```

选择器仅输出 SAFE 计数；私有清单写入新文件、权限 0600、已存在则拒绝覆盖。状态即使为 `R58_ROUND1_PRIVATE_SHORTLIST_READY__INDEPENDENCE_REVIEW_PENDING`，仍是 `SHORTLIST_ONLY__NOT_ADMITTED`，未接触候选回复正文。

## 5. 首轮结构与质量审核

仅对已隔离世界中的私有会话做定额定向结构筛查，累积最多 20 条待审回复。要求完成消息、对应真实 User、父分支/重试/streaming 有据可查，硬事实/禁句、严重玩家自主权、叙事连续性与文学质量执行两位互不共享判断的 Reviewer。G2 必须能证明目标时点的故事卡、会话摘要、历史/输出清洗与实际 Prompt；无法复原则 `HOLD_RUNTIME_REPLAY`，不能靠高质量评分抵消。

本轮可以以 **全部候选被 HOLD/REJECTED** 完成“审核结算”，但**不能**把 HOLD 当 PASS。需要逐案的脱敏 SAFE 结算（实际审查条数、PASS/REJECT/HOLD、每种门禁阻塞原因；不含 ID、正文、hash）。

## 6. 完成检查点与扩样提醒（硬门禁）

首轮完成条件：选样/保护世界边界审核 + 有限候选结构审核 + 两位独立质量审核（或明确终止并以 HOLD 结算）+ 可审计 SAFE 结果。只有完成后才可创建：

`docs/evidence/R58_ROUND1_PILOT_COMPLETION_SAFE.json`

并且其顶层 `status` 经独立审核确认为 `R58_ROUND1_PILOT_REVIEW_COMPLETE`。此时**提醒 Owner**核对样本质量、保护世界隔离、成本和风险；**在 Owner 在对话内明确确认扩大范围前，禁止扩样或自动启动下一批筛选**。

`docs/evidence/R58_ROUND1_METADATA_PILOT_GATE_SAFE_20261030.json` 只是**准备期**回执，其 `completion.status=NOT_COMPLETE`，不能触发完成提醒。

首轮停止条件：若任一保护门禁无法确认、真实部署 Runtime 证据缺失、Reviewer 产生不可解争议，相关候选 HOLD，避免扩大样本掩盖问题。

当前 Train/Validation/Teacher 准入均为 0。PR #7 Draft；Skill v0.1 不变，不合并、不执行收费 HF CPU/GPU、不自动训练。
