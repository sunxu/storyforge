# StoryForge R58 — RolePlay 133 条目标时点输入复原审计 SAFE（2026-10-30）

## 结论

**数据库结构与时间关系已完成真实只读核查；实际应用层 Prompt 组装及完整历史消息字节重放仍 HOLD，未有任何 SFT 正式准入。** 本阶段只读 SQL 不导出故事 ID、会话 ID、消息正文、用户信息、角色卡或逐案 Reviewer 标签。Skill v0.1 不改版。

### A. 135 → 133 的来源复原

- 本次以同一固定种子筛选的 24 个故事 / 45 个已持久化根会话 / 135 个**检查点之后** Assistant 目标位置为基础。
- 原统计 **133/135** 找到早于目标时间的 `story_content_versions.source_updated_at`。另外 2 条不纳入当前来源优先池，维持 HOLD。
- 数据库函数 `archive_story_content_version()` 在 `user_stories` 正文更改之前记录 OLD 版本（保留最近 30 个历史修订），故 `source_updated_at` + `archived_at` 允许重建候选的版本有效区间。
- 在 133 条中：**17 条**由归档版本的起止时间区间支持；**116 条**的现行故事记录 `updated_at` 不晚于目标时间，结构上与“当前版本延续”相容。但**实际生成端可能使用 `public_v2_data` 而非 `v2_data`**，仍须应用代码和当时部署版本验证；两者不能自动认证为真实 System。
- 未证实哪个 API Prompt 模板、卡片投影、导演/记忆组装版本在该条请求时生效。

### B. 检查点和轮次换算

实际 DB 函数 `attach_v2_event_runtime_to_checkpoint()` 使用 `message.turn_index <= checkpoint.turn_index * 2` 说明消息物理序号与检查点逻辑轮次不相等；因此严格要求 **检查点时间早于回复且 `checkpoint.turn_index * 2 < message.turn_index`**。

对 133 条：**133/133** 有先前 `snapshot_version=2` 检查点；`director_state` 键 133、`memory_facts` 键 133、`event_runtime` 键 132、摘要游标键 118。离最近检查点 ≤5 逻辑轮 80、≤20 逻辑轮 128、超过 50 逻辑轮 3，最长间隔 **1957 轮**。某些键存在不保证值非空或与输入一致。

数据库函数 `capture_v2_checkpoint_snapshot_v2()` 显式生成历史游戏状态、角色状态、记忆、导演与摘要，但**不会直接生成完整 System Prompt 或全量模型输入消息列表**；样本完整重放还要补足检查点后的增量、RAG/记忆选择、角色和世界设定投影、全局 Prompt 模板、实际请求历史压缩和版本 pin。

### C. `mutation_revision` 与消息审计账本

实际触发器 `maintain_v2_message_mutation_revision()`：INSERT 赋 0；`role/content/status/metadata/partial_content` 任一变化时 +1；仅 turn compaction 等其他变更不加 1。因此正值**不等同于用户编辑文本**。

133 条中修订正值 129；全部 133 能匹配 `v2_chat_message_ledger` 事件，其中 107 能找到 `update_before` 旧业务快照；对已看到的这些快照，**0 条正文与当前正文不同**。账本写入时刻晚于消息原始创建时刻，且部分生命周期不会存全部旧内容，所以“0 条差异”不等于严格的历史字节级不变性证明。

### D. 源码覆盖边界

检查已连接 GitHub 仓库及代码搜索，未能定位 RolePlay 实际应用仓库（`sunxu/roleplay` / `sunxu/RolePlay` 不可访问），因此**没有读取并核验真实 TypeScript/服务端的 Prompt 组装函数**。通过 PostgreSQL 函数只能核对存储和快照规则，不能声称已确认实际发送给底层模型的全部请求字节。

目标时点输入精确重放 `PASS=0`；该状态是**证据 HOLD**，不是证明 133 条回复质量低劣。

## 可复算证据

- [候选 SQL](R58_ROLEPLAY_POST_CHECKPOINT_PILOT_QUERY_SAFE_20261030.sql)：固定种子、结构分层、检查点后目标选取。
- [本次 133 条结构审计 SQL](R58_ROLEPLAY_TARGET_TIME_REPLAY_AUDIT_QUERY_SAFE_20261030.sql)：仅输出聚合计数，在远端 Supabase 只读执行 PASS。
- 本文件旁 `R58_ROLEPLAY_TARGET_TIME_REPLAY_AUDIT_SAFE_20261030.json` 是机器可读回执。

由于数据库是动态生产库，后续复跑可能取到不同物理消息；真正的冻结阶段需要在私有受控环境保留来源版本和每条目标哈希，不可把本次仅有聚合计数的筛选误认为冻结。

## 下一道真实门禁

优先接入/提供 RolePlay 应用代码和目标时间的已部署 commit（尤其是 V2 Chat System Prompt 拼装、public/draft 卡片选用、导演状态、记忆与历史裁剪、消息完成/修订）。选择首批可证明请求数据的目标完成真正逐字回放：`actual_request_hash` 对 `reconstructed_request_hash`，一旦不一致即 HOLD。此前继续不导出原始会话，不读取 R50，不启动 HF 付费计算，不修改 Skill v0.1。

本报告仅为数据库侧的真实结构验证，**没有完成端到端复原、双 Reviewer 审核或 Dataset v0.4 冻结**。
