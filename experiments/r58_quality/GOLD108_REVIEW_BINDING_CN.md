# Gold108 历史双审证据绑定（只读）

本工具在原有 Gold108 冻结文件中，将 `gold_108_index.csv` 和 `dual_accept_review_evidence_108.jsonl` 按 candidate_id 绑定，并交叉核验 blind_id、story_number、两位 Reviewer 的 ACCEPT、五维评分和证据非空。只输出聚合计数，失败时 HOLD，不能读取 R50 题文。

运行：

```bash
python3 -m unittest discover -s experiments/r58_quality -p 'test_gold108_review_binding.py' -v
python3 experiments/r58_quality/gold108_review_binding.py --repo-root "$PWD"
```

**这不是新的 Quality-v1 双审。** 旧五维记录可作为审核来源，但不能伪造成六维评分或声明 Reviewer 独立性已被证明。目标 SHA256 在 Gold108 index 中有独立字段；Gold108 冻结 JSONL 的 metadata 字段不统一，不能因缺少 `target_sha256_utf8` 就判为没有目标哈希。之后还需和目标文本重新计算的 SHA256 做对照，并核对完整世界关系及派生上下文。历史曝光 Gold 可作为 Train 候选但不可冒充新密封评测题。

不修改原 Gold、不生成训练数据、不开启 HF / GPU / Provider 审计。所有真实训练准入仍为 0。

世界 ID 缺失属于独立的隔离 HOLD，不取消已核验的旧双审绑定；缺失记录不得被默认当成新世界，须先由冻结来源或同一可信索引补足对应关系。
