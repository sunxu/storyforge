# R58 Gold195 冻结目标与来源核验

目标是验证冻结 Gold87/Gold108 中最后一条 Assistant 目标与冻结目标 SHA256 是否逐条一致，并确认可在不改原始文件的前提下提取当前 User 与目标 Assistant。

```bash
python3 -m unittest discover -s experiments/r58_quality -p 'test_gold195_target_source.py' -v
python3 experiments/r58_quality/gold195_target_source.py --repo-root "$PWD"
```

Gold87 对照每条 metadata.target_sha256_utf8；Gold108 对照原索引 gold_108_index.csv 中 candidate_id 与 target_sha256。只读、只输出安全汇总计数，异常 HOLD，不导出原文/案例 ID/哈希，也不生成训练数据。

**注意：**检验结果不是训练准入。若冻结记录以 Assistant 开头，必须按单独受控的派生版本处理，不要把历史 Assistant 当成 System，也不要生成伪造世界卡。没有可信世界卡、语义世界组件隔离、两份真实六维审核、16K Token/last_round Mask 验证，不得晋升到训练。Gold108 已知有 3 条故事 UUID 缺口，应独立保持世界隔离 HOLD。绝不接触 R50 密封题文。
