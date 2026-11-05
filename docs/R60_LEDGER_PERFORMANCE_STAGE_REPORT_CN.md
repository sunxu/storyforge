# R60 Ledger 性能优化阶段报告

日期：2026-11-05  
仓库：sunxu/storyforge  
分支：r60/ledger-performance-handoff  
范围：只读性能研究、恢复代码审计、合成批量实验；不包含真实索引变更、训练或数据准入。

## 1. 阶段结论

- T0：PASS（代码与任务书已核对；共享实现当前没有被本轮修改）。
- T1：PASS（Connector 身份、只读和 RLS 已核验；HypoPG 权限已核验）。
- T2：PASS（Owner 本机 SAFE 回执提供三个 Session 的 Baseline/A/B 对照；Connector 另完成一组真实参数 Baseline EXPLAIN）。
- T3：PASS（查询与缓存路径审计完成；提出 Current History 跨 Case 复用方案，未改变核心算法）。
- T4：合成实验 PASS（500/1000/2000 比较完成；结果仅代表本地 JSON 解码/批次组织，不代表 PostgreSQL 性能）。
- T5：HOLD（缺少可用磁盘余量、WAL 保留、写入速率时间窗口和副本滞后等变更窗口证据；不申请立即创建索引）。
- T6：未执行；需要单独授权。

## 2. T0：代码基线与审计范围

工作分支相对 `r60/gold192-ledger-diagnostics` ahead 2 / behind 0；本轮读取的共享代码文件 Blob SHA：

| 文件 | Blob SHA |
|---|---|
| `src/storyforge_gold_quality/message_ledger.py` | `b72cf37dbc0d9f57c9a219b23fd370b51f79ed08` |
| `src/storyforge_gold_quality/history_recovery.py` | `6be6a42e3de564a6da465fd5ee9c0a16a8ee2906` |

本轮未修改共享 Ledger / Recovery 核心。

## 3. T1：Supabase Connector 核验

身份 guard：

- database：`postgres`
- current_user：`supabase_read_only_user`
- `transaction_read_only=on`
- `row_security=on`
- Ledger 表 `relrowsecurity=true`

HypoPG：

- extension：`hypopg 1.4.1`
- `extensions` schema USAGE：true
- `hypopg_create_index(text)` EXECUTE：true
- `hypopg_reset()` EXECUTE：true

Connector 角色当前能看到 Ledger 的四个 `pg_stats` 列统计：`session_id`、`story_id`、`turn_index`、`recorded_at`。这与先前 Owner 本机角色查询 0 行的观察不同；两种连接身份的统计可见性不得互相推断。

HypoPG 是会话级规划器状态。Connector 的两次独立 SQL 调用没有保留同一 HypoPG 假想索引状态：创建假想索引后，下一次 EXPLAIN 仍为原始索引计划。因此本轮不声称 Connector 已完成 B2 HypoPG 复验，也没有为此申请权限变更。

数据库规模（本轮只读 catalog 查询）：

| 指标 | 观察值 |
|---|---:|
| Database size | 204,158,102,675 bytes |
| Ledger total size | 110,025,793,536 bytes |
| Ledger heap | 18,082,234,368 bytes |
| Live tuples estimate | 43,104,350 |
| Dead tuples estimate | 1,082,609 |
| 当前五个 Ledger 索引合计 | 10,155,589,632 bytes（约 9.46 GiB） |

索引统计：

- session 索引：5,998,698,496 bytes；idx_scan 57,244
- recorded_at 索引：1,401,716,736 bytes；idx_scan 5,919
- user 索引：1,091,903,488 bytes；idx_scan 1,190
- primary key：1,000,423,424 bytes；idx_scan 853
- client partial index：662,847,488 bytes；idx_scan 0

`idx_scan=0` 不是删除依据。统计计数是累计观测值，不能直接解释为当前时段负载。

## 4. T2：跨 Session B0/B2

