# R60 Base336 P2 Protected Crosswalk 证据索引（2026-11-18）

## 状态与用途

**P2-A：READY。P2-C：HOLD。P2-B：NOT_GENERATED。**

本索引用于区分当前真实 SAFE、Owner-local 私有证据、仓库中可复用的脚本/共享算法，以及尚未形成的保护集交叉核验。它是证据定位与执行顺序索引，不是 P2-C 通过证明，不包含私有正文、逐案标识、Owner 私有路径或 SHA256。

本次只读核验基线：分支 `r60/common2-cpu2-owner`，HEAD `0476e3210889f41db993f9e8ab9b8e86e2f651ce`。该 SHA 是本次索引审查时的 GitHub 代码基线，不是任何 Owner-local 私有输入的 SHA。

## 0. 必须区分的两组“8”

| 集合 | 范围 | 当前结论 |
|---|---|---|
| P2 新公开来源 | Supabase 公开原创故事 8 条、5 位作者、8 个不同 World JSON | P2-A Inventory READY；保护集 crosswalk 未验证 |
| Base336 历史跨 split World 组 | 冻结 336 cases / 172 stories 中的 8 组精确 World JSON 值关联 | 7/8 组当前值跨 Train/Validation；8/8 组语义裁决 HOLD |

这两组“8”不是同一批对象。Base336 的 8 组 roster 不能被当作 P2 的 8 条来源清单；P2 的 8 条来源也不能直接填入 Base336 Train/Validation 组件 roster。

## 1. P2-A：Supabase 公开来源 Inventory

- 执行入口：`experiments/r58_quality/r60_base336_p2_public_source_inventory_cpu.py`。
- Owner 提供的 SAFE Schema：`storyforge_r60_base336_p2_public_source_inventory_safe_v1`。
- 最新状态：`P2_PUBLIC_SOURCE_INVENTORY_READY__PROTECTED_CROSSWALK_PENDING`。
- 已验证：8 条来源；5 位作者；8 个不同 World JSON；3 条记录创建于 GPU Run 前、5 条创建于 GPU Run 后；revision / moderation snapshot / permission event 绑定通过；指定范围内 GPU 前公开原创 World JSON 精确重叠为 0。
- 私有 Source Manifest 已由 Owner 创建，但其内容、路径、ID、作者映射和 SHA 必须留在 Owner Mac。
- 该 SAFE 不证明 Base336 私有来源隔离、R50 排除、R47/R48/R55 暴露排除、语义 World 隔离或历史 actual-sent 独立性。
- 权利范围仅为 Owner 确认的内部独立评估提示构造，不扩展为训练、公开发布或再分发授权。

## 2. Base336 历史 World 交叉审查证据

### 2.1 私有 roster

- 代码：`experiments/r58_quality/r60_base336_world_cross_split_private_roster_cpu.py`。
- 私有 Schema：`storyforge_r60_base336_world_cross_split_review_private_v1`；SAFE Schema：`storyforge_r60_base336_world_cross_split_review_safe_v1`。
- 它绑定冻结 336 cases / 172 stories，识别 8 组 current + archived World JSON 精确值关联。
- 既有 roster 合同的聚合范围：38 个受影响故事、28 个 Train stories、10 个 Validation stories、82 个受影响 cases（65 Train / 17 Validation）；8 组中 7 组当前 World 值跨 split。
- 该工具以精确 JSONB 相等构造待审查组，代码明确标注 `NOT_SEMANTIC_IDENTITY`。它只建立审查 roster，不裁决语义，也不证明与 P2 新来源隔离。

### 2.2 决策模板

- 代码：`experiments/r58_quality/r60_base336_world_review_decisions_template_cpu.py`。
- 私有 Schema：`storyforge_r60_base336_world_group_decisions_template_private_v1`。
- 模板为 8 组建立待审查决策槽，默认全部 `HOLD`，需要逐组来源引文、来源字段、版本证据及通用模板 / 共享世界分析。
- 模板创建本身不读取 World 正文、不访问数据库、不证明语义隔离；不允许将空白模板或默认 HOLD 改写成 PASS。

### 2.3 代表性 World source evidence

- 代码：`experiments/r58_quality/r60_base336_world_group_source_evidence_cpu.py`。
- 私有 Schema：`storyforge_r60_base336_world_evidence_private_v1`；SAFE Schema：`storyforge_r60_base336_world_evidence_safe_v1`。
- 既有证据为每组一个代表性 current 或 archived World 对象，共 8 个对象；SAFE 合同标记 source-bound，但 `semantic_review_completed=false`、`actual_sent_prompt_verified=false`。
- **不能把每组一个代表性 World 对象说成 38 个成员的完整证据。** 它不覆盖全部成员 current / archived revision 的角色卡与 Opening，也不证明历史实际发送版本。

### 2.4 成员级 character / characters / opening 证据

- 代码：`experiments/r58_quality/r60_base336_group_cards_opening_cpu.py`。
- 私有 Schema：`storyforge_r60_base336_card_opening_evidence_private_v1`；SAFE Schema：`storyforge_r60_base336_card_opening_evidence_safe_v1`。
- 工具设计范围：8 组、38 个受影响故事；对 roster 列出的成员和匹配的当前 / 归档版本读取 `character`、`characters`、`opening`，每组产生一个 Owner-private 文件。
- 该脚本要求先重放核对 roster 成员集合，且输出目录 create-only；不产生语义裁决，不验证历史 actual-sent。
- 已知此前一次执行只返回泛化 `BASE336_CARD_OPENING_EVIDENCE_HOLD`，没有 failure phase / reason。当前不能假定 8 个输出文件存在，也不能覆盖可能已生成的文件。
- **禁止再次运行全量 `--execute`**，直至 Owner 只读 inventory 确认已有输出、权限和 SAFE，并明确此前失败阶段；不得重建 roster/template/evidence 或覆盖输出目录。

## 3. 可复用的结构检查与其证明边界

| 组件 | 可证明内容 | 不能证明的内容 |
|---|---|---|
| `r60_base336_world_linkage_screen_cpu.py` | Base336 336 cases / 172 stories 的精确 target/history SHA、session/message ID 结构关联 | 语义别名完整性、语义 World 隔离、R50 完整排除 |
| `r60_base336_world_metadata_coverage_cpu.py` | 冻结来源元数据字段覆盖情况 | 原始故事/角色卡认证、语义别名完整性、R50 排除 |
| `r60_base336_world_cross_split_impact_cpu.py` | 当前及归档 World JSON 精确值跨 split 影响统计 | 精确相等之外的语义同源判断 |
| `src/storyforge_dataset/world_isolation.py` | 对 Reviewer 已声明的 semantic component assignment 做完整覆盖和 Train/Validation 冲突检查 | 不阅读或推断语义；不证明 Reviewer 独立、actual-sent、R50/R47/R48/R55 完整排除或训练授权 |

共享函数 `validate_component_review_assignments()` 的输入合同包含 source key、Train/Validation split、semantic component ID、来源证据引用、source snapshot SHA256、版本核验、语义复核完成标记和 PASS/HOLD/REJECT 决策。它只验证提交的分配结构与声明的跨 split 冲突；缺失或无效分配不会被自动推断。

**复用原则：** 不在新实验脚本中复制 split-conflict 算法；也不能把该 Train/Validation helper 误当作 P2-source 对 Base336 / R50 / R47-R48-R55 多保护集合的完整 crosswalk。后者需要基于 Owner 实际私有输入 Schema 的版本化薄适配器。

## 4. R50 Protected / Reserved：仅元数据

- 元数据文件结构检查入口：`scripts/r60_r50_frozen_metadata_inventory.py`。
- SAFE Schema：`storyforge_r60_r50_metadata_inventory_safe_v1`。
- 该脚本显式接收 cases、provenance、exclusion 三个文件，只检查文件类型、权限、稳定读取、JSON / JSONL 结构和行数；即使文件可解析，返回的也是 `R50_METADATA_FILES_PARSEABLE__COVERAGE_HOLD`，并固定 `r50_complete_exclusion_verified=false`。
- 该检查**不是**完整 Protected / Reserved 覆盖证明，也不是 P2 来源 crosswalk。
- 既有 `scripts/r60_r50_preseal_crosswalk_cpu.py` 仅对 46 条 pre-seal 记录做结构核对，成功状态仍为 `R50_PRESEAL_46_CROSSWALK_PASS__FINAL_COVERAGE_HOLD`；不能把 46/46 说成最终 50 条完整保护集排除。
- 本轮没有收到 Owner 的完整 R50 metadata-only roster 与对应 SAFE。状态：**UNKNOWN / HOLD**。
- 任何步骤均不得读取 R50 正文、提示、答案或密封材料。

## 5. R47 / R48 / R55 历史暴露材料

仓库存在历史流程代码，例如：

- R47：`scripts/v02_r47_eval_validate.py`、`scripts/v02_r47_review_freeze.py`。
- R48：`scripts/v02_r48_review_freeze.py` 及对应四臂离线流程。
- R55：`scripts/v03_r55_gold5_final_evidence_resolution.py` 及其审核/证据解析流程。

这些脚本分别验证或冻结特定历史任务的提示、审核、四臂结果或 Gold5 证据；**代码存在不等于本轮已取得完整暴露清单，也不等于 8 条 P2 来源已完成精确及语义变体排除。**

`scripts/r57_g3_private_exposure_ledger.py` 是 R57 G3 特定训练 / 验证精确目标暴露账本，不得替代 R47/R48/R55 的完整暴露证据。其他历史批次的局部 SAFE、旧 reviewer 回执或代码测试同样不能自动证明全量覆盖。

Owner 于 2026-11-18 已返回 R47/R48/R55 的本机 metadata / shape inventory。该输出确认 R47 Report、Audit、20-row Manifest、20-row compiled Test、20-row prompts、R48 Source Audit，以及 R55 若干私有 Coordinator Index / SAFE 文件存在；但 R47 Manifest 不直接含 Story ID；仓库代码 audit_v01_integrity.py / v02_r48_four_arm_build.py 提供了通过 source_line、prompt hash、完整消息前缀到 canonical Test metadata.story_id 的复合绑定路径，尚待 Owner-local SAFE 实际执行。R55 第一层 Index 代码保存 source_sample_id_private，第二 / 第三层有 token 回连链；本轮只核验文件元数据，未读取 Index / SAFE 内容或确认旧 R47 source preflight 绑定。故完整 source / exposure manifests 与同批次 SAFE 仍未完成内容及覆盖验证。状态仍为：**UNKNOWN / HOLD**。详见 [R47/R48/R55 Source Shape Audit](../evidence/R60_P2_R47_R48_R55_SOURCE_SHAPE_AUDIT_20261118_CN.md)。

## 6. P2-B 提示包

- 结构校验器：`experiments/r58_quality/r60_base336_p2_public_prompt_package_gate.py`。
- 合成测试：`tests/test_r60_base336_p2_public_prompt_package_gate.py`。
- 最新权威状态：真实 48 条 JSONL / Manifest **NOT_GENERATED**；没有真实提示包 SHA256。
- 9/9 合成测试只证明校验器合同，不证明真实包存在、来源独立或提示质量通过。
- 旧启动提示词中的 Draft 文件名与 SHA 记录已更正为过期信息，不得复用或引用为有效工件。
- 按当前补充决策，P2-C 保护集 crosswalk 完成前不生成正式 Held-out 提示包，不执行模型请求。

## 7. 当前门禁矩阵

