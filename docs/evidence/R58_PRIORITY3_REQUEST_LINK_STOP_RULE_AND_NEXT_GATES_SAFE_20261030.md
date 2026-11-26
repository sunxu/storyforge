# StoryForge R58 — 固定三案例请求关联停止条件与下一关（SAFE）

日期：2026-10-30。证据来自 Owner 在其 Mac 私有目录执行的 SAFE 聚合 JSON，**非第三方签名的独立运行结果**。没有在 GitHub 归档真实故事正文、用户/会话/消息/请求 ID、私有哈希、具体时间戳或填充真实 ID 的 SQL。

## 截止本轮，已经达到的证据等级

| 范围 | 可宣告状态 | 不能宣告 |
| --- | --- | --- |
| 冻结 3 条来源、逐案 12 项内容指纹 | PASS_OWNER_REPORTED | 来源未被第三方篡改的独立保证 |
| 3 组条件窗口各 11 消息 | CONDITIONAL_STRUCTURE_PASS | 当时线上 session 游标与历史请求字节已完全复现 |
| 固定 33 条消息，当前来源摘要/修订与冻结包一致 | LEDGER_CURRENT_PARITY_PASS_OWNER_REPORTED | 实际请求时刻文本和数据库历史读取流程全部一致 |
| Ledger 53 次操作分类 | PASS_OWNER_REPORTED | 每个 revision 都是单一流式完成事件 |
| 请求终态事件 ↔ 延迟指标，同 request_id | 9/9 日志层 join | 目标 assistant UUID ↔ request_id 的直接 join |
| 目标请求的软时间线过滤 | AUTHOR=2、CURRENT_PUBLIC=4、OLD_PUBLIC=2 | 唯一 target-to-request 映射 |
| 目标 metadata 已知请求标识键 | 3 × 7 顶层键均不存在 | 所有可能的其他/嵌套/历史日志键必定不存在 |

## 为什么应停止继续靠近邻时间筛选

新增两项软信号后：
- `historyMsgCount=11`：仍有 2/5/2 个候选，**9/9 都符合，区分力为零**。
- 目标 Assistant `update_after` Ledger 时间的 ±2 分钟邻近：变成 2/4/2，**只排除 1 个候选**。
- 两者交集：仍是 2/4/2，三组都不唯一。
- 固定源码 `sunxu/RolePlay@e9fe29c42434caeb0bac5acc91845ab4741ecb2b` 的 streaming 运行路径会先持久化 Assistant 占位行，再在生成完成时以 UPDATE 完成；终态请求事件是异步写入。因而目标消息的 `created_at`、Ledger 更新时间和 `v2_chat_request_events.occurred_at` 代表不同阶段，**没有可直接证明的精确时序同一性**。
- `v2_chat_messages.analytics_event_id` 列存在，但在已检查的请求/消息持久化源码路径中，**未发现已验证的 API `request_id` 写入关系**。单凭 UUID 列名或时间相关性不得建立伪外键。

继续收窄 2 分钟窗口、挑“最接近”的事件或过滤模型/时间戳，只会增强**启发式猜测**，不满足训练样本所要求的精确请求来源证据。严格停止以 soft similarity 升级 PASS。

## 新证据才能解除 REQUEST_LINK_HOLD

至少取得一种**可独立核验**、与历史请求版本相符的证据：

1. **直接因果关联**：有可信的原始日志/持久化事件明确把 target Assistant physical ID 或对应不可歧义的 turn/attempt 与 request_id 绑定；需证明记录生成与目标时间、部署版本一致。候选重复或语义推测不满足。
2. **原始 provider 输入证明**：可信的历史请求快照、请求 ID → 实际发送消息的原始字节或经固定 canonicalization 证明的原始调用内容；须核对 provider、model、参数与版本。后验重建的 canonical JSON hash 不等于原始 HTTP 字节。
3. **当时 runtime 状态证明**：线上已部署 commit、当时 session.summary/last_summary_turn、动态记忆与 RAG、请求 flags（resume / regenerate / continue）、locale、最后用户提示和 post-DB scrub。固定 Git 源码 PIN 不是实际部署证明。

若没有新证据，三个案例应标注：
`R58_FROZEN_SOURCE_AND_CONDITIONAL_HISTORY_PASS__REQUEST_LINK_AND_PROMPT_BYTES_HOLD`。

可保留作私有研究/预检和构建**明确标为估计输入的实验性 replay**，但不得称为原始部署时的字节级请求，更不得不经独立质量/保护世界/训练门禁直接录入 Dataset v0.4 的 Train/Validation/Teacher。

## 后续实际工作优先级

优先切换到**代码层的条件性 Prompt 组装差异清单**（System/世界卡/summary/RAG/客户端 flags/locale/策略清理/模型参数），只输出 SAFE 布尔缺口与聚合，不输出私有文本；每一项划分 VERIFIED、CONDITIONAL、MISSING。若需要字节级 PASS，则单独索取历史部署/请求快照等硬证据。不要继续对这三例重跑生产数据库选样；不修改首次固定源包。

训练准入 Train/Validation/Teacher 均为零。Skill v0.1 不变，PR #7 Draft，R50 保护集不访问，无模型推理或 HF CPU/GPU Job。
