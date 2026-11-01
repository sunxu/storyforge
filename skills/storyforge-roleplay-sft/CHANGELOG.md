# 0.1.2 — 2026-11-01

- 将 CPU Token 预检失败诊断细化为安全阶段码：区分 Chat Template 渲染失败、Token ID 结构无效及其他编码失败；异常原文不进入日志。
- 更新 Skill 执行顺序与技术文档：先复用共享核心，修复后补充合成回归测试，再刷新私人 STAGE。
- 明确用户要求 HF CPU 预检工作流时无需逐 Job 费用授权；GPU 推理/训练仍须单独明确授权。
- 不修改私人输入或已有回执；不执行推理、GPU 或训练，不授予质量准入。

# 0.1.1 — 2026-11-01

- 将仓库 `AGENTS.md` 的“优先复用 HF CPU Token 预检”落入 Skill 执行顺序：先查现有工具和可信 SAFE 回执，再决定是否运行付费 Job。
- 指向唯一共享实现 `src/storyforge_dataset/token_preflight.py`、历史 R50/R53/R58 CPU132 证据与 R58 13 条双审适配器，明确不在 Skill 内复制底层算法。
- 明确 Mac 只做数据准备和 SAFE 回执复核，真实 Tokenizer 在 HF CPU 运行；严格检查输入、序列化 Prompt、模型/版本、thinking、输出预算及共享核心代码的匹配才允许复用。
- 区分 Token 预算与真实 ms-swift Collator/last_round 训练标签检查；两者都不构成文学质量或数据准入。
- 修正过时的生产请求精确回放 G2 门禁对 Quality-v1 LoRA 主线的干扰，保留旧代码和冻结证据但禁止伪造旧 G2 PASS。
- 保持私人 A/B 隔离、R50 保护和 HF CPU/GPU 分别授权；本次更新不发起 Job、不给质量准入。

# 0.1.0 — 2026-10-30

- 增加只读 RolePlay 表结构/故事候选 SQL 模板（不读取正文）。
- 增加 HF 私有环境离线 `shortlist` / `gate` / `freeze` CLI。
- 强制逐案双 Reviewer（声明与证据）、Owner 批准、世界组件隔离、Source/Input/Target SHA256、派生模型谱系；不宣称可以机器证明语义正确。
- Teacher 上限默认 20%，仅允许进入 Train；验证集不得使用 Teacher 产物。
- 不覆盖输出；保护文件模式 0600；摘要不包含原文或逐案 ID。
- 使用虚构样本完成 10 个单元测试。真实 Supabase 数据未导出，正式准入仍为 0（本 Skill 阶段）。
