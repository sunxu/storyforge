# StoryForge R58 — G1 保护世界元数据证据清单（SAFE）

日期：2026-10-30；当前状态：**世界隔离与保护集独立性 HOLD**。Owner 已报告 G1 合成测试 41/41 PASS；本机 5 条故事队列，10 个成对比较，同作者、同标题、原始世界设定精确相等和 `v2_data.world` JSONB 精确相等四项均为 0。以上仅证明**已测试的精确碰撞信号未出现**。

## 当前缺口（不能自动把 false 改 true）

1. **semantic_world_graph**：五个候选的世界实体映射、世界别名、改编和派生链接、继承关系、分支连通证据；必须有独立语义审核。
2. **r50_protected_worlds**：仅来自受许可元数据的 R50 保留世界索引。禁止访问保护题全文、原始测试回复、得分、答案。至少证明索引覆盖对应所有 R50 被保护世界，而非只看已知五个档案标题。
3. **prior_sft_exposure**：各轮 SFT Train/Validation/Dev 的语义世界曝光表及来源版本。仓库现有 `docs/HF_RUN_REGISTRY.md` 只能作为运行与版本导航；并未在本次访问的内容中提供满足这五个候选逐个核对的权威语义世界完整映射。
4. **r55_r57_dev_worlds**：已有 R55/R57 开发/仲裁使用世界的元数据索引，禁止将既有开发题冒充新 held-out。
5. **other_protected_or_holdout**：其他保护/冻结世界与已暴露世界的边界索引，含所用截止时点和完整性说明。

注意：**没有发现可核实的索引 ≠ 索引不存在；某个索引没有命中 ≠ 证明没有语义重叠**。未认证来源的哈希、临时命名的 component ID、仅有当前数据库 `v2_data` 的相等/不相等，均不能单独清关。

## 下一步：只填写元数据证据目录，不读取正文

已经添加无敏感字段的空白模板：
`experiments/r58_round1/G1_METADATA_EVIDENCE_INVENTORY_BLANK.csv`。

Owner 在 Mac 本地复制为新的私有文件：

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only
umask 077

G1ROOT="$HOME/.storyforge-r58-private/round1_pilot_20261030"
test ! -e "$G1ROOT/g1_evidence_inventory_private.csv" &&
  cp -p experiments/r58_round1/G1_METADATA_EVIDENCE_INVENTORY_BLANK.csv \
    "$G1ROOT/g1_evidence_inventory_private.csv" &&
  chmod 600 "$G1ROOT/g1_evidence_inventory_private.csv"
```

只在这个本地副本中逐项标注：
- `private_source_reference`：已存在的私有**世界元数据索引**位置或版本证明；不得指向保护题正文或待审核故事内容。
- `source_revision`：数据索引源 commit/revision 或 freeze 版本；没有则留空。
- `coverage_status`：默认 `UNKNOWN`。只有对索引覆盖范围有可复查证据时可改为 `OWNER_COVERAGE_ATTESTED`，不意味着独立通过。
- `world_identity_namespace`：世界实体映射如何同一化，不能用故事 UUID 代替独立语义世界。
- `independent_review_status`：初始 `PENDING`，需要单独审查而非自行自动赋 PASS。

**禁止把本地含私有路径、受保护的元数据文件、故事 ID 或 hash 的副本发到 GitHub/聊天。** 如果想反馈目前进度，可以只报告五个 scope 中 `UNKNOWN` 和 `OWNER_COVERAGE_ATTESTED` 的个数，以及哪些类别仍缺来源（类别名无敏感信息），但**不要把清单内容原样复制到聊天**。

获得上述可靠索引后，可在 Owner 私有环境中执行 component-level 交集核验。任何索引缺失、覆盖不清或语义关联不确定的候选仍为 HOLD；之后再考虑为已独立证实无曝光的故事设置 G1 cleared 标志并开展至多 20 条回复的结构与质量复核。

## 当前门禁

`G1=HOLD_NO_COMPLETE_PROTECTED_WORLD_EXPOSURE_PROOF`；`G2=HOLD`；`G3=NOT_STARTED`；Train/Val/Teacher 为 0；私有原始 5 条队列不改写；首轮限制 5 个世界/20 条回复，未获 Owner 扩样确认不增加。PR #7 保持 Draft，不修改 Skill v0.1，不启动付费 HF 或 GPU。
