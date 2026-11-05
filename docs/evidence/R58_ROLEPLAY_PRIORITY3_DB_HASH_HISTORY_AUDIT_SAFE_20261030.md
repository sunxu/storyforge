# R58 Priority3 — 数据库内 SHA256 与历史重放证据审计（SAFE）

审计日期：2026-10-30。RolePlay 源码固定于 `sunxu/RolePlay@e9fe29c42434caeb0bac5acc91845ab4741ecb2b`。本次 SQL 查询只返回**聚合计数**；未返回消息 ID、用户 ID、故事卡、内容或 SHA256 十六进制值。

## 执行结果

沿用上轮已选出的 3 个优先位置（作者稿、当前读者公开稿、历史旧公开稿各 1 个）。Supabase READ ONLY 内部实际计算以下字段的 SHA-256：

| 项目 | 数据库内摘要成功 |
|---|---:|
| 目标之前的审核批准故事卡 `snapshot.source.v2Data` | 3 / 3 |
| 目标之前的 V2 检查点 JSON | 3 / 3 |
| 每条目标前最近 24 条数据库历史消息（含内容，按序 JSON） | 3 / 3 |
| 当前完成的 Assistant 目标文本 | 3 / 3 |
| 审核 `content_revision` | 3 / 3 有 |

**注意：SHA-256 使用 PostgreSQL `jsonb::text` 的 UTF-8 规范化表示，属于数据库内容指纹，而不是生成请求原始传输字节。更重要的是，尚未把每条样本的原始内容及 hash 持久化到 HF 私有 Bucket，因此不允许宣布“已冻结”。**

## 历史账本核查

3 个目标在当前数据库均存在 24 条已完成的前置消息，总计 **72 条**。这 72 条均在目标生成时刻之前有账本事件，且未找到其在目标生成之后的新账本更新。可见账本未显示这些旧正文与当前正文不同。**这不证明账本从每条消息最初创建起完整保存了全部字节变化。**

## 实际历史窗口长度：3/3 获得结构一致证据

核查已提交源码：
- `src/app/api/chat/v2/route.ts` 的默认历史上限 `PRUNE_MAX_KEEP_MESSAGES=12`，数据库有界预读上限为 24；
- `src/lib/story-v2/summary-history-window.ts` 在已有摘要时选取最多 12 条，再用 `alignHistoryWindowToUser()` 从第一条 User 记录开始；
- `src/lib/story-v2/history-window.ts` 实现这一首条 User 对齐。

对实际 3 条目标：
- 历史检查点的 `last_summary_turn` 均为正值；
- 最近 12 条消息状态均为 `completed`，角色严格交替；
- 这 12 条以 Assistant 开始，第二条是 User，最后一条是 User；
- 去掉第一个 Assistant 后按当前源码计算为 **11 条**；3 条附近成功推理指标均显示 `historyMsgCount=11`。

这是对历史窗口**数量和结构**的交叉证据，而不是逐字验证或精确 request_id 关联。历史滚动摘要可能在目标之前更新，超管评估 header、重新生成、反复读 scrub、当前 User 注入也可能影响实际输入。

## 事件状态链证据

- **当前公开稿读者**：当前目标的 `v2EventRuntimeBefore` 与上一条已完成 Assistant 的 `v2EventRuntimeAfter` **JSONB 完全相等**。
- **旧公开稿读者**：同样完全相等，即使其最近检查点与目标前状态不一致，也有更直接的相邻消息证据。
- **作者稿**：目标没有事件前后状态字段，标为 `NO_EVENT_METADATA`，不将其视为事件链失败。

事件状态连续性 PASS(2/2 可检查)，但角色状态、RAG 内容、译文和完整 System Prompt 仍无字节级证据。

## 未通过的门禁与后续

1. 尚未在 HF 私有 Bucket 固定每个 case 的来源 ID、历史审核版、检查点 ID、各源字节和 SHA256；当前仅是生产库 SELECT，即时复跑可能选出不同物理消息。
2. 3 条中 2 条目标早于 2026-10-29 固定源码提交；线上当时的部署 commit 尚未获取。没有准确的 locale、模型请求 body、rollout 配置、RAG 结果快照、Gemini/relay 提交字节和真实 request hash。
3. 完整模型请求字节哈希对照目前 `PASS=0`。无历史原始请求可比对时，只能降级 `RECONSTRUCTED_WITH_EVIDENCE`，不能编造 `BYTE_EXACT_PASS`。
4. 尚未完成独立世界/保护集曝光审计、质量双审、Owner 逐批准入与 HF CPU Collator。

**下一阶段应在 HF 私有运行环境以只读数据库凭据进行受控导出及文件冻结；未得到可信实际请求及动态依赖日志者继续 HOLD。不得将原始对话、作品或逐条 provenance 上传普通 GitHub。**

## 可复现 SQL

- [3 条筛选与会话窗口](R58_ROLEPLAY_PRIORITY3_SOURCE_WINDOW_QUERY_SAFE_20261030.sql)
- [本次服务器内哈希、历史、事件证据综合核验](R58_ROLEPLAY_PRIORITY3_HASH_AND_HISTORY_PROOF_QUERY_SAFE_20261030.sql)

本轮保持 Skill v0.1 不变，PR #7 继续 DRAFT，Dataset v0.4 正式准入 **0**，无 Supabase 写入、R50 访问或 Hugging Face 付费任务。

## 隔离导出工具已准备（但未执行）

新增 [三案例私有隔离查询模板](../../experiments/r58_roleplay_replay/PRIVATE_PRIORITY3_QUARANTINE_EXPORT_TEMPLATE.sql) 与 [HF 私有工作区操作手册](../../experiments/r58_roleplay_replay/PRIVATE_CAPTURE_RUNBOOK_CN.md)。数据库已对该私有模板执行**仅 `EXPLAIN`**，解析/规划成功，**从未运行会返回对话正文的 SELECT**。模板约束只读、近检查点、事先审核版本、每个案例 24 条前置消息和无后续账本更新；输出必须保存在 HF 私有隔离目录，且继续标注不是训练样本。当前无 HF Job、无物理 ID 冻结；正式准入仍为 0。
