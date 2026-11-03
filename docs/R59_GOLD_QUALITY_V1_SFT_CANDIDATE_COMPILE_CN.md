# StoryForge R59 — 从 Gold Quality-v1 进入 SFT 候选编译（非训练准入）

日期：2026-11-03。主线：高质量中文互动剧情 LoRA。历史 Supabase Ledger 的精确事件回放不再是新训练候选的前置条件；历史 R59 HOLD 保留归档，不能谎称历史来源审计 PASS。


## 2026-11-03 执行检查点：Owner Evidence v2

- 当前分支 HEAD：`e2d266a1966d18e407af8b34fcadf7fef871a055`。
- 同一 HEAD 的 GitHub CI、Gold Quality Pipeline（synthetic + R57 regression）、R58 scoped synthetic（no training）均已通过；这些是代码/合成回归，不是私有 Gold 数据的审核通过。
- 当前 Source Stage：72 行中 5 行可进入 Review Bind，67 行保持结构 HOLD。
- 5 行候选均已与 A/B 冻结审核结构关联；此前 SAFE 核验确认其中 3 行命中 Strict28。Owner Evidence 模板已生成 5 行，但仍为空白：`attestations_populated=0`、`quality_v1_admitted=0`。
- Owner 补充严重问题筛查现已单独归属 `owner_supplemental_safety_review`，不再伪装成 Reviewer A 的原始字段。旧模板字段不得沿用。
- PR #11 仍为 Draft；当前代码通过不代表 PR 已合并或训练已获授权。

### 当前唯一需要人工完成的步骤

使用本机最近生成、SHA256 为 Owner 本地 SAFE 回执所对应的 `OWNER_CASE_EVIDENCE_TEMPLATE_PRIVATE.jsonl`，复制为新的 `OWNER_CASE_EVIDENCE.jsonl`（保留原始空白模板），逐案核验后只填写有真实证据支持的字段。不得将模板 SHA、Staging SHA、当前 Story Draft 快照 SHA 混作原始 Gold 来源版本 SHA。

逐案检查：
1. 读取该候选的完整历史上下文和最终 Assistant 目标，判断上下文连贯、没有未来信息泄漏、隐私合规；不要静默删消息或截断后声称原上下文完整。
2. 逐项核对 Reviewer A/B 的真实私有审核材料和证据定位。只有确有盲审且相互独立的证据，才填写 `reviewers_blinded_and_independent_attested=true`；单凭两份文件或两份评分不能证明独立性。
3. Owner 单独完成 `owner_supplemental_severe_flags` 三项筛查，并引用实际证据；任一项为 true 不得进入候选，未知保持 null。
4. 核实原始 Gold 来源版本、世界图/组件身份及 Train/Validation 分配。当前 Story Draft 快照及 `updated_at` 不能单独证明目标时点的历史版本；找不到可靠原始版本时保持 null。
5. 逐项核实全部 `EVIDENCE` 字段及三项保护集负面字段。未知不能填 true/false 来消除 HOLD；保护集缺少完整清单时不得声称已证明无重叠。

只有 Owner 在本机完成以上工作后，才运行 Review Bind。SAFE 回执只返回聚合数量和原因码；不得把逐案材料、私有路径、ID、剧情或哈希发到聊天。若五条中只有部分证据完整，允许部分进入后续候选；不得为凑满五条放宽门槛。

### Owner Evidence 聚合预检（先于 Review Bind）

新增 `experiments/r58_quality/r59_owner_evidence_preflight.py`。它读取本机 Source Stage、SAFE 回执和 Owner Evidence，按候选逐条检查必需字段是否完整，只输出聚合计数及缺失字段计数，不输出 Case ID、Story ID、剧情、路径或哈希。它不读取 Reviewer 原始文件、不判断 Reviewer 独立性、不证明保护集完整性，也不执行准入。

