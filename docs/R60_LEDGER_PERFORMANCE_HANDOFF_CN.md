# R60 Ledger 性能优化交接说明

日期：2026-11-05  
仓库：sunxu/storyforge  
交接分支：r60/ledger-performance-handoff  
基线分支：r60/gold192-ledger-diagnostics  
范围：R59 Gold192 历史上下文恢复的数据库读取性能优化；不包含训练准入或生产数据库变更。

## 1. 一句话结论

Pilot8 历史恢复引擎已能逐案隔离 HOLD：8 条请求中恢复 5 条、HOLD 3 条，整体耗时约 436.7 秒。主要瓶颈是 Ledger Metadata 查询。真实参数第一页 EXPLAIN 与 HypoPG 对照显示，把 story_id 加入复合索引键能显著降低优化器估算成本。当前保留 B0（窄索引）和 B2（全覆盖索引）两个候选；B1 不再优先。尚未创建真实索引，尚未完成跨 Session 验证，也没有训练准入。

## 2. 已验证基线

### 2.1 Pilot8 恢复结果

- Pilot 请求：8
- 恢复：5
- HOLD：3，原因均为 HISTORY_SUFFIX_NOT_USER
- 恢复 Session：4
- 恢复 Story：4
- 历史消息总数：9,599
- 恢复 wall time：436,740.936 ms
- SQL execute wall time：435,964.018 ms
- SQL fetch wall time：303.250 ms
- SQL 查询次数：111
- profiler 实际返回行数：659,707
- Metadata 查询：66 次，328,185.424 ms，641,051 行
- Detail 查询：16 次，83,135.125 ms，6,854 行
- Current history 查询：8 次，21,299.892 ms，11,708 行

cursor.execute 计时是客户端调用 wall time，包含数据库执行与往返等待，不是数据库 CPU 时间。SAFE 中旧的按 Case 归因字段会对同一 Session 多个目标重复归因；应使用新增的 fetched 口径区分实际 SQL 返回行数。

### 2.2 数据库规模及索引

只读检查观察到：

- Ledger 总大小约 102 GB
- Heap 约 17 GB
- 当前索引总大小约 9,683 MB
- Live tuples 约 43,092,617
- Dead tuples 约 1,082,609
- Heap pages：2,072,171
- All-visible pages：2,007,685（96.89%）
- 最近 Auto Analyze：2026-10-12
- 最近 Auto Vacuum：2026-10-07

现有索引：

| 索引 | 定义 | 大小 | idx_scan |
|---|---|---:|---:|
| idx_v2_chat_message_ledger_session | (session_id, recorded_at, id) | 5,719 MB | 57,235 |
| idx_v2_chat_message_ledger_recorded_at | (recorded_at, id) | 1,336 MB | 5,918 |
| idx_v2_chat_message_ledger_user | (user_id, recorded_at DESC) | 1,041 MB | 1,190 |
| primary key | (id) | 954 MB | 853 |
| idx_v2_chat_message_ledger_client | (session_id, client_msg_id) WHERE client_msg_id IS NOT NULL | 632 MB | 0 |

idx_scan=0 不能单独作为删除索引的依据；需要结合统计周期、业务流量、约束及其他查询负载评估。

### 2.3 真实参数第一页 EXPLAIN

使用 Pilot8 已恢复成功的大 Session，目标最大 Turn 为 2602。真实 ID 仅保存在 Owner 本机，不进入本交接文档。

Baseline：
- Node：Limit -> Index Scan
- Index：idx_v2_chat_message_ledger_session
- Index Cond：仅 session_id
- Filter：turn_index 范围 + story_id
- Limit Total Cost：约 330,281.54
- Index Scan Total Cost：约 1,218,638.27

这证明该实际参数下 Story 和 Turn 没有成为 Index Cond。Cost 是优化器成本单位，不是毫秒，也不是实际扫描行数。

## 3. HypoPG 实验结果

HypoPG 1.4.1 已安装。本机连接角色 r58_export_reader，只读事务及 RLS 均开启。最初缺少 USAGE ON SCHEMA extensions；随后 Owner 授予了 USAGE（未授予 CREATE），HypoPG 比较脚本成功。新会话必须重新核对权限状态，不要假设 Connector 角色具有相同权限。

