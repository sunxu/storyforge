# R60 Ledger 性能优化任务书（新会话执行版）

日期：2026-11-05  
仓库：sunxu/storyforge  
工作分支：r60/ledger-performance-handoff  
基线：r60/gold192-ledger-diagnostics  
任务性质：只读数据库性能研究 + 恢复代码审计；不包含生产索引变更、训练或数据准入。

## 0. 新会话启动指令

你接手的是 StoryForge R59 Gold192 历史上下文恢复的数据库性能优化子任务。目标是降低 Pilot8 恢复时 Ledger Metadata / Detail 读取成本，同时保持历史证据、时间边界、Ledger 重建语义和逐案 HOLD 规则不变。

先阅读：
1. docs/R60_LEDGER_PERFORMANCE_HANDOFF_CN.md
2. 本任务书
3. docs/R60_PILOT8_PERFORMANCE_DIAGNOSIS_CN.md
4. experiments/r58_quality/r59_gold192_history_recovery.py
5. src/storyforge_gold_quality/history_recovery.py
6. src/storyforge_gold_quality/message_ledger.py

先核对 GitHub 分支最新 HEAD 和工作区状态。新会话不要假定已有本机 worktree；不要切换或覆盖 Owner 的其他 worktree。不要在 detached HEAD 上提交。

## 1. 总目标

在不改变恢复结果和安全语义的前提下：
- 找到 Ledger Metadata 查询耗时高的根因。
- 评估 B0/B2 索引候选在多个 Session 上的稳定性。
- 识别 Metadata 与 Detail 查询是否存在可安全合并、投影优化、批量优化的机会。
- 通过合成测试评估 Detail batch 500/1000/2000，不直接对生产扩大批量。
- 对 Current History 查询做计划检查，但不得放松时间、Story、Session、Turn 约束。
- 给出真实索引是否值得申请的量化建议。

非目标：
- 不要求 192 条全部恢复或全部通过。
- 不改变任何 HOLD 为 PASS。
- 不做训练候选 admission。
- 不启动 GPU、不运行 SFT。
- 不修改 Supabase schema/index/trigger/policy/grant。
- 不启用 Session 并发，除非后续独立设计证明 Ledger 顺序与一致性安全，并另行审批。

## 2. 当前已知性能证据

Pilot8：
- 8 requested / 5 recovered / 3 HOLD。
- HOLD reason：HISTORY_SUFFIX_NOT_USER × 3。
- 4 Session / 4 Story。
- 9,599 history messages。
- 436,740.936 ms recovery wall time。
- 435,964.018 ms SQL execute wall time。
- 303.250 ms fetch wall time。
- 111 SQL queries / 659,707 actual fetched rows。

耗时类别：
| Query | Count | Execute ms | Rows |
|---|---:|---:|---:|
| LEDGER_METADATA_QUERY | 66 | 328,185.424 | 641,051 |
| LEDGER_DETAIL_QUERY | 16 | 83,135.125 | 6,854 |
| CURRENT_HISTORY_QUERY | 8 | 21,299.892 | 11,708 |

### 2.1 索引结果

真实参数第一页 EXPLAIN：
- Baseline Limit Cost：330,281.54（约值）
- Index Cond 只有 session_id。
- story_id 与 turn_index 位于 Filter。

HypoPG 对照：
| 方案 | 大小估算 MB | Limit Cost | 扫描 |
|---|---:|---:|---|
| Baseline | — | 330,281.54 | Index Scan |
| A | 11,955.12 | 52,426.37 | Index Only Scan |
| B / B2 | 11,955.13 | 2,613.51 | Index Only Scan |
| B0 | 7,332.48 | 18,256.46 | Index Scan |
| B1 | 8,395.16 | 18,312.80 | Index Scan |

B0 定义：
(session_id, story_id, recorded_at, id)

B1 定义：
B0 + INCLUDE (turn_index)

B2 定义：
B0 + INCLUDE (turn_index, message_id, role, operation)

B2 的 Index Cond 已验证包含 session_id + story_id；Turn 范围仍在 Filter；没有额外 Sort。B1 增加约 1.06GB，却没有比 B0 更好的估算计划，当前淘汰。B0 空间优先，B2 性能优先。以上均为一个大 Session 的 HypoPG 估算，不能等同真实性能提升。

## 3. Supabase 调用分工（强制）

### 3.1 Agent 必须直接使用 Supabase Connector

当前已验证 Connector：
- database：postgres
- role：supabase_read_only_user
- transaction_read_only：on
- row_security：on

通过已连接的 StoryForge Supabase Read Only 插件直接执行可完成的只读请求。不得让 Owner 复制执行 Agent 自己能够通过 Connector 完成的 SQL。

