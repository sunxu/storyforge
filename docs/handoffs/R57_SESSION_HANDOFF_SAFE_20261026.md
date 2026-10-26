# StoryForge R57 — 2026-10-26 GitHub 安全交接

此摘要只含冻结数目和流程门禁；完整中文对话交接由 Owner 保存为 `StoryForge_R57_Handoff_20261026_CN.md`。本文件**不包含**小说原文、真实世界 UUID、逐条 SHA、私有 Reviewer 文件或 R50 数据。

## 当前实验与工程结论

- GitHub 私有仓库 `sunxu/storyforge`，实验分支 `r57/v03b-data-design`，PR #5 继续 **Draft**。`main` 未合并。需由后续 Agent 重新核对提交、CI。
- G0 实验合同待 Owner 签核。G1 准入/索引工具合成 CPU 测试 PASS，**不是质量或训练准入**。
- G2 冻结 Gold87/Gold108/v0.1 Train65/Val15 四份 Git Blob 完整字节由 CI 回放 PASS。Gold195 目标 metadata SHA256 **195/195 PASS**。Gold108 三种元数据字段实际为 `90/15/3`。
- G2 Owner Mac 八源（加 R46 Train49/Val15，R54 Train31/Val9）冻结真实字节核对、14/9/8 与目标/历史交叉精确回放 **Owner-reported PASS**。这是 Owner 本机程序结果，不是新获取的 HF 提供商证明。R46/R54 compiled Trainer 无 metadata，不可伪造 world ID。
- Gold195 历史 `Train` 精确目标匹配 66，`Validation` 24，两个集合交叉 9；合并 **81** 个，**114** 个 final Assistant 目标未发现精确复用。按两来源：Gold87 20 曝光/67 未匹配，Gold108 61 曝光/47 未匹配。
- R46/R54 四个 compiled split 共 **104 行**，每行 final target SHA256 在 Gold195 唯一命中；可用 Gold 原始 metadata 恢复 observed story UUID（不意味着历史 role/content 相同）。
- 114 无目标精确复用里有 **82 行与旧 SFT 共享原始故事 UUID**，只剩 **32 行不共享旧 SFT UUID**，来自 Gold87 **2 个来源故事**，各 14、18 行；观察到 29 个 UUID（旧 SFT 27 + 额外 Gold 2）。**不同 UUID 不代表独立世界**。
- 各个 v0.1/R46/R54 内部 Train/Val 没有完全相同故事 UUID；但 R46 Train ↔ R54 Validation 跨训练版本仍有相同故事 UUID。
- Owner 已生成语义别名问题表：候选故事 2 × 历史 SFT 世界 27 + 两候选互查 1 = **55 对**；最近返回 `UNREVIEWED=55`、人工已审核 **0/55**，语义别名/world-component isolation **HOLD**。Owner 还需真实故事角色关系证据及独立复核。
- G3 Gold195 来源元数据预筛 PASS，但 **195 条独立权利/质量/年龄/同意/目标时点设定审核未完成**；`Dataset v0.4 admitted = 0`，R54 v0.3-A NO-GO 未更改。
- R55 四条冻结 HOLD 保留；**R50 禁止访问**。无 GPU/HF/训练/模型晋升/PR merge。

## 当前已有的安全工具

在 `scripts/`：
`r57_g2_mac_preflight.py`、
`r57_trainer_exact_replay.py`、
`r57_g3_private_exposure_ledger.py`、
`r57_g2_target_anchored_world_audit.py`、
`r57_g2_owner_world_review_roster.py`、
`r57_g2_alias_pair_review.py`、
`r57_g2_private_candidate_source_locator.py`、
**`r57_g2_alias_name_hints.py`（最新待 Owner Mac 实测）**。

具体 Owner 操作见 `docs/R57_G2_OWNER_WORLD_NAME_HINTS_CN.md`、`docs/R57_G2_OWNER_ALIAS_55_PAIR_REVIEW_CN.md`、`docs/R57_G2_MAC_OWNER_EXECUTION_20261026_CN.md`。

## 下一步：在 Owner Mac 本地生成 29 个故事可读索引

务必在既有 StoryForge 仓库根目录、无未保存修改状态下执行：

```zsh
git fetch origin r57/v03b-data-design
git switch r57/v03b-data-design
git pull --ff-only origin r57/v03b-data-design

PRIVATE="$HOME/.local/share/storyforge/r57/private"
umask 077
python3 scripts/r57_g2_mac_preflight.py --repo-root "$PWD" --private-root "$PRIVATE"

NAME_INDEX="R57_G2_WORLD_NAME_HINTS_$(date +%Y%m%d_%H%M%S)_PRIVATE.json"
python3 scripts/r57_g2_alias_name_hints.py \
  --repo-root "$PWD" --private-root "$PRIVATE" \
  --create-private-name "$NAME_INDEX"
```

工具固定读取 8 份冻结源并重算 pin，安全 stdout 只含计数；**所有真实故事名/来源/UUID 的索引都只存 Owner Mac 仓库外的私有目录（0600）**。不得自动打开源文件正文、自动批准不同 UUID 或批量填 55 条 DISTINCT；保留 `UNREVIEWED` / `HOLD`。

## CI 基准

2026-10-26 交接前检查：R57 CPU 专项 workflow 运行 [#40292709690](https://github.com/sunxu/storyforge/actions/runs/40292709690) **178 tests PASS**，全仓 CI [#40292709657](https://github.com/sunxu/storyforge/actions/runs/40292709657) **FAIL（202 Ruff，最近无 R57 文件违规）**。后续以新的 SHA/Actions 为准。