| 子门禁 | 状态 | 依据 / 缺口 |
|---|---|---|
| P2-A 公开来源 revision / snapshot / permission | READY | Owner 2026-11-18 SAFE，8/8 |
| P2-A 指定范围精确 World JSON 去重 | PASS（仅精确检查） | overlap=0；不代表语义隔离 |
| Base336 历史 8 组 roster | 已有私有证据，语义 HOLD | 8 组、38 个受影响故事、82 cases |
| Base336 成员级 card/opening | HOLD / 文件状态待 inventory | 既有全量执行返回泛化 HOLD；不得盲目重跑 |
| Base336 semantic component review | HOLD | 语义决策与来源引文未完成 |
| 历史 actual-sent 版本绑定 | UNKNOWN / HOLD | 代表性 World 证据明确未验证 |
| R50 完整 Protected / Reserved 元数据排除 | UNKNOWN / HOLD | 仅有局部 pre-seal / metadata 工具合同 |
| R47/R48/R55 暴露及语义变体排除 | CODE PATH FOUND / OWNER SAFE PENDING / HOLD | R47 Sample → canonical Test metadata.story_id 代码链已找到；R55 第一层 source_sample_id 与第二 / 第三层 token 链代码已找到；实际 Index / receipt / 旧 R47 preflight 覆盖尚未核验 |
| Reviewer 独立性 / Owner freeze | HOLD | 尚无完整独立审阅和冻结回执 |
| P2-B 真实 48 条提示包 | NOT_GENERATED | 只有校验器与合成测试 |
| P2-C 总门禁 | **HOLD** | 保护集交叉覆盖不完整 |

## 8. 下一步最小执行顺序

1. Owner Mac 的 metadata inventory 已收到，但只完成文件形态确认：R47/R48 的 20-case Prompt / Sample 文件与 Audit 存在；R55 三个私有 Coordinator Index 及两个 SAFE 文件存在。下一步不再重复目录盘点：按审计文档执行 R47 Manifest / prompts / canonical Test / P2 Manifest 的 Owner-local exact crosswalk SAFE；并核验 R55 私有 Index 的 Schema / token 链 / 20-case 覆盖 / receipt 哈希及旧 R47 source preflight。R47 Sample → metadata.story_id 的代码绑定路径已找到，实际文件值仍须 SAFE 复核；Base336 / R50 的其他缺件仍按本索引各节处理。**文件存在不等于内容、Schema、完整性或保护集覆盖通过。**
2. 对此前 `BASE336_CARD_OPENING_EVIDENCE_HOLD`，只核对已存在的 SAFE 聚合字段和输出文件状态。没有明确失败阶段前，不重跑数据库查询，不执行全量 `--execute`。
3. 根据实际存在的文件和真实 Schema，确认各输入是否完整、是否来自同一冻结版本、是否覆盖全部保护范围。缺项继续 HOLD。
4. 输入合同确认后，才实现版本化、Owner-local、create-only 的 P2 Protected Crosswalk 薄适配器；将精确身份匹配、语义组件复核、R50 metadata-only 排除、R47/R48/R55 暴露排除和覆盖完整性分别记录，不能用一个精确 hash PASS 替代所有门禁。
5. 适配器先做合成测试和 SAFE 隐私测试；真实私有值、source IDs、作者映射、原文、逐案引文、SHA 和本机路径始终留在 Owner Mac。
6. P2-C 全部通过并由独立 Reviewer / Owner 冻结后，再依据最新授权推进正式提示包构造。P2 PASS 不自动授权 GPU / HF 推理。

## 9. 永久安全边界

全程保持：

- `database_modified=false`。
- `gpu_started=false`、`hf_jobs_submitted=0`、`model_requests=0`。
- `train_admitted=0`、`quality_v1_admitted=0`、`model_promoted=false`。
- 不访问 R50 正文；不修改冻结 293/43、历史 checkpoint、Gold Manifest 或既有私有审计文件。
- 私有 crosswalk、逐案语义结论、原文引文、身份映射和私有 SHA 不进入 GitHub、CI 日志或聊天。

**当前唯一业务阻塞不是 Supabase 查询，而是 P2 8 条新来源与 Base336 / R50 / R47-R48-R55 完整保护集之间，尚无可复核的 source-bound 交叉核验证据。**


## 10. 下一 Agent 的权威入口

当前专项提示词：`docs/R60_BASE336_P2_CROSSWALK_NEXT_AGENT_PROMPT_20261118_CN.md`。Owner 已返回 R47/R48/R55 部分 metadata inventory；新 Agent 必须先完成实时 GitHub 核验，再按第 11 节对 R55 私有 Index 做结构 / 覆盖 SAFE 检查，并寻找 Sample → Story ID 权威绑定。Base336 / R50 等其他保护集缺件仍按各自章节处理；不得重复盘点已确认文件或绕过真实 Schema 直接设计适配器、执行数据库提取。


## 11. 2026-11-18 Owner R47 / R48 / R55 metadata / shape audit 增量

Owner 已返回本机审计输出，详见 [R60_P2_R47_R48_R55_SOURCE_SHAPE_AUDIT_20261118_CN.md](../evidence/R60_P2_R47_R48_R55_SOURCE_SHAPE_AUDIT_20261118_CN.md)。

关键更新：

- **R47**：20 条 Manifest 元素仅含 sample_id、prompt_sha256、source_line；20 条 compiled Test 记录有 id/messages/metadata；20 条 Prompt 记录只有 messages。现有校验器保证 Sample / Prompt / 回复包内部一致，但未建立经验证的 sample_id ↔ compiled_test.id ↔ story_id 绑定。
- **R48**：20-case / 80-response 四臂包复用同一 R47 历史 Prompt；固定 canonical Test SHA 和 Gold target hashes 证明文件 / 目标摘要绑定，不提供可见 Story ID crosswalk。R48 不增加独立案例数。
- **R55**：三个 0600 私有 Coordinator Index、一个旧 R47 source preflight SAFE 和一个 R54/R55 intake SAFE 的文件元数据已确认；本轮未读取其内容，因此不能确认当前 Schema、版本一致性、完整 20-case 覆盖或 Story ID 映射。
- **精确隔离**：此前 P2 × Base336 的 336 cases / 172 Story IDs overlap=0，以及 P2 × R50 的 exact Source ID disjoint PASS 保持各自范围；这些结果不能外推到 R47/R48/R55。
- **门禁**：P2 × R47/R48/R55 exact Story ID crosswalk = UNKNOWN / HOLD；semantic variants = HOLD；P2-C 总门禁继续 HOLD。

下一步：Owner-local 只读核验 R55 Index 的真实 Schema / 覆盖，并查找 Sample → Story ID 的权威来源绑定；没有真实绑定就继续 HOLD，不得按行序或字段名推断。


### R47/R48/R55 crosswalk code-path refinement（2026-11-18）

仓库代码复核发现：R47 Manifest 的 Sample ID 可以通过 source_line、prompt_sha256 和完整 role/content prefix 与 canonical compiled Test 行绑定，再读取该行 metadata.story_id；不要使用通用 id 字段冒充 Story ID。R55 第一层 arbitration index 保存 source_sample_id_private，第二 / 第三层分别保存 original candidate token 链，可以回连第一层。

这使 Owner-local exact crosswalk 具备明确实现路径，但**代码存在不是实际 SAFE PASS**。实际 P2 × R47/R48/R55 overlap、R55 三层 Index 的 receipt/version 绑定、20-case 覆盖和旧 R47 source preflight 证明仍需在 Owner Mac 只输出聚合结果后确认。详见 docs/evidence/R60_P2_R47_R48_R55_SOURCE_SHAPE_AUDIT_20261118_CN.md。


### 2026-11-18 R55 Prep SAFE 文件存在性补充

Owner 本机 metadata inventory 确认三个准备回执存在且均为 0600：Arbitration Prep 1,292 bytes；Second Audit Prep 1,598 bytes；Third Audit Prep 1,498 bytes。此次未读取文件正文，故实际 schema/status、对应 Coordinator Index 文件 SHA256、token 链和 20-case 覆盖依然 UNKNOWN / HOLD。详见专项审计报告第 8 节。本轮不修改 P2-C 门禁。


### Owner R55 三层索引实际 SAFE（2026-11-18）

已收到 `r60_r55_three_index_link_safe_v1`：`R55_THREE_INDEX_LINK_AND_RECEIPT_PASS__P2_C_HOLD`。

- Arbitration / Second / Third：76 / 68 / 46 条，三组真实 Schema、Candidate Token 唯一性及 Prep Index SHA 绑定均通过。
- 第一层 20/20 R47 Manifest source samples 覆盖；extra=0，missing=0，case indices valid。
- 第二层 68/68 回连第一层；第三层到第二层 / 第一层的链接和三层一致性均通过。
- 不重做三层索引校验。下一步执行 R47 Sample → canonical Test `metadata.story_id` 的 Owner-local 联合 SAFE，并与 P2 的 8 个 Story ID 交叉。
- `P2_R47_R48_R55_EXACT_STORY_ID` 仍 UNKNOWN/HOLD；旧 R47 preflight 的其他限定、完整历史暴露范围、语义和 actual-sent 尚未通过；P2-C 继续 HOLD。


### 2026-11-18 Owner-local P2 × R47/R48/R55 exact Story ID SAFE 结果

Owner 返回 `r60_p2_r47_r48_r55_exact_story_crosswalk_safe_v1`，R47 canonical Test SHA、Prompt / Manifest 绑定、Sample → `metadata.story_id` 复合绑定和 R48 canonical source SHA 绑定均通过。R47 20 prompts 对应 **2 个唯一 Story IDs**；P2 8 个唯一 Story IDs 与该 20-case 历史集合精确 overlap=0。

结合已通过的 R55 三层 Index SHA / token 链及第一层 20/20 R47 Sample 覆盖，可将 R55 这批 76/68/46 派生记录传递映射至同一 R47 20-case / 2-Story 集合；在这一**已验证的有限链范围**内，P2 × R47/R48/R55 exact Story ID overlap=0。R55 派生记录数不是独立故事数。

统计解释必须保守：20 prompts 只有 2 个 Story IDs；R48 不增加独立故事，R55 记录数也不增加独立故事数。未来质量评估需按 Story 聚类，不能把 20 prompts 作为 20 个独立故事来声称泛化。

**仅关闭 R47/R48/R55 已验证 20-case 链的精确身份门禁，不等于完整历史 exposure universe 已穷尽。** 旧 R47 source preflight 附加约束、语义 World/alias 变体、actual-sent 版本、Base336 成员级语义证据、R50 metadata-only 完整性和 Reviewer 独立性仍 HOLD。P2-C 继续 HOLD，P2-B 仍 NOT_GENERATED。


### 2026-11-18 Owner Card/Opening 精确本地文件定位 SAFE

Owner 执行只读 `r60_base336_card_opening_local_locator_safe_v1`，状态 `CARD_OPENING_FILES_INCOMPLETE_OR_MISSING`：

- 四份既有证据：`R60_BASE336_WORLD_CROSS_SPLIT_REVIEW_PRIVATE.json`（15,003 B）、`R60_BASE336_WORLD_GROUP_DECISIONS_TEMPLATE_PRIVATE.json`（4,374 B）、`R60_BASE336_WORLD_GROUP_DECISIONS_CODEX_PRIVATE.json`（43,218 B）、`R60_BASE336_EIGHT_WORLD_SOURCE_EVIDENCE_PRIVATE.json`（9,256 B）全部 PRESENT、mode 0600。
- 目标目录 `r60-base336-group-cards-opening-20261115`：**MISSING**；预期组 01–08 的 `R60_BASE336_WORLD_GROUP_XX_CARD_OPENING_PRIVATE.json`：**0/8 PRESENT**。
- Owner-private R60 树文件名检索：`alternate_match_count=0`。未找到候补 Card/Opening 输出。
- 核验只读取文件系统元数据；`file_contents_read=false`、`database_accessed=false`、`gpu_started=false`、`private_values_emitted=false`。

