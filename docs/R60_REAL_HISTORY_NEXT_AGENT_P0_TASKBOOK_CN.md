# R60 新 Agent P0 实施任务书：从真实历史候选到合规质量审核

更新：2026-11-08。此文为**立即接手的执行清单**，不是重新提交“准备材料”的任务。主线文档见 `docs/R60_REAL_HISTORY_SFT_MAINLINE_CN.md`，已验证全范围 G0 见 `docs/R60_GLOBAL_SUPABASE_METADATA_DISCOVERY_20261108_CN.md`，新增权益来源审计见 `docs/R60_REAL_HISTORY_RIGHTS_PROVENANCE_AUDIT_20261108_CN.md`。

## 总原则

**只用真实历史 User/Assistant 数据作为训练来源**。不重新跑 GPU smoke，不改 RolePlay，不对旧三案重复寻找已证实缺失的 Provider 轨迹；严禁通过当前模型生成的内容冒充原始真实历史数据。新实验线可以使用明确审核的 `DB_FINAL_PERSISTED_ASSISTANT` 作为目标（旧 `DB_FINAL_DELIVERED_ASSISTANT` 是先前命名，不能仅凭 DB completed 证明用户实际成功接收），配真实历史消息和**明确标注的规范化**输入。严格 Gold192 的 A/B 不变。

用户已授权所有 Story/Session 的 **G0 只读元数据与聚合发现**；这不是所有正文的 G1 审核授权，更不是作品/聊天参与者的 G2 模型训练许可。当前 MCP SQL 角色是 `supabase_read_only_user`，`transaction_read_only=on`、`rolbypassrls=true`；不可谎称以 `r58_export_reader` 运行。GitHub 可以读写两个 Private Repo，但 Private GitHub 不等于存储原文的合法授权。**不向 GitHub 上传真实未审查的私有正文、用户 ID、真实完整 prompt、隐私信息、DSN、私有原件或 R50 内容。**

## 当前冻结事实与不可重复劳动

- 跨作品 G0 聚合 Pilot 已完成：64 Story/64 Session/1,280 completed Assistant/1,278 紧邻 completed User/523 技术优先（4 来源类别，各 16 Story，每 Session 最近 20 回复），**任何条目都尚未经人工/AI 内容审核**。
- 另一次 original/public 32 Story Pilot 为 640 回复、365 技术优先；与 64 Story 可能重叠，不可相加。
- 新 original/private/author==player 独立 Pilot：16 Story/320 completed Assistant/77 技术优先；包含技术优先的 10 Story，与其他 Pilot 可能重叠。
- 全库规模 `pg_catalog` 估计：消息约 700 万、Session 21.7 万、Story 5,282。**统计估值不是 exact count**。
- 同作者同玩家 original/private 中有 **1,039 条 30+ 轮 Session**（814 Story ID），只是更便于核对双侧来源关系的权限核查优先群，不是有权训练。
- 原 Owner Mac G0 获得单对 40 Pair；G1 原三案目标身份/SHA/历史位置 PASS，但原始 Prompt/版本/Attempt HOLD；严格/实验两轨均 0 准入。
- `voice_consents` 不可用于文字模型训练同意；在 public schema 表/列名审计未找到可直接证明普通文字训练同意的专用字段；不代表协议不存在。
- `sunxu/storyforge-owner-evidence` Private 仓库已配置 SAFE 投影校验；截至当前核验 `packets/safe/r60-real-01.json` **不存在**。不要杜撰其已同步。
- `quality_v1.py` 是 Gold195/R58 封闭来源的结构/声明审查，不可将新实验线强行伪装成 `original_gold` 或修改冻结数据来绕门槛。

## P0-A：已授权 G0 聚合发现的结果固化（即刻）

执行路径：`experiments/r58_quality/sql/r60_global_real_history_aggregate_READ_ONLY.sql`（四来源）与 `.../r60_author_player_original_private_aggregate_READ_ONLY.sql`（作者参与原创私有）。

1. **先检查现有 SAFE/SQL 与 GitHub Commit**，不要为了凑更多数字重复运行相同查询。只有需要验证不同时间窗口、数据有变化且 query bounded 时才再跑。
2. 建立候选波次标记 `REAL_HISTORY_AUTHOR_PLAYER_ORIGINAL_PRIVATE_PILOT01`（只是逻辑波次名，不包含真实 Story ID）；保留 query SHA/版本、日期、抽样策略、技术阈值、未准入状态。
3. 下一步必须有**有权做 G1 正文审核的范围**，才可保存逐案真实 Locator；目前全站 G0 授权不足以执行批量 G1。只可先形成字段清单、权益证据判定表和 SAFE。

交付：`R60_REAL_P0_G0_AGGREGATE_SAFE.json`（仅聚合、无 ID 和来源 SHA）、现有 Commit 关联和分析报告。G0 `DISCOVERED` 不等于质量或训练 PASS。

## P0-B：来源权益/参与者隐私取证（最高阻断）

