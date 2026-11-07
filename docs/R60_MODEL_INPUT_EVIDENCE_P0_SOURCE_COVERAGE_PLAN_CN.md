# R60 P0：Gold192 模型输入证据来源覆盖率首轮核查（只读）

日期：2026-11-07
状态：待执行。**此计划没有执行行级查询，也没有把任何候选样本升级到 A/B/C/D。**

## 0. 已收到 Owner 证据槽位初始化 SAFE

- schema: `r60_model_input_evidence_seed_safe_v1`
- status: `EVIDENCE_SLOTS_SEEDED_NOT_REVIEWED`
- Gold192 总数: 192；`UNKNOWN_NOT_REVIEWED=192`
- A/B/C/D: null，代表**尚未核实**，不是 0
- source locator SHA256: `eb2b186b03ffc31585c224ac75cbfd7dd20c8d762887a6463c85bc5090ae9739`
- private slots SHA256: `69e83d6c61a6be5eb1516d3fd2987fc086259597fd8f900cc02c445debb9a5e9`
- `evidence_review_started=false`、`quality_v1_admitted=0`、`training_authorized=false`、`gpu_started=false`、`database_modified=false`、`r50_accessed=false`、`private_values_emitted=false`。

这些哈希由 Owner 的 SAFE 回执提供，尚未从本环境读取并独立计算本机私有文件字节。该回执只证明槽位初始化程序返回预期状态，不证明已查到任何真实 Provider 请求。

## 1. 已确认的证据容器（仅 Catalog 元数据）

对已连接 Supabase 只读 Catalog 做过 `pg_catalog` 查询，确认：

| 表 | 相关字段 | 对 Gold192 的作用 |
|---|---|---|
| `public.v2_chat_reply_jobs` | `request_envelope`、`model_id`、`attempt_count`、`session_id`、`assistant_turn`、`client_msg_id` | 生成任务关联候选，**并非发送态完整请求证明** |
| `public.chat_abnormal_snapshot` | `request_id`、`relay_request_id`、`conversation_context`、`history_preview`、`memory_injection`、`continuation_attempts`、`expires_at` | 失败、重试等异常的部分输入/尝试证据；经常截断 |
| `public.chat_latency_metrics` | `request_id`、`relay_request_id`、`relay_trace_id`、`attempt_trace`、`model` | 尝试关联候选，非原始请求体 |

**当前连接角色为 `supabase_read_only_user`**，不是 R60 私有恢复基线的 `r58_export_reader`。因此前一步只查询表/列定义，未查实际生产用户数据。后续任何聚合或 Gold192 局部证据验证，都须通过 Owner 已验证的受限凭据/权限执行，确认 RLS、只读事务和超时设置。

此外，异常表名必须是 `chat_abnormal_snapshot`（单数），不能使用 `chat_abnormal_snapshots`。

## 2. 第一轮只读聚合的先决条件

1. 连接角色必须满足最小权限，且可观察到的行集满足本项目的业务授权。绝不为提升覆盖率使用 service_role 或 RLS bypass。
2. 在 `BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY` 后确认 `current_user`、`transaction_read_only`、`row_security`、`statement_timeout` 和 `lock_timeout`；未满足立即停止。
3. **首先只查询 Catalog**：三个候选表的 relkind、估算行数、索引列、RLS 与关键字段；确认预期索引可支持有界时间窗才执行真实聚合。
4. 对经确认授权且范围有界的查询，仅输出：覆盖时间窗、行数分桶、关键 linkage 字段非空率、请求重试/模型路由计数的整数；不输出任何 user_id、session_id、request_id、message_id、故事名、prompt、JSON payload。
5. 若读取 `request_envelope` 或 `conversation_context`，**只做 SQL 侧类型、键存在、长度和截断标识的聚合**；不返回内容。不能认为某 JSON key 存在即完整输入可证明。
6. 若存在留存清理或事件覆盖缺失，只标记 `EVIDENCE_SOURCE_COVERAGE_UNKNOWN_OR_MISSING`，不把受影响 Case 判 D。
7. Gold192 Case 关联是单独第二阶段：只能在 Owner 本地用原始冻结 locator 做受控 JOIN，输出 Case 级结果到 0700/0600 私有文件，并只打印聚合 SAFE。没有此步不得给出 A/B/C/D 统计。

## 3. 针对性分期核查

### S1：有无实际可查记录（表级）

