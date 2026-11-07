# R60 Gold192 模型真实输入证据来源盘点：P0 第一轮源码核验

日期：2026-11-07
RolePlay 来源：`sunxu/RolePlay@ccdf2e8dc2723f481cd0392883bc359e9e341c66`
StoryForge 来源：`r60/gold192-history-v3-adapter`
审计范围：RolePlay GitHub 代码及 SQL 迁移定义；**未访问生产消息正文、对象存储或私有 Gold192 Case；未执行数据库查询**。

## 一、直接结论

**当前已找到构建/发送模型请求的链路，以及若干旁证型日志/归档。尚未从已检查代码发现一个可证明“全部生成尝试的完整最终发送请求体与最终 Assistant 回复不可混淆绑定”的通用持久化机制。**

这不证明历史 Gold192 没有这样的证据：生产库、Relay、其他归档、对象存储或未扫描代码中仍可能有记录。此处仅标记 `SOURCE_CODE_EVIDENCE_NOT_YET_ESTABLISHED`；**不把任何一个 Case 提前判成 A/B/C/D。**

数据库历史、模型输入构建、最终出站 Payload 和 Provider 收到的请求是不同的证据层级。若 Provider 不提供输入回显，本地出站记录也不能称为 Provider 独立校验了请求内容。

## 二、候选来源登记

