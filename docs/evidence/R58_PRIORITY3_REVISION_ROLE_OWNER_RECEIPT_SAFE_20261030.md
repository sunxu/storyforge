# R58 Priority3 — 修订角色离线验收回执（SAFE）

日期：2026-10-30。证据仅来自 Owner 本地脚本的非敏感 JSON 输出，未接触原始私有来源包。

## 已验证（Owner 回执）

- `AUTHOR`：窗口 11、Assistant 5 条且 revision-positive 5 条，User 6 条且 revision-positive 0 条，目标消息创建时间之后 Ledger 事件 0。
- `CURRENT_PUBLIC`：同上，事件前后 JSONB 连续性已在前一轮证据中验证。
- `OLD_PUBLIC`：同上，事件前后 JSONB 连续性已在前一轮证据中验证。
- 合计 33 条历史窗口消息，15/15 条 Assistant revision-positive，18/18 条 User revision-positive=0。
- 输出状态：`R58_MUTATION_REVISION_ROLE_AUDIT_PASS__HISTORICAL_TEXT_PARITY_HOLD`。数据文件内部 SHA256 与权限的先前回执均 PASS。

## 解释限制

根据只读检查的数据库触发器函数，`mutation_revision` 因 role/content/status/metadata/partial_content 的变化递增，因此上述 15 个正修订不证明文本发生了 15 次编辑，也不能证明一定只是 streaming 完成。Ledger 业务触发器不会登记 status/partial_content-only 修改。

时间界限采用 assistant 目标消息的 `target_created_at`，**不是已证实的 API 请求发起时刻**。既有“post-target Ledger = 0”证明范围有限，不能替代请求时刻的 `as-of` 历史内容和 Prompt 字节级一致性校验。

## 下一阶段门禁

- 仅对已经冻结的 3 条 cohort 的 33 条消息，按固定 message ID 核验 Ledger 操作分布、修改时间及当前文本指纹；只在 Owner 私有终端完成标识匹配，GitHub/ChatGPT 只接收计数和 HOLD/PASS。
- 不重选样、不覆盖 `source.private.jsonl` 或 `manifest.private.json`。如有缺失、不一致或记录时间边界不明，保持 HOLD。
- 即使 Ledger 计数全部符合，也保留：线上部署 SHA、请求特征、异步摘要与记忆/RAG、post-DB 历史 scrub、模型/语言注入、最终请求原始字节等未验证项。

这是阶段性证据，不是训练数据准入。Train/Validation/Teacher=0，Skill v0.1 不变，PR #7 Draft。