**证据裁决：** 现存四份 World/决策材料不可替代 38 个成员的 current/archived `character/characters/opening`。Card/Opening 数据产物明确缺失，语义组件裁决仍 HOLD。脚本 `r60_base336_group_cards_opening_cpu.py` 的 `except Exception` 抹平了失败阶段；现有终端 SAFE 和缺失输出目录不能反推出根因。下一最小动作是**无数据库**的 roster/template + 运行环境只读预检，随后在合成环境为脚本加入固定、去敏的 failure_phase/reason_code 和测试。未确定失败阶段与最小授权前，继续禁止重新执行全量 `--execute`。


### 2026-11-18 无 DB 预检 PASS 与诊断修复提交

Owner 返回 `r60_base336_card_opening_no_db_preflight_v1`：`ROSTER_PRECHECK_PASS__NO_DB`。

- `roster_template_bound=true`，`group_count=8`，`unique_member_count=38`，`member_scope_38=true`。
- `output_dir_absent=true`，`output_parent_exists=true`；`psycopg_installed=true`，`readonly_dsn_configured=true`。
- `database_accessed=false`，`database_modified=false`，`gpu_started=false`，`private_values_emitted=false`。
- 仅证实当前本地解释器有数据库驱动及 DSN 环境变量；不证实已成功连接数据库，也不能追溯此前失败原因。8 个真实 Card/Opening 输出仍 MISSING，P2-C 继续 HOLD。

对仓库脚本 `experiments/r58_quality/r60_base336_group_cards_opening_cpu.py` 的改动：
- 保持旧 CLI、create-only、read-only DB 和私有输出协议不变。
- 新增有限枚举 `failure_phase` / `reason_code`，覆盖冻结输入、输出保护、DB connect、DB guard、World/fields、package 和写入；未识别异常统一 `UNEXPECTED_HOLD`，不输出私有异常字符串或堆栈。
- 失败时 `database_accessed=null`，避免用未知代替 false。
- synthetic-only 测试覆盖已知拒绝原因、不可信异常脱敏、非 DB 阶段定位和 CLI SAFE 格式。
- 新脚本**尚未对 Owner 的真实数据库运行**；原先的 `BASE336_CARD_OPENING_EVIDENCE_HOLD` 仍不可追溯到具体历史阶段。保持对全量 `--execute` 的禁止，直到执行环境、代码版本及最小重试范围被明确授权。


### 2026-11-18 Owner PostgreSQL 只读连接守卫 SAFE

Owner 返回 `r60_base336_db_readonly_preflight_safe_v1`，状态为 `DB_READONLY_PREFLIGHT_PASS__NO_STORY_DATA`。

- `dsn_configured=true`、`connection_established=true`；
- `expected_role_verified=true`（守卫中的预期角色 `r58_export_reader`）；
- `transaction_read_only=true`、`row_security_enabled=true`；
- `role_bypassrls=false`、`role_superuser=false`；
- `story_tables_queried=false`、`private_story_content_read=false`、`database_modified=false`、`gpu_started=false`、`hf_jobs_submitted=0`、`model_requests=0`、`private_values_emitted=false`。

本次仅对数据库连接、事务状态及角色元数据做验证，未访问应用故事表；因而可以排除**本次运行环境**的连接失败和只读守卫不符合要求，但不能推导旧提取失败原因，也不能证明冻结 World 组与当前数据库一致。下一门禁是经 Owner 明确授权的只读 World 快照比较；在此之前不得运行 Card/Opening 全量 `--execute`。


### 2026-11-18 Owner 冻结 38 成员 World Snapshot Replay SAFE

Owner 回传 `r60_base336_world_snapshot_replay_safe_v1`，状态 **`WORLD_38_MEMBER_SNAPSHOT_REPLAY_PASS__P2_C_HOLD`**：

- 冻结 Roster/Template 绑定：true；8 组、38 个唯一 Story IDs，**40 条 group-member 关联**（部分故事跨组，因此 40 != 38）。
- 只读、RLS 和数据库角色守卫：`db_readonly_guard_verified=true`。
- 仅以已冻结 38 Story IDs 执行 World 组 Replay：`expected_membership_rows=40`、`observed_membership_rows=40`、`missing_membership_rows=0`、`extra_membership_rows=0`，`world_snapshot_matches_roster=true`。
- `database_accessed=true`、`database_modified=false`、`character_opening_read=false`、`story_text_read=false`、`world_json_returned_to_client=false`、`private_values_emitted=false`、`gpu_started=false`、`model_requests=0`。

**证据边界：** 该 PASS 是 38 个已冻结成员的当前/归档 World 关联快照匹配，不是重新对完整 172 Story 范围扫描并证明不存在新的关联组，也不是语义、actual-sent 或 Card/Opening 证据通过。当前环境连接/只读守卫及所检查的 40 条关联已通过，故下一最小动作是仅在内存中核对 roster 指定的 current/version `character`、`characters`、`opening` 字段及大小上限，失败只输出固定阶段/计数；禁止打印私有字段、ID、hash 或异常字符串。Card/Opening 产物仍 0/8，P2-C 仍 HOLD。


### Owner Card/Opening 只读内存预检：字段大小超限（2026-11-18）

Owner 返回 `r60_base336_card_opening_memory_preflight_safe_v1`：状态 `CARD_OPENING_MEMORY_PREFLIGHT_HOLD`；`failure_phase=READ_FIELDS`、`reason_code=FIELD_TOO_LARGE_HOLD`。此前预检已通过只读连接/RLS/角色守卫及冻结 38 Stories 的 40/40 World 关联匹配。

- 本轮 `groups=8`、`unique_stories=38`、`db_guard_verified=true`、`database_accessed=true`、`private_fields_read_into_local_memory=true`；
- `output_dir_absent=true`、`private_files_created=0`、`packages_within_size_limit=false`、`largest_package_bytes=null`；
- `source_records_current/archived/total=0` 是脚本在全部正常结束时才赋值的默认零值，**不能解释为零记录已读**；`packages_within_size_limit=false` 与 `largest_package_bytes=null` 不能证明触发了 `MAX_GROUP_BYTES`；
- 源码 `r60_base336_group_cards_opening_cpu.py` 中 `source_fields()` 对每个 `character/characters/opening` JSON 值按 `json.dumps(..., ensure_ascii=False, sort_keys=True, allow_nan=False).encode('utf-8')` 计算字节数，单字段超过 `MAX_FIELD_BYTES=24000` 则 `FIELD_TOO_LARGE_HOLD`。这足以解释本轮中断及没有创建文件；**尚不能反证此前历史全量提取是否为同一原因**。
- 继续保持 `database_modified=false`、`gpu_started=false`、`hf_jobs_submitted=0`、`model_requests=0`、`private_values_emitted=false`。

下一步：只读、Owner-local、单事务复核 40/40 World 关联后，对实际 roster 指定的 current/version 字段逐条统计三个字段的最大序列化字节数与超过 24KB 的记录数；同时独立检查 `MAX_GROUP_BYTES=185000` 限制。只输出按字段、source kind、group 的安全聚合；不得输出任何正文、Story/Revision ID、SHA 或 DB 异常。证据收集前不增加上限、不截断内容、不创建文件、不宣称语义隔离通过。P2-C 继续 HOLD。


### 2026-11-18 Card/Opening 字段与分组大小审计、安全边界调整

Owner 返回 `r60_base336_card_opening_field_size_audit_safe_v1`，状态 `FIELD_OR_GROUP_LIMITS_EXCEEDED__HOLD`：

- 冻结 8 组 / 38 唯一 Stories / 40 member 关联，World Snapshot 再核验通过；
- 59 次来源记录读取（current 38、archived 21）。字段计数均为 59；
- `character`：max 21,445 bytes，原 24,000 byte cap 超限 0；
- `characters`：max 25,549 bytes，原 cap 超限 1；
- `opening`：max 51,811 bytes，原 cap 超限 7；
- 8 个组内 4 组超过原 `MAX_GROUP_BYTES=185,000`，最大 575,785 bytes；
- 没有输出文件生成、没有数据修改，也没有模型调用或私有值输出。

源码检查确认 **第三层阻塞**：`r60_real_private_batch.private.write_new()` 的全局 `MAX_CAPTURE_BYTES=200_000`，也会拒绝大于 200 KB 的组文件。只调大字段与组限制不足以完成创建。

针对专属 Card/Opening 工具，采用与本次实测数据相匹配且仍受限的配置：单字段 **65,536 bytes（64 KiB）**，单组 **655,360 bytes（640 KiB）**；单独使用 `O_CREAT|O_EXCL|O_NOFOLLOW`（若支持）的 create-only 0600 写入，保留组上限；**不修改公共 `private.MAX_CAPTURE_BYTES`，不截断或删改任何角色卡、Opening 内容**。合成测试覆盖过去超过 24 KB 的 opening、严格 64 KiB 边界、575,785 byte 输出、已存在文件拒绝及超过 640 KiB 的拒绝。

只有在新代码定向测试通过、Owner 工作区同步、真实最小源快照/冻结范围再次核对并明确执行门禁后，才可运行一次真实 `--execute`，且只允许新建缺失的私有 8 组证据；这不证明语义、actual-sent、R50 全覆盖或 P2-C 通过。


### 2026-11-18 Owner 六目录冻结链唯一绑定（本地只读）

Owner 返回 `r60_base336_six_dirs_frozen_binding_safe_v1`，状态 `SIX_FROZEN_DIRS_EXACT_BINDING_PASS__NO_DB`：候选 A（`r60-quality-fast1000-api-v1`）完整 `frozen._frozen` 链验证为 true，冻结 336 cases / 172 stories，与 8 组、38 Stories 冻结 Roster 范围吻合；候选 B（`r60-quality-first-1000`）`FROZEN_BINDING_HOLD`。其余五个目录经 Owner 本地标志文件与 0700/0600 权限定位各唯一一个：`r60-real1000-v1-repair-plan-20261114`、`r60-real1000-v2-priority-replay-v1`、`r60-real1000-v3-consistent-replay-v1`、`r60-real1000-v123-crosswalk-v1`、`r60-real1000-r50-known5-quarantine-v1`（均相对于 Owner `~/.local/share/storyforge/r60/private/`）。本轮无 DB 查询、文件创建、模型或 GPU。此裁决消除了 OLD_DIR 双候选歧义，但不代表 Card/Opening 提取已执行或 P2-C 已通过。

后续仅使用上述六目录、既有 `r60-base336-world-cross-review-20261115` Roster 和预期不存在的 `r60-base336-group-cards-opening-20261115` 目录，先跑原脚本无 DB 的预检，随后受限 `--execute` 只新建 8 份 Owner 私有 0600 文件；真实结果以 SAFE 回执为准。


### 2026-11-18 Owner 8 Group Card/Opening 真实提取 SAFE READY，语义仍 HOLD

Owner Worktree 上针对已调整上限的脚本定向合成测试 **10 passed**，未触库预检状态 `BASE336_CARD_OPENING_EVIDENCE_PRECHECK__NO_DB`，其后在冻结六目录/只读数据库与 8 组 Roster 下运行 `--execute`，返回：