```bash
PRIVATE="$HOME/.local/share/storyforge/r59/private"
STAGE="$PRIVATE/source-staging-priority72-20261103"
OWNER="$PRIVATE/quality-v1/OWNER_CASE_EVIDENCE_20261103.jsonl"

.venv/bin/python experiments/r58_quality/r59_owner_evidence_preflight.py \
  --staged-jsonl "$STAGE/GOLD_SOURCE_STAGING_PRIVATE.jsonl" \
  --staging-safe "$STAGE/GOLD_SOURCE_STAGING_SAFE.json" \
  --owner-evidence-jsonl "$OWNER"
```

预检显示字段齐全只代表可以进入下一步 Review Bind；不代表审核独立性、保护集完整性、Quality-v1 准入或训练授权。若字段缺失，按 SAFE 中的 `field_checks_missing` 在本机补充真实证据；不得向聊天发送私有记录。

预检支持部分候选先行：若 SAFE 状态为 `OWNER_EVIDENCE_PARTIAL_FIELDS_PRESENT__BINDER_REVIEW_REQUIRED`，并且 `rows_with_all_required_fields_present` 大于 0，可将该批次交给现有 Review Bind 做最终逐案证据关联；未完成的候选仍应由 Binder HOLD。该状态绝不是准入。若完整行数为 0，不要运行 Binder，继续补证或保留全部 HOLD。

### 2026-11-03 Owner Evidence 首次预检结果与补证顺序

本次 Owner SAFE 回执显示：5/5 候选身份匹配，Staging SHA 与 Source Context SHA 均为 5/5 匹配；其余 Owner 证据字段均为 0/5。结论是输入绑定正确、Owner 证据尚未填写，不是来源审核失败，也不是候选质量 Reject。

按以下顺序在 Owner 本机处理，逐条允许 HOLD：

1. **先做 Owner 补充安全审查**：逐条阅读实际训练输入上下文和最终目标，填写三项 `owner_supplemental_severe_flags`，并引用本机可定位的审核记录。不得用 Reviewer B 的空 flags 替代 Owner 审查，也不得把未知写成 false。
2. **再定位 Reviewer A/B 原始证据**：从冻结的 Reviewer A/B 私有结果中建立逐案 `reviewer_a_evidence_ref`、`reviewer_b_evidence_ref`。A/B 文件存在和评分结构通过，只证明记录可读取；不自动证明盲审、独立性或现实身份独立。
3. **核实原始 Gold 来源版本**：`source_version_sha256` 必须来自实际 Gold 来源版本字节或可信冻结版本记录。Source Context 文件 SHA、Staging 文件 SHA、模板 SHA、当前 Story Draft 快照 SHA 均不得代替它。
4. **核实世界图与分配**：`world_graph_sha256`、`world_component_id`、`split` 必须来自可追溯的原始世界组件及数据集划分依据。当前 Draft 的 `v2_data` / `updated_at` 只能说明被观察到的快照，不能自动证明目标样本生成时的世界版本。
5. **最后做质量、隐私及保护集检查**：11 项正向声明必须逐项有 Owner 可定位依据；`known_protected_overlap`、`final_heldout_overlap`、`protected_test_body_accessed` 必须由适当的完整元数据/访问记录支持。若保护集清单不完整，相关项保持未知，不能写 false。

已有 Evidence Inventory 只能支持此前已报告的 5 条候选精确 locator 匹配、5 条 Draft 关联和 5 条历史 exposure 文件匹配；`NOT_FOUND_IN_PINNED_HISTORY` 不等于无历史曝光。它也没有证明保护集完整性、世界组件隔离或原始 Gold 目标时点版本。

### Gold192 Story Review Packets 冻结副本核验（2026-11-03）

