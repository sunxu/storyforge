# R58 G1：仅对剩余四个故事核对 R57 Gold195 参考/开发来源（SAFE）

2026-10-31。此前 Mac **88/88 PASS**，5 条冻结候选、1 条历史 SFT UUID 已排除；其余 4 条对 R50 来源编号 16–20 的 5 个 Protected UUID 交集为 **0**，R50 两份来源回执 SHA-1 验证通过。R50 正文未读取。此为 Owner 回报的已验证 SAFE 聚合，不能代表 G1 整体通过。

## 为什么是 Gold195 的 UUID 来源

既有 R57 G2 私有 `R57_G2_WORLD_ALIAS_REVIEW_*_PRIVATE.json` 固定了来自八组历史来源的 **29 个故事 UUID**，其中 27 个已有历史 SFT 精确 UUID 曝光。按来源分组 `GOLD87` 和 `GOLD108` 可区分 **13 个 Gold195 来源故事 UUID**，其中预期 2 个不属于前述 27 个历史已训练 UUID。既然 Owner 已定义 UUID=独立世界，这 13 个来源可作为一组额外的开发/来源暴露世界进行严格排除。读取这些**源计数元数据**，不读取任何 Gold 回复、原始故事或 R50 题目。

这里的“Gold195 来源”不是 R55/R57 所有开发题的完整全集：R47/R48/R55/R57 还使用了来源为 **v0.1 Test 的旧 DEV20 两个世界**，本次工具不读取该 Test 原文，因此也不据此声称已经清除此门禁。

## Owner Mac 一次操作

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only

python3 -m unittest discover -s experiments/r58_round1 \
  -p 'test_*.py' -v &&

ROOT="$HOME/.storyforge-r58-private/round1_pilot_20261030"
python3 experiments/r58_round1/check_r57_gold195_uuid.py \
  --private-sft-holds "$ROOT/g1_prior_sft_uuid_owner_policy_v2_private.json" \
  --private-r50-holds "$ROOT/g1_r50_protected_holds_private.json" \
  --private-discovery "$ROOT/g1_index_candidates_autodiscovered_private.json" \
  --private-output "$ROOT/g1_r57_gold195_source_holds_private.json"
```

本次新增 **9** 项纯合成测试，预期总数 **97**，Owner Mac 运行结果待回报。工具会在本地校验 SFT/R50 两份固定五条私有账本的一致性、R57 29 个 UUID 计数与 Gold195 13 个来源 UUID 的完整性，并只输出聚合 SAFE JSON。私有输出 0600，拒绝覆盖；队列不修改，不增加故事，历史已排除 UUID 不重新进入候选。

## 可能结果

- `r57_gold195_exact_uuid_matches_among_remaining_four` 大于 0：对应旧 Gold195 来源世界保持隔离，不作为新世界训练/评估候选；不补选。
- 为 0：四条与已核验的 Gold195 13 个 UUID 不重叠；**仍不能断言 R55/R57 Dev 全部清除**，因为旧 DEV20 (v0.1 Test) 世界来源以及其他独立保留世界的 UUID 集合未核实。
- 输出表中的 `remaining_without_sft_r50_or_r57_gold_source_uuid_match` 只在三组已核查 UUID 中计算剩余数量，不是 Train/Val 数据准入数。
- 源 schema、计数、文件权限或固定五条账本不一致时 `HOLD`，绝不自动更新 guard flags。

## 余下三项资料

1. 旧 R47/R48/R55/R57 DEV20 的 **2 个 v0.1 Test 来源故事 UUID**：先查已冻结元数据专用索引。不能未经授权把原始 Test 对话正文当作元数据文件上传或输出。
2. 其他独立留出/冻结来源（例如 R56 旧开发目标）：需要来源 story UUID 的元数据版本及覆盖全集说明。
3. 训练曝露 completeness：现有 R57 27 个 UUID 对应 v0.1/R46/R54 冻结八源；确认没有遗漏的其他实际投入训练的故事 UUID，才能给 `prior_sft_clear` 完整标志。

Owner 已确认「所有故事均源于 RolePlay / UUID 为语义世界键」。后续只需故事 UUID 排除，不重做语义别名图。所有剩余 G1 保护 guard 仍 HOLD；R50 原文访问 0；Train/Validation/Teacher 准入 0；G2/G3 尚未开始；最多 5 个故事、20 条回复；PR #7 Draft；不扩样、不自动收费、Skill v0.1 不变。