- `schema=storyforge_r60_base336_card_opening_evidence_safe_v1`
- `status=BASE336_EIGHT_GROUP_CARD_OPENING_PRIVATE_READY__SEMANTIC_HOLD`
- `groups=8`，`affected_story_ids=38`，`affected_candidate_cases=82`
- `source_records_current=38`，`source_records_archived=21`
- `private_files_created=8`，`source_roster_bound=true`
- `database_accessed=true`，`database_modified=false`，`private_values_emitted=false`，`gpu_started=false`，`hf_jobs_submitted=0`，`model_requests=0`，`train_admitted=0`
- `historical_actual_sent_verified=false`，`semantic_world_alias_verified=false`，`world_component_isolation_verified=false`，`r50_complete_exclusion_verified=false`，`reviewer_independence_verified=false`。

此证据只证明 Owner 本地按脚本成功创建了 8 个 create-only Card/Opening 私有包；**尚未独立读取并核对新文件的实际结构、权限、摘要/来源成员完整性**。P2-C 继续 HOLD。后续优先本地离线独立核验这 8 个 0600 文件与私有冻结 Roster 的严格一致性，绝不上传内容/ID/哈希；然后对世界设定/角色卡/Opening 的语义隔离、actual-sent、R50 排除继续定向补审，不能将文件生成成功等同于评估样本准入。


### 2026-11-18 Owner 八份 Card/Opening 离线完整性 SAFE PASS

Owner 返回 `r60_base336_card_opening_integrity_safe_v1`，状态 **`CARD_OPENING_8_FILES_INTEGRITY_PASS__SEMANTIC_HOLD`**。实际验证 `files_verified=8`、`groups_verified=8`、`distinct_story_ids=38`、`source_records_current=38`、`source_records_archived=21`；`roster_sha256_matched=true`、`source_membership_matched=true`、`field_limits_verified=true`、`permissions_verified=true`。全过程 `database_accessed=false`、`database_modified=false`、`private_files_modified=false`、`private_values_emitted=false`、`gpu_started=false`、`model_requests=0`。

Card/Opening 8 份 create-only Owner-private 来源证据的**采集与离线结构完整性子任务完成**。此项 PASS **不等于**历史实际发送版本、World/Character/Opening 语义隔离、R50 全量排除、独立 Reviewer 或 P2-C 准入通过；P2-C 继续 HOLD，`train_admitted=0`。


### 2026-11-18 Owner 既有 Codex 八组语义裁决结构 SAFE（未裁决）

Owner 返回 `r60_base336_codex_semantic_structure_safe_v1`：`CODEX_EIGHT_GROUP_STRUCTURE_FOUND__SEMANTIC_REVIEW_HOLD`。Roster/template 绑定均 MATCH；8 组 World evidence 绑定通过；Codex JSON 合法且发现完整 8 组 collection；8 组决策全为 HOLD（PASS=0、REJECT=0、OTHER_OR_MISSING=0）。`historical_actual_sent_verified=false`、`independent_semantic_review_verified=false`、`train_admitted=0`。

此结果证明现存 Codex 审查结构完整并绑定当前冻结 Roster/template，但**不证明审查语义正确或独立**。下一最小步骤不是重跑 Codex，也不是直接把 HOLD 改为 PASS，而是做 Owner-local schema-only shape 对照：对 8 个 Codex group rows 与 8 个 Card/Opening 包的成员级记录只输出字段名/类型/非空计数/来源类型计数，核对旧 HOLD reason 缺失的 member character/plot/version 证据是否被新包覆盖；禁止输出私有值、Story/Revision IDs、正文或 SHA。随后才制定独立 Reviewer 的逐组 source-quoted 语义复核输入与裁决，实际语义判断不由结构脚本代替。


### 2026-11-18 Owner Base336 成员级 Card/Opening 与 Codex 交叉核验 SAFE

Owner 返回 `r60_base336_member_evidence_codex_crosswalk_safe_v1`，状态 **`MEMBER_EVIDENCE_CROSSWALK_PASS__SEMANTIC_REVIEW_REQUIRED`**。

- Codex 8 组完整，8/8 决策仍为 HOLD；Roster 与 Template 绑定均通过。
- 8/8 Card/Opening 文件读取成功；每组实际记录数与冻结 Roster 预期记录数完全一致，8/8 `membership_exact=true`。
- 成员级来源覆盖：38 条 current、21 条 archived，共 59 条；三个字段 `character`、`characters`、`opening` 在全部 59 条来源记录中均存在且非空。
- Codex 原有四类证据字段在 8/8 组均非空：World 原文引用、World source field、source revision evidence、generic template vs shared world analysis。
- 本轮未读取数据库、未修改数据库或私有文件、未输出私有值、未调用模型、未启动 GPU；`train_admitted=0`。
- `structured_plot_field_counts` 对三个字段均为 0，表示本次检查器未识别到预设名称的结构化 Plot key；**不代表自然语言字段中不存在剧情信息，也不构成剧情独立证明**。

**裁决边界：** 本轮关闭 Base336 8 组成员级 Card/Opening 与 Codex 的结构/来源成员 crosswalk 缺口。它没有判断内容的语义相同、隐藏别名、共享剧情或 World component；也没有证明历史 actual-sent 版本、R50 完整排除或 Reviewer 独立性。Codex 的 8 个 HOLD 不得自动改为 PASS。P2-C 仍 HOLD，P2-B 仍 NOT_GENERATED。

**下一步：** 不重跑 Card/Opening 提取、完整性检查或本次 crosswalk。进入 Owner-authorized、source-quoted 的逐组语义复核：逐条阅读 59 条 current/archived 的 character/characters/opening 内容，并与 8 组既有 Codex HOLD 理由及代表性 World evidence 对照；对每组记录 World、Character/alias、Plot/event、Opening、version/timepoint、generic-template-only 等判断及来源引文。任何无法证实、来源版本不清或证据不足的项目继续 HOLD。独立 Reviewer 必须与原 Codex 审查有可核验的人员/流程独立性；模型或本 Agent 的建议不能冒充独立签署。语义分配最终再调用 `src/storyforge_dataset/world_isolation.py` 的共享校验器；其结构 PASS 仍不等于独立语义证明。


### 2026-11-18 Owner 12-file Base336 semantic pre-review: substantive cross-split reuse

Owner 向当前审查会话提供了 12 份私有证据的 ZIP（8 个 group Card/Opening、Roster、Template、Codex 及 8 World representative evidence）。本轮从上传包读取私有文件并在隔离会话内比对，不向 GitHub 提交任何原文、Story ID、作者、版本 ID、引用片段、SHA 或私有包本身。

SAFE 汇总 `r60_base336_semantic_prereview_safe_v1`：
`SUBSTANTIVE_CROSS_SPLIT_REUSE_EVIDENCE_FOUND__P2_C_HOLD`；
`files_verified=12`、`groups_reviewed=8`、`source_records=59`；
`high_risk_groups=4`、`medium_risk_groups=1`、`unresolved_groups=3`。

- 组 02：**HIGH**。不同 Story ID、不同 split 之间 Opening 长文本完全一致（最长 2,368 字符），另有具体角色背景重复。
- 组 05：**HIGH**。不同 Story ID、不同 split 之间长角色背景完全一致（最长 3,789 字符）；部分角色设定存在高度近似变体。
- 组 06：**HIGH**。不同 Story ID、不同 split 之间成段角色背景及 Opening 实质重复，存在多个跨 split 匹配对。
- 组 08：**HIGH**。不同 Story ID、不同 split 的完整 `character/characters/opening` 字段有逐字相同记录，并存在近似变体。
- 组 04：**MEDIUM**。角色描述表现出写作模板或风格相似，但尚未据此确证同一人物/剧情/World。
- 组 01、03、07：**UNRESOLVED**。在本轮指定字段中未观察到跨 split 的长文本完全重复；这不是语义独立的证明。

本轮排除了相同 Story ID 的 Current/Archived 重复副本，且核对组内成员来源与冻结 Roster 的严格绑定。准确结论是**已有来源中的跨 split 复用/高度疑似复用**，不是已证明 historical actual-sent 的模型训练泄漏。旧 Codex 8 组 HOLD 保持不变；任何 World JSON 通用模板认定都不能覆盖成员级相反证据。

独立 Reviewer 尚未签署；`historical_actual_sent_verified=false`、`r50_complete_exclusion_verified=false`、`train_admitted=0`，P2-C HOLD，P2-B NOT_GENERATED。下一步由独立 Reviewer 在 Owner-private 的逐案来源引文、版本链、角色同一性与 Plot/Opening 语境证据上复核高风险组，并确定共享语义组件的分组隔离或候选排除方案；不得用推断的 PASS 自动准入。


### 2026-11-18 Base336 cross-split exact reuse independent recheck

基于 Owner 提供的原始 12 文件 ZIP，在本次隔离审查会话内对每组所有跨 Train/Validation、不同 Story ID 的来源对独立重算，**不是原先 Codex Reviewer 的独立签署**。比较三个字段完整结构相等，以及嵌套字符串长度 >=120 Unicode 字符的逐字相等；排除 URL 字符串；排除同 Story ID 的 current/archive 重复，把不同版本的匹配证据折叠成唯一跨 split Story 配对。

SAFE `r60_base336_source_reuse_independent_recheck_safe_v1`，`SOURCE_REUSE_RECHECK_COMPLETE__SEMANTIC_SIGNOFF_HOLD`：12 文件、8 组、59 来源记录；分组跨 split 来源组合数 `[20,1,6,2,54,9,2,6]`；有精确完整字段或长文本复用的**唯一不同 Story ID 配对**数 `[0,1,0,0,1,2,0,2]`，合计 6 个组内去重的故事配对；高风险组 02/05/06/08。组 04 仍需语义复核；组 01/03/07 无此阈值下的精确正例，不能作独立性证明。

证据强度：
- 02：两个不同故事 current/current 对有 2,368 / 1,396 / 1,159 字符的长文本相等；
- 05：current/version 之间的长字符串逐字相等，最长 3,789 字符；
- 06：两对不同 Story 的 source 组合存在 1,492、1,391 字符或多段其他文本的逐字相等；
- 08：一对故事的 `character`、`characters`、`opening` **三个完整字段逐字结构相等**（字段的 JSON 表达约 2.2 KB、4.2 KB、0.4 KB），另一对的 `character`、`characters` 两字段结构相等。

完整逐案来源引用、版本 ID、hash 和最小引文仅保存在会话生成的私有文件 `R60_BASE336_SOURCE_REUSE_RECHECK_PRIVATE.json` 中；GitHub 不存储这些值。方法仅验证精确复用，不涵盖变体、隐含别名、Plot 语义或实际训练时 actual-sent 版本。独立 Reviewer 未签署；`historical_actual_sent_verified=false`、`train_admitted=0`，P2-C 继续 HOLD。下一步优先获取可绑定 6 个跨 split 故事配对的 request-effective actual-sent/source revision 历史证据，再作独立语义组件裁决或保守排除，且不可仅因结构匹配就判定已发生模型训练泄漏。


### 2026-11-18 Six source reuse pairs: 22-case provisional hold scope

本次在隔离会话重新读取 Owner 提供的 12 份原始私有 JSON（ZIP）和上一轮逐对复核记录，完成**原文证据回放验证**，不是直接信任此前预审文本。

`r60_base336_source_reuse_provisional_hold_scope_safe_v1` 返回 `SIX_SOURCE_REUSE_PAIRS_REVERIFIED__22_CASES_PROVISIONAL_HOLD__P2_C_HOLD`：

