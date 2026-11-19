# R60 Base336：Supabase 公开故事来源 P2 补充决策（2026-11-17）

## 2026-11-19 Gold/原始回答匹配：P2-B 来源设计新增硬约束

Owner 明确要求**训练模型的作答要与原始回答进行同题比较**。此前只依据公开 World/Character/Opening “从零构造 8×6=48 个提示”的设计，无法**自动得到** 48 条与提示严格对齐的历史原始 Assistant 回答。**这不是旧 R48 Gold 可以复用的相同测试集**，也不能把公开 Opening 认作某个新 Prompt 的回答。

新 Agent 必须先验证新 8 来源所允许的公开资料能否提供真实 `prompt prefix → original assistant reply` 来源/版权/时间/版本绑定；`scripts/v02_r48_four_arm_build.py::read_gold` 已定义严格的 `original.messages[:-1] == frozen_prompt.messages` 合同。**任何私有用户对话仍禁止访问**；当前授权只允许公开素材构造内部评估提示，不意味着可以查询私有回复或让模型生成所谓“原始回答”。

若无 48 份同题原始回复，新增 `P2_NEW48_MATCHED_ORIGINAL_GOLD=UNVERIFIED_HOLD`；正式“五种匿名回答来源”评估不能宣称已可执行。Owner 应在保持独立世界/权利边界下决定：扩大合法公开来源的已完成问答筛选，或另行生成由作者/人工提供的**新参考回答（需明确非历史原始 Gold）**；这两种方案必须单独记录授权和真值性质，不允许悄悄替换。旧 R47/R48 20 Prompt 的 Gold 只做单独 EXPOSED_DEV 回归，不计入 P2 新来源的 Held-out 结论。

**新增 Gold 只是 Reviewer 盲评时的匿名对照回答，不写入 P2 prompt JSONL 的模型生成字段**：原来的 `user/assistant/user` 输入、无 System、无 reference-label 泄漏等校验规则不放宽。所有生成答案与 Gold 对应同一个 Prompt SHA，只有审阅器拿到匿名回答；评分结果需报告 R60 Base336 vs Gold 以及 Base、v0.2 与 v0.3-A 对照。详细操作规则见 [现行交接任务书第八节](../R60_BASE336_P2_QUALITY_EVAL_NEXT_AGENT_HANDOFF_20261119_CN.md)。

P2-A READY、P2-C HOLD、真实 48 提示 NOT_GENERATED、GPU/HF 未授权、train/quality admission=0、模型未晋升均不变。

---


## 2026-11-19 最新 P2 决策与接手入口（覆盖旧第一动作）

**现行 Agent 任务书：** [R60 P2 Quality-v1 接手](../R60_BASE336_P2_QUALITY_EVAL_NEXT_AGENT_HANDOFF_20261119_CN.md)。本文件 P2-A 8 条来源的内部评估用途权利边界、8×六维共 48 提示及 `user/assistant/user` 三消息格式保持有效；但先前“Owner 尚未返回 inventory”“R55 三层未核验”“R47/R48/R55 无 Story ID 映射”“需重新申请只读 DB”已过期，**不得照做**。

真实进展：P2-A 8 来源 READY；P2 × Base336 172 Story 精确 overlap=0；R50 原始 50 provenance 50=46+4 PASS、冻结五个受保护 Story 身份与原始 50 来源集合严格一致，P2 overlap=0；R47/R48/R55 旧 20 Prompt / 2 Story 精确 overlap=0、R55 三层回链已通过。**这不是 P2-C 的完整语义/历史曝光 PASS**：全 172 current+archived 语义证据仍缺（Owner read-only source SQL HOLD），其余 Protected/Reserved、历史额外 Dev/训练/教师曝露全集、actual-sent、独立 Reviewer 与 Owner Freeze 仍 HOLD。真实 48 prompt JSONL/Manifest 未生成。

新 Agent 不重跑 P2-A、R50 50/46/4 或五世界、旧 20-case/R55 索引、R58 空白 CSV、旧 35 案例图；只推进新 8 来源的独立性、未覆盖的来源全集并在 P2-C 真正通过后完成 48 提示与 Base/Adapter 质量评估。只读 DB 访问已获范围许可，无需反复申请；GPU/HF 推理需单独批准。

---


## 状态

**P2_SOURCE_SET_VERIFIED__WORLD_EVIDENCE_ALL_HOLD__PROMPT_PACKAGE_NOT_GENERATED__WORLD_COMPONENT_CROSSWALK_PENDING**

