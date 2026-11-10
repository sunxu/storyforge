# R60 新 Agent 启动指令（可直接复制）

接手 `sunxu/storyforge` **R60 真实优质历史数据 SFT 主线**。请直接推进可执行任务，不要再只提交空泛计划。

先以只读方式核对 GitHub `r60/gold192-history-v3-adapter` 分支、PR #25、Issue #26（主线）与 Issue #27（许可阻断），按顺序读取：
1. `docs/R60_NEW_AGENT_MASTER_HANDOFF_20261108_CN.md`
2. `docs/R60_REAL_HISTORY_NEXT_AGENT_P0_TASKBOOK_CN.md`
3. `docs/R60_REAL_HISTORY_RIGHTS_PROVENANCE_AUDIT_20261108_CN.md`
4. `docs/R60_GLOBAL_SUPABASE_METADATA_DISCOVERY_20261108_CN.md`
5. `docs/R60_REAL_HISTORY_SFT_MAINLINE_CN.md`
6. `experiments/r58_quality/sql/r60_author_player_original_private_aggregate_READ_ONLY.sql`

同时确认受控私有协作库 `sunxu/storyforge-owner-evidence` 中是否已经有真实经投影的 `packets/safe/r60-real-01.json`，如不存在须明确写为“未收到”，不能臆造结果。

**目标**：在不改 RolePlay、不重做 GPU 可行性实验、不读取 R50 正文的前提下，从 Supabase **真实历史** User/Assistant 数据推进到可审训练候选。已完成全范围 G0 聚合 64 Story/1,280 completed/523 技术优先；另外已核验 original/private/作者本人参与 1,039 条 30+ 轮 Session（814 Story ID），新 16 Story/320 completed/77 技术优先。抽样可能重叠、技术优先不等于 Quality PASS 或合法训练资格。先调查**文字对话**历史权益/同意的实际证据与生效版本，优先作者本人参与的原创私有作品；`voice_consents` 只涉及语音，不可替代文字训练许可。

**权限**：用户授权所有 `story_id`/`session_id` **G0 元数据与聚合只读发现**，不是全库 G1 正文审查或 G2 训练许可。ChatGPT Supabase 当前 `supabase_read_only_user` 只读但 `BYPASSRLS=true`，不能写“RLS 对它生效”，也不能改 DB；本地 `r58_export_reader` 是另一身份，不能伪称当前已使用。仅当逐项可审内容范围核实后，才可有限定点查看必要的真实文本并按 Quality-v1 六维+严重问题拒绝审核。原单对的 G1 授权不扩大到全站。不得直接将用户私有正文/ID/DSN 上传 GitHub。

**下一回合必须实际完成**：核对已有版权/用户协议/隐私/作者与参与者授权的可用来源；给出新发现或明确的 `RIGHTS_EVIDENCE_SOURCE_UNAVAILABLE`，并维护 GitHub Issue #27；如果合规 G1 范围已有足够证据，则立刻开始有限真实文本审核并记录私有审查结论/SAFE。准备数据分轨与 CPU，但没有全部权益、隐私、R50 完整元数据隔离、世界组件证据不得准入。GPU 未授权不启动。

**禁止**：RolePlay 修改、HF Job/GPU 运行、R50 正文读取、旧三案 Provider 证据重复挖掘、由当前 Story Draft 回填假历史 System/Memory、合成数据替代主线、篡改 Gold192 冻结、越权导出生产对话原文。

交付一个**实际执行回执**：调用/阅读了什么，新增事实和计数，HOLD 原因，GitHub Commit/PR/Issue，Owner 私有输出所在的*泛化说明*（不公开绝对路径），以及下一步最小可执行动作。不要仅重复上述指令。
