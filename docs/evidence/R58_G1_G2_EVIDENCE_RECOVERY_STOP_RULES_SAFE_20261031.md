# StoryForge R58 — G1/G2 证据恢复顺序与停止规则（SAFE）

日期：2026-10-31。仅针对 `r58/roleplay-sft-skill-v01` / Draft PR #7。**G1=HOLD、G2=HOLD、Train/Validation/Teacher=0，固定五候选之一排除、剩余四候选 HOLD，不扩样。**

## 本轮新核查的证据边界

通过已授权 StoryForge Supabase **只读 table schema** 查看 `public` 元数据，不执行 SELECT 内容查询、不读取 `v2_chat_messages.metadata` 或异常快照、不读取任何 R50 题目或候选世界正文。

| 来源 | 发现的结构 | 不能推断 |
|---|---|---|
| `user_stories` | 当前 `id`、`v2_data`、`public_content_revision`、`public_content_hash` | 历史 target-time 所见内容一定与当前相同 |
| `story_content_versions` | `story_id`、`content_revision`、归档时间与 `v2_data` | 所有历史版本永久保存；尤其不能凭当前最近版本替代旧请求 |
| `story_v2_sessions` | Session、摘要版本、历史恢复校验字段 | 当时实际 Prompt 或 Provider 端收到的消息 |
| `v2_chat_messages` | 消息 `id`、`metadata` JSONB、`turn_index`；**未发现顶层 `request_id`** | `metadata` 中一定有/没有 request_id（未读取 JSONB） |
| `v2_chat_request_events` | `request_id`、`occurred_at`、`story_id`、`session_id` 和状态 | 事件本身可以和具体 assistant target 做唯一直接关联，或含 Provider 字节 |
| `chat_latency_metrics` | `request_id`、`relay_request_id`、`relay_trace_id`、`attempt_trace`、模型标记 | Provider 真实 input bytes；该在线日志的保留窗口足以覆盖任意历史目标 |
| `ai_model_scene_runtime_routes_history` | 路由修订与发布时间 | 某一次请求必定使用了特定 revision |
| `chat_abnormal_snapshot` | 异常现场可能含敏感上下文；存在过期字段 | 它是全部请求的权威 Prompt 台账。本轮**未读取** |

**因此：**数据库结构可以为未来**已批准的固定目标**提供有界的元数据关联线索，但不能单靠结构说明 G2 的 `direct_target_request_link_proven` 已成立；没有原始 Provider 请求 payload，更不能认定 17 个字节级阻塞已消除。

## G1 证据取得顺序

1. **不再重扫已审日志。**此前 18 未分类 GPU 日志信号 1/17，单个 CANCELED Job 仅存在含 `started_at`、缺 `finished_at` 的提供商元数据；已有两份私有回执交叉核验 PASS，但没有实际优化器更新证据。
2. **查找可信原始运行工件。**只有找到与该私有 Job ID 因果关联的 Trainer 运行摘要（`global_step` / 优化器步骤）、Checkpoint 输出/写入时间、实际 Train/Validation 输入 SHA256、原始运行版本，才能把潜在训练迹象升级为证据。来源可能是本机已保存的原始审计包或服务端历史工件；**本轮未检索这些可能含敏感内容的工件**。若要审阅，先由 Owner 明确限定访问范围与可输出字段。
3. **其余 Job 一律 PENDING。**之前 60 未充分分类的任务（GPU 18、CPU 42），不能因为机器为 CPU、任务 CANCELED/ERROR 或没有日志信号就排除训练。现存 69 个 Job 也不能保证涵盖被删除、其他 namespace 或其他平台。
4. **保护集全集单独审查。**使用 Owner 已冻结的授权 UUID-only 元数据来源及其版本来覆盖 R50、Gold/DEV、R55/R57、其他 heldout/保留世界；`r58_g1_scope_reconcile.py` 只核对局部集合内部一致性，永远不自动授权 G1。在线业务库当前故事集合不是这些保护集合的权威历史全表。