### 3.1 完整覆盖索引比较

| 方案 | Index key | INCLUDE | 估算大小 | Limit Cost | 扫描节点 |
|---|---|---|---:|---:|---|
| Baseline | 现有 Session 索引 | 无 | — | 330,281.54 | Index Scan |
| A | (session_id, recorded_at, id) | story_id, turn_index, message_id, role, operation | 11,955.12 MB | 52,426.37 | Index Only Scan |
| B / B2 | (session_id, story_id, recorded_at, id) | turn_index, message_id, role, operation | 11,955.13 MB | 2,613.51 | Index Only Scan |

Candidate B 的真实计划结构：
- Index Cond：session_id + story_id
- Filter：turn_index 范围
- 无额外 Sort
- Index Only Scan

相对 Baseline，B2 的 Limit Cost 下降约 99.21%。这是优化器估算，不可表述为实际耗时提升 126 倍。

### 3.2 窄索引比较

| 方案 | 定义 | 估算大小 | Limit Cost | 扫描节点 |
|---|---|---:|---:|---|
| B0 | (session_id, story_id, recorded_at, id) | 7,332.48 MB | 18,256.46 | Index Scan |
| B1 | B0 + INCLUDE (turn_index) | 8,395.16 MB | 18,312.80 | Index Scan |
| B2 | B0 + INCLUDE (turn_index, message_id, role, operation) | 11,955.13 MB | 2,613.51 | Index Only Scan |

结论：
- B1 相比 B0 增加约 1,062.68 MB，Limit Cost 反而略高（约 0.31%），仍是 Index Scan；当前证据下淘汰 B1。
- B0 是空间优先候选，约 7.16 GiB；Limit Cost 相比 Baseline 下降约 94.47%。
- B2 是性能优先候选，约 11.68 GiB；Limit Cost 相比 Baseline 下降约 99.21%。
- B0 与 B2 的成本比较只针对一个 Session 和一个第一页查询。不得据此宣称全局性能收益。

### 3.3 统计信息问题

本机 r58_export_reader 查询 pg_stats 时，session_id、story_id、turn_index、recorded_at 均返回 0 行；列 SELECT 权限为 true。尚未确认原因。不要直接运行 ANALYZE；先检查 pg_attribute.attstattarget、pg_statistic 可见性、连接角色权限和统计信息状态，再由 DBA 决定是否维护。

### 3.4 HypoPG 限制

- HypoPG 只改变当前数据库会话的规划器视图，不创建真实索引。
- hypopg_relation_size 是估算值，不是真实磁盘占用或构建峰值。
- 普通 EXPLAIN 不执行查询，不能得到真实 I/O、实际 Heap Fetches 或 wall time。
- 当前 Heap Fetches 未提供；普通 EXPLAIN 不会提供真实执行时的 Heap Fetches。
- 不可把估算成本直接换算为毫秒或真实吞吐量。

## 4. Supabase 访问分工（新会话必须遵守）

### A. ChatGPT Agent 负责：连接器可完成的只读工作

当前已验证的 ChatGPT Supabase Connector 身份：
- database：postgres
- current_user：supabase_read_only_user
- transaction_read_only=on
- row_security=on

Agent 应直接通过已连接的 StoryForge Supabase Read Only Connector 执行只读 SQL，不要要求 Owner 复制粘贴本可由 Connector 执行的查询。

Agent 负责：
1. 每次工作先核验连接身份、只读和 RLS。
2. 查询 schema/table/index 元数据、表统计、列统计、约束、索引定义及大小。
3. 对连接器可见且经过范围控制的参数执行普通 EXPLAIN (FORMAT JSON)，不使用 ANALYZE。
4. 对比插件角色与本机角色的 grants、RLS、可见范围；不能假定两者等价。
5. 检查连接器角色是否可访问 HypoPG Schema/函数；只检查，不授予权限。
6. 输出 SAFE 聚合结果，不输出 Story/Session/Message ID、故事正文、消息正文、目标文本、DSN、token 或私有记录。
7. 每条查询使用合理 statement timeout；避免无边界全表扫描、COUNT 全表和大范围 JSONB before-image 读取。
8. 记录查询范围、角色、RLS 状态、查询时间和结果限制。