Owner 本机 SAFE 回执确认 `GOLD192_STORY_REVIEW_PACKETS_PRIVATE.jsonl` 可完整解析为 13 条 JSONL 记录，且与交接包内同名冻结副本字节一致（1 个副本、1 个精确匹配）。这 13 条是 Story Review Packet 层级记录，不应误解为 Gold192 的逐案数量；Gold192 候选仍由各 Packet 内的 case 记录及其身份字段确定。当前 SAFE 只证明文件完整性和冻结副本一致，不自动证明每个 Packet 内的原始来源版本、世界卡时间点或保护集状态。

同轮 Evidence Inventory：5 条 staged candidate 的 Source Locator、Story Draft 和 Historical Exposure 均精确关联；两条候选故事对应的 Draft 均标记 `CURRENT_V2_DATA_NOT_HISTORICAL`。因此 `source_version_verified=false`、`historical_snapshot_temporality_proven=false`、`world_component_isolation_proven=false`、`protected_set_completeness_proven=false`、`reviewer_independence_proven=false` 继续保持。历史 Exposure 的 `NOT_FOUND_IN_PINNED_HISTORY` 不得解释为无训练/验证/测试曝光。

下一步先对 13 条 Packet 做本机 SAFE 结构盘点：只输出每层字段名、JSON 类型、数组长度分布、case 级记录数量及与当前 5 条 staged candidate 的匹配计数；不得输出 Packet 正文、ID、逐案哈希或私有路径。确认 Packet schema 后，再实现可复用 Assembler；不得猜测字段路径或把当前 Draft 快照当作历史 Gold 来源版本。

结构盘点完成后，Packet schema 已确认：13 个 packet root 含 `cases` 列表，共 192 个 case 对象；每个 case 含 `case_id`、`target_sha256`、`history`、`current_user_text`、`target_assistant_text`；packet root 含 `world_card`、`world_card_sha256`、`world_card_source_kind`、`world_card_review_status`、`world_card_approved_for_system`、`review_protocol` 和 `review_protocol_addendum`。当前五条 staged candidate 精确匹配 5/5，分布于 2 个 packet。

新增可复用工具 `experiments/r58_quality/r59_packet_evidence_inventory.py`，测试为 `test_r59_packet_evidence_inventory.py`。工具在本机验证 Packet/Stage JSONL、文件权限、case 结构和精确 `(case_id, target_sha256)` 关联，生成两个文件：

- `R59_PACKET_EVIDENCE_ASSOCIATIONS_PRIVATE.json`：0600 私有映射，包含 packet 行号、case 数组索引、packet world-card 快照元数据和本机定位符；不得上传或发送到聊天。
- `R59_PACKET_EVIDENCE_INVENTORY_SAFE.json`：只含聚合统计、world-card 审批/来源状态分布、review protocol 标记计数及固定 HOLD 声明。

运行示例：

```bash
PRIVATE="$HOME/.local/share/storyforge/r59/private"
STAGE="$PRIVATE/source-staging-priority72-20261103"
OUT="$PRIVATE/quality-v1/packet-evidence-inventory-20261103"
mkdir -m 700 "$PRIVATE/quality-v1" 2>/dev/null || true
test ! -e "$OUT"
.venv/bin/python experiments/r58_quality/r59_packet_evidence_inventory.py \\
  --packet-jsonl "$PRIVATE/GOLD192_STORY_REVIEW_PACKETS_PRIVATE.jsonl" \\
  --staged-jsonl "$STAGE/GOLD_SOURCE_STAGING_PRIVATE.jsonl" \\
  --output-dir "$OUT"
```

此工具只生成精确定位索引，不填入 Owner 的质量、安全、权益、来源版本、world graph、split 或保护集声明。Packet 内 `world_card` 是导出快照；review protocol 明确要求不得假设它在目标生成时已可用，并区分 world-card 审批与样本质量。因此 Packet 的 `world_card_sha256` 只能作为快照定位/指纹，不能代替历史 `source_version_sha256`，也不能单独证明 `world_graph_sha256`、组件隔离或可用时间。历史上下文以 Packet 的 `history` 为审阅依据；若其首条为 assistant，必须保留并审阅，不得静默删除。


