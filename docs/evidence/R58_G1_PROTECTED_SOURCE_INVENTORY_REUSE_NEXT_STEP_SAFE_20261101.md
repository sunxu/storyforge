# StoryForge R58 G1 — Protected / DEV 来源名册证据恢复（复用现有工具）

日期：2026-11-01。工作范围：`r58/roleplay-sft-skill-v01`，Draft PR #7。

## 本次冻结结果

已独立从 GitHub 固定 SAFE 文档与 R57 分支既有 Owner 计数回执核对：R55 的 DEV20 为 v0.1 Test 两个旧开发世界；R56 Stage7 五条候选均属 Gold195、零新 UUID；R57 八源（Gold87/Gold108 + 六份 Train/Validation）已有冻结来源回放回执。以上只证明各文档的**已检查局部范围**，不是 R55/R56/R57 其他 Dev/Arbitration/Protected/Reserved 的权威全集。

具体证据、Blob SHA 与缺口标记：
`docs/evidence/R58_G1_R55_R56_R57_PROTECTED_SOURCE_GAP_MATRIX_SAFE_20261101.json`。

目前八范围 UUID-only 合约中，仍缺三个权威集合：`r55_r57_other_dev`、`other_reserved_heldout`、`other_historical_training`。另外，R50 已知五保护世界交集为零也不等于全部 Protected 证明；历史 CPU/GPU Job 曝光范围同样没有完整证明。固定五候选队列仍一条排除、四条 HOLD。

## 下一步：检查是否已有 PRIVATE 五范围来源证据目录

不新造 UUID 核验器。先复用仓库已存在的 `audit_g1_index_readiness.py`，该工具仅打开五行 PRIVATE CSV 目录清单，并对清单引用的源文件做存在性 `lstat`；**不会读取那些来源文件的正文、故事 UUID 或 R50 题目**。

在已经切换到 R58 分支、上游 remote 配置正确的 Owner Mac 仓库中执行：

```bash
git pull --ff-only
ROOT="$HOME/.storyforge-r58-private/round1_pilot_20261030"
INVENTORY="$ROOT/g1_evidence_inventory_private.csv"
if [ -f "$INVENTORY" ] || [ -L "$INVENTORY" ]; then
  python3 experiments/r58_round1/audit_g1_index_readiness.py \
    --private-inventory "$INVENTORY"
else
  printf '%s\n' '{"schema":"r58_g1_private_inventory_availability_safe_v1","status":"EXISTING_OWNER_PRIVATE_SOURCE_INVENTORY_NOT_FOUND__G1_HOLD","source_index_bytes_read":false,"g1_clearance":"HOLD","g2_clearance":"HOLD","train_admitted":0,"validation_admitted":0,"teacher_admitted":0,"expansion_allowed":false}'
fi
```

只返回工具 stdout 的 SAFE JSON；若脚本退出 42，只报告固定 `R58_G1_INDEX_READINESS: HOLD`，不复制原本地清单，不粘贴文件路径或原始 story UUID。

如果清单缺失，先记录源目录缺口，不自动生成“已完成”或从 R50/原始故事重新扫描。若存在，五范围状态只是 **L0/L1 或 Owner 声明**，不能当作独立审阅通过。若需要新建或填写 Owner 私有来源目录，按仓库已存在的 `R58_ROUND1_G1_INDEX_READINESS_RUNBOOK_SAFE_20261030.md` 执行，必须由 Owner 确定确切、已授权的元数据专用索引，而非直接对正文/测试题开文件。

已有 `skills/storyforge-roleplay-sft/v02/r58_g1_scope_reconcile.py` 八范围 UUID-only 合约及 `r58_pipeline_bridge.py g1-audit` 可在正式冻结、获得授权元数据后复用，**当前不要为了让其通过而臆造剩余三个范围或自动填 Owner_COMPLETE**。

## 停止门禁

`G1=HOLD`、`G2=HOLD`、`G3=NOT_STARTED`、Train/Validation/Teacher=0、`expansion_allowed=false`；R50 密封、Skill v0.1/v0.2 与 main 未更改，不启动 HF Job、不扩样、不自动训练。