Owner 提供的 SAFE 回执包含三个匿名 Session。结果如下；成本均为 EXPLAIN/HypoPG 估算单位，不是毫秒：

| 样本 | 事件数 | Baseline Limit Cost | A Limit Cost | B2 Limit Cost |
|---|---:|---:|---:|---:|
| S01 | 6,794 | 3,407.99 | 489.26 | 2.29 |
| S02 | 13,740 | 3,407.99 | 489.26 | 3.79 |
| S03 | 606,860 | 330,289.22 | 52,496.15 | 2,617.14 |

三组 Baseline 均为 `Limit -> Index Scan`；A/B2 均为 `Limit -> Index Only Scan`。

B2 相对 Baseline 的估算 Limit Cost 降幅：

- S01：99.93%
- S02：99.89%
- S03：99.21%

B2 相对 A 的估算成本分别约低 213.65 倍、129.09 倍、20.06 倍。

解释边界：

1. 三组都支持 B2 对该 Ledger Metadata 查询形态有稳定的规划器收益。
2. S01/S02 的估算行数分别为 1/11；S03 受 LIMIT 10,000 约束。不能把估算成本直接换算为实际耗时或吞吐提升。
3. 这不是生产索引实测，也不代表其他业务查询没有回归。
4. Owner 提供的 SAFE 回执报告：`database_modified=false`、`real_index_created=false`、`private_values_emitted=false`。

Connector 另以 RLS 可见范围内的一个匿名 Session 做了真实参数 Baseline EXPLAIN，结构为 `Limit -> Index Scan`；Index Cond 仅使用 `session_id`，Story 与 Turn 仍在 Filter。Connector 假想索引跨调用状态未保留，因此没有把该样本纳入 B2 结果集。

## 5. T3：代码审计

### 5.1 Metadata

`load_session_events` 当前：

- 每个 Session 一次 Metadata 读取流程。
- 以 10,000 条为页大小。
- 使用 `(recorded_at, id)` 作为稳定 Keyset 游标。
- SQL 按 `recorded_at, id` 排序。
- 每页仅读取事件元数据，不直接读取大 JSONB before-image。

结论：不改变分页顺序或事件排序。不能擅自把排序改为 `id` 单列，也不能把 turn 范围解释为已认证的事务提交顺序。

### 5.2 Detail

- 当前每批 500 个 ID。
- 仅按主键取 `id,row_data`。
- 仅取 target boundary 与可能影响重建的 first post-boundary events。
- 结果保存在 Session 级 details map，再回填事件。
- UPDATE_BEFORE / DELETE snapshot 与 INSERT / UPDATE_AFTER marker 校验仍然独立。

不应通过批量增大来改变 required-event 集合或事件顺序。

### 5.3 Session / Event 缓存

`recover_cases_independently` 已按 `(story_id, session_id)` 分组，并且：

- 每个 Session 一次 Ledger Metadata / Detail 读取；
- 每个 Session 构建一个 `LedgerEventIndex`；
- Session lineage 与 Story version 使用缓存。

因此“同一批 Case 重复加载 Ledger Metadata”不是当前批量入口的主要剩余问题。单 Case `recover_case` 仍保留独立读取回退路径。

### 5.4 Current History

`_history` 仍由每个 Case 调用一次。Pilot8 观测为 8 次查询、11,708 行、约 21.3 秒。

低风险优化候选：在同一 Story/Session 的 Case 组内，读取一个受限的历史超集（最大 target time 与最大物理 turn cutoff），然后在内存中按每个 Case 自己的 `created_at < target_time` 和 `turn_index <= target_turn - 1` 再过滤。

实施前必须证明：

- Superset 有独立硬上限；超过上限时逐案 HOLD，不截断。
- 不同 target 的 created_at 与 turn cutoff 分别应用。
- 不跨 Story/Session 复用。
- 完整保留 `created_at,id` 排序及状态过滤语义。
- 对“先删除后目标”“未来消息”“边界同时间戳”“fork child materialized history”建立测试。
- 逐案 `HISTORY_SUFFIX_NOT_USER` 仍由每个目标自己的重建结果决定。