**执行策略**：先在本机识别已知属于 Strict28 的 3 条候选，优先完成这 3 条；不把候选身份发到聊天。每条证据不足就保留 null/HOLD。Owner Evidence Preflight 通过后，再运行现有 Review Bind；Review Bind 通过后才运行 SFT Candidate Compiler。当前 `quality_v1_admitted=0`、`training_authorized=false`，不得提交 HF GPU Job。

## 已交付代码

- `experiments/r58_quality/quality_v1_sft_candidates.py`：直接调用冻结的 `quality_v1.py` 校验函数，不重新实现质量六维评分，不凭空生成 Reviewer / Owner 证据。
- `experiments/r58_quality/test_quality_v1_sft_candidates.py`：只使用原创合成记录验证，通过/拒绝、Assistant-first、最后目标唯一 loss、世界隔离、重复哈希、私有文件 0600 和不可覆盖。
- 专项 GitHub Actions 自动运行 Ruff 与合成回归；不启动 HF / GPU，不读取 R50。

### 输入合同

必须是私有 `storyforge-quality-v1-private-candidate-v1` JSONL；原始 Gold、Reviewer A/B 的分数、上下文已审核声明、保护隔离核验和独立源 pin 必须从 Owner 实际证据构建。脚本不会根据 Gold192 的统计数量自动生成审核通过记录，也不会把历史 Reviewer 的 PASS 自动转换为质量准入。使用 `quality_v1.py` 的 `decide()` 及 `summarize()` 执行全体重复与跨世界隔离检查。

输入文件必须是普通文件，不是 symlink，权限为 0600；最多 195 条。建议先从有可信私有证据的 Strict28 / Gold72 候选生成输入，缺少 Evidence 的记录应保持 HOLD，不得补全虚假字段。

### 本机运行（不访问数据库）

在 Gold Quality 分支工作树、现有项目 venv 下：

```bash
PRIVATE="$HOME/.local/share/storyforge/r59/private"
INPUT="$PRIVATE/quality-v1/OWNER_REVIEWED_GOLD_CANDIDATES.jsonl"
OUT="$PRIVATE/quality-v1/sft-candidates-20261103-run1"
test -f "$INPUT"
test ! -e "$OUT"
.venv/bin/python experiments/r58_quality/quality_v1_sft_candidates.py \
  --private-reviewed-jsonl "$INPUT" --output-dir "$OUT"
```

`PRIVATE/quality-v1` 须预先由 Owner 创建为 0700 目录；产物本身不会覆盖任何已有文件，也不能写在 Git checkout 内：

- `SFT_CANDIDATES_PRIVATE.jsonl` — 当前通过结构与审核声明门禁的候选消息（含 last-assistant-only loss 标记）及内部身份字段；权限 0600。
- `SFT_CANDIDATES_SAFE.json` — 仅聚合统计与私有文件 SHA256，不含剧情、Case ID 或世界 UUID。

### 准入与训练门禁

`PRIVATE_SFT_CANDIDATES_BUILT__NOT_QUALITY_ADMITTED` **不等于** `QUALITY_V1_ADMITTED`。当前 `quality_v1_admitted=0`、`dataset_frozen=false`、`tokenizer_collator_checked=false`、`training_authorized=false`、`gpu_started=false`。必须后续逐条核实私有 Reviewer A/B 的来源独立性、上下文质量及世界隔离，生成经 Owner 核对的实际准入名单，然后冻结 Train/Validation，并在 HF CPU 做 Qwen tokenizer + ms-swift collator 的真实预检。禁用 R50 题文访问和自动 GPU 提交。

不要强制要求复现原生产 System Prompt；现有无世界卡 System Prompt 方案可以用于明确标记的训练上下文编排，但本脚本只消费已准备并校验的 `messages`，不杜撰角色世界卡，也不写入生产数据库。

