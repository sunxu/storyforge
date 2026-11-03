# R58 RolePlay → StoryForge SFT Skill v0.1.14

本目录定义 StoryForge RolePlay / Quality-v1 工作流的 AI 执行顺序与安全边界。它不是数据库自动导出器、质量评审模型或训练器；不会自动连接生产数据库、写入 GitHub、运行推理或启动 GPU Job。

## 固定执行顺序

1. 查找已有工具和证据。
2. 优先复用共享核心、适配器、有效 SAFE 回执与 checkpoint。
3. 只有通用能力缺失时才扩展共享核心，项目差异保持为薄适配器。
4. 添加合成回归测试，覆盖成功、失败、隐私、幂等和不可覆盖行为。
5. 更新 Skill 执行顺序与技术规范。
6. 验证差异、测试、manifest 和权限边界，再报告结果。

## 权威文档

- [AI 执行顺序与门禁](SKILL.md)
- [HF Token Preflight 完整技术规范](../../docs/standards/HF_TOKEN_PREFLIGHT_REUSE_CN.md)
- [R58 GPU Review / Batch Quote Repair 完整技术规范](../../docs/standards/R58_GPU_REVIEW_QUOTE_VALIDATION_CN.md)
- [R58 私人审核证据复用规范](../../docs/standards/R58_PRIVATE_REVIEW_EVIDENCE_REUSE_CN.md)
- [Quality-v1 主线计划](../../docs/plans/R58_LORA_QUALITY_FIRST_MAINLINE_20261101.md)
- [唯一共享 Token 核心](../../src/storyforge_dataset/token_preflight.py)
- [统一 Gold Quality Pipeline Manifest / CLI](../../docs/standards/GOLD_QUALITY_PIPELINE_CN.md)
- [R59 Strict28 历史上下文恢复](../../docs/R59_STRICT28_HISTORY_RECOVERY_CN.md)
- [共享历史恢复核心](../../src/storyforge_gold_quality/history_recovery.py)

完整算法、Schema、失败码、缓存身份、checkpoint 规则和复现步骤只维护在对应技术规范及共享源码中；不要在 Skill 或 README 复制实现。统一 Gold Quality Manifest 仅作为私有 append-only 事件账本和编排入口，不替代来源、世界隔离、质量或训练准入门禁。

## 安全边界

- RolePlay 数据库只读；PRIVATE 原文、Owner crosswalk、逐案标识和模型原始输出不得进入普通 GitHub、Job 日志或聊天。
- R58 私人材料统一根目录为 `$HOME/.local/share/storyforge/r58/`；私人任务/Manifest 的实际路径必须先按技术规范只读定位，不能把历史预期路径当作已存在文件。
- R50 密封测试正文不得访问或用于训练、开发、调参或 checkpoint 选择。
- 模型 Tokenizer / Chat Template 预检在 HF CPU 执行；GPU 推理、评审和训练需要单独明确授权。
- Token PASS、结构 PASS 或模型评审 PASS 均不自动构成 Quality-v1 训练准入。

## 历史上下文恢复\n\nR59 的共享历史恢复核心与 Strict28 适配器按目标时点、Session lineage、fork cutoff、摘要覆盖范围和历史版本时间戳恢复上下文。它不重建历史 Provider System Prompt，不把当前故事快照当作历史版本，也不构成质量准入。\n\n## 合成测试

在仓库根目录运行：

```bash
python3 -m unittest discover -s skills/storyforge-roleplay-sft/tests -p 'test_*.py' -v
```

测试仅使用合成数据，不访问生产数据库、私人故事、HF 模型权重或 GPU。完整 R58 合成测试由仓库的 scoped GitHub Actions workflow 执行。

## 当前 R58 状态（2026-11-02）

Batch Quote Repair v2 / checkpoint v3 A/B GPU Pilot 已完成：A/Qwen 2/2 PASS，B/GLM 1 PASS + 1 HOLD；4 个 checkpoint 通过 CPU 身份和引用复核。只有一个共同配对样本，不能据此判断模型整体优劣。Gold195 Grok Web 三案试点也已结案：2 案双审暂定通过但语义仍 HOLD，Case02 严重争议未决；3/3 历史 Manifest 身份匹配，192 条不在该 Manifest 中。未证明文学质量/审核者独立性/世界隔离；其余 60 条没有 Grok 外发授权，132 条 Assistant-first 语义策略未解决。Quality-v1 admission=0，训练未授权。