Agent 优先执行：
1. 身份/只读/RLS guard。
2. 当前表结构、索引定义和索引大小。
3. 表/列统计、pg_stats / pg_statistic 可见性诊断。
4. 对连接器可见的受限 Session 执行普通 EXPLAIN (FORMAT JSON)，不使用 ANALYZE。
5. 检查连接器角色是否可访问 HypoPG Schema/函数；只检查，不授予权限。
6. 通过有限、聚合化的查询发现连接器可见的候选 Session，并在安全范围内做跨 Session 计划比较。
7. 每次查询前判断是否可能触发大表扫描；设定 statement_timeout；不跑无边界 COUNT(*) 或大范围 payload 读取。

Agent 不得执行：
- DDL/DML、migration、ANALYZE、CREATE/DROP/REINDEX、GRANT/REVOKE。
- 修改 RLS、trigger、role 或 schema。
- 用管理连接、service_role 或 BYPASSRLS 绕过访问限制。
- 输出私有正文、ID、DSN、token、私有 case-level 数据。
- 把 RLS 造成的不可见误报为数据不存在。

### 3.2 Owner 本机执行仅作为最后手段

仅在下列条件之一成立时才要求 Owner 本机操作：
- 必须使用 Owner 本机私有 DSN 的 r58_export_reader，且 Connector 角色的数据可见范围不同。
- 参数只存在于本机私有恢复证据，Agent 无法从 Connector 安全取得。
- 必须检查本机私有文件、SHA256、HypoPG JSON 或私有运行环境。
- 必须在本机运行恢复引擎或离线合成测试。

要求 Owner 操作时：
- 先解释为何 Connector 无法完成。
- 给出一组最小命令，避免多轮复制。
- 只让 Owner 返回 SAFE 汇总，不要索取 SQL 参数、ID、正文或文件内容。
- 不重复要求 Owner 查询 Connector 已可查询的表结构、统计或索引信息。

### 3.3 Connector 与本机角色差异

本机角色：r58_export_reader；曾验证其业务表 SELECT 与 RLS on，并由 Owner 为 HypoPG 使用授予了 USAGE ON SCHEMA extensions（未授予 CREATE）。  
Connector 角色：supabase_read_only_user。两者权限、RLS identity、JWT subject、数据范围均不可假定相同。

每次连接器执行 SQL，先运行：

    SELECT current_database(),
           current_user,
           current_setting('transaction_read_only'),
           current_setting('row_security');

如连接器没有看到本机私有 Session，不得通过提高权限、切换角色或使用 BYPASSRLS 绕过。改用连接器可见的安全样本做计划结构验证；如果这无法回答目标问题，再明确提出最小 Owner 本机验证。

## 4. 任务阶段与验收

### T0 — 接手核验（必须先做）

Agent：
- 核对分支 HEAD、当前文件内容、相关 CI 和工作树/分支状态。
- 读取共享恢复核心和 Ledger 实现。
- 复核查询生成点、分页策略、Metadata/Detail 分批逻辑、event ordering、snapshot/marker 规则。
- 对照已有性能报告，确认报告与代码版本一致。
- 输出一份 SAFE 接手报告。

验收：
- 明确代码 SHA 与报告对应关系。
- 找出 Metadata 查询具体 SQL 及其分页游标语义。
- 找出 Detail batch 默认值和 payload 读取路径。
- 不修改代码或数据库。

### T1 — Connector 只读可见性和统计信息诊断

Agent 通过 Supabase Connector：
- 验证身份、read-only、RLS。
- 检查 ledger 表大小、索引定义及统计。
- 解释为何 pg_stats 可能对 Connector 返回 0 行；比较 pg_statistic 的安全可见性，但不要尝试绕过权限。
- 检查 hypopg 扩展和函数权限；不得主动授予 USAGE。
- 检查索引扫描统计的观测窗口局限。

验收：
- 输出 Connector role 的可见性结论。
- 清楚区分权限不可见与数据为空。
- 不执行 DDL/DML/ANALYZE。

### T2 — 跨 Session B0/B2 计划结构验证

优先用 Connector 能安全访问的真实数据。选择至少 3 个不同规模/不同 Story 的可见 Session（小、中、大），但不要全表扫描寻找样本。可从已有安全聚合结果或受限分组统计开始。

对每个 Session：
- 使用普通 EXPLAIN (FORMAT JSON, COSTS TRUE)。
- 比较 Baseline 与 B0/B2（仅在 Connector 角色可使用 HypoPG 时）。
- 记录 Index Cond、Filter、Sort、Plan Rows、Total Cost、扫描类型。
- 参数和 ID 只在工具调用内使用，最终只输出匿名 case key。
- 不能用 HypoPG 时，先比较 Baseline 的结构，记录限制，不要为了实验改权限。