## R59 Supabase → Review 输入桥接

新增 `experiments/r58_quality/gold_source_context_stage.py`，用于将 Owner 现存的 `R59_SOURCE_CONTEXT_PRIVATE.jsonl` 转成私有的 Source Review Staging 包。它**不是**完整的 `quality_v1.py` 输入：特意将世界组件、Train/Validation、Reviewer 证据、source version pin 标记为未核实，不会伪造这些字段。它只帮助省去从现有 Supabase 提取文本再次人工粘贴到新审核格式的步骤。

必须使用以前已经批准的**通用无世界卡 System Prompt** 原始文件，单独提供真实 SHA256 pin；脚本会校验文件内容与 pin，绝不自动构造世界卡或宣称该 Prompt 是历史生产时的 Prompt。

```bash
PRIVATE="$HOME/.local/share/storyforge/r59/private"
SOURCE="/ABSOLUTE/PRIVATE/R59_SOURCE_CONTEXT_PRIVATE.jsonl"
SYSTEM="/ABSOLUTE/PRIVATE/APPROVED_GENERIC_SYSTEM_PROMPT.txt"
SYSTEM_SHA256="$(shasum -a 256 "$SYSTEM" | awk '{print $1}')"
OUT="$PRIVATE/source-staging-run1"
test ! -e "$OUT"
.venv/bin/python experiments/r58_quality/gold_source_context_stage.py \
  --source-context-jsonl "$SOURCE" \
  --system-prompt-file "$SYSTEM" \
  --system-sha256 "$SYSTEM_SHA256" \
  --output-dir "$OUT"
```

**注意：** 上面的 `SOURCE` 和 `SYSTEM` 是占位路径，不应在文件不存在时盲目运行。两份输入都必须是权限 0600 的私有非符号链接普通文件，输出父目录须是 0700 且位于 Git checkout 外。审核工作流的后续步骤必须基于真实的 Reviewer A/B 记录，单独绑定世界语义 ID、权益与隐私证据。不能把 `GOLD_SOURCE_STAGING_PRIVATE.jsonl` 直接改名为 `OWNER_REVIEWED_GOLD_CANDIDATES.jsonl`。

Source Staging SAFE 不会回显 Story/Case ID 或任何正文；含原始文件 SHA256、System SHA256、结构 HOLD 统计、已成功暂存数量。对于交替角色不合规、非 completed 或末条非 User 的上下文，保留私有 HOLD 而不是静默删除或修复。此桥接只做数据工程，不执行 HF CPU 预检，也不执行 GPU 训练。


## R59 Owner 本机 Reviewer A/B 证据绑定（新增）

新增 `experiments/r58_quality/gold_quality_review_bind.py`，把 Source Staging 与**冻结 SHA256** 的原始 Reviewer A、Reviewer B 和 11 条排除记录对齐，再消费 Owner 逐案提供的证据，不访问 Supabase、R50 或 HF。

重要：过去 A 的 192 条结果中部分 `PASS_ONLY` 为**集合级推断且没有逐案六维评分**；这些记录一律保持 HOLD。只有 A 真实的 `scores_1_to_5`/逐案评分、B 的 `scores_1_to_5` 均可核实并且明确通过，才可能进入候选。冻结源 SHA 来自既有 `r59_gold192_supabase_extract.py`：A `641b71e10a14318b57e69cb0239172f7016fe5b9d2149923f876308f5e6fe1e4`、B `bdd1980eacf9e21c08fb3e5ada482ea476f35c2018c6120e0f708718eda666e8`、11 条排除 `9ca99432e08b680cb67b5a1f89d172a337cb91c9bd02af70b68356938c6c04ed`。使用原始字节文件，不能通过重排 JSON 字段来重新构造 pin。若本机 A 文档使用其他版本或上游记录格式变化，先确认其来源，不要伪造适配。

### Owner 证据输入合同