本文件是对 `R60_BASE336_POST_TRAIN_QUALITY_EVALUATION_20261117_CN.md` 第 6、7 节的来源路线补充，不覆盖原计划的独立性、六维质量、盲审或训练授权门禁。证据文件定位、脚本复用边界和当前缺口统一见 [P2 Protected Crosswalk Evidence Index](R60_BASE336_P2_PROTECTED_CROSSWALK_EVIDENCE_INDEX_20261118_CN.md)。

Owner 已明确批准：本轮以 Supabase 作为主要新来源，采用“仅公开故事与公开世界设定，构造全新评估提示，不读取用户私有会话正文”的路线。

授权范围仅为**内部独立评估提示构造**。不据此推断作者授予训练、公开发布或再分发权利；不把这些内容加入训练集。

## 1. Base336 时间边界

- Base336 探索性数据发布/冻结时间：2026-11-16 02:03:25 UTC。
- Base336 GPU Run 开始时间：2026-11-17 05:56:22 UTC。
- 入选来源均在 Base336 数据发布/冻结时间之后创建，因此记录级来源不属于该次 293/43 冻结数据包。
- 其中 3 条在 GPU Run 开始前创建，5 条在 GPU Run 开始后创建。

时间边界可证明这些故事记录晚于 Base336 数据包；**不能单独证明它们与 Base336 既有世界组件在语义上完全隔离**。

## 2. Supabase 来源筛选

只读取公开故事来源字段及审核/权限元数据；不查询私有会话消息表。候选筛选条件：

- `visibility = public`
- `status = published`
- `deleted_at IS NULL`
- `moderation_state IN (ai_approved, human_approved)`
- `source_type = original`
- `public_v2_data.cardType = story`
- `public_v2_data.opening.originality = original`
- `public_v2_data.opening.visibility = 公开`
- `created_at >= 2026-11-16T02:03:25Z`（晚于 Base336 数据集冻结/发布边界）
- `length(public_v2_data.world.worldSentence) > 5`，排除世界描述信息不足的记录
- 对冻结边界前的公开原创故事执行 `public_v2_data.world` 精确 JSON 去重

筛选结果：

| 项目 | 数量 |
|---|---:|
| 入选公开故事 | 8 |
| 故事谱系 | 8 |
| 作者 | 5 |
| 入选故事的不同 World JSON | 8 |
| Base336 GPU Run 开始前创建 | 3 |
| Base336 GPU Run 开始后创建 | 5 |
| 公开来源审核快照完整性通过 | 8/8 |
| 最新权限事件绑定最新审核提交 | 8/8 |

另有 2 条公开原创候选因可用世界描述过少（`worldSentence` 长度分别为 5 和 2）未进入本轮提示构造。它们不被判为质量失败，只是不满足本轮来源信息最低要求。

精确 JSON 去重未发现与 Base336 数据集冻结边界前公开原创故事的重复 World JSON。该结论只代表精确 JSON 不重复，不代表与 Base336 私有来源、R50 Protected/Reserved World 或其他历史开发材料语义隔离。

## 3. 来源版本与权限核验

8 条入选来源均通过以下只读核验：

1. `public_content_revision` 与最新审核提交的 `content_revision` 一致。
2. 最新审核快照中的 `snapshot.source.v2Data` 与当前公开 `public_v2_data` 完全一致。
3. 审核快照内的 `contentHash` 与审核提交的 SHA256 一致。
4. 最新权限事件绑定到最新审核提交，目标可见性为 public。

SHA256 的作用域是包含 `source.v2Data` 的审核快照；不把它描述成只对 `public_v2_data` 计算的 SHA256。数据库中的 32 位 `public_content_hash` 仅作为不透明字段保留，不推断其算法或覆盖范围。

公开发布状态与 AI/审核批准记录用于确认本轮来源版本和公开状态；它们不被解释为作者授予通用模型训练权利。当前用户授权只覆盖本轮内部评估提示构造。

## 4. 新构造提示集：计划，尚未生成

拟构造 48 条全新评估提示：

- 8 个来源，每个来源 6 条。
- 每个来源分别覆盖冻结 Quality-v1 六个维度各 1 条：
  - `chinese_prose`
  - `character_consistency`
  - `npc_initiative`
  - `player_agency`
  - `rule_fidelity`
  - `narrative_continuity`
- 每条提示采用全新构造的三消息上下文（`user / assistant / user`），不伪装成历史持久化消息。
- 不含 System 消息、目标答案或参考答案。
- 上下文只可基于已获准的公开世界/角色/开场信息；不得把隐藏 director/system-like 指令作为模型输入。

