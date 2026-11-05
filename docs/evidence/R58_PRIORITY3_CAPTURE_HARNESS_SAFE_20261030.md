# R58 Priority3 — 私有隔离捕获工具验证（SAFE，2026-10-30）

**终态**：`PRIVATE_CAPTURE_HARNESS_SYNTHETIC_PASS__HF_CAPTURE_NOT_STARTED`

## 目标
前一轮已在数据库内完成 3 条来源的批准历史故事卡、检查点、历史 24 条消息和 Assistant 目标 SHA256 计算，但这些指纹**没有在私有目录持久化**。本轮修复“只有 SQL + 手工 runbook、没有拒绝覆盖的源包捕获器”的问题。

## 本轮可核验证据

- 更新 `experiments/r58_roleplay_replay/PRIVATE_PRIORITY3_QUARANTINE_EXPORT_TEMPLATE.sql`：每个来源记录携带历史批准事件 `approval_at`，不能用未来获批的故事卡回填历史目标。**PostgreSQL 只执行 `EXPLAIN` PASS，未运行包含原文的 SELECT**。
- 新增 `experiments/r58_roleplay_replay/capture_priority3.py`：输入 SQL JSONL，核对严格 3 条分别覆盖作者、现公开、旧公开三个路径；校验 story/target 唯一、批准/检查点/前置消息时点、24 completed、账本后续更新 0。拒绝覆盖、符号链接、非 0700 私有父目录。
- 运行成功时在新私有目录内保存 `source.private.jsonl`、`manifest.private.json` 及末尾标记 `CAPTURE_COMPLETE`。manifest 记录原始 JSONL 文件级 SHA256 和每条批准卡、检查点、history24、target 指纹；这些本身带 source ID，因此**是 PRIVATE，不能放入 GitHub**。
- 新增 `test_capture_priority3.py`：在本地隔离环境使用虚构 JSONL 运行 **17/17 单元测试 PASS**。测试包括有效捕获、禁止覆盖、异常状态、三路径不齐、故事 ID 重复、私有权限、路径符号链接、JSON 损坏、过大文件、时点倒置等。
- Github 文件完成提交与可读性检查，但 **没有远端 CI/HF 环境的生产数据运行结果**。

## 尚未完成

1. 不能把此次在本地合成数据上的 PASS 写成“HF 私有源包已冻结”。目前只读 Supabase 已核验数据库侧数据存在；**没有运行实际私有内容导出**。
2. 没有原始模型 HTTP 请求与真实部署环境的可信日志，因此 `BYTE_EXACT_PASS=0`。
3. 仍未完成世界别名保护、R50 元数据泄漏、质量双审、Train/Val 划分和 CPU Collator。**Dataset v0.4 Train 0 / Val 0**。
4. 当前实验脚本不属于 Skill 正式发布；保留用户“完整流程跑通后再改 Skill”的约束。

## 下一步

在具备用户批准的受控 HF 私有环境和**私有只读 PostgreSQL 访问**后，先使用 `PRIVATE_CAPTURE_RUNBOOK_CN.md` 命令跑合成测试，再将 SQL 结果通过管道输入捕获器，验证真实输出 3 条及 `CAPTURE_COMPLETE`，并保存私有 manifest；严禁提交私有源数据至仓库或输出到对话。随后才能开始静态/动态 Prompt 重放。

本轮未启动 HF Job，没有运行任何含内容的数据库 SELECT，没有读取 R50，也没有更改 Supabase。PR #7 继续 Draft，Skill v0.1 不变。
