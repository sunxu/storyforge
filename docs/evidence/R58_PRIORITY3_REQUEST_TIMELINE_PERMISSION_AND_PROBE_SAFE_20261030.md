# R58 Priority3 — 固定 3 案例请求时间线关联（SAFE，2026-10-30）

状态：**新工具已提交，Owner Mac 本机真实执行尚未报告**。没有访问或上传私有故事正文、消息 UUID、SQL payload、哈希或数据库密码。

## 本次权限核验（数据库元数据 only）

在 `r58_export_reader` 下，对 `public.v2_chat_request_events` 的列权限：`request_id`、`occurred_at`、`status`、`duration_ms`、`user_id`、`session_id`、`story_id` 的 SELECT 均为 true。未授予的 `error_code`、`platform`、`is_realtime` 不在本轮 SQL 中使用。

已获 `chat_latency_metrics` 表 SELECT（原有只读权限）。本轮无数据库授权变更。

## 真实源码与数据时序

对照固定源码 `sunxu/RolePlay@e9fe29c42434caeb0bac5acc91845ab4741ecb2b`：

- `src/lib/db/v2-chat-request-event-service.ts` 在请求 **onTerminal** 时使用异步、fire-and-forget 的数据库 insert 记录 `request_id`、`duration_ms`、`user_id`、`session_id`、`story_id` 等字段；
- `src/lib/api-logger.ts` 用 `performance.now()` 计时；
- `chat_latency_metrics` 有 `request_id` 与任务、模型指标，但不能自动推出 `v2_chat_messages.id ↔ request_id` 的主键级映射；
- `v2_chat_request_events.occurred_at` 是**异步终态记录时间**，绝非精确网络请求开始时间；使用其 `duration_ms` 回推起点只是粗粒度线索，不能消除日志异步写入延迟或缺失。

## 本轮工具边界

新增 `experiments/r58_roleplay_replay/audit_priority3_request_timeline.py`：

1. 离线验证现有首次固定来源包、12 项内容指纹及私有权限；
2. 从现有 3 个 target_message_id（不重选故事）在专用只读数据库中定位其目标行，读取该目标行的 user_id 做跨用户过滤；
3. 对同一个 user/story/session 的 `v2_chat_request_events` 检索目标记录时间之前 2 分钟到之后 20 分钟的成功终态事件（上限 101，超出 100 则 HOLD）；
4. 用 `request_id` **精确连接两份日志表**（`v2_chat_request_events` 和 `chat_latency_metrics`），并以事件耗时估算请求时间区间；
5. 只输出每 cohort 的安全计数/布尔值，绝不输出 UUID、正文、digest、模型、绝对时间、SQL 或异常中的私有信息；
6. 无论是否出现唯一时间匹配候选，`exact_target_message_to_request_join=false`、`request_start_time_certified=false`、`provider_request_byte_exact=HOLD` 与 `training_admission=HOLD`。

查询通过本机 `psql` 的 stdin 传入私有目标 ID，强制 `BEGIN READ ONLY`、固定数据库主机/只读用户、`PGOPTIONS=default_transaction_read_only=on`。它不会写入数据库或源包。新工具附带 11 项纯合成测试。

已使用一个**虚构且不存在的 UUID** 经 Supabase 只读连接验证 SQL 的 CTE 和列权限可执行：安全结果 `target_found=false`、候选 0。不是对实际 3 个来源的查询，也不是 Mac 端到端验证。

## Mac 本地执行

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only
python3 -m unittest discover -s experiments/r58_roleplay_replay \
  -p 'test_audit_priority3_request_timeline.py' -v

# 仅在测试全部通过后，先进行离线范围检查：
python3 experiments/r58_roleplay_replay/audit_priority3_request_timeline.py \
  --private-dir "$HOME/.storyforge-r58-private/priority3_source_20261030_first_capture" \
  --plan-only
```

完成这两步且既有只读 PGHOST/PGUSER/PGPASSWORD 仍在安全 Mac 会话中可用后，再执行同一脚本去掉 `--plan-only`。只提交输出的安全聚合 JSON 与测试计数，不上传 SQL/UUID/故事正文/源包。

## 仍然缺失

历史线上部署 commit、请求体及继续/重生成 flags、当时 `last_summary_turn` 会话值、动态记忆与 RAG、实际模型和 locale、post-DB history scrub、最后用户提示注入、API 请求起点与原始 provider request bytes。

本轮只确认列级授权、查询语法与代码提交。**无 SFT 准入升级，Train/Val/Teacher=0，Skill v0.1 不改，PR #7 保持 Draft。**