| 来源 | 可从源码确认的能力 | 缺口/风险 | 下一步 |
|---|---|---|---|
| `v2_chat_reply_jobs` | [20260820 迁移](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/supabase/migrations/20260820213000_v2_durable_reply_jobs.sql#L3-L49) 有 `request_envelope`、`model_id`、`attempt_count`、Job 状态/租约等 | request envelope 注释说明是 Worker 重放信封，**不等于**最终模型 messages；是否承载有效旧请求、关联到最终回复仍未知 | 只读查 schema / 有无记录 / 生命周期 / Worker 使用点；禁止提取正文至 SAFE |
| `chat_abnormal_snapshots` 及 Diagnostic Archive | [snapshot service](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/src/lib/db/chat-abnormal-snapshot-service.ts#L130-L228) 有 request_id/relay_request_id、异常分类、上下文、记忆等；部分异常档案保存较长内容 | DB 常规 history_preview **最多 6 条、每条 300 字符**；特殊 `upstream_content_rejected` / retry / rollback 记录与生成尝试的对应程度不同；不能视为完整 Provider payload | 优先检查 request/relay ID 与 Gold target 的连接能力，确认档案保留和截断情况 |
| `Chat Archive` | [chat-archive.ts](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/src/lib/archive/chat-archive.ts#L20-L42) 保存 append/edit/delete/delete-all/session-hard-delete 的消息事件，运行时开关可关闭 | 是聊天消息操作归档，不包含发送时的裁剪后 System、最终 messages 或 Provider 参数；写入采用不阻断主流程的异步设计 | 可作为 C/B 的历史版本旁证，不能单独作为 A |
| `Chat Latency / Relay correlation` | [chat_latency_attempt_trace](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/supabase/migrations/20260807103000_chat_latency_attempt_trace.sql) 明确禁止存 Prompt/响应正文；[relay correlation](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/supabase/migrations/20260809190000_chat_relay_correlation.sql) 增加请求/trace ID | 能帮助找生成尝试，但不是请求全文 | 查 requestId/relayId 与最终 assistant message 的稳定联结字段及留存时间 |
| `/api/admin/prompt-debug-v2` | [debug route](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/src/app/api/admin/prompt-debug-v2/route.ts#L98-L251) 重建并预览 System、历史、记忆 | **当前/调试时刻的模拟构建**，不能自动声称与过去某个 Provider 请求逐字相同；可能缺少真实裁剪与当时 Runtime 快照 | 仅作为 B 类重建代码参考，不作为 A 类证据 |
| `SceneOpenAIProvider` 及 Provider adapters | [scene-openai-provider.ts](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/src/lib/ai/scene-openai-provider.ts#L50-L123) 构建包括 `messages`、模型、max_tokens、temperature 等 Payload，并序列化出站；读取响应 request ID | 代码里可看到出站边界，但**未看到把该完整出站 Payload 可靠持久化的步骤**；另有不同协议/路由需单独审查 | RolePlay P0 应在各 Provider adapter 最接近网络出站处统一留证，保留每 attempt 的参数和输出映射 |

## 三、已经确认导致数据库历史 ≠ 模型输入的处理

- [chat/v2 route 历史获取](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/src/app/api/chat/v2/route.ts#L2280-L2410)：从 DB 获取 `completed` 历史，过滤 regenerate 尾部，按摘要裁剪，剔除 `legacy_uncardd` 历史，清洗 Assistant 结构化残留及被误标 completed 的策略拒绝。
- [Runtime Prompt 组装](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/src/app/api/chat/v2/route.ts#L2500-L2552)：Runtime Base 灰度、角色卡、Tail、输出语言限制；其后还可能拼接每轮记忆和警示。
- [降密重试](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/src/app/api/chat/v2/route.ts#L4580-L4670)：`buildReducedRetryMessages(messages)` 明确改变历史窗口。
- [自动续写](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/src/app/api/chat/v2/route.ts#L4265-L4348)：新 attempt 会追加此前 Assistant 片段及续写指令。
- [输出校验重试](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/src/app/api/chat/v2/route.ts#L4850-L4950)：新的 retryMessages、原草稿异常快照、重新生成与最后输出入库之间还存在多个转换步骤。
- [最终落库](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/src/app/api/chat/v2/route.ts#L5030-L5080)：持久化的是通过输出审查后的最终内容；被 moderation 替换的兜底正文不能错误归因于某个 Provider 的原始输出。

**结论：一条最终 Assistant 消息不一定唯一对应一个原始 Provider completion；多段 auto-continue、重试及 moderation 改写必须显式记录。** Gold192 SFT 标注需进一步定义可训练的目标类型（单次 Provider 输出 vs 经组合/后处理的完整交付回复），否则即使保留全部发送体也可能错误配对。

## 四、Gold192 P0 下一次只读调查的顺序

1. **证据源存在性元数据**：以 production 只读目录/归档 manifest 判断 `v2_chat_reply_jobs`、abnormal snapshots、chat archive、Relay 提供的历史窗口是否存在；只返回是否存在、时间范围、数量、截断/保留策略，不读取正文；对不存在的来源写 `SOURCE_UNAVAILABLE`。
2. **目标绑定**：通过 Gold192 冻结 locator，逐条验证目标 message 与 request/attempt ID 的一对一或一对多关系；失败只记 `TARGET_ATTEMPT_LINK_UNVERIFIED`。
3. **请求完整性**：检查实际发送 Payload 是否覆盖 System/历史/记忆/重试/Provider 路由、参数和版本，是否有 hash/时间及不可篡改证据；不把简单的 `request_envelope`、latency ID 或诊断预览误当完整出站 Payload。
4. **目标语义**：若经过自动续写/重试、内容合并/清洗/安全替换，输出应标记为 `COMPOSITE_OR_POSTPROCESSED_TARGET` 或 `PROVIDER_OUTPUT_MATCH`；前者默认 HOLD 直到定义专门可复现的 SFT 监督规则。
5. **A/B/C/D**：只有完成个案真实证据核实才分类。未访问或暂查不到来源记 `UNKNOWN_NOT_REVIEWED`，不是 D。先形成聚合 SAFE，无任何私有标识。

## 五、运行/安全边界

- 未读取 Gold192 私有包、目标消息内容或历史模型请求正文；**当前 A/B/C/D 数量未知**。
- 没有生产数据库接入或使用 Reply Job/归档的实际保留证明；不能声称现有来源覆盖多少历史 Gold192。
- 不再把全量 Ledger T1–T7 作为全部输入证据审查的前置；对使用 Ledger 逆向恢复数据的旧适配器，继续保持 fail-closed。
- Source identity Pilot7、Gold192 质量冻结、11 exclusion、R50 隔离、Owner 审批、world isolation、历史训练曝光等门槛不变。
- `quality_v1_admitted=0`、`training_authorized=false`、`gpu_started=false`、`database_modified=false`。

## 六、Supabase 实际数据库 Catalog 只读核验（2026-11-07）

通过已连接的 Supabase **只读 Catalog 查询**验证了公共 schema 的表名/字段，未读取任何业务表数据行、请求正文、用户标识、故事 ID、JSONB 内容或消息正文。

- 当前 Connector 角色为 `supabase_read_only_user`，**不是** Gold192 历史恢复适配器要求的 `r58_export_reader`。此次仅查询 `pg_catalog.pg_class/pg_attribute/pg_namespace` 元数据；不能据此替代 R60 受限角色/隔离级别验收，不能使用此连接进行 Gold192 私有行级取证。
- 数据库中实际表名是 **`public.chat_abnormal_snapshot`**（单数），而不是初步猜测的 `chat_abnormal_snapshots`；字段含 `request_id`、`relay_request_id`、`conversation_context`、`history_preview`、`memory_injection`、`assistant_output`、`continuation_attempts`、`expires_at` 等。结构存在不等于旧记录当前还留存或未截断。
- `public.v2_chat_reply_jobs` 存在，包含 `request_envelope jsonb`、`model_id`、`attempt_count`、`client_msg_id`、`session_id`、`assistant_turn` 等；字段结构存在**不意味着**保存了 Provider 已出站完整 Payload 或当前还能读取 Gold192 的旧 Job。
- `public.chat_latency_metrics` 存在，包含 `request_id`、`relay_request_id`、`relay_trace_id`、`attempt_trace jsonb` 和模型/Token/状态等字段；未发现名为 `request_payload` 或 `prompt_hash` 的对应专用字段。不要从 `attempt_trace` 的存在推断包含请求正文。
- `public.v2_chat_messages` 与 `public.v2_chat_message_ledger` 均存在，但属于数据库历史层而不是实际 Provider 输入证明。
- 在本次限定检索范围（公有 schema 关系名含 abnormal/archive/attempt/prompt/reply_job）内未发现专用完整 Provider 请求归档表。这只是**目录范围内未发现**，不能排除其他表、外部对象存储、Relay 或服务器文件系统中存在证据。

### 后续取证必须遵守的门槛

1. 先确认授权的 `r58_export_reader` 路径、实际生产来源与 RolePlay 当前运行版本；本轮 Catalog 结果只能说明连接目标数据库的结构。
2. 用受控权限做**记录数量、保留区间、字段非空率**的聚合验证，再考虑是否和冻结 Gold192 locator 做私有 Join；在权限不匹配时不得继续行级查询。
3. 旧异常快照可能受 `expires_at` 清理；不得假定当前表有覆盖历史日期的数据，也不得因零记录直接把任何 Case 判为 D。
4. 完整对话/请求正文只允许 Owner 私有处理，不进入 SAFE、GitHub、聊天或 CI 日志。
5. 所有分类仍为 `UNKNOWN_NOT_REVIEWED`；本次为 source inventory + catalog metadata 层，不属于 A/B/C/D 个案判定。

## 七、已实现独立 P0 私有证据槽位初始化（不读取生产正文）

新增 [r60_model_input_evidence_seed.py](../experiments/r58_quality/r60_model_input_evidence_seed.py) 和 [合成测试](../experiments/r58_quality/test_r60_model_input_evidence_seed.py)。它读取与 R60 Source Extract 同一目录的冻结 192 条 locator 和 SAFE 记录，校验条数与来源哈希后，在 Owner 私有目录创建 192 条待审核槽位，**全部为 UNKNOWN_NOT_REVIEWED**；不会读数据库、模型请求、故事正文或输出候选训练 JSONL。

注意：`A/B/C/D` 的已证实数量仍然是 `null`（未盘点），不是 0；只确认 192 条待调查，并不宣称已经逐案取证。程序不赋予 Quality-v1 admission。

Owner 在已有的 StoryForge R60 Worktree 执行：

```bash
set -euo pipefail
umask 077
cd "$HOME/workspace/storyforge-r60-ledger-diagnostics"
test -z "$(git status --porcelain)"
git fetch origin r60/gold192-history-v3-adapter
git pull --ff-only origin r60/gold192-history-v3-adapter

BASE="$HOME/.local/share/storyforge/r59/private"
SOURCE="$BASE/r60-source-v3-pilot7-verified-20261107"
OUT="$BASE/r60-model-input-evidence-seed-$(date -u +%Y%m%dT%H%M%SZ)"
python3 experiments/r58_quality/r60_model_input_evidence_seed.py \
  --source-locators "$SOURCE/R60_SOURCE_LOCATORS_192.jsonl" \
  --source-safe "$SOURCE/R60_SOURCE_SAFE.json" \
  --output-dir "$OUT"
```

CLI 仅打印 SAFE 聚合，无私有 Case ID。新增目录为 0700，两个输出文件为 0600。命令需使用 R60 V3 Source Extract 的真实有效同次运行目录；若用户本地命名不同，只替换 SOURCE 行。若遇到来源哈希不一致或输入权限不符则 fail closed，不改动已有文件。**不要上传私有槽位文件到 GitHub/聊天。**

本阶段只建立统一的逐案证据问题清单，下一阶段需利用授权数据源逐案审阅才能出现 A/B/C/D 的真正统计；不能自行填写推测等级。