- 8 个 World Groups，59 条 current/archived 来源记录，12/12 文件输入；
- 4 个组（02、05、06、08）存在已验证精确跨 split 内容复用；
- 6 个跨 Train/Validation 的不同 Story ID 配对，去重后 **11 个 Stories**（Train 6、Validation 5）；
- 通过冻结 Roster 的逐 Story 候选位置绑定，关联到 **22 条唯一冻结候选 Case**（Train 11、Validation 11）；
- 原 Card/Opening JSON 实际回放验证 **5 个完整字段相等证据**及 **12 个 >=120 字符长文本逐字相等 SHA/路径证据**，所有报告中的配对来源引用与原始记录精确绑定；未复印私有原文；
- 现有私有 Reviewer worksheet 仍是全部 HOLD，尚未独立签署；
- `database_accessed=false`、`database_modified=false`、`source_data_modified=false`、`private_values_emitted=false`、`model_requests=0`、`gpu_started=false`、`train_admitted=0`。

隔离会话中的私有新产物：`R60_BASE336_22_CASE_PROVISIONAL_HOLD_SCOPE_PRIVATE.json`、对应 SAFE、`R60_BASE336_ACTUAL_SENT_EVIDENCE_REQUEST_PRIVATE.md` 和打包 ZIP（不进 GitHub）。私有产物保存每个配对的来源 kind、revision、冻结候选位置及证据字段路径，便于 Owner 做严格的 request-effective / training-input 版本核验。

**严格限定：** 22 条是有逐字来源复用证据支持的**优先暂缓解除隔离候选范围**，不是已经从 293/43 数据集中剔除的记录，也不能宣称已进入训练输入。其余 60 条虽没有本轮精确证据，仍不能视为语义独立。仍需逐对确认 actual-sent 时间点/源版本、prompt assembly、历史 train/eval manifest、独立 Reviewer 和 Owner 正式签署；R50 完整元数据排除及历史 exposure universe closure 等仍 HOLD。P2-C HOLD、P2-B NOT_GENERATED、`train_admitted=0`。


### 2026-11-18 Final 293/43 release split vs provisional World roster: implementation-path audit

**重要纠正：之前 22-case SAFE 中的 Train 11 / Validation 11 是基于原 World Roster 的初始 split，不是 GPU 训练时的最终 293/43 split，严禁称为最终训练/验证的 11/11 泄漏。** 仓库权威实现为：

- `experiments/r58_quality/r60_base336_exploratory_split.py::split` 先以 `r60_base_start_world_split_preview.preview` 的 276/60 初始划分为基线，将八组精确 World JSON 关联组成 connected components；若任一连通分量出现 Train，则统一放入 Train，最终 293 Train/43 Validation，`crossing_known_world_groups_after_split=0`。
- `r60_base336_exploratory_release_verify.py::verify` 对 Owner 私有 `train.jsonl`、`validation.jsonl` 和 `R60_BASE336_EXPLORATORY_MANIFEST_PRIVATE.json` 校验 293/43 行数、完整 SHA256 和 message 合同；发布 JSONL 每行只有 `messages`（User/Assistant/User/Assistant），不含 Story ID 字段。因此**必须**与冻结 336 候选重新构建结果按行内容相等绑定，不能从 JSONL 的位置推断 Story ID。
- GPU Stage `scripts/r60_base336_gpu_stage.py` 在 `private/release/` 保存发布字节、Stage SHA256 Manifest；`scripts/r60_base336_gpu_worker.py` 将这两个 staged JSONL 作为 `swift sft --dataset/--val_dataset` 输入。这解释正确的实际输入链，但代码路径本身尚不是对应 Run 的 Owner-local Stage/Worker 字节证明。

为此在当前隔离环境制作只读 Owner-local 工具 `r60_base336_actual_release_scope_cpu.py` 及 synthetic-only 测试，**5 passed**（最终划分映射、内容篡改、双 split 同行歧义、重复来源位置、源缺失）；随 `R60_BASE336_FINAL_RELEASE_22_CASE_AUDIT_TOOLS.zip` 提供 Owner。此工具尚未运行于 Owner 真实冻结 293/43 文件，**不宣称实际风险 6 对已被重新验证或实际训练输入链已完成**。工具执行顺序：复用冻结六目录，验证发布 Manifest 和 JSONL，重新构建的字节与保存的发布文件逐字节相等，按真实 row bytes 将 22 case 映射到最终 split，报告原 6 对有多少仍跨最终 split。只在 Owner 输出 SAFE 数量，不显示真实 ID/引文/哈希，不触 DB/模型/GPU，不写冻结文件。

若 6 对最终 split 共置，仅可关闭**这 6 对在该冻结发布版本上的跨 293/43 精确文本相等风险**；并不能证明其它未发现的语义组件、历史 actual-sent 请求、R50 全量元数据排除、R47/R48/R55 全暴露排除或 Reviewer 独立性。P2-C HOLD、P2-B NOT_GENERATED、`train_admitted=0` 保持不变。下一步等待 Owner-local `r60_base336_actual_release_scope_safe_v1` SAFE 回执，并另核 Stage Manifest / GPU Worker 实际 Job 的输入链。


### 2026-11-18 Owner actual 293/43 release 22-case replay SAFE PASS

Owner 已执行 `r60_base336_actual_release_scope_cpu.py`，回执 `r60_base336_actual_release_scope_safe_v1`，状态 **`FINAL_293_43_RELEASE_SCOPE_REPLAY_PASS__SEMANTIC_HOLD`**。审计脚本和合成测试从临时 ZIP 迁入 PR #31 GitHub 分支：`experiments/r58_quality/r60_base336_actual_release_scope_cpu.py`（commit `3d25e29`）及 `experiments/r58_quality/test_r60_base336_actual_release_scope_cpu.py`（commit `ce2ff9e`）；5/5 synthetic-only tests passed。此前只交付 ZIP 而未版本化是工作流遗漏，已纠正。

本次 Owner SAFE：
- 293 Train / 43 Validation，336/336 Release 记录验证，发布 SHA256 PASS；`reconstructed_release_bytes_equal=true`、`release_roster_and_stats_bound=true`。
- 6/6 前述跨初始 split 的精确来源复用 Story pairs，经冻结 336 来源与实际 release rows 重建/逐字节对照，**最终跨 293/43 split 数为 0**、`source_reuse_pairs_colocated_final_split=6`。
- 原 22 个优先复核 Case 在本次最终发布中 **22 Train / 0 Validation**。旧审查中的 `Train 11 / Validation 11` 是初始 Roster 标签，不是发布 split；禁止再用于实际 GPU 训练风险表述。
- 另有独立 release-stage SHA 绑定 SAFE：两个发布目录（A、B）均与唯一的目标 GPU Stage Manifest 的 train/validation 文件 digest 匹配。故 B 可用于同字节发布内容复核，但其目录创建时间并不能证明 B 是唯一历史输入来源。
- `actual_training_release_input_proven=false`、`historical_request_effective_source_proven=false`、`world_semantic_isolation_verified=false`、`r50_complete_exclusion_verified=false`、`reviewer_independence_verified=false`、`train_admitted=0`。
- 本轮无 DB 访问/修改、模型调用、GPU、私有文件修改或私有值输出。

**有限门禁结论**：可以关闭“已识别的六对精确重复来源在最终 Base336 293/43 发布数据中跨 split”这一特定风险，不能将此 PASS 扩展为所有隐藏语义组件、完整 R50 metadata-only 排除、历史已暴露评估源、request-effective actual-sent 或训练 Worker 最终实际读取字节证明。下一步优先复核 GPU Stage/Worker receipt 的具体输入链，以及最终 293/43 的其他语义组件和 P2 新来源与保护集交叉隔离；不得直接解 HOLD 或生成正式 P2-B 48 提示。P2-C HOLD、P2-B NOT_GENERATED、train_admitted=0。


### 2026-11-19 Mainline reset: P2 protected crosswalk prioritized

经再次对照 `docs/R60_BASE336_POST_TRAIN_NEXT_AGENT_HANDOFF_20261117_CN.md`、`docs/plans/R60_BASE336_POST_TRAIN_QUALITY_EVALUATION_20261117_CN.md` 和公开来源补充决策，确认**阶段性偏离主线**：最近针对原 8 个 World 关联、6 对精确来源复用、22 条候选和 GPU Stage 的审计占据了主要工作，而当前项目真正需要的是**8 个新的 P2 Supabase 公开来源作为独立 held-out**，相对于所有历史训练/验证、密封与已暴露测试集的交叉独立性证据。

已关闭并停止重复：针对已识别 6 对精确来源复用，在最终冻结 293 Train / 43 Validation 发布字节中，6/6 全部 colocated、0 crossing；22/22 候选位于最终 Train。该事实不是所有语义组件全局隔离，更不是 P2 新 8 来源的独立性 PASS。两份同字节 release 的 Stage SHA 绑定和相关本机工具只作历史审计证据保留。不再继续 GPU Worker/Checkpoint 的延伸调查，除非出现直接影响 P2 的具体版本争议。注意此前新增 `r60_base336_actual_release_scope_cpu.py` 的 synthetic tests 只覆盖局部 mapping helper，不能替代实际 Owner SAFE，后者已经独立提供；不要声称 HEAD CI 通过，直到获得对应检查证据。

回归 P2 主线门禁与顺序：

1. **P2-A READY**：8 条已授权内部独立评估提示构造的 Supabase 公开来源，版本/公开权限/审核快照绑定已通过。此 8 条与历史 8 World 组不同；不能混同。
2. **P2-C-P1（优先）**：将 P2 8 来源实际 source/version/World/角色语义组件，与 Base336 **全部 172 个故事/336 条冻结来源**作来源绑定的交叉核验。已知 exact Story ID overlap=0、受限 World JSON overlap=0 不代表全部 172 故事的语义隔离。既有 8 组/38 故事成员级 evidence 可供风险定向审阅，但不能冒充完整 172 故事的语义证明。
3. **P2-C-P2**：R50 Protected/Reserved **完整 metadata-only roster**，先核清完整性，再核 exact IDs / source lineage / semantic World assignment；严禁读取密封正文、提示、答案。
4. **P2-C-P3**：R47/R48/R55 已验证的 20-case/2-Story 链 exact overlap=0 已关闭；继续处理 **完整历史 exposure-universe coverage**、语义别名/改写及额外保护集，不重跑同一 20-case exact crosswalk。
5. **P2-C-P4**：8 个新 P2 来源的 actual request-effective timepoint、创建时间与历史训练暴露窗口、World/Character/Plot 语义组件证据和 Reviewer 人员/流程独立签署；Owner 源/Prompt Manifest 最终冻结。来源创建于 GPU Run 后仅是辅助时间证据，不能单独认定未暴露。
6. **P2-B**：全部 P2-C 门禁签署后，才构造并冻结实际 48 prompts JSONL/Manifest/SHA；P3-P6 仍等待相应授权及完整证据。

本轮不重跑数据库提取、训练、GPU 或模型推理，不读 R50 正文，不提交任何 Owner-private 内容。**下一最小外部证据请求**：Owner 提供 8 条 P2 Source Manifest 的 SAFE Schema / 版本覆盖，以及 R50 完整 metadata-only roster 的现有 SAFE 完整性/范围回执（非正文）；先复用已存在的清单和 SAFE，不进行宽泛 inventory。总门禁 P2-C HOLD、P2-B NOT_GENERATED、`train_admitted=0`。


### 2026-11-19 PR31 CI blocker triage and P2-C next-source contract