**截至本补充文件修订时，48 条提示尚未生成、未冻结、未进行独立复核，也没有提示包 SHA256。** 先前版本将“拟构造”误写为“已生成”，本段予以更正。

在生成之前，必须先明确本轮公开故事内容可用于内部评估提示构造的权利范围，并完成来源版本/世界组件审计。公开可见、AI 审核通过或内容标记为原创，本身不等于作者授权用于模型训练、评估、再分发或公开发布。若无法确认内部评估用途的授权依据，该来源必须排除或保持 HOLD。

六维门槛继续复用 `experiments/r58_quality/quality_v1.py` 中既有规则：4/4/3/4/4/4；严重标记仍为 `serious_player_agency`、`hard_fact_or_ban`、`safety_exclusion`。

拟生成文件是**独立评估提示包**，不是 Quality-v1 SFT 候选 JSONL。不得把 Base/Adapter 生成回复送入 `quality_v1.py` 的源候选 `decide/summarize`，不得向 Gold Manifest 追加合成评估事件。

## 5. 未访问与未执行事项

- 未读取用户私有会话正文；未从 `v2_chat_messages` 提取私有消息内容。
- 未读取或访问 R50 密封测试内容。
- 未将 293/43 内容复制进新提示。
- 未修改 Supabase。
- 未启动 GPU、未提交 HF Job、未运行 Base/Adapter 推理。
- 未实现正式 Pairer、Backend 或 Profile。
- 48 条提示 JSONL/Manifest 尚未生成；仓库中只有结构校验器与合成测试，不能把测试夹具或历史计划描述当作真实提示包。
- `quality_v1_admitted = 0`，`train_admitted = 0`，`model_promoted = false`。

## 6. P2 剩余门禁

当前仍不得冻结为独立 Held-out。正式 P2 PASS 前还需：

1. 将 8 个新来源的 World 组件与 Base336 293/43 私有来源清单、已知 Protected/Reserved World 元数据做交叉核验；仅有不同 MD5、不同故事 ID 或晚于时间边界均不足以证明语义隔离。
2. Owner 提供或在 Owner Mac 本地执行受限交叉核验：使用 Base336 私有 source roster / 已审核的 World component evidence，以及 R50 仅元数据排除清单；不得读取 R50 正文。当前会话无法访问 Owner Mac 私有文件，因此此项保持 HOLD。
3. 对 48 条提示执行逐条来源忠实性、无原文长段复用、无未来信息泄漏、无隐藏指令混入的复核；检查 NPC/角色新增细节是否属于明确标注的合成情境，而不是伪称来源事实。
4. 完成 R47/R48/R55 已暴露开发题的来源/语义排除核验。
5. 确认权利范围仅覆盖 Owner 已批准的内部评估提示构造；不得扩大为训练、公开发布或再分发。
6. Owner 冻结最终来源 Manifest、提示 SHA256、World 组件隔离证据及独立 Reviewer 结论。

若无法取得完整的世界组件交叉核验证据，对应来源保持 HOLD；不得通过改名、重算 MD5 或仅凭时间戳宣布语义隔离 PASS。

P2 通过后，才按原计划进入 P3 的版本化薄适配器与合成测试。P4 Base/Adapter GPU 配对推理仍需单独、明确的 Owner 授权。


## 7. 最新回传：Base336 八组世界来源证据（2026-11-18）

Owner 本轮提供 `R60_BASE336_EIGHT_WORLD_SOURCE_EVIDENCE_PRIVATE.json`，结构为 `storyforge_r60_base336_world_evidence_private_v1`。仅记录安全聚合，不把私有 Story ID、世界正文、roster/template SHA 或引文复制进仓库。

回执结论：

- `all_decisions=HOLD`；8/8 组均保持 HOLD。
- 7/8 组 `current_world_cross_split=true`；另 1 组当前版本未跨 split，但仍然 HOLD（当前+归档版本的分组关联不能据此豁免）。
- `semantic_review_completed=false`。
- `actual_sent_prompt_verified=false`。
- `train_admitted=0`。

这份文件每组仅绑定一个代表性当前 `v2_data.world` 对象；不是 38 个成员的完整角色卡/Opening 证据，也不是历史实际发送版本证明。它不能单独支持 `GENERIC_TEMPLATE`、`SPECIFIC_SHARED_WORLD` 或语义组件分配，更不能把任何组提升为 PASS。

