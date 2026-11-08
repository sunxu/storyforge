# R60-REAL P0 文字对话权益来源实查回执（2026-11-08）

状态：`RIGHTS_PUBLIC_POLICY_SOURCE_FOUND__HISTORICAL_ACCEPTANCE_AND_OPT_OUT_HOLD`。**仅 G0；新增 G1 审核范围 0，G2 训练准入 0。** 本回执不是法律意见，也不是对任何具体用户的授权认定。

## 本轮实际核验：新来源

1. 只读核验产品入口：`https://isekai.zone/` 当前重定向到 `https://yime.ai/en`。这一现时跳转**不能单独证明**历史版本、历史运营主体、旧账号与新页面协议的法律连续性。
2. 当前公开隐私页 `https://yime.ai/en/privacy`，页面自标 `Last updated: January 12, 2026`。该页面提到收集聊天历史，并将模型训练列为信息用途之一，同时允许用户选择退出训练；给出的数据权利/退出请求渠道是应用内反馈。**这是文字模型训练权益的实际公开线索，不是逐用户已接受且未退出的证明。**
3. 当前公开服务条款 `https://yime.ai/en/terms`，页面自标 `Last updated: September 24, 2026`。阅读可见服务与 AI 互动相关条款；未从该页面核证到足以覆盖每位作者原作品、第三方素材与历史玩家消息的单独、可追溯微调授权。
4. 页面的 `Last updated` 不是用户实际接受时间，也不证明当时对应 App、地区、渠道和版本真实展示、通知或同意。需核对历史版本原件/生效区间、运营主体与平台迁移关系、逐参与者退出/删除状态，以及作者与所用素材的权利。当前只能标 `AUTHORIZATION_EVIDENCE_FOUND_NOT_YET_VERIFIED`。

## 本轮真实生产 G0 只读检查

连接身份仍是 `supabase_read_only_user`，已知 `BYPASSRLS=true`；**本次没有用 `r58_export_reader`，没有将 RLS 视为该连接器的有效权限边界。**

- 执行 `information_schema.columns` 的扩展目录诊断，额外覆盖 `accept/terms/policy/opt-in/opt-out/train/consent/rights` 相关表列（包括可见的 `auth` schema），只获取**表名、列名、类型**。出现 `auth.oauth_consents`（OAuth 客户端范围授权，不代表训练许可）、`public.voice_consents`（语音），以及与文字 SFT 无直接对应关系的业务 `policy_version` 等列；**未在这次目录结果发现可直接验证普遍文字训练 opt-out/用户协议接受版本的专用记录**。这不能排除 JSONB、外部系统、历史归档或法务记录。
- 执行新增可复现的 G0 聚合 SQL：`experiments/r58_quality/sql/r60_author_player_rights_policy_date_buckets_READ_ONLY.sql`。来源条件 `original/private/published`、未删未归档、作者即会话玩家、`total_turns>=30`；输出聚合计数，不返回任何 ID、用户信息或正文。

| 2026-11-08 查询结果 | 数量 |
|---|---:|
| 符合条件的 Session | **1,040** |
| 不同 Story | **814** |
| Session 创建早于 2026-01-12（UTC） | 0 |
| 2026-01-12（含）至 2026-09-24（不含） | **601** |
| 2026-09-24（含）以后 | **439** |
| 创建日期为空 | 0 |
| 最近消息时间为空 | 3 |

旧交接快照为 1,039 Session/814 Story；**本轮多 1 Session**，反映查询时数据变化或快照差异，未做 ID 级归因。仅按 Session 创建时间分桶，不能代表每条训练消息的生成时间、当时协议生效或用户同意，不能将 601/439 计为有权样本，也不能与 64 Story Pilot 和 16 Story Pilot 的技术候选相加。

## 主线 STOP / HOLD

- `HISTORICAL_POLICY_VERSION_APPLICABILITY_UNVERIFIED`：当前页可见，但缺历史版本原件、时段、法律主体/产品迁移一致性证明。
- `USER_ACCEPTANCE_AND_TRAINING_OPT_OUT_UNVERIFIED`：未核得每位相关作者/参与者的接受版本、年龄/地区（如适用）、退出、撤回、删除或保留状态。
- `AUTHOR_THIRD_PARTY_RIGHTS_UNVERIFIED`：即使作者=玩家，也不自动证明原创作品无外部权利或允许向独立训练流程披露文本。
- `G1_REVIEW_PURPOSE_AND_ACCESS_SCOPE_NOT_APPROVED`：新跨 Story 的 G1 审核者、用途、范围与数据处理通道仍未获核实；此前单对 G1 不扩权。
- `R50_COMPLETE_METADATA_AND_WORLD_SPLIT_UNKNOWN`：不读取 R50 正文；未核得独立完整保护元数据与世界连通组件。

本轮：新 G1 范围 **0**；新 Quality-v1 真实文本审核 **0**；已核实的训练权利案例 **0**；两轨训练准入 **0/0**；未导出私人正文/ID；未修改生产 DB/RolePlay；未读取 R50 正文；未提交 HF Job/GPU。

## 解除阻断的最小一次性核证输入（Owner/合法记录持有方）

仅需一个**受限的权益证据引用包**，不用提交聊天原文或明文 DSN：① 历史相关条款/隐私政策和版本生效区间、旧域名与当前域名的适用关系；② 候选作者和玩家的接受版本、训练 opt-out/撤回/删除状态的受控断言；③ 该作品的作者权属与第三方内容排除依据；④ 经 Owner 明确签核的 G1 **小批**（至多 5–10 条）正文审核用途、审核角色、处理媒介与保存删除规则。真实身份及证据 Locator 仅留 Owner 受限私有区，向 GitHub 只同步脱敏原因码与聚合结果。已有授权的原单对不自动证明新的 author-player 群可审。

只有完成 ①–④ 并逐项证实 `CONTENT_REVIEW_AUTHORIZED`，才启动这些限定对象的六维 Quality-v1；训练仍另等 G2、真实目标前上下文、世界/R50 完整隔离与 CPU 校验。

## SAFE 不变量

`global_g0_metadata_authorized=true`；`new_g1_scopes_verified=0`；`training_rights_cases_verified=0`；`quality_reviewed_new_cases=0`；`strict_gold_train_admitted=0`；`experimental_train_admitted=0`；`production_db_modified=false`；`roleplay_modified=false`；`r50_body_accessed=false`；`gpu_started=false`；`owner_private_packet_received=false`（`packets/safe/r60-real-01.json` **未收到**）。

来源：`https://yime.ai/en/privacy`；`https://yime.ai/en/terms`；`https://isekai.zone/`；GitHub Issue #27。以上为聚合 SAFE 审计记录，不包含客户/作者/故事/会话/消息定位符或内容。

## GitHub 仓库公开性独立复核（安全修正）

GitHub API 在 2026-11-08 查询显示：`sunxu/storyforge` 的 `visibility=public`，`sunxu/storyforge-owner-evidence` 的 `visibility=private`。旧交接文件将主仓库也写为 Private，与当前 API 事实不一致。**本报告所在的主仓库应按公开仓库对待**，禁止存放任何真实身份/正文/ID/DSN/原始私有证据。受控仓库虽然为 Private，仍只能接收符合 SAFE 合同的不可逆聚合投影；精确目标 `packets/safe/r60-real-01.json` 仍**未收到**。
