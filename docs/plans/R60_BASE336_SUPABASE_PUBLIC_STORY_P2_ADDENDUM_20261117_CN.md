# R60 Base336：Supabase 公开故事来源 P2 补充决策（2026-11-17）

## 状态

**P2_SOURCE_SET_VERIFIED__WORLD_EVIDENCE_ALL_HOLD__PROMPT_PACKAGE_NOT_GENERATED__WORLD_COMPONENT_CROSSWALK_PENDING**

本文件是对 `R60_BASE336_POST_TRAIN_QUALITY_EVALUATION_20261117_CN.md` 第 6、7 节的来源路线补充，不覆盖原计划的独立性、六维质量、盲审或训练授权门禁。

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