- `v2_chat_reply_jobs`：状态和 created_at 年月分桶；含输入信封的 JSON 类型，但绝不读取原值到客户端。
- `chat_abnormal_snapshot`：异常类型/保留时间窗；request_id / relay_request_id 非空率；history/context 是否被截断的元数据。
- `chat_latency_metrics`：日期/模型通道分桶、request_id 与 relay_request_id 非空率；仅计数。
- 归档文件/Relay 外部存储：请 RolePlay 项目方核实**是否启用、旧数据保存多久、是否存在请求正文、是否能与最终回复绑定**。不可仅依赖数据库目录猜测。

### S2：Gold192 Target—Attempt 关联（私有）

严格使用冻结 locator 中可验证的 message/session/turn 身份，核实：

- 有无对应 reply_job、latency request ID、异常快照，是否出现多对一或一对多；
- 生成尝试之间是否发生降密重试、validation_retry、auto_continue、模型 fallback；
- 最终 Assistant 可能是多个分段拼接或 moderation 替换，必须单独标记；
- 只有模型输入证据原始留证完整且可追溯时，才考虑 A / B。

### S3：逐案证据判定

- `A`：实际最终发送请求和目标生成尝试完整关联（需考虑 Provider 出站转换）。
- `B`：完整且可独立验证的确定性输入重建（所有运行时依赖和后处理可验证）。
- `C`：部分旁证、缺少关键输入或关联，保持 HOLD。
- `D`：经过可解释的独立来源核查，确属不可验证，不能因为表中查不到就自动标 D。
- `UNKNOWN_NOT_REVIEWED`：尚未逐案完成上述流程。

所有级别与 `Quality-v1`、Reviewer、Owner 授权、Train/Validation/Test 隔离、R50 Held-out 隔离独立；`admitted=0` 不变。

## 4. 本阶段禁止事项

不运行数据库 DML/DDL，不访问 R50，不导出聊天/Prompt 原文至聊天或 GitHub，不读生产 JSONB 全文，不允许绕过 `LEDGER_TEMPORAL_ORDER_AUDIT_REQUIRED`，不生成训练候选，不启动 GPU。

T1 Ledger Writer Path 审计保留为 RolePlay P1 的数据可靠性治理以及必要个案的支持任务，不作为 P0 输入证据调查的统一硬门槛。


## 5. S1 已实现：Catalog-only 守卫预检（2026-11-07）

新增 [`r60_model_input_coverage_catalog.py`](../experiments/r58_quality/r60_model_input_coverage_catalog.py) 和 [合成测试](../experiments/r58_quality/test_r60_model_input_coverage_catalog.py)。

**当前仅执行 Catalog，不执行真实表的 COUNT/SELECT 业务数据。** 它通过 psycopg 用 Owner 本地的 `STORYFORGE_SUPABASE_DSN` 发起 `REPEATABLE READ READ ONLY` 事务，首先确认：`current_user=r58_export_reader`、`transaction_read_only=on`、`row_security=on`，15 秒语句超时和 1 秒锁等待；失败则输出聚合 HOLD。它只读取 `pg_catalog` 表名、列名、索引名和 `has_table_privilege` 布尔值，最后显式 rollback；没有读取请求信封、聊天正文、JSONB 或用户行。

RolePlay 当前历史 migration [`20260820213000_v2_durable_reply_jobs.sql`](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/supabase/migrations/20260820213000_v2_durable_reply_jobs.sql) 最初对 `v2_chat_reply_jobs` 只授予 `service_role` 业务表权限，因此 **不能假设** `r58_export_reader` 必然拥有该表的 SELECT。若预检发现权限不足或 RLS 不符合要求，应停在 HOLD，另行制定经批准的最小权限访问方案；严禁切到 `service_role` 或关闭 RLS。

Owner 使用原有私人凭据运行：

```bash
set -euo pipefail
cd "$HOME/workspace/storyforge-r60-ledger-diagnostics"
git fetch origin r60/gold192-history-v3-adapter
git pull --ff-only origin r60/gold192-history-v3-adapter

# 在原 Owner 私有环境中加载 STORYFORGE_SUPABASE_DSN（不要在聊天中提供连接串）
test -n "${STORYFORGE_SUPABASE_DSN:-}"
python3 -m unittest experiments.r58_quality.test_r60_model_input_coverage_catalog -v
python3 experiments/r58_quality/r60_model_input_coverage_catalog.py
```

