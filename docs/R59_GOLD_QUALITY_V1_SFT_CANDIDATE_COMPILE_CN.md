# StoryForge R59 — 从 Gold Quality-v1 进入 SFT 候选编译（非训练准入）

日期：2026-11-03。主线：高质量中文互动剧情 LoRA。历史 Supabase Ledger 的精确事件回放不再是新训练候选的前置条件；历史 R59 HOLD 保留归档，不能谎称历史来源审计 PASS。

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

由 Owner 创建权限 0600 的私有 `OWNER_CASE_EVIDENCE.jsonl`。每行对应一个已暂存的 `case_id`，只填写**实际已核验**的内容；不需要为全部 192 条填写，缺少记录的候选自动 HOLD。每行字段包括：

- `case_id`, `target_sha256`, `story_id`, `session_id`：必须与 Staging 一致；
- `staged_file_sha256`：`GOLD_SOURCE_STAGING_SAFE.json` 中的 `staged_file_sha256`；
- `source_context_file_sha256`：上述 SAFE 中的 `source_context_file_sha256`；
- `source_version_sha256`：Owner 核实的冻结 Gold 来源版本 SHA256，**不能**以 Staging 文件 SHA 代替；`world_graph_sha256`、`world_component_id`：Owner 核实的世界隔离证据，不能由故事名称自动推断；
- `split`：明确为 `train` 或 `validation`，跨世界组件拆分会整体 HOLD；
- `reviewer_a_evidence_ref` / `reviewer_b_evidence_ref`：本机私有审核证据引用，引用不能为空（本工具不会凭字符串引用独立证明审核独立性）；
- `reviewer_a_severe_flags`：三个布尔字段 `serious_player_agency`、`hard_fact_or_ban`、`safety_exclusion`，来源必须是真实审核证据；不要为了 PASS 默认填 `false`；
- `evidence`：与 `quality_v1.py` 中 `EVIDENCE` 完全一致的 Owner 核实布尔字段（需明确为 `true`），另外 `known_protected_overlap`、`final_heldout_overlap`、`protected_test_body_accessed` 三项须经实际核实并明确为 `false`。不能因未知而填写通过值。

证据不足时**应省略该 case 或填写真实 False**；脚本输出 HOLD 计数，不会代填缺失的证据。

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