此前的独立 Codex 汇总曾报告 7 组 `GENERIC_TEMPLATE`、1 组 `INSUFFICIENT_EVIDENCE`，但该汇总本身仍为 8 组隔离 HOLD，且不能替代本轮逐成员 source-bound 复核。必须与原始 roster、决策模板、8 组成员 `character/characters/opening` 私有证据及独立审阅记录逐项绑定后，才能形成可复核的语义组件分配。

**下一步先诊断既有 `r60_base336_group_cards_opening_cpu.py --execute` 的 `BASE336_CARD_OPENING_EVIDENCE_HOLD`**：此前 Owner SAFE 只有泛化 HOLD，未给出 failure phase/reason；权威最小门禁文档已明确暂停再次执行全量 `--execute`。当前只允许在 Owner Mac 对已有私有目录做只读文件清单/权限检查，并回传已有 SAFE 的完整聚合字段；不要重跑 DB 查询、不要删除或覆盖已有 roster/template/evidence/output。待失败阶段明确、Owner重新确认范围后再决定是否修复工具或继续提取。仍不重建 roster、不访问 R50 正文、不启动模型/GPU；缺少成员级证据时全部 HOLD。

## 8. 2026-11-18 Supabase 来源 Inventory 只读复核

已对当前 Supabase 做一次限定范围的只读复核，使用与 P2 Draft 相同的确定性选择合同；没有读取私有会话正文，没有修改数据库。

结果：

- 选定来源：8 个公开原创故事。
- 作者：5。
- 精确 World JSON：8。
- Base336 GPU Run 前创建：3；之后：5。
- 8/8 最新 moderation submission revision 与当前 public revision 一致。
- 8/8 moderation snapshot 的 source.v2Data 与当前 public_v2_data 一致。
- 8/8 最新 permission event 绑定最新 submission，且目标 visibility 为 public。
- 与 Base336 冻结边界前公开原创故事的精确 World JSON 重复：0。

以上只证明 P2 Source Inventory evidence。它不证明与 Base336 私有 World component、R50 Protected/Reserved World 或 R47/R48/R55 暴露材料的语义隔离，也不证明作者授予通用训练权。

Owner 本轮授权继续限定为内部独立评估提示构造；48 条提示仍未生成/冻结。下一门禁是使用 Owner 私有 source roster、R50 仅元数据、R47/R48/R55 暴露排除及语义 World component crosswalk 完成保护集交叉核验。任何一项缺失继续 HOLD。

## 8. P2 草案包结构校验工具

新增本地只读校验器：

- `experiments/r58_quality/r60_base336_p2_public_prompt_package_gate.py`
- `tests/test_r60_base336_p2_public_prompt_package_gate.py`

校验范围包括：48 条与 JSONL SHA256、8 个来源绑定、公开 revision 与审核快照 SHA、权限事件仍绑定最新公开提交、来源创建时间晚于 Base336 冻结边界、3/5 时间分组、六维均衡、三消息角色顺序、无 System/答案字段，以及所有未完成门禁必须继续保持 HOLD。

本地合成测试 **9/9 PASS**，`compileall` PASS（代码测试结果，不代表真实提示包已生成）。当前没有可供该校验器验证的真实 48 条提示 JSONL/Manifest，因此不得报告真实包结构/哈希 PASS。该工具明确拒绝把 Base336 语义隔离、R50 排除、R47/R48/R55 暴露排除或 Owner 冻结标为 PASS。没有触发或声称 GitHub Actions CI PASS。

## 9. 2026-11-18：P2 Owner RLS 根因已定位；最小权限策略待Owner应用

Owner Mac 实际回执显示 8/8 候选的审核提交与权限事件关联字段均为 NULL，导致旧诊断将下游字段全部报告为无效。进一步只读核对当前数据库的表结构、RLS策略和聚合关联后，根因已明确：

### 9.1 数据库证据

- `public.user_stories.id` 是 `text`。
- `public.story_moderation_submissions.story_id` 是 `uuid`，`id` 是 `uuid`。
- `public.story_permission_events.story_id` 是 `text`，`submission_id` 是 `uuid`。
- 三张表均启用 RLS。
- `r58_export_reader` 对三张表均已有 SELECT 权限。
- 但 `pg_policies` 中只有 `user_stories` 有适用于 `r58_export_reader` 的 SELECT policy；`story_moderation_submissions` 和 `story_permission_events` 的适用策略数均为 0。RLS 对无适用 permissive policy 的表默认不返回行。
- 使用当前 Supabase 管理连接（`supabase_read_only_user`，该连接的 `BYPASSRLS=true`，**不是Owner reader**）按相同8条候选做只读聚合：8/8 均存在当前revision且requested_visibility=public的审核提交；8/8 均存在绑定当前提交的权限事件；revision、snapshot V2、permission binding、目标public、kind/result各项均为8/8。当前revision提交共8行，绑定权限事件共9行。

