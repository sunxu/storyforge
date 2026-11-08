# R60-REAL-04：真实历史数据权益/隐私来源取证与候选分层（2026-11-08）

状态：`G0_METADATA_DISCOVERY_COMPLETE__RIGHTS_AND_CONTENT_REVIEW_HOLD`。本次已执行真实生产库的**只读、聚合/系统目录查询**；无正文、账号 ID、会话 ID、密钥或个案 SHA 输出；未修改 Supabase。技术数据质量与合法训练许可完全不同。

## 1. 连接器边界

- ChatGPT Supabase MCP：`supabase_read_only_user`，事务只读 ON、RLS ON，但 `BYPASSRLS=true`。新 Agent 不得把 `row_security=on` 误写成 RLS 实际约束此连接。
- Owner Mac Reader：`r58_export_reader`，与上述连接身份不同。**没有 DSN，也不需要在聊天中索取 DSN**；现有连接器足以做经授权的 G0 聚合调查。
- Owner 最新授权：所有 Story/Session 的 **G0 只读元数据/聚合发现**。它不自动赋予所有用户/作品的 G1 原文审核或 G2 训练使用权；旧单对原 G1 有限私有审核仅限已批准的那个 Story/Session。

## 2. 来源/授权结构实测

生产 `user_stories` 有 `author_id`、`source_type`、`public_source_type`、`source`、`visibility` 等来源/发布字段；`story_v2_sessions.user_id` 可用于核对玩家是否与作品作者一致。通过 `information_schema.columns` 和 `pg_catalog` 检索所有 public schema 中名字含 `consent/license/licence/copyright/train/opt-in/opt-out/rights/privacy/agreement` 的字段/表，发现 `voice_consents` 和 `character_voices.consent_record_id`，属于**语音授权**，不能作为文字互动小说微调/用户对话使用权凭证。未找到可直接证明**全量文字对话训练同意**的通用字段。

这一结论**不等于平台从未取得相关许可**：授权可能在历史用户条款、版本化协议、其他服务、合约或人工记录中，需独立核证，不得把“未在 DB 表名/列名找到”写成“未授权”。

其他必要核证：作品版权/第三方素材、作者授权用途、参与者消息训练使用范围、可删除/撤回、敏感个人信息、地区/年龄条款（如适用）、来源和协议生效版本、数据导出与保留期限；不以“公开”“原创”“同平台”代替明确依据。

## 3. 全范围作者参与会话的聚合发现

基于已发布未删除 Story、未删除未归档 Session、`s.user_id=st.author_id` 比较，且每类仅输出**计数**：

| 来源 | 可见性 | 作者本人参与的 Session（全部长度） | 作者本人参与且 >=30 轮的 Session | >=30 轮覆盖 Story ID | 非作者玩家 >=30 轮 Session |
|---|---|---:|---:|---:|---:|
| original | private | 3,252 | **1,039** | **814** | 676 |
| original | public | 1,900 | 319 | 247 | 18,393 |
| original | unlisted | 215 | 69 | 50 | 443 |
| ai_assisted | private | 672 | 262 | 146 | 7 |
| dice_cocreate | private | 770 | 387 | 124 | 9 |

*不同类别之间无需累加；同一 Story ID 可能关联多 Session；Story ID 数不是世界组件数。真实“作者=参与者”只有身份相等事实，不证明账号被合法授权参与训练，也不证明用户当时拥有所有所用内容版权。*

**P0 合理优先顺序**：先核证 original/private/author-player 的授权记录，其次 original/public/author-player；其他玩家与跨作者对话应当要求更明确的双侧权利及隐私依据。任何来源分层只是权益调查的成本优先级，不自动排除其他合法来源。

## 4. 作者参与原创私有作品的第二个真实技术 Pilot

先通过 `DISTINCT ON (story_id)` 选择每个作品作者自己参与的最长 Session，按 `md5(story_id)` 稳定排序，选 16 Story/16 Session，每 Session 最近最多 20 completed Assistant。必须 `original/private/published`、作者等于会话玩家、会话轮次 >=30，且删除/归档已排除。聚合查询不返回任何标识或正文。

| 实测项目 | 数量 |
|---|---:|
| 抽样 Story/Session | 16 / 16 |
| 已完成 Assistant | 320 |
| 精确相邻 completed User | 320 |
| 回复 >=300 字 | 280 |
| 技术优先（正常结束、无显式编辑/解析警告） | **77** |
| 技术优先覆盖 Story ID | 10 |

复现 SQL：`experiments/r58_quality/sql/r60_author_player_original_private_aggregate_READ_ONLY.sql`。**本抽样与前一轮 64-Story/1,280-回复/523 技术优先的样本可能重叠；不得混加为去重样本量。** 未做 Quality-v1 文学评价、内容取样、授权证明或训练准入。

## 5. 最小可审核权益记录与 G1 准入前检查

新 Agent 首先应查询/阅读 **已有版本化平台条款与 Owner 权利记录**（允许是本机受限合法材料，不得向 GitHub 直接复制）；将每个候选世界/来源分组标记为：
- `AUTHORIZATION_EVIDENCE_FOUND_NOT_YET_VERIFIED`：有明确协议/授权线索但缺核验；
- `CONTENT_REVIEW_AUTHORIZED`：明确授权该数据源、该目的、审核角色和必要文本范围；
- `TRAINING_RIGHTS_VERIFIED`：具体来源和参与者层面的可审计许可、版本、生效期、撤回/隐私依据都满足要求；
- `HOLD`：其他状态，无推断 PASS。

每条私有证据引用必须能绑定作品作者/会话参与者、适用文本范围与历史版本（例如保留本机私有 source locator 和证据哈希）；不得把权益结论放在不含身份的公共 SAFE 中假装完成了逐案验证。

只有 `CONTENT_REVIEW_AUTHORIZED` 才允许在相应边界内开展 G1 限量正文质量审核；`TRAINING_RIGHTS_VERIFIED` 且 Quality/Context/World/R50 等全部通过后才可能训练准入。训练与评估目录不得复制旧 Gold192/R50 原件。

## 6. 下阶段应交付的新 SAFE

- `r60_real_rights_source_inventory_safe_v1`：`schema`、`authorized_g0_scope=ALL_STORY_SESSION_METADATA`、`content_review_scope_count`、`training_rights_verified_count`、各类 HOLD 原因聚合、`raw_text_exported=false`、`gpu_started=false`、`db_modified=false`。
- 只读能力与证据线索诊断；**若拿不到版本化平台条款或作者/参与者许可原件，需写 `RIGHTS_EVIDENCE_SOURCE_UNAVAILABLE`，不要继续无意义地重复查询 DB 字段**。
- 新 Agent 不应该擅自要求修改 RolePlay、扩大原文导出、使用 GitHub Private Repository 存放未核实版权与隐私的原始消息。

**正式训练准入 0 / 0。**
