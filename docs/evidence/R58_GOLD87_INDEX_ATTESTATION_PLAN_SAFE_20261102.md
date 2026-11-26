# R58 Gold87 历史索引审核事实与后续证据绑定

日期：2026-11-02。Gold192 中的 87 条 Gold87 候选。

## 已确认事实

冻结 Gold87 索引有 87 条：Reviewer A ACCEPT 87，Reviewer B ACCEPT 87，Reviewer C ACCEPT 2、NOT_REVIEWED 85。Owner 历史质量选择 87，但训练准入全部 PENDING_NOT_APPROVED、Split 全部 UNASSIGNED。

A 引用状态：原文或有效压缩引用 80、严格连续引用 6、仅片段匹配建议重引 1。历史相关审查字段分别为 77 条未复验和 10 条目标时刻未验证。

以上仅证明索引记载，不证明 A/B 原始评语已被重新核对，不代表新六维质量通过。

## 只读审计工具

`experiments/r58_quality/gold87_legacy_index_audit.py` 检查冻结索引、身份 SHA、审核状态及分类数量，SAFE 聚合输出，不修改冻结文件、不访问 PRIVATE 或 R50、不启动 GPU。

```bash
git pull --ff-only
python3 -m unittest discover -s experiments/r58_quality -p 'test_gold87_legacy_index_audit.py' -v
ruff check experiments/r58_quality/gold87_legacy_index_audit.py experiments/r58_quality/test_gold87_legacy_index_audit.py
python3 experiments/r58_quality/gold87_legacy_index_audit.py --repo-root "$PWD"
```

预期状态：`GOLD87_INDEX_ATTESTATION_ONLY__REVIEW_EVIDENCE_UNBOUND`。

下一步应先定位可信的 Gold87 历史 A/B 审核原始证据，再按匿名候选身份、世界身份、目标哈希严格绑定。不能拿冻结索引中的 ACCEPT 代替历史评语，也不能沿用 Gold108 不同结构的证据合同。Gold192 范围和 Quality-v1=0 不变。
