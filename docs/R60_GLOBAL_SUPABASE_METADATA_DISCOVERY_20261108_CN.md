# R60 全 Story/Session 元数据发现：方案 A 真实执行回执（2026-11-08）

状态：`GLOBAL_METADATA_DISCOVERY_EXECUTED__REAL_HISTORY_QUALITY_AND_RIGHTS_HOLD`。

## 用户新增授权与实际连接

Owner 在本次聊天明确选择“方案 A”，授权 **所有 `story_id` 与 `session_id`** 用于通过既有 Supabase 连接器执行**只读聚合/元数据技术筛选**，不再要求按原先单对 Scope 限定 G0。该授权适用于发现范围，**不自动覆盖所有用户的隐私同意、第三方作品微调许可、原文跨系统导出或正式训练**；原有单对的 G1 私有正文审核授权不随之变成全库正文审核授权。

本次使用的 ChatGPT 连接器数据库角色：`supabase_read_only_user`；实测 `transaction_read_only=on`、`row_security=on`、`rolbypassrls=true`、`rolsuper=false`，无权切换到 `r58_export_reader`。**不能将它的结果伪称为受限角色 RLS 授权证明**。本次没有输出任何 Story/Session/User/Message ID、正文、密钥、原件 SHA、私有路径或个人信息。

## 数据规模（来自 pg_catalog 统计估算，非精确 COUNT）

- `v2_chat_messages`：约 7,000,844 行（约 33 GB）；
- `story_v2_sessions`：约 216,749 行；
- `user_stories`：约 5,282 行；
- `chat_latency_metrics`：约 2,879,427 行。

由于生产量级较大，本次不做无界 JOIN 或全表正文扫描。

## 首批真实跨作品技术筛选

使用 `story_v2_sessions` 已发布未删除、未归档且 `total_turns >= 50` 的会话；每个 Story 选最长的一条会话，各类别用 `md5(story_id)` 作**确定性抽样排序**，每类 16 个不同 Story / 16 Session，每 Session 仅按 `turn_index DESC` 查最近最多 20 个 completed Assistant。此抽样不是统计随机样本，也不是全部历史分布估计。

| 类别 | Story/Session | 完成 Assistant | 精确相邻 completed User | User 相邻且目标 >=300 字 | 技术优先 | 技术优先的 Story |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| original/public | 16/16 | 320 | 320 | 256 | 167 | 15 |
| original/private | 16/16 | 320 | 320 | 293 | 111 | 13 |
| ai_assisted/public | 16/16 | 320 | 320 | 281 | 101 | 12 |
| dice_cocreate/public | 16/16 | 320 | 318 | 293 | 144 | 15 |
| **合计** | **64/64** | **1,280** | **1,278** | **1,123** | **523** | **55（跨分类 Story 数）** |

技术优先条件：相邻 completed User、Assistant >= 300 字、正常 finishReason、无 `originalContent`/`editedAt` 和 `parseWarnings` 键。**无标记不等于未发生后处理**。没有查询或输出实际 User/Assistant 正文、完成请求的 Prompt、用户 ID 或案例级定位符。

此前独立 32 Story / 32 Session 的 `original/public` 限定 Pilot：640 completed、640 对精确相邻 User、533 对目标 >=300 字、365 技术优先、覆盖 30 Story。该 Pilot 与四类的 16-Story 抽样不同，不得累加去重或当做 888 条独立结果。

## 与法律、来源、训练的关系

数据库 `user_stories` 有 `author_id`、`source_type`、`visibility` 等字段，但从三张相关表的列结构检索，未发现可直接证明“所有对话可用于模型微调”的专用 `training_consent`/`license`/`rights` 类列。**原创、公开、属于同一个平台或 Owner 给出数据库查询范围授权都不是完整的微调权利或参与者隐私同意证明**。

当前任何一条真实原文未被审为 Quality-v1 PASS，也未构建/批准真实上下文、独立世界拆分或 R50 完整保护集排除；两轨正式准入仍为 0。

## 后续 P0（主线，不改 RolePlay）

1. 将这套固定抽样 SQL 保存为 `experiments/r58_quality/sql/r60_global_real_history_aggregate_READ_ONLY.sql`，保持**聚合输出**及类别分层；任何扩容都用有界批次，限制查询成本和 User 对话暴露。
2. 用 Owner 可独立核验的来源权益/隐私许可记录先划出允许**私有内容审核**的 Story/Session/用途范围；已授权的原单对 G1 可继续执行。对其他范围保持 `CONTENT_REVIEW_SCOPE_PENDING`。
3. 只对允许 G1 的真实候选定点读取必要 User/Assistant 与目标前上下文，进行六维 Quality-v1 独立评分。不要因为 523 技术优先而批量导出 523 份正文。
4. 另行建立 `DB_FINAL_DELIVERED_ASSISTANT` 目标语义与 `RECONSTRUCTED_NOT_ACTUAL_SENT` 输入标记，不要求所有实验线案例先证明单次原始 Provider 输出，但必须进行内容/上下文一致性、目标质量与来源权利核验。
5. 验证 R50 完整元数据排除、世界/历史 Test 曝光及独立 Train/Validation、CPU Collator 后，由 Owner 单独授权训练费用/GPU。

所有记录：`training_authorized=false`，`strict_gold_admitted=0`，`experimental_admitted=0`，`database_modified=false`，`r50_content_accessed=false`，`gpu_started=false`。

**注意**：本次只证明全库技术发现路径存在真实规模，绝不把 523 升格成可训练样本或法律授权。
