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