调查顺序：
1. 寻找**可验证的历史版本化**用户协议、隐私政策、平台文本训练条款、作者作品授权与第三方许可、用户撤回/删除机制、实际生效时间；明确其覆盖生成对话、训练用途、数据导出及审核者。仅审核已有合法渠道，不再全文查询未授权内容。
2. 区分来源：`original/private/author==player` → `original/public/author==player` → 其他。后续每项都须证明作品作者与聊天参与者的权限，不得单靠 `user_id=author_id` 或 `visibility=public` PASS。
3. 将查到的证据摘要/来源版本、适用范围和验证人记录在**Owner 私有物料**；不上传原条款中的个人信息。若证据只能由 Owner Mac 提供，明确缺口和应交付的非敏感、不可逆最小证明。
4. 逐候选范围批准 G1 审核与 G2 训练必须分别记录；权限失效、删除/撤回、作品第三方素材或敏感数据未知则 HOLD。

交付：`R60_REAL_RIGHTS_SCOPE_SAFE.json` 聚合（核实来源数/准许 G1 范围数/训练权利已证实数/HOLD 原因码）；明确 `db_modified=false`、`r50_content_accessed=false`。如果缺少凭证，`RIGHTS_EVIDENCE_SOURCE_UNAVAILABLE`，不要反复写同一 HOLD 清单。

## P0-C：真实内容 Quality-v1 小批审核（仅在 G1 范围证实后）

先对**最少阻断、明确允许正文审核的 5–10 个目标**进行试审。筛选仅是候选：`finishReason` 正常 + >=300 字 + 相邻 completed User + 无明显编辑/解析标记，不证明没有 Provider 后处理。

最小读取：仅确切目标及其前置 User、必要且经允许的目标前历史片段。严禁整批导出 523 / 77 条正文；禁止读取 R50 题目。审核六维：
- `chinese_prose>=4`
- `character_consistency>=4`
- `npc_initiative>=3`
- `player_agency>=4`
- `rule_fidelity>=4`
- `narrative_continuity>=4`

严重违规项：`serious_player_agency`、`hard_fact_or_ban`、`safety_exclusion` 任一为真直接拒绝。两名独立审阅者与 Owner 补充安全审核应有独立证据引用；同一个 Agent 两次自评不应宣称独立盲审。评分完成但权益/R50 未核实只能是 `QUALITY_REVIEWED_ADMISSION_HOLD`。

交付：Owner 私有 `R60_REAL_HISTORY_QUALITY_REVIEW_PRIVATE.jsonl`（只在合法私有范围内存）、`R60_REAL_HISTORY_QUALITY_SAFE.json`（分数分布/原因计数，无原文/身份），**不入训**。

## P0-D：真实历史上下文和目标语义

每条候选验证目标前 User/Assistant 轮次、身份、状态、分支和继承依赖，不能把未来消息或目标内容拼回输入。历史 `Story/System/Memory` 版本若未知，明确 `RECONSTRUCTED_NOT_ACTUAL_SENT` 与规范化假设；不能用当前 `user_stories.v2_data` 冒充历史时点快照。目标来源如为 DB 最终文本，标注 `DB_FINAL_PERSISTED_ASSISTANT`、是否可见编辑/续写/过滤迹象和 UI 实际交付的未证实状态。高风险目标 HOLD。

交付：私有 Context Provenance 记录、input/target SHA、源窗口/重建方法、语义校验 SAFE；`context_validated` 不等于 Train Admit。

## P0-E：R50、世界组件与历史曝光

R50 只有经过授权的**完整、带版本与全集完整性证明的保护集元数据**可用于排除；不读取正文，不从保护集选样。故事 ID 不等于独立世界；角色、别名、跨作品复用和共享来源构成的连通组件必须同 Split。任何 Test 曝光范围或元数据完整性未知，`R50_EXCLUSION_UNKNOWN_HOLD`。不得把“未发现重叠”记为 PASS。

## P1 只有当 P0 全部通过

分别冻结新实验线的真实数据 Manifest/Train/Validation 和 Strict Gold192；审计版本 SHA、来源权益、世界划分、R50 排除及完整审核；运行 CPU Tokenizer/Collator；准备 GPU 成本与用户单独许可。过去 R46 已证明技术可训练，不重做新的可行性 smoke。**不得自动启动 GPU**。

## 停止条件与移交给下一 Agent 的实际第一回合

- **首先读取**本文、主线文档、全范围 G0 报告、权益审计和 GitHub Issue #26。
- **接着核对** `sunxu/storyforge-owner-evidence` 是否出现合规的真实 SAFE；如无，则保持缺失事实，不要认为已收到 Owner 私有文本。
- **然后优先做权益来源可获得性核验**；若存在真实可核证的 G1 内容范围，再对最少数真实样本进行 Quality-v1 实测。若无，则制定精确、一次性的来源授权补证要求，并可继续经授权的聚合指标研究。
- 不要再要求在聊天中贴 DSN、生成全套新计划替代执行、修改 RolePlay、重复旧 3 案调查或启动付费 GPU。
- 每一轮给出：实际查了什么、结果计数、精确阻断原因、commit/文件路径、下一项可执行动作；有证据才写 PASS。

### 标准回执

```json
{
  "schema": "storyforge_r60_real_history_agent_handoff_safe_v1",
  "status": "P0_RUNNING_ADMISSION_HOLD",
  "global_metadata_discovery_authorized": true,
  "global_content_review_authorized": false,
  "train_admitted_strict": 0,
  "train_admitted_experimental": 0,
  "production_database_modified": false,
  "roleplay_modified": false,
  "r50_body_accessed": false,
  "gpu_started": false
}
```

回执仅是状态模板；没有新增执行证据时，不能将字段推定为真实审核成果。
