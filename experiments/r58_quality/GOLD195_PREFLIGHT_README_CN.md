# R58 Gold195 只读结构预检（Quality-v1）

仅用于对冻结 Gold87 + Gold108 做元数据/消息结构计数，**不产生训练输入、不授予质量准入**。不复用废弃的生产请求精确回放条件。原始 Gold 不修改。

## 使用

在 StoryForge checkout 中运行：

```bash
python3 -m unittest discover -s experiments/r58_quality -p 'test_gold195_preflight.py' -v
python3 experiments/r58_quality/gold195_preflight.py --repo-root "$PWD"
```

输入仅为 `evaluations/v0.2/gold-quality-87/gold_quality_accepted_87.jsonl` 和 `evaluations/v0.2/gold-quality-108/gold_quality_accepted_108.jsonl`。输出只含汇总计数（不含逐案 ID、UUID、内容或哈希）；错误时返回 exit 42 和固定 HOLD 状态。不得将汇总当作实际内容质量或世界隔离审核。

## 已知待办

历史 87 + 108 逐案双接受属于旧五维标准，**不得伪造为新六维双审**。源格式可能以历史 Assistant 起始，且末条为目标 Assistant；必须生成单独版本的派生训练上下文，不能就地修改 Gold。世界 UUID 不等于语义世界组件。R56 已知 163 条曾曝光，仍可能用于 Train，但不能当全新独立测试；其余 32 条也未自动获得密封评测资格。

本脚本**不做**真实 Qwen 16,384-token 测试、ms-swift last_round mask、语义世界隔离、Reviewer 独立性验证、R50 访问或 HF Job。下阶段先将已有审核和源文件按候选绑定，再补齐实际缺口。严格不读 R50 密封题，不启动训练。