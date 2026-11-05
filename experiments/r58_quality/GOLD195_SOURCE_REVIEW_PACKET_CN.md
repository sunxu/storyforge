# R58 Gold195 — 原文忠实的审核候选包（非训练数据）

本阶段聚焦**可审核的 Gold195 上下文**，不再调查历史生产请求字节。目标 SHA256 已由 `gold195_target_source.py` 验证。

## 默认只读预检（GitHub Actions / Owner Mac 均适用）

```bash
python3 -m unittest discover -s experiments/r58_quality -p 'test_gold195_source_review_packet.py' -v
python3 experiments/r58_quality/gold195_source_review_packet.py --repo-root "$PWD"
```

仅输出 SAFE 汇总；不写入 JSONL。脚本识别历史 Assistant 开头造成的上下文审核缺口，不删除其内容，不捏造 System Prompt，保留 3 条 Gold108 缺少 UUID 的世界身份 HOLD。

## 生成私人本地审核候选（不进入训练）

仅在受控 Mac/私有环境，明确准备审核文本时执行。输出不得位于 Git 仓库，所在目录需为权限 0700 的新建私有目录，例如：

```bash
mkdir -m 700 -p "$HOME/storyforge-review-private"
python3 experiments/r58_quality/gold195_source_review_packet.py \
  --repo-root "$PWD" \
  --private-review-output "$HOME/storyforge-review-private/gold195-review-source-v1.jsonl"
```

输出只能创建新文件，权限 0600，无法覆盖现有文件；记录包含真实故事上下文、当前 User、完整冻结 Gold target、目标及来源指纹、逐案 HOLD 原因。不要上传到 GitHub、ChatGPT 或公开 CI 日志。

## 继续数据主线

1. 从授权的实际世界/人物设定来源绑定 System/卡片版本；不用还原线上 Provider 请求原样。
2. 对 132 个以历史 Assistant 开头的候选明确审核截断前文，不把孤立首条 Assistant 当 System，不暗中丢弃。
3. 以语义世界组件证明 Train/Validation 和保护集不重叠；3 条缺失 UUID 不可自动补假值。
4. 复用历史五维双审证据，独立补齐六维真实审核，不可伪造评分或 Reviewer 身份。
5. 对实际 Quality-v1 通过的派生版本执行 Qwen 16K / ms-swift `loss_scale: last_round` CPU 预检，再请求 GPU 单独授权。

**注意：此包不是 Quality-v1 合同所需的最终 messages+target 训练候选，所有 195 条质量准入仍 HOLD。** 原始 Gold 不修改，R50 密封题不触碰，HF Job 不启动。

## 同源目标哈希绑定的 UUID 补全

Gold108 原索引缺失 UUID 时，可以从 Git 冻结的 R02 `candidate_card_version_evidence_108.csv` 读取已记录的 `story_id`，**仅在 candidate_id 和目标 SHA256 完整相等、全部 108 条一一对应、且不与非空主索引冲突时**补全派生内存索引，不改动任何原件。该 UUID 补全不等于语义世界隔离审批，未通过保护集检查者仍 HOLD。
