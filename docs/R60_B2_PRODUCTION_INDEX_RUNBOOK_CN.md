# R60 B2 生产索引上线 Runbook（仅 DBA 手工执行）

日期：2026-11-05  
目标数据库：Supabase PostgreSQL 17.6 / `postgres`  
目标表：`public.v2_chat_message_ledger`  
变更类别：单个 **非唯一** B-tree 索引，在线并发创建  
对应代码：`ops/r60/build_b2_index_prod.sh`  
状态：**准备就绪，实际执行 HOLD（容量、WAL/副本、变更窗口与具有 DDL 权限的生产连接待核验）**。

## 0. 绝对边界

- 本文件是**运维 Runbook**，不是自动执行的数据库 migration。CI/PR 合并不得运行脚本。
- 不删除、替换或重建原有 5 个 Ledger 索引。
- 不修改 RLS、Policy、Trigger、权限、表数据或 schema 中任何其他对象。
- 不启动 GPU、不训练、不扩大 Gold192 样本，也不改变逐案 HOLD。
- 原有 Ledger `(recorded_at, id)` 排序、UPDATE_BEFORE/UPDATE_AFTER 和时间边界原样保留。
- 执行账号须为目标表所有者 `postgres`，并持有数据库 DDL 能力；`r58_export_reader` 和 `supabase_read_only_user` 均不可使用。
- 不得在聊天、仓库、日志、CI 中存储 DSN、密码、Session/Story/Message ID 或正文。

## 1. 实证与候选选择

已经完成三个不同规模 Session 的 HypoPG 对照（成本是规划器估算单位，不是毫秒）：

| 样本 | 事件数 | Baseline Limit Cost | A Limit Cost | B2 Limit Cost |
|---|---:|---:|---:|---:|
| S01 | 6,794 | 3,407.99 | 489.26 | 2.29 |
| S02 | 13,740 | 3,407.99 | 489.26 | 3.79 |
| S03 | 606,860 | 330,289.22 | 52,496.15 | 2,617.14 |

Baseline 为 Index Scan；B2 三组均为 Index Only Scan。B2 估算体积约 **11,955 MB（11.68 GiB）**，该值不是实测构建峰值空间。

生产 DDL，仅在下面所有门禁 PASS 后由运维脚本执行一次：

```sql
CREATE INDEX CONCURRENTLY idx_v2_chat_message_ledger_r60_b2
ON public.v2_chat_message_ledger USING btree
  (session_id, story_id, recorded_at, id)
INCLUDE (turn_index, message_id, role, operation);
```

不使用 `IF NOT EXISTS`，避免与已有 INVALID 同名索引发生静默跳过。

## 2. 当前已由 Agent 只读核验的门禁

| 检查 | 实际观测 | 状态 |
|---|---|---|
| PostgreSQL 版本 | 17.6 | PASS |
| 目标表 | 非分区、持久表，owner `postgres` | PASS |
| 索引 key / INCLUDE 列 | 均存在；类型合法 | PASS |
| 同名 R60 B2 索引 | 不存在 | PASS |
| 原有索引 `indisvalid/indisready` | 五个全部 true | PASS |
| 正在构建该表索引 | 0 | PASS |
| Connector 当前事务 | read-only=on | 元数据检查 PASS；**不可执行 DDL** |
| 可用数据库宿主磁盘容量 | SQL catalog 无法证明 | HOLD |
| WAL/副本与构建窗口负载 | 单点累计统计不足以证明 | HOLD |
| 可执行 DDL 的 Owner 生产连接 | 当前 Agent 不持有 | HOLD |

相关环境观测：Ledger total 约 110.0 GB；WAL `max_wal_size=4096 MB`，`maintenance_work_mem=512 MB`，`max_parallel_maintenance_workers=1`。`pg_stat_replication` / `pg_replication_slots` 当前查询均未返回活动数据；这不代表托管环境没有副本或 WAL 风险。

## 2A. 2026-11-05 Owner Dashboard 磁盘截图核验（已获取）

Owner 提供 Supabase Dashboard **Disk** 截图，显示 primary database：