因此，这次 Owner SAFE 的10项失败并非10种数据缺陷，而是两个 metadata LEFT JOIN 被 RLS 全部过滤后的级联 NULL。不能据此说故事没有审核记录，也不应更改JOIN业务条件或放宽校验标准。

### 9.2 最小权限修复

新增人工审阅SQL：

`experiments/r58_quality/sql/r60_base336_p2_public_source_reader_rls_policies_REVIEW_ONLY.sql`

该文件只创建两条面向 `r58_export_reader` 的 SELECT policy：
1. moderation submissions：只允许候选窗口内公开、已发布、未删除、审核批准、原创、符合P2公开V2筛选条件的故事之**当前public revision**提交记录。
2. permission events：只允许绑定上述当前revision公开提交的权限事件。

不授予额外GRANT，不修改角色属性，不读取私有会话，不开放历史非当前revision提交。事件策略通过submission策略限定，避免仅凭story_id读取无关事件。SQL文件是REVIEW_ONLY；没有在本轮连接器中执行，也没有修改Supabase。

### 9.3 代码防回归

P2脚本现新增只读RLS preflight，执行来源SQL前确认两张表RLS启用、SELECT已授权且两条指定policy存在。缺失时返回 `SOURCE_METADATA_RLS_POLICY_HOLD` 与聚合缺失表名，不再让8条NULL字段扩散成10种SOURCE_BINDING失败。

同时：
- JOIN统一为明确的 `sm.story_id::text = selected.story_id`，与实际字段类型一致。
- LEFT JOIN缺失时只报告 `moderation_submission_metadata_not_visible` / `permission_event_metadata_not_visible`，不重复报告下游NULL派生错误。
- 真实revision、snapshot、permission绑定和visibility门禁不放宽。

### 9.4 Owner执行顺序

**先由Owner在Supabase SQL Editor审阅并执行上述REVIEW_ONLY SQL**。执行前确认当前数据库、角色及两条策略范围；若策略已存在或SQL报错，不要DROP/覆盖，先回传错误。

随后在Owner Mac更新分支。先只跑无DB预检；确认输出目录无已创建manifest后，才运行一次 `--execute`。新代码会先执行RLS preflight；如果仍缺策略，会明确报出缺失策略表名并停止，不执行来源查询。

只回传SAFE JSON。不要上传私有manifest、原始故事、ID、DSN或快照。即使8/8来源绑定通过，也仅代表P2公开来源Inventory通过；Base336/R50/R47/R48/R55保护集交叉核验、语义World隔离、独立Reviewer和Owner freeze仍HOLD，训练/GPU/HF/模型请求保持0。

## 2026-11-18 Owner SAFE 更新：P2-A 公开来源 Inventory READY；P2-C 仍 HOLD

Owner 本轮真实 SAFE（由 Owner 提供）：

```json
{
  "authors": 5,
  "created_after_gpu_run": 5,
  "created_before_gpu_run": 3,
  "database_accessed": true,
  "database_modified": false,
  "distinct_world_json": 8,
  "exact_world_overlap_pre_cutoff_public_original": 0,
  "gpu_started": false,
  "hf_jobs_submitted": 0,
  "model_promoted": false,
  "model_requests": 0,
  "private_file_created": true,
  "private_values_emitted": false,
  "protected_crosswalk_verified": false,
  "quality_v1_admitted": 0,
  "revision_snapshot_permission_verified": true,
  "rights_scope_owner_confirmed_only": true,
  "schema": "storyforge_r60_base336_p2_public_source_inventory_safe_v1",
  "selected_stories": 8,
  "status": "P2_PUBLIC_SOURCE_INVENTORY_READY__PROTECTED_CROSSWALK_PENDING",
  "train_admitted": 0
}
```

### 证据解释