本轮 GitHub 实际 Actions 排障（非 P2-C 数据门禁）：最初的 CI FAILURE 来自两个新 source-release auditor 文件的 Ruff import order / BLE001；修复后 full pytest 又发现 4 个旧合同/测试扩容不匹配（P2 source binding 聚合失败码替代旧单字段码、禁用的 legacy submit 被 HF SDK 预检提前拦截、两项嵌套 pytest 对通过数写死）。全部均已提交针对性修复：P2 source 的缺失 metadata 必须继续 fail closed；legacy submit 在所有 HF/SDK 检查前拒绝；nested suites 要求返回码 0 且通过数不低于既定测试数，不得以数量增长判失败。首次修复时错误地写入字面量反斜杠+n，已通过后续提交更正为真实 Python 换行。**必须看最新 HEAD GitHub Actions 后才能声称 CI PASS**，不将测试断言修复冒充 P2-C 证据。

下一项 P2 主线实物证据固定为 Owner 原有 `~/.local/share/storyforge/r60/private/r60-p2-public-source-inventory-20261118/R60_P2_PUBLIC_STORY_SOURCE_MANIFEST_PRIVATE.json`，其真实编制合同由 `experiments/r58_quality/r60_base336_p2_public_source_inventory_cpu.py` 定义：`sources` 中 8 条，包含 story/revision、public content hash、snapshot/permission 绑定、World exact hash 和时间元数据；`gates.base336_private_source_crosswalk`、`gates.r50_metadata_exclusion`、`gates.r47_r48_r55_exposure_exclusion` 仍为 HOLD，源 Inventory READY 并不改变此事实。

先不要重复原 22-case、293/43、R47/R48/R55 20-case 精确核验。下一步需要 **P2 8 来源相对于 Base336 全部 172 Stories 的语义交叉证据**，以及 Owner Mac 既有 **R50 全部 Protected/Reserved metadata-only roster 的完整性 SAFE**。P2 manifest 仅含可用于身份/版本/时间绑定的元数据，**不含充分的 World/Character/Plot/Opening 原文，单独提供它不能完成语义核验**。不得读取/上传 R50 密封正文；不能根据任一目录存在推断 R50 metadata roster 已完整。P2-C HOLD；真实 P2-B 48 Prompts NOT_GENERATED。


### 2026-11-19 PR31 CI repaired at code commit 5b9ce93

GitHub Actions 对 `5b9ce93785230139cd1cadb44c552b276c38b738` 的四项 PR 工作流均 **completed/success**：`CI`、`R60 Base336 P2 Source CI`、`R58 scoped synthetic (no training)`、`R60 REAL1000 Quality Reviewer (synthetic only)`。此前 CI 失败链最终定位到测试导入/断言更新中的字面量换行，以及 legacy-disabled submit 守卫前存在 HF SDK 依赖检查；修复提交均在 PR #31，保持 submit 永久失败关闭，不进行 HF SDK/GPU 调用。该 CI PASS 只代表代码及合成测试，不代表 P2-C 数据/语义隔离 PASS。

当前优先事项没有变化：使用 Owner 已存在的 P2 8-source private Manifest，取得 Base336 全 172 Stories 的来源绑定语义证据，以及 R50 完整 Protected/Reserved **metadata-only** 清单与现有 SAFE；继续历史已暴露全集补全，独立 Reviewer 签署。不要重开 6-pair/22-case 或旧 GPU Stage 审计。P2-C HOLD、P2-B NOT_GENERATED。


### 2026-11-19 Owner R50 46/46 pre-seal structural replay PASS

Owner 执行仓库原有 `scripts/r60_r50_preseal_crosswalk_cpu.py`，使用六个明确指定的既有 R50 Owner-local 输入（46 cases、46 provenance、selection、admission、full original World inventory、R45 gate），返回 `storyforge_r60_r50_preseal_crosswalk_safe_v1`，状态 **`R50_PRESEAL_46_CROSSWALK_PASS__FINAL_COVERAGE_HOLD`**：

- `preseal_cases_checked=46`、`case_id_order_exact=true`、`provenance_story_fields_present=true`、`history_reference_fields_present=true`。
- `selection_expected_fields_present=true`、`admission_expected_fields_present=true`、`worlds_expected_fields_present=true`、`r45_gate_expected_fields_present=true`。
- `reason_code=PRESEAL_STRUCTURE_ONLY`；`frozen_protection_50_verified=false`、`r45_full_source_isolation_verified=false`、`r50_complete_exclusion_verified=false`。
- 无 DB、GPU、HF Job，`train_admitted=0`，无私有内容输出。此前一次 `FILE_PERMISSION_HOLD` 因既有 Admission Status 文件权限为 0644；Owner 将该文件权限缩紧至 0600 后重验通过；内容未由本审查程序修改。

**裁决**：可以关闭六份 R50 既有证据的 pre-seal 46 条成员顺序与来源结构一致性子门禁。**不允许**据此认定完整 Protected/Reserved roster 已交付或 50/50 封存，且 R45 Gate 预期字段存在不代表 R45 全来源隔离 PASS。下一最小动作是在 Owner 本地仅对已知 World Inventory、Selection、Admission、R45 Gate 做 **ALLOWLISTED 状态/计数字段** 的只读、聚合 SAFE 诊断：确认 original/selected/excluded/final seal 统计之间的条件关系，区分尚缺最终 4 条、缺签署或缺元数据全集证明；不得读取候选内容或 R50 密封题目，不要将现有结构 PASS 扩展为 P2-C PASS。P2-C HOLD，P2-B NOT_GENERATED。

## 2026-11-19 Owner evidence reconciliation and next execution (supersedes earlier pending notes)

### A. R50 status projection: field presence only, not 50+46+4 exact complement

Owner-provided metadata-only projection reports:

| Scope | Observed fields / values | What this proves |
|---|---|---|
| Selection | original=50, selected=46, excluded list count=4, final seal field present | Metadata fields and counts are present |
| Admission | candidate=46, excluded=4, final seal and promotion fields present | Metadata fields and counts are present |
| R45 Gate | frozen R45 hashes verified=true, heldout_cases_sealed=0, incomplete/hidden alias field present | Frozen hash check is reported; no heldout seal |

This projection does **not** prove the original 50 source rows equal the exact union of derived 46 plus excluded 4. The code file scripts/r60_r50_original50_complement_cpu.py exists, but no Owner SAFE stdout for its exact 50/46/4 row-level complement audit has been provided in this evidence set. Therefore do not record R50_ORIGINAL50_46_PLUS4_EXACT_COHORT_PASS, frozen_protection_50_verified=true, or r50_complete_exclusion_verified=true.

Current R50 ledger:
- 46-case PRESEAL structure / provenance crosswalk: PASS, limited to the six inputs and fields checked by scripts/r60_r50_preseal_crosswalk_cpu.py.
- Selection / Admission metadata field projection: PASS as field-presence/count inspection only.
- Exact original-50 = selected-46 + excluded-4 row-level complement: **NOT VERIFIED / HOLD**.
- R45 full-source lexical screen: Owner-reported exact screen only; semantic aliases and shared-world isolation remain HOLD.
- Final heldout seal: **HOLD** (heldout_cases_sealed=0).
- Official heldout admission: 0.

### B. Base336 all-172 source evidence capture implementation

The frozen candidate JSONL metadata coverage audit reported 336 cases / 172 unique stories but zero structured World / Character / Opening fields. The existing 38-story / 59-record card-opening evidence is valid for its scoped 38 stories only; it cannot be extrapolated to all 172.

A new Owner-local read-only capture tool is now present:

- experiments/r58_quality/r60_base336_p2_source_evidence_capture_cpu.py
- Synthetic-only tests: experiments/r58_quality/test_r60_base336_p2_source_evidence_capture_cpu.py

The tool:
1. Revalidates the frozen 336-case / 172-story scope using the six bound Owner directories and quarantine manifest.
2. Reads the existing 8-row P2 public source manifest; it does not rediscover or reselect P2 sources.
3. Uses one REPEATABLE READ READ ONLY transaction under r58_export_reader, row_security=on, with the existing P2 RLS preflight.
4. Captures current and all archived v2_data fields (world, character, characters, opening) for the 172 frozen Base336 story IDs.
5. Captures the exact approved public snapshot fields for the 8 P2 sources, binding current public revision, moderation submission/content hash, snapshot-vs-current JSON equality, permission event, permission submission and public visibility.
6. Records exact field equality counts only as an exact-match screen. It does not infer semantic equivalence, actual-sent prompt state, or World-component independence.

Private output is create-only under ~/.local/share/storyforge/r60/private/, with directory mode 0700 and package mode 0600. The full source values, identifiers and pair mappings stay on the Owner Mac. Stdout contains only bounded aggregate counts. No R50 body, private session messages, prompt answers, GPU, HF Job, inference, training, admission or promotion is accessed or started.

The tool's successful SAFE status is intentionally only:
- P2_BASE336_SOURCE_EVIDENCE_CAPTURED__SEMANTIC_REVIEW_REQUIRED when exact Story-ID overlap is zero; or
- P2_BASE336_SOURCE_EVIDENCE_CAPTURED__EXACT_STORY_ID_OVERLAP_HOLD otherwise.

Neither status is a semantic-isolation PASS.

### C. CI evidence for the new capture tool

At commit 7486fb5980aa049039b0ec4f5600848cd0f1ce7e on branch docs/r60-p2-r47-r48-r55-source-shape-audit-20261118, the following workflows completed successfully:
- CI
- R58 scoped synthetic (no training)
- R60 Base336 P2 Source CI
- R60 REAL1000 Quality Reviewer (synthetic only)

These are code/test results only. No Owner-private 172-story database capture has been run by CI.

### D. Next Owner action — one scoped read-only capture

Run the new tool first without --execute; this is a local precheck only. If it returns P2_BASE336_SOURCE_EVIDENCE_PRECHECK__NO_DB, run the same command with --execute on the Owner Mac. The exact local six-directory and P2-manifest paths are in the Owner's 2026-11-18 inventory; do not copy private paths, identifiers, hashes or source values into GitHub or chat. Use a new, nonexistent output directory directly under ~/.local/share/storyforge/r60/private/.

Return only the printed SAFE JSON. Never upload R60_BASE336_P2_SOURCE_EVIDENCE_PRIVATE.json.

After a successful capture:
1. Independently review the private source package for semantic World / Character / Plot / Opening aliases across all 172 Base336 stories and the 8 P2 sources. Keep exact-match screening separate from semantic judgments.
2. Bind any reviewer component assignments to the captured source/version evidence and use the existing src/storyforge_dataset/world_isolation.py helper for split conflicts; do not duplicate its algorithm.
3. Keep historical_actual_sent_verified=false until request-effective historical system/card evidence exists.
4. Finish R50 exact 50/46/4 complement and complete R50 metadata-only P2 exclusion as separate gates; do not infer them from field presence or the 46-case preseal crosswalk.
5. Finish R47/R48/R55 complete exposure-scope closure and semantic variants, independent Reviewer signoff, and Owner freeze.
6. Only after every P2-C gate passes may P2-B produce the real 48-row prompt package. No inference or GPU is implied.

**Current mainline priority:** complete source-bound P2 × Base336 172-story evidence first. P2-C remains HOLD; P2-B remains NOT_GENERATED; train_admitted=0.


## 11. 2026-11-19 主线门禁状态校正（覆盖本索引中较早的待核验文字）

本节仅合并已存在的 Owner SAFE / SAFE 状态和仓库历史证据，不新增私有数据读取或门禁通过声明。

### 已关闭的精确身份子项