| 指标 | 截图观察值 |
|---|---:|
| Provisioned disk | 219 GB |
| Used | 191.39 GB |
| Free（计算值） | 27.61 GB |
| Used ratio（计算值） | 87.39% |
| B2 预计最终占用 | 约 11.68 GiB / 12.54 GB |
| 不扩容、仅计索引体积的预计剩余 | 约 15.07 GB |
| 不扩容、仅计索引体积的预计使用率 | 约 93.12% |

**容量 Gate 结论：HOLD。** 本截图 **不能**标记 `R60_B2_DISK_APPROVED=YES`。现有空余 27.61 GB 不满足前述至少 36 GiB（约 38.65 GB）初步人工余量要求，更不足以覆盖 B2 最终空间、构建临时数据、WAL、持续写入及平台其他空间需求。

建议在 Supabase Database Settings / Infrastructure 主动**扩容到 300 GB**（可接受的较低成本备选 280 GB，但需 DBA 明确确认负载余量）。300 GB 情况下，仅计当前已用与 B2 最终体积，估算剩余约 96.07 GB；这仍非真实构建峰值可用空间的证明。

扩容前应核对 Supabase 实际计费预览。gp3 额外 provisioned disk 按 $0.125/GB/月近似，219 → 300 GB 增加 81 GB，约多 $10.13/月；不含其他费用。Supabase 付费项目约 90% 使用率时可触发自动扩容；95% 有进入只读状态的风险；每次磁盘修改后存在约四小时冷却。**不要依赖并发建索引过程中自动扩容救场**。

行动顺序：

1. Owner 在 Dashboard 将 Disk size 调至建议值，确认费用与变更。
2. 只有 Dashboard 显示扩容完成、provisioned / used / free 已更新且没有剩余磁盘修改中的状态，才重新判定磁盘 Gate。
3. DBA 审核此前的 15m / 1h / 24h WAL、复制、IO 和写入峰值；必要时增加预留，不足则继续 HOLD。
4. 使用独立生产 Owner 可写**直连或会话保持**的主机与数据库身份，在低峰窗口执行脚本；不得把写入 DSN 发给 ChatGPT。
5. 构建后再由 Owner 只读校验新索引有效、应用写入正常以及计划改善。

官方依据：
- https://supabase.com/docs/guides/platform/database-size
- https://supabase.com/docs/guides/platform/compute-and-disk
- https://supabase.com/docs/guides/platform/manage-your-usage/disk-size

## 3. 执行前必须在 Supabase 平台侧验证

由 DBA/项目 Owner 在 Supabase Dashboard `Database Settings` / `Infrastructure` 检查：

1. **实际 provisioned disk / used / free**，不是 `pg_database_size`。记录构建前空余、扩容剩余次数、是否处于磁盘扩容冷却期及是否临近 90% 自动扩容或 95% 只读阈值。
2. 为 B2 约 11.68 GiB 索引预留额外构建临时空间与 WAL 余量。**建议至少预留约 36 GiB 的可用空间作为初始人工门槛**（约三倍索引估值），并依照最近实际 WAL 峰值、并发写入及平台规定增加余量；36 GiB 本身不是足够空间的证明，DBA 可要求更高门槛。
3. 检查最近 15 分钟、1 小时及 24 小时的 WAL 增量、磁盘 IOPS/带宽、CPU、正在运行的写入事务和 replication lag。若无法查看托管副本指标，应联系平台/DBA，不得据空结果判为无副本。
4. 在低峰维护窗口创建，DBA 指定监控人员、停止阈值、复查窗口以及是否需要提前扩容。
5. 本脚本只接受人工 `YES` 门禁，不会通过 PostgreSQL SQL catalog 自动取得云盘空余空间。必须先完成真实观察并留存运维记录。

Supabase 参考：https://supabase.com/docs/guides/platform/database-size
PostgreSQL 17 `CREATE INDEX CONCURRENTLY` 参考：https://www.postgresql.org/docs/17/sql-createindex.html

## 4. 正式部署（仅经 Owner + DBA 核验后）