- P2-A Supabase 公开来源 inventory：READY，8 条来源已选定，revision / snapshot / permission 绑定已验证。
- 本次精确 World JSON 比较在指定的 GPU 前公开原创范围内为 0 overlap；这不是语义世界隔离证明，也不覆盖 Base336 私有来源、R50 Protected/Reserved、R47/R48/R55 暴露材料。
- 8 个不同 World JSON 不等于 8 个语义独立世界。
- 5 条创建于 GPU Run 后只代表数据库记录创建时间；不能单独证明其底层素材、版本或语义未提前暴露。
- 权利状态为 `rights_scope_owner_confirmed_only=true`，只代表 Owner 已确认的内部独立评估提示构造用途；不扩展为训练、再分发或公开用途授权。
- `private_file_created=true` 表示 Owner 私有来源 Manifest 已创建；私有 Manifest、source IDs、作者映射、正文和 SHA 不得上传 GitHub 或贴入聊天。

### P2-C 尚未完成的保护集交叉核验

必须将上述 8 个 P2 来源与以下保护范围进行精确及语义交叉核验：

1. Base336 冻结 Train/Validation 私有 source roster 和已审查的 World component evidence。
2. R50 完整 Protected/Reserved World **仅元数据**清单；不读取 R50 正文、提示、答案或密封材料。
3. R47/R48/R55 已暴露开发题及其语义变体的来源/暴露元数据。
4. 现有其他独立评测集及未解决保护集合；不得将部分保护清单称为完整覆盖。

当前可复用 Base336 Owner-local 证据目录为 `~/.local/share/storyforge/r60/private/r60-base336-world-cross-review-20261115/`，包含既有 8 组 cross-split roster、decision template、Codex review 和代表性 World source evidence；这些历史回执仍不能证明本轮 P2 8 个新来源已与保护集完成 crosswalk。成员级 card/opening 证据此前未确认存在。R50 旧有 pre-seal 证据曾显示完整排除与最终封存仍 HOLD；R47/R48/R55 全量语义变体排除材料也未形成可验证的完整 crosswalk。

### 当前禁止推断

- 不因 8/8 revision / snapshot / permission PASS 推断 P2-C PASS。
- 不因 exact overlap=0 推断语义隔离 PASS。
- 不因 Owner 确认评估用途推断训练授权。
- 不生成正式 48 条 Held-out prompt 包，不启动 Base/Adapter Pairing 或模型推理。
- 不改写 Quality-v1 六维门槛，不新增评分标准，不向 Gold Manifest 追加生成评估事件。

继续保持：`model_promoted=false`、`train_admitted=0`、`quality_v1_admitted=0`、GPU/HF/model requests = 0。

### 下一项最小动作

在 Owner Mac 只做私有文件**元数据 inventory**，确认以下材料的实际存在性、路径、文件大小、权限和修改时间：本轮 P2 private source manifest；Base336 cross-review roster/template/evidence；R50 完整 Protected/Reserved metadata-only roster 与现有 SAFE；R47/R48/R55 exposure/source manifests 与 SAFE。不得 cat、grep 正文、上传文件或打印任何 ID/正文/哈希。根据真实 schema 再设计一个版本化、create-only、Owner-local 的保护集 crosswalk 适配器；在输入 schema 和保护集覆盖范围被确认前，不编造通用代码或宣称 crosswalk 完成。


## 2026-11-18 交接执行冻结与专项提示词

P2-A Owner SAFE 已 READY；P2-C 仍 HOLD；真实 P2-B 48 条提示包 NOT_GENERATED。详细保护集范围、可复用脚本及证明边界见 `R60_BASE336_P2_PROTECTED_CROSSWALK_EVIDENCE_INDEX_20261118_CN.md`。

**当前未收到 Owner Mac 私有文件 metadata inventory 输出。** 新 Agent 不得推断私有文件存在或 Schema 已知。第一动作只核对文件名、大小、权限和修改时间，不读取文件正文，不输出 Story ID、作者映射、私有 SHA 或本机绝对路径。

此前 `r60_base336_group_cards_opening_cpu.py --execute` 返回泛化 `BASE336_CARD_OPENING_EVIDENCE_HOLD`，未提供 failure phase / reason。暂停再次执行全量 `--execute`；不重跑数据库查询、不重建或覆盖 roster/template/evidence/output。先核对已有 SAFE 和文件元数据，再诊断失败阶段；需要任何进一步提取或修复时，须由 Owner 对具体最小动作重新确认。

当前 Agent 的可复制执行提示词：`docs/R60_BASE336_P2_CROSSWALK_NEXT_AGENT_PROMPT_20261118_CN.md`。本轮任务书与总体交接入口：`docs/R60_BASE336_POST_TRAIN_NEXT_AGENT_HANDOFF_20261117_CN.md`。不因本次文档整理改变任何数据库、训练、推理或准入状态。
