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

Owner 于 2026-11-18 已返回 R47/R48/R55 的本机 metadata / shape inventory。该输出确认 R47 Report、Audit、20-row Manifest、20-row compiled Test、20-row prompts、R48 Source Audit，以及 R55 若干私有 Coordinator Index / SAFE 文件存在；但 R47/R48 可见结构没有经验证的 Story ID 映射，R55 私有 Index 本轮只核验文件元数据、未读取 Schema / 内容 / 覆盖范围。故完整 source / exposure manifests 与同批次 SAFE 仍未完成内容及覆盖验证。状态仍为：**UNKNOWN / HOLD**。详见 [R47/R48/R55 Source Shape Audit](../evidence/R60_P2_R47_R48_R55_SOURCE_SHAPE_AUDIT_20261118_CN.md)。

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
| R47/R48/R55 暴露及语义变体排除 | PARTIAL METADATA / UNKNOWN / HOLD | 已收到文件形态 inventory；R47/R48 无已验证 Story ID 映射；R55 私有 Index 内容 / Schema / 覆盖未核验，完整暴露清单仍缺 |
| Reviewer 独立性 / Owner freeze | HOLD | 尚无完整独立审阅和冻结回执 |
| P2-B 真实 48 条提示包 | NOT_GENERATED | 只有校验器与合成测试 |
| P2-C 总门禁 | **HOLD** | 保护集交叉覆盖不完整 |

## 8. 下一步最小执行顺序

1. Owner Mac 的 metadata inventory 已收到，但只完成文件形态确认：R47/R48 的 20-case Prompt / Sample 文件与 Audit 存在；R55 三个私有 Coordinator Index 及两个 SAFE 文件存在。下一步不再重复目录盘点，而是对 R55 私有 Index 做只输出 Schema / 字段名 / 计数 / 版本绑定的结构检查，并寻找真实的 Sample → Story ID 来源映射；Base336 / R50 的其他缺件仍按本索引各节处理。**文件存在不等于内容、Schema、完整性或保护集覆盖通过。**
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

当前专项提示词：`docs/R60_BASE336_P2_CROSSWALK_NEXT_AGENT_PROMPT_20261118_CN.md`。该提示词包含 Owner-local metadata inventory 命令、禁止重跑的全量 `--execute` 说明、各阶段门禁和交付物格式。新 Agent 必须先完成实时 GitHub 核验，再等待 Owner 提供 inventory；不得绕过第一阶段直接设计适配器或执行数据库提取。


## 11. 2026-11-18 Owner R47 / R48 / R55 metadata / shape audit 增量

Owner 已返回本机审计输出，详见 [R60_P2_R47_R48_R55_SOURCE_SHAPE_AUDIT_20261118_CN.md](../evidence/R60_P2_R47_R48_R55_SOURCE_SHAPE_AUDIT_20261118_CN.md)。

关键更新：

- **R47**：20 条 Manifest 元素仅含 sample_id、prompt_sha256、source_line；20 条 compiled Test 记录有 id/messages/metadata；20 条 Prompt 记录只有 messages。现有校验器保证 Sample / Prompt / 回复包内部一致，但未建立经验证的 sample_id ↔ compiled_test.id ↔ story_id 绑定。
- **R48**：20-case / 80-response 四臂包复用同一 R47 历史 Prompt；固定 canonical Test SHA 和 Gold target hashes 证明文件 / 目标摘要绑定，不提供可见 Story ID crosswalk。R48 不增加独立案例数。
- **R55**：三个 0600 私有 Coordinator Index、一个旧 R47 source preflight SAFE 和一个 R54/R55 intake SAFE 的文件元数据已确认；本轮未读取其内容，因此不能确认当前 Schema、版本一致性、完整 20-case 覆盖或 Story ID 映射。
- **精确隔离**：此前 P2 × Base336 的 336 cases / 172 Story IDs overlap=0，以及 P2 × R50 的 exact Source ID disjoint PASS 保持各自范围；这些结果不能外推到 R47/R48/R55。
- **门禁**：P2 × R47/R48/R55 exact Story ID crosswalk = UNKNOWN / HOLD；semantic variants = HOLD；P2-C 总门禁继续 HOLD。

下一步：Owner-local 只读核验 R55 Index 的真实 Schema / 覆盖，并查找 Sample → Story ID 的权威来源绑定；没有真实绑定就继续 HOLD，不得按行序或字段名推断。