本轮只完成设计，不改共享核心。

## 6. T4：Detail Batch 合成实验

合成规模：6,854 条 JSON 对象，合计 13,941,647 bytes；最大单条 JSON 对象 64,148 bytes。分别比较 500 / 1,000 / 2,000；每组重复 5 次。只模拟 Python JSON 解码与当前全量 details map 保留，不连接数据库、不读取生产数据。

| Batch | 模拟 SQL 批次数 | 最大批次 JSON bytes | 峰值 traced memory | 本地解码中位数 |
|---:|---:|---:|---:|---:|
| 500 | 14 | 1,016,300 | 18.89 MiB | 99.21 ms |
| 1,000 | 7 | 2,032,598 | 18.90 MiB | 90.32 ms |
| 2,000 | 4 | 4,061,453 | 18.90 MiB | 101.68 ms |

每条 SQL 使用一个数组 bind parameter；数组元素数不是 SQL bind parameter 数。当前实现的批量查询形式是 `WHERE id = ANY(%s)`，因此 500/1000/2000 分别仍是 1 个 bind 参数，不触及“每个 ID 一个 bind 参数”的参数数量模型。

解释边界：

- 500 到 1,000 将模拟批次数减半；本地 JSON 解码中位数只小幅变化。
- 2,000 将最大单批 payload 提高到约 4.06 MB，但本地解码中位数反而高于 1,000。
- 峰值 Python traced memory近似不变，是因为当前实现会把全部 detail row_data 保留在 details map；批量大小并没有消除总 payload 驻留。
- 本地 wall time 不包含 PostgreSQL 执行、网络往返、服务端内存、TOAST 解压或 I/O。

建议：保留生产默认 500。1,000 可作为后续受控只读 Pilot 的候选；2,000 暂不推荐。不能仅凭本合成实验修改默认值。

## 7. T5：索引申请评估

候选估算：

- B0：约 7,332.48 MB（约 7.16 GiB）
- B2：约 11,955.13 MB（约 11.68 GiB）

B2 约为当前五个 Ledger 索引总量的 1.24 倍；若直接新增且不替代现有索引，会显著增加索引体积与写入维护成本。B0 较小，但当前证据显示仍是 Index Scan，且成本收益低于 B2。

本轮无法通过当前 Connector 证明：

- 数据盘可用空间及构建期间峰值余量；
- WAL 保留/生成速率的时间窗口；
- 副本 lag 与索引构建期间的复制影响；
- 写入 TPS、Ledger insert rate 的近期区间值；
- B2 对其他生产查询的回归影响。

因此 T5 = HOLD：当前不提交立即创建索引的变更申请。后续 DBA 申请应先补齐容量、WAL、复制、写入负载和其他查询回归证据。不得删除现有索引作为空间腾挪手段。

## 8. 安全与训练边界

本轮没有执行 DDL/DML、ANALYZE、GRANT/REVOKE、RLS/Trigger/Policy 变更、真实索引创建、GPU 或训练。没有访问 R50，没有改变任何 HOLD 或 Quality-v1 admission。

Ledger commit-order 与 trigger-continuity 仍未认证；因此不得把 `recorded_at,id` 的读取顺序提升为数据库事务提交顺序证明。

## 9. 下一步

1. 为 Current History Session 级 superset cache 增加独立设计与合成测试，先不触碰 Ledger 重建算法。
2. 对 B2 继续做更多查询形态的计划回归检查；成本改善不能替代生产负载回归。
3. 由 DBA/Owner 提供可用磁盘、WAL、replica lag、写入负载的安全聚合证据后，再决定是否形成正式索引变更申请。
4. Pilot8 v3 仍需单独授权。