- P2-A：8 条公开来源、8 个唯一 Story ID，revision / moderation snapshot / permission event 绑定已通过。
- P2 × Base336：既有 Owner SAFE 在冻结 336 cases / 172 stories 范围内 exact Story ID overlap=0。
- P2 × R50：既有 Owner SAFE 报告 exact Source ID disjoint；该结论只限其实际检查的 R50 source scope，不等于 R50 完整 Protected / Reserved roster coverage。
- P2 × R47/R48/R55：Owner-local SAFE 已验证 R47 Prompt / Manifest / canonical Test / `metadata.story_id` 复合绑定，R48 使用同一 canonical Test，R55 三层索引 76/68/46 的 SHA、Schema、candidate-token links 和 20/20 R47 Sample 覆盖；同一 20-case 链范围内 exact Story ID overlap=0。20 prompts 仅对应 2 个 Story IDs，不能按 20 个独立故事计算。
- R55 旧 R47 baseline preflight：仓库历史证据记录 Owner-reported PASS，scope 为 R47/R48 同一 20 个已曝光开发 prompts；底层 SAFE 未在本轮独立重新哈希。它不证明完整历史 exposure universe，也不替代 Story ID crosswalk。

### 仍未关闭的 P2-C 门禁

- Base336：8 组、38 个故事、82 个受影响 cases 的历史结构关联已建立；8 组 Codex 语义决策均 HOLD。7 组成员角色/剧情/版本绑定证据不足；另 1 组仍缺少 World marker 与成员上下文解释。
- Base336 成员级 Card/Opening：Owner 已报告输出目录及 8 组输出文件不存在；current / archived / actual-sent 证据均未取得。既有 no-DB preflight PASS 不代表内容捕获完成。不得重跑旧的全量 `--execute`，除非 Owner 对新的、明确限定的只读数据库捕获动作另行批准。
- R50：已有 50 条原始来源、46 条候选和 4 条排除的结构证据；R45 固定来源哈希检查已通过，heldout sealed=0，隐藏 alias / world-component closure 仍 HOLD。尚无完整 R50 Protected / Reserved metadata-only roster coverage SAFE；不得把 46 条 pre-seal 或局部 exact ID disjoint 扩展为完整 50 条保护集排除。
- R47/R48/R55 完整历史 exposure universe：UNKNOWN / HOLD；已关闭的只是上述同一 20-case 链。
- Actual-sent / delivered version binding、语义 World / hidden-alias exclusion、Reviewer execution independence 与 Owner freeze：仍 HOLD。

### 执行顺序

1. 不重复 P2 × Base336 / R50 / R47-R48-R55 已完成的精确 ID 子检查，也不重复 R55 三层索引链。
2. 下一项需 Owner 决定是否授权一次限定范围的 Base336 current/archived Card/Opening **只读数据库捕获**（仅冻结 roster 中 38 个成员、8 组，私有 create-only 输出；不修改数据库、不读 R50 正文、不输出私有字段）。未获具体授权前不执行。
3. 独立完成 R50 metadata-only 完整覆盖证明及 actual-sent / Reviewer 证据盘点；任何覆盖不完整继续 HOLD。
4. P2-C 全部门禁与独立 Reviewer / Owner freeze 通过之前，P2-B 真实 48 条评估提示仍为 NOT_GENERATED；不启动模型请求、HF、GPU、训练或晋升。

当前：
```
P2_A = READY
P2_BASE336_EXACT_ID = PASS_OVERLAP_0
P2_R50_EXACT_SOURCE_ID = PASS_WITHIN_EXISTING_SAFE_SCOPE
P2_R47_R48_R55_20_CASE_EXACT_ID = PASS_OVERLAP_0
P2_R47_R48_R55_FULL_EXPOSURE_CLOSURE = UNKNOWN_HOLD
P2_BASE336_SEMANTIC_COMPONENTS = HOLD
P2_R50_COMPLETE_METADATA_COVERAGE = UNKNOWN_HOLD
P2_ACTUAL_SENT_VERSION = UNKNOWN_HOLD
P2_REVIEWER_INDEPENDENCE_AND_OWNER_FREEZE = HOLD
P2_B_48_PROMPTS = NOT_GENERATED
P2_C = HOLD
train_admitted = 0
quality_v1_admitted = 0
gpu_started = false
hf_jobs_submitted = 0
model_requests = 0
model_promoted = false
```


## 12. 2026-11-19 Owner 上传的 Base336 八组成员级 Card/Opening 语义复核（本索引最新状态）

Owner 已提供 8 个完整的成员级 Card/Opening 私有 JSON、冻结 8 组 roster、对应 World 证据及既有 Codex HOLD 决策。此前 Owner-local 的只读检查证明所有 8 个文件存在、权限 0700/0600、逐组与 roster 记录完全对齐、roster SHA 绑定通过。59 条 current/archived 来源记录（38 current、21 archived），覆盖 38 个不同故事、82 个相关案例。本次内容复核的 SAFE 报告为：`docs/evidence/R60_BASE336_EIGHT_GROUP_MEMBER_SEMANTIC_REVIEW_SAFE_20261119_CN.md`。

**证据状态变化（覆盖本索引第 11 节中“成员级 Card/Opening 文件不存在”的历史描述）：**
- `BASE336_CARD_OPENING_MEMBER_FILES = PRESENT_8_OF_8__STRUCTURE_VERIFIED`；不可重跑既有数据库提取或覆盖输出。
- 第 02/05/06/08 组在 Train/Validation 两侧发现具名人物及剧情组件的高置信度复用，已标记 `CONCRETE_CROSS_SPLIT_COMPONENT_REUSE_FOUND`，但未完成独立 Reviewer 裁决。
- 第 01/03/06 组及第 02/03 组存在跨组人物关联；第 03 组同时包含不同题材，不能将同一通用 World JSON 的所有成员粗暴合为同一个真实故事世界。
- 第 04 组有明显写作/关系指令模板相似性，仍未证明相同专属世界；第 07 组未发现直接组内实体复用，两组继续 HOLD。
- 旧 Codex 所有组的决定仍为 HOLD。新增材料解决的是“角色卡/开场证据缺失”子项，不是历史实际发送版本、语义终审、Reviewer 独立性、R50 完整覆盖或 P2-C 的 PASS。

下一步是 Owner-local 基于真实成员级证据生成**按具体人物/组织/事件**的组件边候选，由独立 Reviewer 按仓库既定 Gold Quality Pipeline 审查并由 Owner 冻结。任何边仍需真实 source/version 绑定；禁止用模板文字或缺失字段充当无关联证明。不要输出私有 ID 或上传原始 JSON 至 GitHub，亦不允许直接修改冻结案例、生成 48 prompts 或训练。


## 13. 2026-11-19 组件图精确复用下界（本索引最新状态）

在 8 组成员级原始 Card/Opening、冻结 roster 的 59 条 current/archived 记录中，以**不同 Story**为单位聚合、排除非实质性的共同模板，再比较完整 JSON 字段或至少 300 字符的相同非通用内嵌文本，得到：

- 13 对不同 Story 存在可确认的精确内容复用，其中 **6 对跨 Train/Validation**、7 对仅发生于同一拆分。
- 6 对跨拆分精确复用涉及 **11 个不同 Story / 22 个去重候选案例**，这是保守下界，并非完整语义关联上限。
- 跨拆分边按 World group 分布：01↔06 一对、02 组内一对、05 组内一对、06 组内一对、08 组内两对；没有据此把 03/04/07 错误认定为安全。
- 02↔03 的同人物阵容、05 的近似改写和同 Story 多组归属属于独立的候选层，不混进精确证据计数；roster 有 2 个 Story 跨两组（01/06、03/06），不能计为多个不同故事。
- 精确复用属于**静态当前/历史版本内容证据**，仍不等于历史 actual-sent 已泄漏或独立 Reviewer 已完成。

完整脱敏审计为 `docs/evidence/R60_BASE336_COMPONENT_GRAPH_EXACT_REUSE_SAFE_20261119_CN.md`。新的下一步是在 Owner 私有环境进行 6 条精确跨拆分边及其近似扩展的独立语义组件裁决，复用已有 `world_isolation.py`。不重跑数据库、不上传私有路径/原文/ID、不自动修改冻结 split、不得生成 48 条正式评估提示或训练。

```text
P2_BASE336_CARD_OPENING = VERIFIED_8_OF_8
P2_BASE336_CROSS_SPLIT_EXACT_REUSE_PAIRS = 6
P2_BASE336_CROSS_SPLIT_EXACT_REUSE_STORIES = 11
P2_BASE336_CROSS_SPLIT_AFFECTED_CASES_LOWER_BOUND = 22
P2_BASE336_INDEPENDENT_SEMANTIC_REVIEW = PENDING
P2_BASE336_ACTUAL_SENT = HOLD
P2_C = HOLD
P2_B_48_PROMPTS = NOT_GENERATED
TRAIN_ADMITTED = 0
```


## 14. 2026-11-19 Reviewer 候选图范围扩大（取代第 13 节数字）

从当前对话上传的**同一批**八组 Card/Opening + roster 重新机械审计，新增可复现的 300 字符逐字匹配 + 完整 JSON 字段相同两种证据通道。详细 SAFE 收据：`docs/evidence/R60_BASE336_COMPONENT_GRAPH_REVIEW_PACKET_SAFE_20261119_CN.md`。

- **强证据**（≥1000 连续相同字符，或完整非空且含有实质内容的 Card/Opening 字段 JSON 相同）：7 对跨 Train/Validation Story，覆盖 13 个去重 Story / 27 个去重候选案例。
- **扩展候选**（纳入 300–999 字符逐字复用）：10 对跨 Train/Validation Story，覆盖 16 个去重 Story / 35 个去重候选案例。
- 同拆分另外有 16 对精确复用候选；不等于跨拆分泄漏。
- 这是静态输入证据的机械复用**候选**，与旧第 13 节 6 对 / 22 案例的初始计数不同。以本节作为新的 Reviewer 候选范围，不将旧数字继续当作穷尽数量。
- Owner 私有 create-only Reviewer 包中保留证据的 source/version/path/哈希引用和空白 Reviewer 决策字段；公开 GitHub 不上传原始 JSON、私有包、个人身份、正文或逐案映射。
- **未授权自动重分配 split、修改冻结数据或训练。** Reviewer independent execution / actual-sent / R50 Protected-Reserved full roster / Owner freeze 继续 HOLD，P2-C 仍 HOLD，P2-B 48 条未生成。


## 15. 2026-11-19 独立 Reviewer 表单 v2 与严格证据引用校验

新增独立 Reviewer v2 执行合同：`docs/evidence/R60_BASE336_INDEPENDENT_REVIEW_SCHEMA_V2_HANDOFF_20261119_CN.md`。Owner 可下载完整的 `R60_BASE336_INDEPENDENT_EDGE_REVIEW_SCHEMA.json`、`R60_BASE336_INDEPENDENT_REVIEWER_TASKBOOK_20261119_CN.md`、更新后的 `r60_independent_reviewer_offline.py`。v2 改为 A/B 结构化证据引用（记录索引、组别、当前/归档版本、RFC6901 字段路径），`verify --inputs --packet --reviews-dir --schema` 强制从 8 份原始输入重新核验证据页及记录绑定，杜绝只用自由文本写“见证据”的错误 PASS。Owner-local 合成测试覆盖空白 HOLD、合法单项和篡改索引/正文 HOLD。旧 v1 表单不隐式升级，保留原目录，新目录 create-only。仅完成执行工具准备；无真实 Reviewer 答卷或 Owner Freeze，P2-C 继续 HOLD。


## 16. 2026-11-19 Reviewer A 内容完成，但独立资格未获认证（最新状态）

Owner 上传真实 SAFE 回执 `docs/evidence/R60_BASE336_REVIEWER_A_SAFE_V2_20261119_RUN01.json`，另附正式交付说明；脱敏解释与 Reviewer B 独立重新审查命令见 `docs/evidence/R60_BASE336_REVIEWER_A_CONTENT_COMPLETE_INDEPENDENCE_HOLD_20261119_CN.md`。

