# 0.1.0 — 2026-10-30

- 增加只读 RolePlay 表结构/故事候选 SQL 模板（不读取正文）。
- 增加 HF 私有环境离线 `shortlist` / `gate` / `freeze` CLI。
- 强制逐案双 Reviewer（声明与证据）、Owner 批准、世界组件隔离、Source/Input/Target SHA256、派生模型谱系；不宣称可以机器证明语义正确。
- Teacher 上限默认 20%，仅允许进入 Train；验证集不得使用 Teacher 产物。
- 不覆盖输出；保护文件模式 0600；摘要不包含原文或逐案 ID。
- 使用虚构样本完成 10 个单元测试。真实 Supabase 数据未导出，正式准入仍为 0（本 Skill 阶段）。