Agent 不得：
- 执行任何 DDL/DML，包括 CREATE/DROP/REINDEX/ANALYZE/GRANT/REVOKE、migration、更新或删除。
- 修改 RLS、trigger、role、schema 或数据。
- 假设插件角色有 extensions USAGE 或 HypoPG 函数权限；需先通过 Connector 核验。
- 为了完成 HypoPG 擅自扩张插件权限。
- 把连接器角色查询不到的数据解释为数据不存在；应区分 RLS/权限不可见与真实空结果。

### B. Owner 本机负责：仅本机私有环境不可替代的工作

只有以下情形才需要 Owner 本机执行：
1. 必须使用本机私有 DSN 的 r58_export_reader，且 Connector 的可见性/RLS 与其不等价。
2. 查询参数来自本机私有恢复证据，Connector 无法安全取得或不应取得。
3. 必须访问本机私有文件、HypoPG 私有计划 JSON、恢复 JSONL 或本机环境变量。
4. 需要在本机做文件 SHA256、权限检查、离线脚本测试。

交互原则：
- Agent 先判断自己能否通过 Connector、GitHub 或仓库代码完成。
- 能完成的工作不得转交 Owner。
- 真正需要本机私有环境时，Agent 一次性给出最短命令；只要求回传 SAFE 聚合字段。
- 不要求复制 DSN、ID、正文、私有 JSONL、原始 EXPLAIN 常量或完整数据库日志。
- Owner 不应被要求手动重复执行连接器已能查询的元数据。

### C. DDL/DBA 变更权限边界

真实索引创建、删除、ANALYZE、GRANT 或其他数据库变更均需单独方案和 Owner 明确批准。当前没有任何真实索引 DDL 授权。不能把“r58_export_reader 权限可以按需调整”解释为自动批准索引构建或扩大连接器权限。

## 5. 当前分支及代码入口

- 仓库：sunxu/storyforge
- 性能诊断基线分支：r60/gold192-ledger-diagnostics
- 本交接分支：r60/ledger-performance-handoff
- Gold192 Recovery adapter：experiments/r58_quality/r59_gold192_history_recovery.py
- Shared recovery core：src/storyforge_gold_quality/history_recovery.py
- Shared Ledger implementation：src/storyforge_gold_quality/message_ledger.py
- Pilot8 诊断报告：docs/R60_PILOT8_PERFORMANCE_DIAGNOSIS_CN.md

新会话应先检查分支 HEAD、工作树状态和上述文件当前内容，再开始代码工作。不要假设本机 worktree 与 GitHub 分支同步；不要在 detached HEAD 上提交。

## 6. 安全与训练边界

截至本次交接：
- quality_v1_admitted=0
- training_authorized=false
- gpu_started=false
- database_modified=false（上述性能诊断与 HypoPG 实验未修改业务数据或真实索引）
- ledger_commit_order_verified=false
- ledger_trigger_continuity_verified=false
- historical_system_prompt_verified=false（Pilot8 SAFE 总体报告中的状态）
- 5 条恢复成功不等于 Quality-v1 admission。
- 3 条 HISTORY_SUFFIX_NOT_USER 必须继续逐案 HOLD，不得自动放行。
- 不得因为性能优化结果而改变 Gold192、R50、历史 System Prompt、Summary、Story Version 或 Ledger 证据门槛。
- 不启动 GPU、不训练、不编译正式 SFT 数据，除非后续独立门禁全部通过并获得明确授权。

## 7. 交接完成标准

新会话接手后应能在不要求 Owner 重复提供上述性能结果、不要求 Owner 复制执行普通只读元数据 SQL 的前提下：
1. 复核 GitHub 代码和报告。
2. 用 Supabase Connector 完成连接器角色下可做的只读检查。
3. 完成跨 Session B0/B2 普通 EXPLAIN 结构对照（仅限连接器实际可见的安全数据）。
4. 识别 Connector RLS 不可见时需要的最小本机验证，不把空结果当作数据缺失。
5. 提交新的性能验证报告和后续建议。
6. 在无 DDL 授权的情况下保持真实数据库不变。