- Reviewer A 在 10 条跨拆分候选 01/02/11/14/19/21/22/24/25/26 中均填写 `SAME_SEMANTIC_COMPONENT`；`review_edges_filled=10`、`review_edges_pending=0`、`source_versions_reviewed_count=10`、`reference_binding_verified_for_filled=10`。
- `self_attested_independence_count=0`、`reviewer_independence_independently_verified=false`，所以 `status=REVIEW_INCOMPLETE_HOLD` **仍然正确**；不得将已填写误记为“未审”，也不能将非独立内容分析记为正式的独立裁决。
- Owner 报告了 33 次侧记录和 89 条非空字段引用、私有目录 20 文件/0700/0600 及验收 exit 0；这些细节属于交付说明，并未在 SAFE JSON 内独立量化，须按交付方陈述标记，不自行推断为再次核实。
- 不能将任何历史的 `independent_execution_attested=false` 事后改成 true。下一步应在 Owner 私有目录独立 `prepare` Reviewer B 的 10 份 Evidence 和 **全新空白** Decision，再由资格可核验的 B 盲审；不得带入 A 的决定、旧 Codex 或本次筛查 tier。真实双独立审查的数量仍为 0，不宣称 B 可自动纠正 A 的独立性缺陷。
- P2-C 继续 HOLD，actual-sent、R50 完整 protected metadata、旧曝光闭合、语义组件图全量核验及 Owner freeze 仍分别未完成。不得生成 P2-B 48 prompts，不得提交原始私有数据、重分配冻结 split 或开始训练。


## 17. 2026-11-19 Reviewer B 表单完成（最新）：Owner 独立资格认证仍 PENDING

Owner 提交 Reviewer B 的 SAFE 回执及交付说明。已将该回执按原始 SAFE 字段登记为 `docs/evidence/R60_BASE336_REVIEWER_B_SAFE_V2_20261119.json`；审核和后续 Owner 资格核验流程见 `docs/evidence/R60_BASE336_REVIEWER_B_OWNER_QUALIFICATION_PENDING_20261119_CN.md`。

- Reviewer B 的 10 条跨 Train/Validation 候选全部填为 `SAME_SEMANTIC_COMPONENT`，未填 0；`reference_binding_verified_for_filled=10`、`source_versions_reviewed_count=10`，`self_attested_independence_count=10`。正式 v2 校验返回 `REVIEW_FORMS_COMPLETE__OWNER_INDEPENDENCE_CHECK_PENDING`。
- **不是**独立 Reviewer 合格证明：`reviewer_independence_independently_verified=false`。B 的 AI 会话隔离、先前任务参与经历、输入材料范围与审查过程均需 Owner 单独核对。B 提及的姓名/标题别名和“title/summary”等线索必须追溯到经批准的 Card/Opening 实际来源字段；提交说明不能替代源证据。
- Reviewer A 的 10 条静态判断也是同组件，但 `self_attested_independence_count=0`，不能算作双独立一致。即使 B 通过 Owner 核验，仍最多有一位经认可的独立 Reviewer；如门禁需要双独立，需再安排真正隔离的 C。
- 所有 10 条关联及其已涉及的候选故事继续原有 HOLD，不自动修改任何冻结案例或归入训练。Owner 审查私有理由、快照和独立资格后方可使用现有世界隔离函数进行源绑定组件图冲突核验，依旧不得自动宣告全量隔离 PASS。
- `actual_sent=false`、`r50_complete_exclusion_verified=false`、`P2_C=HOLD`、`P2_B_48_PROMPTS=NOT_GENERATED`、`train_admitted=0` 不变。


## 18. 2026-11-19 非阻塞组件冲突候选预览（本索引最新）

为避免 Reviewer B 独立性资格核验阻塞其他工作，在 **不改变 B 仍待 Owner 验证** 的前提下，新增纯 Owner-local、只读、create-only 的组件冲突候选工具 \`experiments/r58_quality/r60_base336_component_conflict_preview_cpu.py\`，运行手册：\`docs/R60_BASE336_COMPONENT_CONFLICT_PREVIEW_RUNBOOK_20261119_CN.md\`。工具复用已存在的 \`storyforge_dataset.world_isolation.component_split_conflicts\`，绝不创建第二套正式隔离 PASS 实现。

以当前已上传八组 member 文件、冻结 roster、V2 packet 进行 source SHA pin / roster pin / recorded source revision 对齐和十条候选边的 union-find：

- 10 对跨 Train/Validation 候选连接成 6 个跨拆分**候选**连通分量，Story 大小为 2、2、2、2、3、5；
- 共有去重 16 个 Story、35 条候选案例需要继续隔离观察；
- Reviewer B 的 10/10 SAME 仅是 SAFE 聚合和待认证的静态语义判断；上述图是“十条边全部同组件”的**假设预览**，没有逐项回放 B 的私有 Decision，也未证明历史 actual-sent；
- 私有组件→Story/冻结案例位置映射只允许保存 Owner 0700/0600 路径，不上传 GitHub。仓库只保存 \`docs/evidence/R60_BASE336_COMPONENT_CONFLICT_PREVIEW_SAFE_20261119.json\` 及工具、合成测试与执行文档。
- 本预览之外的 22 个 Story 不能自动宣称语义隔离 PASS；不得自动修改 336 冻结 split，不能生成正式 P2-B 48 prompts 或启动训练。

Owner B 资格核验、actual-sent、R50 全量 metadata 排除、旧曝光完整覆盖、其余 Base336 世界组件，仍是各自单独的 HOLD；\`P2_C=HOLD\`、\`train_admitted=0\` 不变。下一步优先将预览在 Owner Mac 真实私有目录执行并保存 SAFE 回执，同时并行推进不依赖 B 资格的其他 metadata-only 审计。


## 19. 2026-11-19 Owner Mac 组件冲突预览运行回执已核对

Owner 在本次对话实际回传 `schema=storyforge_r60_base336_component_conflict_preview_safe_v1`、`status=BASE336_COMPONENT_CONFLICT_PREVIEW_READY__P2_C_HOLD` 的 Mac SAFE JSON。其全部聚合字段与本 PR 已保存的 `docs/evidence/R60_BASE336_COMPONENT_CONFLICT_PREVIEW_SAFE_20261119.json` 一致，登记说明为 `docs/evidence/R60_BASE336_COMPONENT_CONFLICT_PREVIEW_OWNER_RECEIPT_20261119_CN.md`。这项核对基于用户提交的运行回执；未由本助手直接读取 Owner 私有输出。

- 10 条跨拆分候选边构成 6 个候选冲突组件（Story 数 2/2/2/2/3/5）、16 个去重 Story、35 个去重候选案例；
- 预览只验证保守候选图，不读取或回放 B 的逐边私有 Decision；`reviewer_b_aggregate_checked=false` 只表示未传入可选 B SAFE，不能用来逆转 B 的既有审核结果；
- **尚未产生“35 案例已在消费入口隔离”的执行证据**，也没有自动修改冻结 roster、拆分、评估集或训练入口；
- 其余 22 个 Story 仍未获得全量语义隔离证明；actual-sent、R50 完整 protected metadata、R47/R48/R55 已曝光集合闭合和 Reviewer B Owner 资格继续分别 HOLD；
- `P2_C=HOLD`、`P2_B_48_PROMPTS=NOT_GENERATED`、`train_admitted=0` 不变。

下一项可独立推进的工作是只读验证 35 条风险候选在**预定数据消费/生成入口**不会被准入，并行继续 actual-sent 与其他 metadata-only 来源排除审计。不得在验证前把 “candidate conflict preview” 或 “建议隔离”表述成 “已实施正式隔离”。


## 20. 2026-11-19 R50 50/46/4 provenance-only 补集 SAFE 已通过（覆盖本文较早 HOLD 记载）

Owner 新回传原始 SAFE 回执已登记于 `docs/evidence/R60_P2_R50_50_46_4_PROVENANCE_COMPLEMENT_SAFE_20261119.json`，状态 `R50_PROVENANCE_50_46_4_METADATA_PASS__P2_C_HOLD`。

- 50 条原始 **provenance-only** 的历史固定大小+SHA 核对通过；46 条 derived provenance ID/原始父行序和四项来源身份字段一致，Selection 4 条排除 = Admission 4 条排除 = 原始 50 减 derived 46 的确切补集。
- P2 八条公开 Story IDs 与这 50 条 R50 provenance 来源 Story ID 的精确交集为 0；不等于语义独立。
- **本轮未打开 R50 密封内容**；没有读取原始 50 条题目 JSONL 或访问数据库。其成功依赖原始来源 metadata 的已有锁定字节哈希，而不是对密封题目重新打开做完整 frozen seal。
- **已关闭**：原 50 → 派生 46 + 排除 4 的 *provenance metadata subset* 子门禁、此 50-story-source scope 的精确 ID 不交集子门禁。本文此前在第 10 节记载的“50/46/4 complement NOT VERIFIED”现仅对**密封原始 cases 字节层面**和正式 heldout seal 仍成立；不要再误把 metadata-only 补集写为未执行。
- **未关闭**：R50 完整 Protected/Reserved World metadata roster 的**穷尽性及源/版本绑定**、语义世界别名与同组件归属、R45 全来源隔离、最终 sealed heldout 与 Reviewer/Owner 冻结。现有 `R50_FULL_ORIGINAL_WORLD_INVENTORY_PRIVATE.json` 仅有历史文件元数据与字段类型存在证据，未提供完整 5 World protected/reserved semantic coverage 的正式 SAFE；此项继续 HOLD。

主线进入下一项**仅 R50 World 元数据全集范围证明**，而非重复 46/46 或 50/46/4 元数据子集审计；可并行处理 R47/R48/R55 完整历史暴露全集闭合。Base336 全 172 来源 DB 报错期间禁止猜测性重复重抽。P2-C=HOLD、48 正式提示未生成、train_admitted=0、GPU/HF 未启动。


## 21. 2026-11-19 R50 冻结五世界来源身份等价 Owner PASS（更新第 20 节）

Owner 又回传 `R50_PINNED_FIVE_BOUND_TO_ORIGINAL50__P2_EXACT_DISJOINT__UNIVERSE_HOLD`；原样 SAFE 已归档为 `docs/evidence/R60_P2_R50_PINNED5_TO_PROVENANCE_OWNER_SAFE_20261119.json`。

复用现有 `experiments/r58_round1/check_r50_protected_uuid.py::protected_ids` 及历史两份**固定 Git Source / Admission SAFE Blob**，与 50 条仅含来源身份的已固定原始 provenance 进行 Owner 本地集合比对，核验五个受保护 Story UUID **与完整原始 50 provenance Source Story 集合严格相等**；新 8 条 P2 来源与该五世界精确交集为 0。全程未打开 R50 sealed cases/答案，不访问数据库。该证据比仅有“五世界 / 50/46/4 计数”更强，正式关闭 **R50 已知 W16–W20 五世界源身份集合绑定** 子门禁。

**不外推**：这不是其它历史 Protected/Reserved 世界名册的全集认证，也不证明隐藏世界别名/语义同源排除或实际推理时发送版本。完整 `P2_C` 仍 HOLD，不生成 48 条 P2-B 正式 prompt，不启动模型/GPU，不准入训练。后续只关注 R50 **之外** 其他 Protected/Reserved、历史其他 Dev/仲裁/训练来源权威全集、Base336 全 172 语义隔离、actual-sent 与独立 Reviewer/Owner Freeze；不再重跑五世界固定元数据检查或原 50 的 provenance 46+4 补集。