回传仅 CLI SAFE JSON；不要打印连接串或业务内容。预检通过仍只能说明结构与表级权限可进一步核查，**不是 Gold192 覆盖率数字，也不表示可直接读取生产行**；继续检查角色可见性和时间窗索引后才能执行有界覆盖计数。

### 最新的停止条件

- `CATALOG_PREFLIGHT_HOLD`：先修复权限、表结构或环境问题（需独立审批），不自动降级为不受控连接。
- `CATALOG_PREFLIGHT_PASS_NO_BUSINESS_ROWS_READ`：允许准备下一轮限定时间窗的聚合方案，尚未执行它。
- A/B/C/D 继续未知；`UNKNOWN_NOT_REVIEWED=192`；`quality_v1_admitted=0`，无 GPU。


## 6. S1 Owner 预检回执与 SELECT/RLS 进一步核证（2026-11-07）

Owner 返回 `r60_input_evidence_catalog_preflight_safe_v1`：`CATALOG_PREFLIGHT_HOLD`；使用 `r58_export_reader`、只读事务、`row_security=on`。三个目标表的必需列与索引均存在，`business_rows_read=0`、`aggregate_counts_executed=false`，且无数据库修改、R50 访问、GPU、训练准入。

| 表 | SELECT 授权 | RLS | 已发现 SELECT/ALL Policy 数 | 结论 |
|---|---|---|---:|---|
| `v2_chat_reply_jobs` | false | true | 0 | 表授权与行策略均阻断 |
| `chat_abnormal_snapshot` | false | true | 0 | 表授权与行策略均阻断 |
| `chat_latency_metrics` | true | true | 0 | **原程序的 CATALOG_READY_COUNTS_NOT_RUN 不能代表可见有效数据**；没有适用的 SELECT RLS 策略 |

以上政策数量来自独立 `pg_catalog.pg_class` / `pg_policies` 元数据只读查询，连接为 `supabase_read_only_user`，不是 Owner 的 `r58_export_reader`；查询没有读取业务表数据。三个目标表 `relforcerowsecurity=false`；此事实不允许推断在服务方或表所有者身份下的数据可见性。

**修订后的预检规则**：在已有 `r58_export_reader` 和只读事务检查之外，新增 `pg_policy` 计数。即便具备 SELECT 授权，SELECT/ALL RLS policy 为 0 也必须 `RLS_POLICY_ABSENT_HOLD`；即便存在策略，若尚未审查适用角色、表达式、业务数据授权范围，也只能 `RLS_POLICY_REVIEW_REQUIRED`，不能自动准许覆盖率聚合。实现及合成测试见 `r60_model_input_coverage_catalog.py`。

### 推荐授权路径（未执行、待批准）

**优先**由 RolePlay 管理者设计专用且经安全审核的聚合统计 RPC（或等价受控只读导出服务），返回仅限已批准时间窗口的计数、完整性标记与关联率；不直接公开 `request_envelope`、`conversation_context`、原始 request IDs。此方案必须明确：

1. 明确函数执行身份、调用角色、授权业务范围、租户/用户数据访问规则，禁止宽泛 `SECURITY DEFINER` 自动绕过 RLS；如必须使用 definer，须通过固定 `search_path`、固定 SQL、严格输入验证、授权白名单、资源限额、审计日志和安全评审。
2. 只对必要函数授予 `EXECUTE`，不要直接给 `r58_export_reader` 两张敏感表的全文 SELECT 或使用 `service_role`；继续以唯一已批准受限角色调用。
3. 必须保留 `READ ONLY`、RLS/等价明确授权行过滤和最小必要的结果字段；无合适索引、范围不可控、权限异常时 fail closed。
4. 生产 DDL（包括创建函数、GRANT、RLS policy）必须由 Owner **另行明确授权**并通过 RolePlay 仓库迁移与审查流程，当前 StoryForge 工作不能代行。
5. 如产出是全站统计，需考虑跨租户泄露及小样本重识别，必要时仅返回粗粒度桶与最小样本阈值。

**当前判定：** S1 `CATALOG_PREFLIGHT_HOLD`；不能读取业务记录，也不能推断 Gold192 历史数据缺失。192 个槽位仍为 `UNKNOWN_NOT_REVIEWED`，A/B/C/D 全部未知，`quality_v1_admitted=0`、`training_authorized=false`、`gpu_started=false`。


## 7. Owner 允许扩大只读数据库权限：StoryForge 自主元数据取证方案（2026-11-07）