必须使用 **独立的可写直连/会话保持型 PostgreSQL 连接**，切勿使用事务池化器、只读 DSN 或将 DDL 嵌入 `BEGIN`。

建议从私人凭据管理器加载独立 Owner 连接信息为 `PGHOST`、`PGPORT`、`PGDATABASE`、`PGUSER`、`PGSSLMODE` 和受保护的 `~/.pgpass` / `PGPASSFILE`。不要将凭据放在命令行参数、shell history 或 GitHub Secrets 的公开输出中。不要重复使用 `r60-explain-private.env` 的只读设置。

```bash
# 仅在 DBA 认可容量/WAL/副本与变更窗口之后设置：
export R60_B2_OWNER_APPROVED=YES
export R60_B2_DISK_APPROVED=YES
export R60_B2_WAL_APPROVED=YES
export R60_B2_WINDOW_APPROVED=YES

# 在 r60/ledger-b2-production 分支工作树运行：
bash ops/r60/build_b2_index_prod.sh
```

脚本先检查角色、只读开关、RLS、普通持久表、所有者、同名索引不存在、索引构建空闲；任一不满足即 HOLD。构建使用 `CREATE INDEX CONCURRENTLY`，会话级 `lock_timeout=5s`、`statement_timeout=0`（仅允许监控窗口下长时运行）。如果执行失败，不会自动删除任何索引，需 DBA 查看 INVALID 状态再决策。

## 5. 运行期间只读监控

另开一个 DBA 只读监控连接：

```sql
SELECT phase, blocks_total, blocks_done, tuples_total, tuples_done,
       lockers_total, lockers_done
FROM pg_stat_progress_create_index
WHERE relid = 'public.v2_chat_message_ledger'::regclass;
```

同时监控 Supabase 平台磁盘使用、CPU、IO、WAL、复制延迟、错误率与应用写入时延。

**停止条件：** 磁盘剩余触及 DBA 预设安全下限、持续复制积压、应用写入超出 SLO、出现严重锁等待或其它生产负载异常；由 DBA 决定是否停止建索引进程，并执行后续残留索引核验。

## 6. 完成后核验

```sql
SELECT c.relname,
       i.indisvalid, i.indisready, i.indislive,
       pg_size_pretty(pg_relation_size(c.oid)) AS index_size,
       pg_get_indexdef(c.oid) AS index_definition
FROM pg_class c
JOIN pg_index i ON i.indexrelid = c.oid
WHERE c.oid = to_regclass('public.idx_v2_chat_message_ledger_r60_b2');
```

要求：`indisvalid=true`、`indisready=true`、`indislive=true`、定义严格匹配 B2。下一步用 Owner 私有参数执行普通 `EXPLAIN (FORMAT JSON)`（**不含 ANALYZE**），记录是否被优化器选中、Index Cond（session+story）、Sort/Filter、估算成本。验证应用正常写入。不得宣称真实 wall-time 加速，除非后续另行批准只读运行时 Pilot 并获得对照。

## 7. 失败与回滚

构建失败后，先仅查询 catalog，辨别同名索引是否存在且无效；**不要直接重新执行脚本**，也不要将 INVALID 残留当成已部署。DBA 在充分确认目标对象名称及依赖后，可以单独审批：

```sql
DROP INDEX CONCURRENTLY public.idx_v2_chat_message_ledger_r60_b2;
```

同样不允许包装在 `BEGIN` / `COMMIT` 中，不能误删原有 5 个索引。回滚不意味着撤销建索引期间的 IO/WAL 成本。需重新验证原查询与应用运行。禁止在未经诊断的情况下自动 DROP / REINDEX。

## 8. 交付状态和必要人工门禁

- 生产脚本：已准备，必须经 DBA 执行。
- 真实生产索引：**尚未创建**。
- 该次生产变更范围仅为 **单一 B2 索引**，绝不自动扩展至其他表/索引。
- Owner 用户的“尽快完成生产索引落地”确认了推进目标，但并不能自动证明平台空间充足或 DBA 写入身份已授权。任何缺少第 3 节证据的执行均保持 HOLD。
