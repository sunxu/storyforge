# R58 RolePlay → StoryForge SFT Skill v0.1.8

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
- [Quality-v1 主线计划](../../docs/plans/R58_LORA_QUALITY_FIRST_MAINLINE_20261101.md)
- [唯一共享 Token 核心](../../src/storyforge_dataset/token_preflight.py)

完整算法、Schema、失败码、缓存身份、checkpoint 规则和复现步骤只维护在对应技术规范及共享源码中；不要在 Skill 或 README 复制实现。

## 安全边界

- RolePlay 数据库只读；PRIVATE 原文、Owner crosswalk、逐案标识和模型原始输出不得进入普通 GitHub、Job 日志或聊天。
- R50 密封测试正文不得访问或用于训练、开发、调参或 checkpoint 选择。
- 模型 Tokenizer / Chat Template 预检在 HF CPU 执行；GPU 推理、评审和训练需要单独明确授权。
- Token PASS、结构 PASS 或模型评审 PASS 均不自动构成 Quality-v1 训练准入。

## 合成测试

在仓库根目录运行：

```bash
python3 -m unittest discover -s skills/storyforge-roleplay-sft/tests -p 'test_*.py' -v
```

测试仅使用合成数据，不访问生产数据库、私人故事、HF 模型权重或 GPU。完整 R58 合成测试由仓库的 scoped GitHub Actions workflow 执行。

## 当前 R58 状态（2026-11-02）

Batch Quote Repair v2 / checkpoint v3 A/B GPU Pilot 已完成：A/Qwen 2/2 PASS，B/GLM 1 PASS + 1 HOLD；4 个 checkpoint 通过 CPU 身份和引用复核。只有一个共同配对样本，不能据此判断模型整体优劣。Quality-v1 admission=0，训练未授权。