由 Owner 创建权限 0600 的私有 `OWNER_CASE_EVIDENCE.jsonl`。可使用新增的 `experiments/r58_quality/r59_owner_evidence_template.py` 从 Staging + SAFE 自动生成空白身份模板，避免手工抄写 Case/Story/Session 对应关系。该工具只复制逐案身份与 Staging pin，所有 Owner 声明、来源版本、世界信息、Reviewer 引用和严重问题标记均为 `null`；输出状态严格为 `OWNER_EVIDENCE_TEMPLATE_CREATED__NOT_EVIDENCE`，**绝不构成证据或准入**。每行只填写**实际已核验**的内容；缺少记录的候选自动 HOLD。每行字段包括：

- `case_id`, `target_sha256`, `story_id`, `session_id`：必须与 Staging 一致；
- `staged_file_sha256`：`GOLD_SOURCE_STAGING_SAFE.json` 中的 `staged_file_sha256`；
- `source_context_file_sha256`：上述 SAFE 中的 `source_context_file_sha256`；
- `source_version_sha256`：Owner 核实的冻结 Gold 来源版本 SHA256，**不能**以 Staging 文件 SHA 代替；`world_graph_sha256`、`world_component_id`：Owner 核实的世界隔离证据，不能由故事名称自动推断；
- `split`：明确为 `train` 或 `validation`，跨世界组件拆分会整体 HOLD；
- `reviewer_a_evidence_ref` / `reviewer_b_evidence_ref`：本机私有审核证据引用，引用不能为空（本工具不会凭字符串引用独立证明审核独立性）；

- `owner_supplemental_severe_flags` 与 `owner_supplemental_severe_evidence_ref`：Reviewer A 冻结结果中没有逐案严重问题字段时，Owner 可基于可访问的原始逐案审核材料另行完成补充严重问题筛查。该记录明确归属于 Owner，不得写成 Reviewer A 的结论；三项标记为 `serious_player_agency`、`hard_fact_or_ban`、`safety_exclusion`。必须提供真实私有证据引用；证据不足时保留 `null`，候选继续 HOLD。
- Source Stage 的 `SOURCE_STRUCTURE_HOLD` 行不是 Reviewer 候选。Review Bind 应单独统计 `source_stage_held` / `source_stage_hold_reasons`，不得将这些行误报为 Owner Evidence 身份缺失。只有 `SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING` 的有效 Staging 行进入 Reviewer / Owner 绑定。
- `owner_supplemental_severe_flags`：三个布尔字段 `serious_player_agency`、`hard_fact_or_ban`、`safety_exclusion`，必须有对应的 `owner_supplemental_severe_evidence_ref`。这是单独的 Owner 补充筛查，不回填 Reviewer A 原始审核；不要为了 PASS 默认填 `false`；
- `evidence`：与 `quality_v1.py` 中 `EVIDENCE` 完全一致的 Owner 核实布尔字段（需明确为 `true`），另外 `known_protected_overlap`、`final_heldout_overlap`、`protected_test_body_accessed` 三项须经实际核实并明确为 `false`。不能因未知而填写通过值。

证据不足时**应省略该 case 或填写真实 False**；脚本输出 HOLD 计数，不会代填缺失的证据。
Quality-v1 候选中的 `reviews[reviewer_a].severe_flags` 保留为 `null`（当冻结 A 记录没有该字段时）；Owner 的补充筛查单独写入 `owner_supplemental_safety_review`，含 `scope=SUPPLEMENTAL_SEVERE_FLAG_SCREEN`、`decision`、`severe_flags` 与独立的私有证据引用。Quality-v1 只在这份 Owner 补充筛查完整且全部为 `false` 时允许缺失 A 严重标记的记录继续评估；任何 `true` 均拒绝，未知或缺证据仍 HOLD。这样不会把 Owner 判断冒充为 Reviewer A 的判断。