验收：
- 至少 3 个 Session 的计划结构比较，或提供 Connector RLS/权限不允许时的可复现 HOLD 原因。
- 明确报告估算成本不是实际耗时。

### T3 — 恢复引擎查询代码审计

检查：
- Metadata 查询 SQL、分页和 ORDER BY。
- load_session_events 是否每个 Session 重复拉取 Metadata。
- Detail 查询的批量大小、JSONB row_data 体积和 before-image 解析成本。
- 是否可安全缓存 session 级不可变/已验证事件。
- 多个目标 Case 共享 Session 时，能否在一次读取后复用相同 LedgerEventIndex。
- RecoveryStageCursor 计时口径是否正确；execute wall time 包含网络往返。
- SQL 读取范围、commit-order/trigger-continuity 的认证要求。

任何优化必须保持：
- 原始 Ledger event order 语义。
- recorded_at, id 或当前已认证顺序规则，不可凭经验改为 id 单列排序。
- UPDATE_BEFORE / UPDATE_AFTER marker 与 snapshot 语义。
- lineage、target boundary、created_at cutoff。
- HISTORY_SUFFIX_NOT_USER 逐案 HOLD。
- 失败时 fail-closed，不得静默截断 Ledger 事件或历史消息。

验收：
- 先提出小范围设计，不直接改核心算法。
- 明确哪些优化只减少重复读取，哪些会改变读取顺序/一致性语义。
- 给出测试计划和回滚方式。

### T4 — Detail batch 合成实验

只在合成数据或本地 fixture 上比较 500 / 1,000 / 2,000 IDs：
- SQL statement count
- 总 wall time
- 峰值内存
- 单批 JSONB bytes
- 最坏 case payload 大小
- 参数数量及 PostgreSQL 限制

不直接对生产数据库用 2,000 batch 试跑。通过合成测试后，才可设计小范围只读 Pilot，并先评估数据库负载。

### T5 — 生产索引评估（不执行）

比较 B0/B2：
- 预计索引体积及真实 build peak 估算。
- 当前磁盘可用空间、磁盘增长率、WAL、replica lag、写入负载。
- CREATE INDEX CONCURRENTLY 运行窗口、失败残留索引处理、回滚方案。
- 新索引是否能替代/不替代现有索引；不得因 idx_scan=0 自动删除 client index。
- 多 Session 计划结构稳定性。
- 对其他生产查询的回归风险。

交付：一份 DBA/Owner 变更申请草案，写明收益证据、空间成本、风险、监控、回滚。不得执行真实索引 DDL。

### T6 — 小型 Pilot8 v3 方案（未获授权前不执行）

只有 T0-T5 通过后，提出 Pilot8 v3 的执行方案。需要单独确认：
- 是否在相同 Pilot8 样本上重测。
- 资源/statement timeout。
- 预期只读负载。
- 结果一致性对照。
- SAFE receipt 字段。
- HOLD 隔离及 stop conditions。

不得自行启动 Pilot8 v3，除非 Owner 明确批准。

## 5. 绝对禁止事项

- 不启动 GPU，不执行 SFT，不提交 HF GPU Job。
- 不做 Quality-v1 admission，不修改 quality_v1_admitted。
- 不扩样至 72/192。
- 不访问 R50。
- 不改写 Gold192 冻结源或 Owner 私有审核结果。
- 不把 3 个 HISTORY_SUFFIX_NOT_USER HOLD 改成 PASS。
- 不修改 Ledger commit ordering、trigger continuity 或 marker 语义。
- 不启用 Session 并发。
- 不运行生产 EXPLAIN ANALYZE、全表 ANALYZE、无边界 COUNT(*)。
- 不创建、删除或重建真实索引。
- 不修改数据库权限、RLS、Policy、Trigger、Schema、数据。
- 不把 ID、正文、私有记录、DSN、token 放进 GitHub、日志或聊天。

## 6. 输出与交付

每阶段输出：
- 结论（PASS / HOLD / FAIL）
- 实际执行的查询/代码范围（不包含私有参数）
- Connector role 与 RLS 状态
- 只读保护是否通过
- 统计数据与查询计划（脱敏）
- 限制与未验证事项
- 是否需要 Owner 本机介入，以及为什么
- 下一步最小动作

代码/文档变更必须走本分支 PR，执行 scoped Ruff / pytest。先不要修改共享 Ledger 核心，除非有针对性测试证明行为保持一致。

## 7. 当前接手后的第一件事

不要让 Owner 再复制任何已经给过的 EXPLAIN、HypoPG、索引或表统计结果。

先从 GitHub 读取本交接分支和基线分支，核对实现；再用 Supabase Connector 做身份 guard 和统计信息可见性诊断。若 Connector 只能看到自己的 RLS 范围，先报告这一事实，再决定是否需要 Owner 本机最小验证。