Owner 表示可以扩大数据库读取权限。为了让 R60 在 RolePlay 暂时无法交付新接口的条件下继续运行，本轮已提供 **review-only 管理员 SQL 模板**，但**尚未在生产执行**：

- [授权模板](../experiments/r58_quality/sql/r60_model_input_evidence_metadata_access_REVIEW_ONLY.sql)
- [回滚模板](../experiments/r58_quality/sql/r60_model_input_evidence_metadata_access_ROLLBACK_REVIEW_ONLY.sql)

### 本轮明确的授权边界

- 允许 `r58_export_reader` 在三张证据表读取必要的 **元数据列**：时间、Session/Story/Request 标识、模型、状态、尝试数和关联信息；R60 本地程序只输出聚合 SAFE，不输出标识或敏感值。
- **暂不授权** `v2_chat_reply_jobs.request_envelope`，`chat_abnormal_snapshot.conversation_context`、`history_preview`、`user_input`、`assistant_output`、`memory_injection`、`continuation_attempts`，`chat_latency_metrics.attempt_trace` 等敏感正文/JSONB 字段。
- RLS 使用 `TO r58_export_reader` 的专用 SELECT policy。当前 SQL 模板 `USING (true)` 意味着该角色可见**全站所有所有者**的已授权元数据行，不是租户级隔离；因此管理员必须明确批准该范围，且在单独管理的私有数据库执行。
- 首轮预检中 `chat_latency_metrics` 已有整表 SELECT 有效授权。为了避免加上 RLS policy 后意外暴露全部字段，授权模板显式 `REVOKE SELECT ON chat_latency_metrics FROM r58_export_reader`，再授予列级 SELECT。**这可能影响其它使用该角色的功能，必须先保存 `pg_class.relacl`、`pg_attribute.attacl` 和角色继承关系的 BEFORE 快照并确认依赖。** 若整表权限来自继承，简单 REVOKE 不会移除它，StoryForge 预检会继续阻断，不能强行继续。
- 不授予 DML、DDL、RLS bypass、service_role、超级用户或数据库所有者权限；不改变应用角色权限。

### 执行顺序

1. 由授权的数据库管理员核对授权模板、现有 ACL（包括 role membership 和 `has_table_privilege` 的来源），并保存可回滚的 BEFORE ACL/RLS 快照。
2. 先在隔离环境检验 Policy 与列级 SELECT 的有效授权，再于经批准的生产维护窗口执行模板。
3. 用 Owner Mac 现有 `STORYFORGE_SUPABASE_DSN` 重跑 `r60_model_input_coverage_catalog.py`；新程序分别检查关键列的 `has_column_privilege`、整表 `has_table_privilege` 以及 SELECT/ALL Policy 存在性。
4. 预检中 **整表 SELECT = true**、未授予所需列、缺 RLS policy、角色错误等任何情况继续 HOLD；若 policy 存在，状态仍是 `RLS_POLICY_REVIEW_REQUIRED`，待管理员独立确认 SQL 条件和授权范围才执行业务表聚合。
5. 授权通过后才实现/运行 **仅元数据、按日期窗口有界** 的覆盖率查询。初始只验证记录覆盖率、请求关联字段非空率和时间窗口，不触及请求正文或 Gold192 分级。
6. 要证明真正发送的 Provider 请求，后续另设**必要、定向、Owner 私有**的正文证据审查，单独审批其访问字段；不能将此元数据 GRANT 视为真实模型输入已被证明。

### 避免误用

- SQL 文件是 **审查模板**，不属于生产 migrations，不能自动部署。当前 GitHub 工作仅修改 StoryForge 代码和文档，未修改 RolePlay Repo 或数据库。
- 回滚模板仅撤销 R60 专用列授权与政策；之前的整表 SELECT 是否需要恢复，必须根据 BEFORE 快照人工确认，不得盲目重授。
- 既有 Gold192 192 个槽位保持 UNKNOWN_NOT_REVIEWED，A/B/C/D 未知；Quality-v1 admission=0，无 GPU。



## 8. Owner 生产授权回执与数据库实际 Policy 复核（2026-11-07）

Owner 第二次 S1 SAFE 回执确认三张表的关键元数据列均可 SELECT，整表 SELECT 均为 false，RLS 启用且 SELECT policy 计数均为 1。状态继续 `CATALOG_PREFLIGHT_HOLD`，每表状态 `RLS_POLICY_REVIEW_REQUIRED`，这是之前的**人为安全审核门槛**而不是表授权失败。