### 生成空白 Owner Evidence 模板（可复用）

在确认 `$REVIEW_DIR` 已是权限 0700 的私有目录后执行；`OUT` 必须是此前不存在的新目录：

```bash
PRIVATE="$HOME/.local/share/storyforge/r59/private"
STAGE_DIR="$PRIVATE/source-staging-priority72-20261103"
REVIEW_DIR="$PRIVATE/quality-v1"
OUT="$REVIEW_DIR/owner-evidence-template-run2"

test "$(stat -f '%Lp' "$REVIEW_DIR")" = 700
test ! -e "$OUT"
.venv/bin/python experiments/r58_quality/r59_owner_evidence_template.py \
  --staged-jsonl "$STAGE_DIR/GOLD_SOURCE_STAGING_PRIVATE.jsonl" \
  --staging-safe "$STAGE_DIR/GOLD_SOURCE_STAGING_SAFE.json" \
  --output-dir "$OUT"
```

将 `--owner-evidence-jsonl` 指向输出的 `OWNER_CASE_EVIDENCE_TEMPLATE_PRIVATE.jsonl` 即可直接运行 Binder，不必复制或改名。Owner 只能在本机私有文件中把 `null` 改成已核验的真实值；未知项继续保持 `null` 或不填写。严禁把模板 SAFE 的状态解释成 Owner Evidence 已完成。

### 本机运行顺序

```bash
cd ~/workspace/storyforge-gold-quality
git fetch origin gold-quality/quality-v1-sft-candidates
git switch gold-quality/quality-v1-sft-candidates
git merge --ff-only origin/gold-quality/quality-v1-sft-candidates

PRIVATE="$HOME/.local/share/storyforge/r59/private"
STAGE_DIR="$PRIVATE/source-staging-run1"
REVIEW_DIR="$PRIVATE/quality-v1"
OWNER="$REVIEW_DIR/OWNER_CASE_EVIDENCE.jsonl"
A="/ABSOLUTE/PRIVATE/R59_REVIEWER_A_192_PRIVATE.json"
B="/ABSOLUTE/PRIVATE/R58_GOLD192_REVIEWER_B_BLIND_20261102.json"
EX="/ABSOLUTE/PRIVATE/QUALITY_V1_EXCLUDED_CASES.jsonl"
OUT="$REVIEW_DIR/review-bind-run1"

test -f "$STAGE_DIR/GOLD_SOURCE_STAGING_PRIVATE.jsonl"
test -f "$STAGE_DIR/GOLD_SOURCE_STAGING_SAFE.json"
test -f "$OWNER"
test -f "$A" && test -f "$B" && test -f "$EX"
test ! -e "$OUT"
.venv/bin/python experiments/r58_quality/gold_quality_review_bind.py \
  --staged-jsonl "$STAGE_DIR/GOLD_SOURCE_STAGING_PRIVATE.jsonl" \
  --staging-safe "$STAGE_DIR/GOLD_SOURCE_STAGING_SAFE.json" \
  --reviewer-a "$A" --reviewer-b "$B" --exclusions "$EX" \
  --owner-evidence-jsonl "$OWNER" --output-dir "$OUT"
```

示例 A/B/EX 路径均为**占位符**，需以 Owner 本机的真实冻结文件取代，不要把内容或本机绝对路径传到聊天。所有输入必须为非符号链接普通文件、0600 权限，输出父目录必须为 0700 且位于 Git checkout 外。

新输出：`OWNER_REVIEWED_GOLD_CANDIDATES.jsonl`（私有，0600）、`GOLD_REVIEW_BIND_SAFE.json`（只含聚合统计、原因码与候选文件 SHA，不含故事文本）。若 `review_bound_candidates > 0`，把第一个文件传给 `quality_v1_sft_candidates.py` 编译；输入为零时不要启动下游。