**停止规则：**源范围不完整、原始运行工件缺失或无法证实 Job ↔ Train/Validation 输入直接关联时，保持 `G1=HOLD`，不做来源排除。

## G2 证据取得顺序

1. 从**已冻结的三条目标**开始，仅在 Owner 批准的具体 case ID 范围内确认是否存在记录于消息元数据的直接 `target_message_id↔request_id`。此处只提出证据路径，不执行行级查询、不补造 ID、不靠时间邻近匹配。
2. 若得到唯一直接关联，再核对请求日志中的 `request_id` / `relay_request_id` 以及当时部署 SHA、运行时 model、Session snapshot 的来源身份。请求级 metrics 只能补充诊断证据，不能自动升级至原始 Provider 消息证明。
3. 最后才讨论 Provider dispatch 完整的前/后 sanitize 消息字节和参数快照，并核验字节级一致性；缺任何关键组件，`G2=HOLD`。

**停止规则：**消息 UUID 与请求没有可信直接关联，或历史部署/Provider 完整消息字节缺失时，不得用软时间线 2/4/2 或现存 `v2_data` 替代原始证据。

## 当前可直接复用的已验证结果

- Skill v0.2：Owner Mac **61/61 PASS**、Ruff PASS；
- `r58_existing_priority_receipt.py` 已完成既有 CANCELED 任务私人回执交叉核验，未调用 HF，原始更新证明仍缺；
- 仓库新回执：`docs/evidence/R58_G1_G2_READONLY_SCHEMA_EVIDENCE_BOUNDARY_SAFE_20261031.json`；
- PR #7 保持 Draft；不覆盖私有回执，不启动付费 HF CPU/GPU、不读取 R50 密封题目、不冻结 Dataset v0.4、不自动合并/晋升。

**本文件是按可信来源类型排序的证据取得计划，不是对原始 Trainer 或 Provider 请求的已完成独立验证。**

## 追加：已冻结 RolePlay 源码的请求关联审计（2026-10-31）

新增 Git blob 精确来源证明：`docs/evidence/R58_G2_PINNED_REQUEST_ID_PERSISTENCE_SOURCE_AUDIT_SAFE_20261031.json`，检查 `sunxu/RolePlay@e9fe29c42434caeb0bac5acc91845ab4741ecb2b` 的 V2 Route、message-codec、V2MessageService 和事件元数据构造器。

**结果：**该固定版本的 API `logger.ctx.requestId` 明确写入请求终态事件、延迟指标和 Provider 请求选项；但在已检查的流式 Assistant 占位与最终完成路径、非流式最终保存路径中，**未发现把该 API request ID 直接写进目标 `v2_chat_messages.metadata` 的代码**。事件 `v2EventClaimId` 是另一种 claim 标识，不可直接当作 API request ID。数据库指标层的同 request_id join，仍不能构成目标 Assistant UUID ↔ request_id 的证明。

这是**固定源代码路径的阴性发现**，不代表核实了当时生产部署 SHA、所有未审代码写入者、历史归档或 JSONB 内全部数据。之前的 3 个目标 × 7 个顶层 metadata 键缺失结论仍只是 Owner 已报告的局部结果；本次没有读取任何实际业务行。

**更新下一步：**不建议再对既有三案例重复执行 metadata 字段试探或 2/4/2 软时间过滤。只有找到可证明由当时运行时写入、并把具体物理目标回复（或者唯一 turn/attempt）与 API request_id 明确绑定的**另一份原始证据源**，才启动单案例、严格限定的只读查询。若来源不能满足该条件，`G2=HOLD` 并停止猜测。Provider 字节级完整回放仍是独立门禁。

G1 的单个 CANCELED HF Job 仍缺原始 Trainer 更新/输入来源工件，相关敏感访问没有扩权，本轮未触碰。
