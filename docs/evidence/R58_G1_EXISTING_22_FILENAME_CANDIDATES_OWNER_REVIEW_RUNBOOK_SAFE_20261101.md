# R58 G1 — 复用此前 22 个 PRIVATE 文件名候选，不重复自动发现（SAFE）

日期 2026-11-01；Draft PR #7，`r58/roleplay-sft-skill-v01`。

## 已知事实与本次目的

Owner Mac 新预检的正式五行 `g1_evidence_inventory_private.csv` 全部 `MISSING_SOURCE_REFERENCE`，这是清单**未填来源引用**，不证明来源文件不存在。本轮结果已归档为 `docs/evidence/R58_G1_FIVE_SOURCE_INVENTORY_OWNER_BLANK_SAFE_20261101.json`。

Owner 在 2026-10-30 已执行过 `autodiscover_g1_index_candidates.py` 并报告：语义世界图 8 条、历史 SFT 2 条、R55/R57 开发 19 条文件名匹配；R50 0、其余保护范围 0；不同候选路径共 22 条。**不要再运行 autodiscover，也不得覆盖当时生成的 PRIVATE 清单。**

本轮只复用原始 `g1_index_candidates_autodiscovered_private.json`，严格核对原报告的 8/2/19/0/0 与 22 个不同路径，创建新 PRIVATE Owner Review JSON；不检查这些候选文件的内容、UUID、原始 SHA、训练数据、题目或历史日志。所有初始 `owner_approved_metadata_only_source=false`、`review_status=UNREVIEWED_FILENAME_ONLY`。这些是文件名线索，不能证明有权读取或覆盖全集。

代码与合成测试：

- `experiments/r58_round1/r58_g1_existing_filename_candidates_review_sheet_safe_20261101.py`
- `experiments/r58_round1/test_r58_g1_existing_filename_candidates_review_sheet_safe_20261101.py`（7 个纯合成测试，Owner Mac 尚未执行）

## 在已配置上游的 R58 工作区执行

```bash
git pull --ff-only
python3 -m unittest discover -s experiments/r58_round1 \
  -p 'test_r58_g1_existing_filename_candidates_review_sheet_safe_20261101.py' -v
python3 experiments/r58_round1/r58_g1_existing_filename_candidates_review_sheet_safe_20261101.py \
  --repo-root "$PWD"
```

正常只输出 SAFE 计数；在下列已存在的 Owner PRIVATE 0700 目录中新建且只允许新建 0600 JSON 文件：

`~/.storyforge-r58-private/round1_pilot_20261030/g1_existing_candidates_owner_review_PRIVATE_20261101.json`

如果旧候选文件缺失、原始计数漂移、文件权限不安全，或者新输出已存在，则脚本返回固定 SAFE HOLD（退出 42）。**不要删除、覆盖旧回执来重试**；不分享任何 PRIVATE 具体路径、候选文件名、UUID 或内容。

下一步需由 Owner 在本机审阅新 review JSON 的候选路径，逐一确认哪些是允许只读的**元数据专用索引**，并有真实冻结 revision、覆盖截止时点和 scope 全集证明。不能因文件名含 `index` / `report` 自动填 `OWNER_COVERAGE_ATTESTED`。原始五行清单不由此脚本修改。

R50 目录不扫描；`other_protected_or_holdout` 仍无命名线索，不代表不存在。世界身份以 Owner 的 RolePlay story UUID 键为准，但同 UUID 比对仍需完整来源集合。若无可靠元数据来源即停止 HOLD，不读取正文。

**门禁：** G1=HOLD、G2=HOLD、G3=NOT_STARTED；Train/Validation/Teacher=0；`expansion_allowed=false`。没有新的 HF Job、GPU、训练、推理、扩样、Skill 改动或 main 合并。