通过受限连接的独立 `pg_catalog` 元数据只读检查，实际部署 Policy 三表均符合下列精确条件：

- policy 名称 `r60_gold192_evidence_metadata_select`；
- `FOR SELECT TO r58_export_reader`，`PERMISSIVE`；
- `USING (true)`，无 `WITH CHECK`；
- 表 `relrowsecurity=true`、`relforcerowsecurity=false`，`has_table_privilege('r58_export_reader', 'SELECT')=false`；
- 之前 Owner 工具已证实所需**列级** SELECT 为 true。

此事实意味着 **该 Reader 对这三表的已授权列可跨所有者读元数据行**，不能视作 Gold192 专属行级授权。允许用于本项目审核过的限制时间窗汇总，严禁把原始用户/请求/Session 标识返回至 SAFE。

修改 [S1 精确 Policy 预检工具](../experiments/r58_quality/r60_model_input_coverage_catalog.py)，只有上述 Policy 签名、列级授权、无整表授权、RLS 都符合时返回 `CATALOG_POLICY_MATCHED_COUNTS_NOT_RUN`。这**仍不意味着业务表已被查询**。

### 8.1 S2 首个有界元数据统计器

新增 [`r60_model_input_metadata_window.py`](../experiments/r58_quality/r60_model_input_metadata_window.py) 与对应合成测试。其行为：

- 只允许带时区的 ISO 8601 UTC/offset 时间窗口，`0 < duration <= 24h`；
- 在 Owner `r58_export_reader` 连接上使用 `REPEATABLE READ READ ONLY`、`row_security=on`、8s `statement_timeout`、1s `lock_timeout`；
- 先重跑精确 Catalog 预检，要求两张统计表存在索引 `idx_chat_abnormal_snapshot_created`、`idx_chat_latency_metrics_created`；
- 只在两张表的 `created_at >= start AND created_at < end` 条件下计算 `COUNT(*)`、`COUNT(request_id)`、`COUNT(relay_request_id)`；
- **不读取**任何 JSONB、Prompt、聊天正文、用户 ID、Session ID、故事 ID；只向客户端返回 6 个整数（两张表各 3 个）；
- `v2_chat_reply_jobs` 暂为 `HOLD_NO_VERIFIED_CREATED_AT_LEADING_INDEX`，避免未验证访问路径的时间范围全表扫描；后续应优先使用已存在的 `(session_id, assistant_turn)` 唯一索引对冻结 Gold192 做经授权的私有 target lookup，或先只读 EXPLAIN；
- 该统计是**表级时间窗元数据覆盖**，不是 Gold192 Case 的请求关联率，更不是实际模型输入认证。

示例仅对 2026-08-01 一天做核查（时间窗是示例，并非声称 Gold192 的确切生成时间）：

```bash
set -euo pipefail
cd "$HOME/workspace/storyforge-r60-ledger-diagnostics"
git pull --ff-only origin r60/gold192-history-v3-adapter
test -n "${STORYFORGE_SUPABASE_DSN:-}"

python3 -m unittest \
  experiments.r58_quality.test_r60_model_input_coverage_catalog \
  experiments.r58_quality.test_r60_model_input_metadata_window -v

python3 experiments/r58_quality/r60_model_input_coverage_catalog.py
python3 experiments/r58_quality/r60_model_input_metadata_window.py \
  --start 2026-08-01T00:00:00Z \
  --end 2026-08-02T00:00:00Z
```

先根据 Owner 私有 frozen locator 的真实日期范围选择窗口，不应照抄示例日期。若生产表较大、索引/执行计划不符合预期或查询达到超时，则 HOLD，不要直接扩大时间窗口。

### 8.2 未改变的限制

不执行 SQL DDL/DML、不修改 RolePlay 生产表、不读取 R50、不导出任何用户/请求 ID、A/B/C/D 全部 UNKNOWN、Quality-v1 admitted=0、training_authorized=false、GPU=false。S2 结果不能自动放行任何训练样本。


## 9. S2 首次运行遇到 COUNT_COLUMNS_MISSING：程序误判已修复（2026-11-07）

Owner 的 `r60_model_input_metadata_window_safe_v1` 回执：`METADATA_WINDOW_HOLD`、`reason_code=COUNT_COLUMNS_MISSING`，`database_modified=false`、`private_values_emitted=false`。**该回执没有声称查询了任何数据或产生覆盖率。**