**安全界限：** 即使全部字段一致，仍只是 `REVIEW_EVIDENCE_BOUND__CANDIDATES_NOT_ADMITTED`，不代表 Owner 证据已被独立证明。正式 Quality-v1 仍为 0，尚需真实性核实、冻结划分、HF CPU Token/Collator 预检和单独 GPU 授权。严格禁止合成 CI 生成的样本冒充真实训练数据。

## R59 可复用证据库存与精确关联审计器

新增 `experiments/r58_quality/r59_evidence_inventory.py`，将 R59 近期临时诊断沉淀为可重复运行的 Owner 本机工具。它只读取已导出的私有 JSONL，不访问 Supabase、R50、HF 或网络；只输出 SAFE 聚合结果，不输出 Case/Story/Message ID、正文或逐案哈希。

功能边界：

- 只按固定 staging schema + `SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING` 识别候选；HOLD 行不计入候选。
- Source Locator 与 Historical Exposure 必须同时精确匹配 `case_id + target_sha256`；重复配对直接 HOLD。
- Story Draft 按 `story_id` 关联，分别统计候选故事数、草稿记录数、每故事多版本情况及 `updated_at` 覆盖。
- 仅检查 `world/components/character/characters/director/opening/visual` 的存在性和 JSON 类型，不读取或输出设定正文，不宣称时间点有效或世界隔离通过。
- 汇总 Story Draft 的 `source_label`；若标记为 `CURRENT_V2_DATA_NOT_HISTORICAL`，SAFE 明确记录当前快照数量，并将历史时点有效性、来源版本验证保持为 false。`updated_at` 和本地 SHA256 指纹均不能单独证明历史版本。
- 原样统计 Exposure status 与布尔字段；明确 `exposure_not_found_is_proof_of_non_exposure=false`。
- 所有输入要求普通文件、非 symlink、0600；SAFE 输出 create-only、0600，父目录 0700，且输出路径必须位于仓库外。

本工具不生成或填充 `OWNER_CASE_EVIDENCE.jsonl`，不替 Owner 认定来源版本、世界组件、Reviewer 独立性、保护集完整性或准入。它是 Inventory/Audit 工具，不是 Binder 或 Admission 工具。

### 本机运行

在项目 venv 和 PR 分支工作树中：

```bash
PRIVATE="$HOME/.local/share/storyforge/r59/private"
STAGE="$PRIVATE/source-staging-priority72-20261103"
REVIEW="$PRIVATE/quality-v1"
LOCATORS="/ABSOLUTE/PRIVATE/R59_SOURCE_LOCATORS_192.jsonl"
DRAFTS="/ABSOLUTE/PRIVATE/R59_STORY_DRAFTS_PRIVATE.jsonl"
EXPOSURE="/ABSOLUTE/PRIVATE/R59_GOLD192_HISTORICAL_EXPOSURE_PRIVATE.jsonl"
OUT="$REVIEW/evidence-inventory-run1"
test ! -e "$OUT"
mkdir -m 700 "$OUT"
.venv/bin/python experiments/r58_quality/r59_evidence_inventory.py \
  --staged-jsonl "$STAGE/GOLD_SOURCE_STAGING_PRIVATE.jsonl" \
  --source-locators-jsonl "$LOCATORS" \
  --story-drafts-jsonl "$DRAFTS" \
  --historical-exposure-jsonl "$EXPOSURE" \
  --output-safe "$OUT/R59_EVIDENCE_INVENTORY_SAFE.json"
```

输入文件必须先由 Owner 确认所选副本一致；工具不自动挑选不同版本的副本。此工具的 SAFE 结果仍不是 Owner Evidence、Quality-v1 准入或训练授权。

工具已登记在 `storyforge-gold-quality inventory` 的 registered_tools 中。合并前可在本机项目 venv 执行合成测试；GitHub Actions 支持手动触发：

```bash
gh workflow run gold-quality-pipeline.yml --ref gold-quality/quality-v1-sft-candidates
```
