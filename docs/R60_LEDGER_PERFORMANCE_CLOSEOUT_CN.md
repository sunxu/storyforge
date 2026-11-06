# StoryForge R60 Ledger 性能优化 · 收尾结项报告

**结项检查日期：2026-11-06（UTC）**  
**仓库：** `sunxu/storyforge`  
**实现与实验 PR：** [#16](https://github.com/sunxu/storyforge/pull/16)（Draft，未合并）  
**生产部署与证据 PR：** [#17](https://github.com/sunxu/storyforge/pull/17)（Draft，未合并；base 为 PR #16 分支）  
**生产目标表：** `public.v2_chat_message_ledger`  
**结项定义：** **B2 生产索引部署、结构验收和证据归档已完成；实际业务吞吐和恢复耗时优化幅度未完成测量，基础设施监控仍需常规 DBA 接手。**

## 一、最终决策

`PRODUCTION_B2_INDEX_DEPLOYMENT_PASS__RUNTIME_BENEFIT_UNVERIFIED`

这不是“R60 性能已经提升约 99%”的结论。该数字来自上线前的 HypoPG **优化器估算成本**，不是生产实测耗时。基础设施索引上线可以结项；运行时收益是独立验证任务。

## 二、关键阶段成果

| 工作项 | 结果 | 验收依据或边界 |
|---|---|---|
| T0 任务书与基线核验 | PASS | 基线、范围、只读与训练边界已冻结 |
| T1 数据库安全与 Catalog | PASS（仅元数据） | 连接器只读，`row_security=on`；但连接器角色 `rolbypassrls=true`，故不得用它读取受保护业务正文 |
| T2 B0/B2 跨 Session HypoPG 对照 | PASS（估算） | 3 个不同规模 Session 均选 B2 Index Only Scan；规划器收益不等于 wall time |
| T3 Metadata/Detail/Current History 审计 | PASS | 检查 Ledger Keyset、Detail 批量、Session 级共享索引与逐案边界 |
| T4 合成 Detail Batch 测试 | PASS（合成） | 500/1000/2000 只作 Python 批次/解码实验；生产默认保留 500 |
| T5 真实 B2 生产索引 | **PASS（已上线）** | 实际索引定义、有效位、体积、原索引保留、无残留构建 |
| T6 Pilot8 v3、真实前后延迟对照 | **NOT RUN** | 该任务未获单独执行授权；不声称真实耗时收益 |
| T7 证据归档与结项报告 | PASS | 本报告 + 不含私有值的 SAFE JSON；GitHub PR 审核留痕 |

## 三、生产索引完整性验收

**生产索引：** `public.idx_v2_chat_message_ledger_r60_b2`

```sql
-- 只记录索引定义作为证据，禁止再次执行 CREATE INDEX。
CREATE INDEX idx_v2_chat_message_ledger_r60_b2
ON public.v2_chat_message_ledger USING btree
  (session_id, story_id, recorded_at, id)
INCLUDE (turn_index, message_id, role, operation);
```

只读 Catalog 复核（最新约 `2026-11-06 03:44:04 UTC`）：

- Key 精确为 `session_id, story_id, recorded_at, id`，INCLUDE 精确为 `turn_index, message_id, role, operation`。
- `indisvalid=true`、`indisready=true`、`indislive=true`、非唯一索引。
- 当前索引实际体积 `7,520,387,072` bytes，约 `7.00 GiB`；大小会随写入变化，不是永久常数。
- Ledger 共 6 个索引，原来的 5 个仍在；`invalid_or_not_ready=0`；`pg_stat_progress_create_index` 目标表无记录。
- 生产建索引动作已在用户侧完成；**本次核验全程没有执行 DDL/DML/ANALYZE 或修改任何权限、RLS、Trigger**。

### 已有查询计划检查

先前以**明确不存在的合成 Story/Session 参数**测试生产 B2：

- 首页 Metadata：`Limit -> Index Only Scan`，使用 B2。
- Keyset 下一页 Metadata：`Limit -> Index Only Scan`，使用 B2；`(recorded_at,id)` 游标条件进入 Index Cond。
- `turn_index` 范围仍在 Filter 中。
- 上述是普通 `EXPLAIN (FORMAT JSON)`，没有 `ANALYZE`，不返回任何生产正文。

**局限：** 不能将合成参数的 plan rows / cost 外推到实际大型 Session。即便 `Index Only Scan` 被选择，真实执行仍可能发生 heap fetch，是否发生只能通过经批准的执行计划/运行监控证明。

### 索引使用计数

`pg_stat_user_indexes.idx_scan` 在本次采样仍为 `0`。它只是该统计计数器当前的观察值，**既不能证明索引无效，也不能证明业务已从中获益**。需用真实负载观察统计增量，并注意 stats reset/读取延迟。

## 四、已有性能基线与工程优化

### 历史 Pilot8 基线（优化前）

- 8 Case 请求，5 恢复、3 HOLD（`HISTORY_SUFFIX_NOT_USER`）。
- 总恢复 wall time 约 436.7 秒。
- SQL execute wall time 约 436.0 秒；其中 Metadata 约 328.2 秒、Detail 约 83.1 秒、Current History 约 21.3 秒。
- 这些数据是在新 B2 索引和 Current History 复用代码上线之前取得，**不是当前生产耗时**。

### 跨 Session 规划器结果

| 匿名样本 | Metadata 截止目标的事件量 | Baseline Limit Cost | Candidate A Cost | B2 Cost |
|---|---:|---:|---:|---:|
| S01 | 6,794 | 3,407.99 | 489.26 | 2.29 |
| S02 | 13,740 | 3,407.99 | 489.26 | 3.79 |
| S03 | 606,860 | 330,289.22 | 52,496.15 | 2,617.14 |

所有成本都是 **HypoPG EXPLAIN 估算值**。不能将估算下降转换为秒数、TPS 或真实加速倍数。

### Current History 代码优化

PR #16 已在 `src/storyforge_gold_quality/history_recovery.py` 实现有界 Session 级历史超集缓存，保留：

- 每个 Case 独立的目标 `created_at < target_time` 和 `turn_index <= target_turn - 1` 过滤。
- `created_at,id` 原始排序和 Ledger 事件 `recorded_at,id` 语义。
- `max_history + 1` 限制，超限时回退原逐案读取，而非截断。
- 每个 Case 的独立 `HISTORY_SUFFIX_NOT_USER` HOLD。
- 不跨 Story 或 Session 共享；无训练准入变动。

PR #16 最后一次确认的 CI：`#2013` **PASS（724 passed、5 skipped、33 subtests passed）**，Gold Quality Pipeline `#935` PASS。**代码仍在 Draft PR 内，未通过合并部署到默认分支**，所以不能声称本优化已经影响线上恢复性能。

### Detail Batch

6,854 条合成 JSONB 对象的 Batch 500/1000/2000 对照完成。初步认为 Batch 1000 值得今后受控验证；没有服务器端实测，**生产默认维持 500**。

## 五、生产健康度单点复核

`2026-11-06 03:44 UTC` 前后从统计视图观察：

| 指标 | 当前观测 |
|---|---:|
| PostgreSQL 数据库大小（pg_database_size） | 213,088,193,683 bytes |
| Ledger 含索引总大小 | 117,834,670,080 bytes |
| Estimated live tuples | 43,227,728 |
| Estimated dead tuples | 1,092,270 |
| 连接数 | 32 |
| 活跃连接数 | 1 |
| idle in transaction | 0 |
| Lock wait connections | 0 |
| 未获授予的锁 | 0 |
| WAL bytes（累计） | 1,900,002,745,988 |
| WAL stats reset | 2026-07-27 |
| 可见复制会话 / 复制槽 | 0 / 0 |

**解释限制：**

1. 这些是单点数值，不构成生产性能 SLO 通过证明。
2. `pg_database_size` 并不等于 Supabase 宿主卷实际已用/可用空间。用户在索引创建前提供过 219 GB provisioned、191.39 GB used 的 Dashboard 截图；**尚无创建后 Dashboard 磁盘数字**。
3. WAL bytes 是自统计重置以来的累计值，不是构建时峰值/WAL 速率。
4. 复制视图无可见会话/槽，不能据此断言托管环境没有副本。
5. `pg_stat_database.deadlocks` 当前累计为 26，缺少相同统计周期的增量，不能判定其与建索引有关。

**因此，本次结项的通过范围是索引部署与数据库 Catalog 完整性，不是全部基础设施 SLO 验收。**

## 六、安全、隐私及冻结约束

- 没有重新执行 B2 建索引脚本，也没有对原五个索引执行 DROP/REINDEX。
- 没有执行数据库写入、RLS/Trigger/Role 修改。
- Supabase 只读 Connector 的角色 `supabase_read_only_user` 具有 `BYPASSRLS`，本轮严格只查系统 Catalog/聚合监控，不查询真实消息正文或私有 Session/Story ID。
- 没有访问 R50、没有启动 GPU/训练、没有新增 Quality-v1 admission。
- Pilot8 原有 3 条 `HISTORY_SUFFIX_NOT_USER` HOLD 保留；不能因索引成功而改判。

## 七、收尾交付与后续所有权

**R60 生产 B2 索引上线工作可按“部署已完成，实测收益待后验”结项。** 请保留以下独立后续事项；无需为了等待这些数据而再次创建索引：

| 剩余事项 | 当前状态 | 建议负责方 |
|---|---|---|
| 生产环境可用磁盘、WAL、复制延迟和写入 SLO 的持续监控 | PENDING | DBA / Supabase 项目 Owner |
| 使用 Owner 私有 `r58_export_reader` 在真实 Pilot8 Session 上只读对比 B2 plan、`idx_scan` 增量、真实耗时、heap fetches、rows 与 HOLD | PENDING，独立授权 | R60 后续性能实验 |
| PR #16 代码审查、合并与部署策略 | DRAFT / UNMERGED | 项目 Owner |
| PR #17 运维脚本、报告及证据合并 | DRAFT / UNMERGED | 项目 Owner |
| Pilot8 v3 数据重跑 | NOT RUN（独立授权） | 数据质量负责人 |

## 八、可回溯证据

- [PR #16 — R60 性能优化与 Current History 代码](https://github.com/sunxu/storyforge/pull/16)
- [PR #17 — R60 B2 生产部署与验收](https://github.com/sunxu/storyforge/pull/17)
- `docs/evidence/R60_B2_PRODUCTION_INDEX_POSTBUILD_SAFE.json`：2026-11-06 首次生产安装验收。
- `docs/evidence/R60_LEDGER_PERFORMANCE_CLOSEOUT_SAFE_20261106.json`：最终复核安全回执。
- `docs/R60_B2_PRODUCTION_INDEX_RUNBOOK_CN.md`：构建及事故处理背景，**建成后不得再次运行 CREATE INDEX 脚本**。
- 本报告：`docs/R60_LEDGER_PERFORMANCE_CLOSEOUT_CN.md`。

**最终状态：`R60_PRODUCTION_B2_INDEX_DELIVERED__CODE_PR_PENDING_MERGE__REAL_RUNTIME_UNVERIFIED`。**