根因是 S1 `classify()` 输出的 `columns_present` 只包含其 `COLUMNS` 白名单，而该白名单在 `chat_abnormal_snapshot` 与 `chat_latency_metrics` 中漏掉了 S2 必须使用的 `created_at`。S2 `check_catalog()` 随后检查 `created_at`，因内部目录描述缺失而触发误 HOLD。先前数据库 Catalog 已独立确认两张表实际存在 `created_at` 字段，并有日期索引。

修正包括：

1. 在 S1 两张表的 `COLUMNS` 和 `METADATA_SELECT_COLUMNS` 中均明确加入 `created_at`，校验实际字段存在与可 SELECT；
2. S2 不再用“配置中声称需要的字段”和 Catalog 字段并集来假装列存在，只根据 S1 实际验证的 `columns_present` 判断；
3. 补充 `created_at` 完整 Catalog 正向回归及缺失字段 HOLD 反向合成测试；
4. 不改任何 RLS policy、GRANT、数据库数据、时间窗大小或训练准入门槛。

**下一步：** 更新 PR #25 后运行 S1 + S2 合成测试，再用同一已明确授权的 24 小时日期窗口重新执行 S2。若仍 HOLD，保留 SAFE reason_code，不扩大日期或改用高权限账号。结果仅是两张表的元数据时间窗计数，与 Gold192 逐案输入证明无关。


## 10. S2 Owner 首轮零记录与 S3 索引定位 Pilot（2026-11-07）

Owner 的首轮 S2 SAFE 回执状态为 `METADATA_WINDOW_AGGREGATES_ONLY_NOT_CASE_LINKED`。请求时间窗口**仅**为 `2026-08-01T00:00:00+00:00` 到 `2026-08-02T00:00:00+00:00`：

| 来源 | 匹配行数 | request_id 非空 | relay_request_id 非空 |
|---|---:|---:|---:|
| `chat_abnormal_snapshot` | 0 | 0 | 0 |
| `chat_latency_metrics` | 0 | 0 | 0 |
| `v2_chat_reply_jobs` | 未执行 | unknown | unknown |

该零结果**只适用于以上 24 小时窗口和当时已授权角色的行可见性**，不能推断 Gold192 无请求证据、不能据此填充 A/B/C/D、也不能排除留存清理影响。

### S3：冻结定位的 Reply Job 定向 Pilot

新增 [`r60_reply_job_locator_pilot.py`](../experiments/r58_quality/r60_reply_job_locator_pilot.py) 和 [合成测试](../experiments/r58_quality/test_r60_reply_job_locator_pilot.py)。它验证冻结 R60 Source Locator 的 192 条数量和 SAFE 内文件 SHA256，以 `case_id` 排序，**最多选取 8 条**具有 `session_id` 与 `turn_index` 的目标。只使用现有索引 `uq_v2_reply_job_assistant_turn` 的键 `(session_id, assistant_turn)` 做只读定位计数和 `attempt_count` 汇总。

此工具不读取 `request_envelope`、不查询任何未许可正文，不打印 session / story / user / request / message ID，不生成训练集，也不做 Gold192 A/B/C/D 分类。成功表示 Reply Jobs 元数据关联候选数，不表示输入或回复链已认证。

Owner 需在已有 `r58_export_reader` 私有凭据环境中运行：

```bash
set -euo pipefail
cd "$HOME/workspace/storyforge-r60-ledger-diagnostics"
git pull --ff-only origin r60/gold192-history-v3-adapter

python3 -m unittest \
  experiments.r58_quality.test_r60_reply_job_locator_pilot \
  experiments.r58_quality.test_r60_model_input_coverage_catalog -v

# SOURCE 必须替换为前次 192 条 locator 与其配套 SAFE 的实际同次目录。
SOURCE="$HOME/.local/share/storyforge/r59/private/r60-source-v3-pilot7-verified-20261107"

python3 experiments/r58_quality/r60_reply_job_locator_pilot.py \
  --source-locators "$SOURCE/R60_SOURCE_LOCATORS_192.jsonl" \
  --source-safe "$SOURCE/R60_SOURCE_SAFE.json" \
  --pilot-count 8
```

该脚本要求源文件为私有的 0600、父目录 0700，连接保持只读事务、RLS、`r58_export_reader` 且每条查询 3 秒超时。返回仅聚合 SAFE；若来源路径/权限/定位签名不符，保留 HOLD。不要把私有 locator JSONL 发送到 GitHub 或聊天。

注意，本次选择按 `case_id` 排序的前 8 条是**技术可执行性 Pilot**，不是质量最优 8 条，不保证在旧 Reply Job 上有覆盖。若 8/8 无匹配，仍然不代表全量 192 条无证据，应进一步按**目标真实生成时间、部署版本**与持久化链路判断是否存在记录。


## 11. Owner S3 首轮 8/8 不匹配：改用 Session/Turn 双层诊断

Owner 回执 `r60_reply_job_locator_pilot_safe_v1`：`REPLY_JOB_LOCATOR_PILOT_METADATA_ONLY_NOT_INPUT_VERIFIED`，`pilot_targets_checked=8`、`reply_job_exact_locator_matches=0`、`reply_job_not_found=8`、`matched_job_attempt_count_sum=0`。这不是数据库执行失败，而是 8 条精确 `(session_id, assistant_turn)` 查询未匹配。没有任何生成请求正文获得验证。

重要解释：

- 首轮 8 条是**按 case_id 排序**的 8 条，不代表不同故事、不同生成日期或不同 RolePlay 部署时期；
- R60 Source Extract 的 `session_id` 来自**当前持久化消息**，可能经过 fork/rewind/import/migration，不能凭它断言生成时的 Reply Job Session 唯一标识相同；
- RolePlay 的 `v2_chat_reply_jobs` 建表迁移时间是 2026-08-20；旧请求可能没有该表对应记录。创建文件时间不是生产部署时间，不能直接用迁移名判断样本来源时点；
- 存在 RLS 限制、记录生命周期、功能模式或不同生成路径等其他解释。**不能把 8/8 零匹配外推到 Gold192 192 条，不应据此划 D。**

### 11.1 S3B 双层定位（仅元数据、最多 8 条）

新增 [`r60_reply_job_session_diagnostic.py`](../experiments/r58_quality/r60_reply_job_session_diagnostic.py)，仅从已经冻结且 SHA256 为 `eb2b186b03ffc31585c224ac75cbfd7dd20c8d762887a6463c85bc5090ae9739` 的 192 条 Source Locator 中读取私有定位字段，按**不同 story 先各选一个**的规则抽取 8 条，不要求与前一轮 8 条不同。

在 Owner 的 `r58_export_reader`、`READ ONLY`、`row_security=on` 事务中，只用已存在的 `session_id` 前导唯一索引（`uq_v2_reply_job_client_msg`）和 `(session_id, assistant_turn)` 唯一索引，每条查询设置 3 秒超时。分别检查：

1. `EXISTS (SELECT 1 ... WHERE session_id=... LIMIT 1)`：是否能看到该 Session 任一 Reply Job；
2. `COUNT(*) WHERE session_id=... AND assistant_turn=...`：是否有目标轮次的准确任务；
3. 只返回聚合三类数：`session_not_found` / `session_found_exact_turn_missing` / `exact_turn_found` 和已匹配任务的 attempt_count 总和。

不读取 Reply Job `request_envelope`、聊天正文、用户 ID 或任何原始标识；**不会写入 Gold192 证据槽位，更不会升级 A/B/C/D**。如 8 个 Session 均不存在，下一步优先排查样本时间与 Job 功能的覆盖期，而不是先做 192 条无区别的重复查询。如出现 Session 存在但 Turn 不匹配，优先核对轮次映射/迁移；如有 exact match，再对命中的 Owner 私有个案做请求证据来源的进一步资格审核。

Owner 执行：

```bash
set -euo pipefail
cd "$HOME/workspace/storyforge-r60-ledger-diagnostics"
git pull --ff-only origin r60/gold192-history-v3-adapter
python3 -m unittest \
  experiments.r58_quality.test_r60_reply_job_locator_pilot \
  experiments.r58_quality.test_r60_reply_job_session_diagnostic -v

SOURCE="$HOME/.local/share/storyforge/r59/private/r60-source-v3-pilot7-verified-20261107"
python3 experiments/r58_quality/r60_reply_job_session_diagnostic.py \
  --source-locators "$SOURCE/R60_SOURCE_LOCATORS_192.jsonl" \
  --source-safe "$SOURCE/R60_SOURCE_SAFE.json"
```

需要使用上次验证过的真实 SOURCE 目录，只有 JSON SAFE 回执允许贴回聊天。所有个人数据保持在 Owner 私有目录内，R50 隔离、数据库不修改、质量准入 0、训练授权 false、GPU false。


## 12. S3B Owner 回执与 S3C 证据源转向（2026-11-07）

Owner 提交的 `r60_reply_job_session_diagnostic_safe_v1` 显示：Gold192 涉及 13 个不同故事；跨故事抽查 8 个目标，`session_not_found=8`、`session_found_exact_turn_missing=0`、`exact_turn_found=0`、`matched_job_attempt_count_sum=0`。源身份仍 192，未获取出站模型输入，数据库未修改。**该回执证明这 8 个 Session 在当前授权行集中的 Reply Job 表没有可见记录，不证明全量 Gold192 没有历史模型输入。**

RolePlay 代码基线 `ccdf2e8dc2723f481cd0392883bc359e9e341c66` 提供有价值的来源解释：

- [Durable Reply 设计](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/.claude/plans/2026-08-20-v2-durable-reply-jobs.md) 规定运行开关 `V2_DURABLE_REPLY_MODE=off|shadow|on`；`off` 模式仍走直接生成。数据库表存在、迁移完成，并不能证明某个历史生成请求走了 Durable Job 路径。
- [Chat Archive](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/src/lib/archive/chat-archive.ts) 的 `CHAT_ARCHIVE_ENABLED` 默认关闭。启用时按用户/Session 写 append-only 消息操作文件；不保证保留最终发送态完整 Prompt。
- [Diagnostic Archive](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/src/lib/archive/chat-diagnostic-archive.ts) 通过 `CHAT_DIAGNOSTIC_ARCHIVE_ENABLED` 单独控制（未设置时回退至 Chat Archive 开关），默认根目录为 `/var/www/isekai-chat-diagnostic-archive`，两个类别目录名分别为 `abnormal-snapshots`、`latency-metrics`，按 UTC 日期及进程 shard 写 JSONL。
- 诊断归档代码标记异常快照 30 天、指标 90 天的保留期，但异常快照的旧版清理另有 `CHAT_DIAGNOSTIC_SNAPSHOT_LEGACY_PRUNE_ENABLED` 控制。**这只是代码中的保留逻辑，不证明当前生产归档已经删除或存在**；异地备份也可能保留历史文件。
- [Archive V2 备份同步脚本](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/ops/backup/chat-archive-v2-sync.sh) 支持加密 S3 备份同步；[Direct Sync](https://github.com/sunxu/RolePlay/blob/ccdf2e8dc2723f481cd0392883bc359e9e341c66/ops/backup/chat-archive-v2-direct-sync.sh) 支持同步批次，故文件取证应先检查 **Owner 已持有的归档 manifest / 本地备份**，不需要 RolePlay 新开发。

### S3C：本地归档文件名存在性清点

新增 [`r60_local_archive_manifest_probe.py`](../experiments/r58_quality/r60_local_archive_manifest_probe.py) 和 [合成测试](../experiments/r58_quality/test_r60_local_archive_manifest_probe.py)。此工具只扫描 Owner 已授权、本机可见的 Diagnostic Archive 目录下 **文件名**，不会打开任何 JSONL、读取正文或修改文件。仅返回两个归档类型的匹配文件数与**年份级**分桶，不输出文件名/具体日期/路径。它不是输入证据分级工具。

Owner 若已将 Diagnostic Archive 安全地同步到本机，可以运行：

```bash
set -euo pipefail
cd "$HOME/workspace/storyforge-r60-ledger-diagnostics"
git pull --ff-only origin r60/gold192-history-v3-adapter
python3 -m unittest experiments.r58_quality.test_r60_local_archive_manifest_probe -v

# 必须替换为已存在且授权访问的本地归档根目录；
# 不能直接把下方服务器默认路径当成本机路径。
ARCHIVE_ROOT="$HOME/.local/share/storyforge/r59/private/roleplay-diagnostic-archive"
test -d "$ARCHIVE_ROOT"
python3 experiments/r58_quality/r60_local_archive_manifest_probe.py \
  --archive-root "$ARCHIVE_ROOT"
```

若本机没有归档根目录，**不必创建空目录伪装已有记录**。应先确认现存服务器归档和备份清单的位置与可访问性；不能推断归档不存在。不要复制用户对话或请求正文至 GitHub/聊天。

### 后续门槛

先确认 Gold192 的实际来源生成时段、当时 Durable Reply 配置和本地/备份归档的真实时间覆盖。若能找到匹配源，再进行私有逐案绑定；若不能，仅记录来源覆盖范围未证实。**A/B/C/D 均不改变；192 条 UNKNOWN_NOT_REVIEWED，quality_v1_admitted=0、training_authorized=false、gpu_started=false。**
