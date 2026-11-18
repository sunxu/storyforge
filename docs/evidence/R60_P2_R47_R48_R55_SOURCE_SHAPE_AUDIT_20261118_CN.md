# R60 Base336 P2：R47 / R48 / R55 历史暴露来源形态审计（2026-11-18）

## 1. 审计范围与结论

本记录基于 Owner 2026-11-18 提供的本机审计输出，以及仓库中 R47 / R48 / R55 对应的校验器和盲化构建代码。目标是确认历史暴露材料的可见结构和来源映射证据边界，不读取或复述历史故事、回复、答案密钥或逐案 Reviewer 内容。

本次本机检查：
- R47 / R48：解析 JSON / JSONL，仅输出文件元数据、Schema、顶层字段、数组计数和元素字段名；没有输出样本 ID、Prompt SHA、目标 SHA 或正文值。
- R55：仅列举文件名、字节数和权限；没有打开三个私有 Coordinator Index、SAFE 回执或 intake 文件。
- SAFE：database_accessed=false、database_modified=false、gpu_started=false、private_values_emitted=false；没有 HF Job 或模型请求提交。

**结论更新：R47 Manifest 本身不含 Story ID，但仓库代码中存在可审计的 Sample → canonical Test row → `metadata.story_id` 绑定路径；R55 第一层 Coordinator Index 也保存 `source_sample_id_private`，第二 / 第三层索引通过原始 candidate token 延续来源链。故此前“没有映射路径”的表述过强。当前尚未对 Owner 本机 R47 文件、P2 私有 Manifest、R55 三个私有 Index 和 SAFE 回执执行同一轮 Owner-local 只输出聚合值的 crosswalk；R55 旧 R47 source preflight SAFE 的内容也未读取。因此，**代码路径已找到，但实际精确交叉结果仍 UNKNOWN / HOLD**；语义变体排除仍为 HOLD。

## 2. R47：可验证的 Sample / Prompt 身份，不是 Story 身份

Owner 本机审计观察到：

| 文件 | 存在 / 大小 / 权限 | 已核验结构 |
|---|---|---|
| R47 私有 Run Report | 存在，2,259 bytes，0600 | 无顶层 schema；状态 R47_THREE_MODEL_REGRESSION_GENERATION_PASS_NOT_PROMOTED；含 run key、三臂完成状态、输入与结果哈希等字段 |
| R47 私有 Audit Summary | 存在，770 bytes，0600 | 无顶层 schema；状态 R47_BLIND_EXPORT_PASS_NOT_FRESH_HELDOUT；记录 20 samples、60 responses、blind / key / prompt / manifest 哈希及非晋升边界 |
| R47 Test Manifest | 存在，3,503 bytes，0644 | Schema storyforge-blind-v1；20 条；每条元素字段为 sample_id、prompt_sha256、source_line |
| R47 canonical compiled Test | 存在，1,113,896 bytes，0644 | 20 个 JSONL 记录；顶层字段为 id、messages、metadata |
| R47 frozen prompts | 存在，1,038,838 bytes，0644 | 20 个 JSONL 记录；顶层字段仅为 messages |

### 2.1 代码合同能证明什么

- v02_r47_collect_validate.py 校验冻结 Prompt / Manifest 的哈希、20 个 Sample ID、三臂 60 条回复、blind rows 与 reviewer sheets 的 Sample ID / 回复排列一致，以及私有映射与回复一致。
- v02_r48_four_arm_build.py 要求 canonical compiled Test 文件 SHA 固定，并逐案核对原始对话在最后 Assistant 回复之前的完整 role/content 前缀与 R47 prompt 一致；Gold 回复取自该记录的最后 Assistant turn。
- 这些检查能证明 R47 / R48 共用同一组 20 个冻结 Prompt 上下文，且 R48 Gold 与 canonical compiled Test 的固定字节版本绑定。

### 2.2 不能据此声称什么

- R47 Manifest 的 sample_id、prompt_sha256、source_line 不包含 Story ID 字段。
- compiled Test 的 id 字段虽然存在，但本次审计没有读取或输出其值；现有 R48 构建器以行顺序和消息前缀配对 Prompt，没有建立 compiled_test.id ↔ manifest.sample_id ↔ story_id 的显式、逐案、可审计绑定。
- Prompt JSONL 本身只有 messages 字段，没有独立身份字段。
- R47 Report / Audit Summary 是批次级摘要；R48 Source Audit 虽记录 canonical Test 文件 SHA、20 个 Gold target SHA、20/80 数量、旧 Test 暴露标记及冻结 R47 run key，但不包含可见的逐案 Story ID 映射。

因此，不能把 Sample ID、`source_line`、JSONL 行序或 compiled Test 的通用 `id` 字段直接当作 Story ID。**但可按已存在的校验代码构造严格的复合绑定**：`sample_id` → Manifest 的 `source_line` / `prompt_sha256` → canonical Test 对应行的完整 role/content prompt prefix → 该行 `metadata.story_id`。`scripts/prepare_blind_eval.py` 生成确定性的 Sample ID；`scripts/audit_v01_integrity.py` 的 `test_alignment_audit()` 逐案验证 source row / prompt / manifest 的前缀、哈希和 source_line；其 `dataset_audit()` 验证 Test 记录具有 `metadata.story_id`；`scripts/v02_r48_four_arm_build.py` 再固定 canonical Test SHA 并逐案核对完整 prompt prefix。该路径不依赖把 `id` 字段猜成 Story ID。实际 R47 / P2 本机文件仍须由 Owner-local SAFE 复核后，才能计算 P2 × R47/R48 的精确 overlap。

## 3. R48：同一 20 案例的四臂历史比较，不增加独立案例数

Owner 本机审计观察到 R48 Source Audit：
- 文件存在，2,947 bytes，权限 0600；
- 没有顶层 schema 字段；
- 状态 R48_GOLD_PLUS_THREE_MODEL_20_80_BLIND_PACK_PASS_NO_PROMOTION；
- 顶层记录 sample_count、reply_count、frozen_r47_run_key、source_compiled_test_sha256、20 项 original_gold_target_sha256、reviewer / blind / private key 哈希，以及 old_test_exposed=true、无 GPU / 新推理 / 训练 / 模型晋升等标记。

R48 的 80 条回复由同一 20 个旧 Prompt 的 Gold / Base / v0.1 / v0.2 四臂构成。它是 R47 历史 20 案例的扩展比较，不是新增 20 个案例，更不是新的 Held-out。R47 的 20 与 R48 的 20 必须按同一历史暴露集合合并去重，不能相加为 40 个独立样本。

R48 的 20 个 Gold target hash 能绑定逐案目标内容摘要，但不能替代 Story ID / Source ID 来源映射，也不能证明 Gold 本身绝对正确。

## 4. R55：发现私有来源索引文件，但尚未做内容 / Schema 验证

本轮只读文件系统 inventory 列出以下相关文件：

| 文件（相对 R55 根目录） | 大小 | 权限 | 本轮验证范围 |
|---|---:|---:|---|
| exposed20/sources/R55_OLD_R47_SOURCE_PREFLIGHT_SAFE.json | 969 bytes | 0644 | 仅文件元数据；未读取 SAFE 内容 |
| gold5-dev20/event-arbitration-v1/coordinator/R55_GOLD5_ARBITRATION_SOURCE_INDEX_PRIVATE.json | 327,678 bytes | 0600 | 仅文件元数据；未读取内容 |
| gold5-dev20/event-evidence-second-v1/coordinator/R55_GOLD5_SECOND_AUDIT_INDEX_PRIVATE.json | 34,017 bytes | 0600 | 仅文件元数据；未读取内容 |
| gold5-dev20/event-evidence-third-v1/coordinator/R55_GOLD5_THIRD_AUDIT_INDEX_PRIVATE.json | 30,942 bytes | 0600 | 仅文件元数据；未读取内容 |
| inference-results/r55-dev-20261022T023436Z-188604/R55_R54_20_OWNER_INTAKE_SAFE.json | 899 bytes | 0644 | 仅文件元数据；未读取 SAFE 内容 |

同一 inventory 还列出 preflight 脚本、测试及 Python cache；它们是代码 / 运行环境文件，不是逐案来源清单。

仓库代码进一步明确了 R55 三层索引的可验证连接：
- `scripts/v03_r55_gold5_event_arbitration.py` 第一层 Index 的每条 record 保存 `source_sample_id_private`、`case_index_private`、`source_arm_private`、`response_sha256`；其来源 `sample_id` 来自经 `v03_r55_gold5_owner_unblind.py::validate_key()` 校验的 20-case Coordinator Key，且该函数要求 Key 的 sample_id 与冻结 reviewer case IDs 按序一致。
- `scripts/v03_r55_gold5_second_evidence_audit.py` 第二层 Index 保存 `original_candidate_token_private`，可回连第一层 candidate token，并核对 case token、source arm 和 response hash。
- `scripts/v03_r55_gold5_third_evidence_audit.py` 第三层 Index 同时保存 `original_second_candidate_token_private` 与 `original_first_candidate_token_private`，可回连第二层和第一层。

因此，R55 的设计提供了 `R55 candidate → R47 sample_id` 的私有链路；再与上节 R47 `sample_id → metadata.story_id` 的绑定组合，可以计算 P2 × R55 的精确 Story ID overlap。**但必须先核验 Owner 本机三个 Index 的真实 Schema、token 链、第一层 20-case 覆盖、SAFE receipt 哈希绑定，以及 `R55_OLD_R47_SOURCE_PREFLIGHT_SAFE.json` 对 R55 原始 20-case 与 R47 来源的证明。**本轮只确认文件元数据，没有读取 Index / SAFE 内容，故尚不能宣称实际映射通过或覆盖完整。

文件存在和 0600 权限是必要的私有证据管理信号，不是内容完整性、Schema 有效性、历史来源身份或保护集覆盖 PASS。R55 仍为 UNKNOWN / HOLD。

## 5. P2 精确身份交叉结果与本轮未覆盖项

此前 Owner SAFE 已确认：
- P2 新来源：8 个来源、8 个唯一 Story ID。
- P2 × Base336：336 cases / 172 unique Story IDs；exact_story_id_overlap=0，exact_source_id_disjoint=true。
- P2 × R50：exact_source_id_disjoint=true；R50 原始正文未打开。

上述结果只关闭各自 SAFE 明确覆盖范围内的精确身份比较，不覆盖 R47 / R48 / R55。当前状态应按下表分别记录：

| 保护范围 | 精确身份结果 | 语义 / 覆盖结果 |
|---|---|---|
| R50 | 既有 SAFE：精确 Source ID 不相交 | R50 完整 Protected / Reserved 覆盖与语义排除仍按既有证据索引保持独立门禁；未读取正文 |
| Base336 | 既有 SAFE：336 cases / 172 stories，Story ID overlap 0 | 8 组 World 语义裁决仍 HOLD；成员级 current / archived card/opening 与 actual-sent 仍未验证 |
| R47 | 仓库代码存在 Sample → canonical Test `metadata.story_id` 绑定路径；Owner-local 联合 SAFE 尚未执行 | 精确 P2 overlap 仍 UNKNOWN / HOLD，等待对 R47 Manifest / prompts / canonical Test 与 P2 Manifest 的只读复核；语义变体 HOLD |
| R48 | 固定同一 canonical Test SHA、20 prompts / 80 replies，复用 R47 同一 20-case 集 | 不增加独立案例；精确 overlap 继承 R47 映射结果，仍待 Owner-local SAFE；语义变体 HOLD |
| R55 | 第一层 Index 保存 source_sample_id；第二 / 第三层有可回连的 candidate token 链；本轮仅核验文件元数据 | 代码路径存在；实际 Schema、20-case 覆盖、receipt 绑定、旧 R47 preflight 证明及 P2 overlap 仍 UNKNOWN / HOLD；语义变体 HOLD |

**不得将 P2 × Base336 / R50 的精确 ID 不相交结果扩展到 R47/R48/R55。** 同样不得将 JSON / SHA 不同、不同 Sample ID、不同文件名或不同文件大小视为语义独立证明。

## 6. 下一步最小动作

1. Owner-local 对 R47 Manifest、frozen prompts、canonical compiled Test、R48 Source Audit、P2 private source manifest 执行同一只读 SAFE：验证 canonical Test SHA、20 条逐案 prompt prefix / prompt hash / source_line 绑定、`metadata.story_id` 完整性，并只输出 P2 × R47/R48 的 exact Story ID overlap count。
2. 对 R55 三个私有 Coordinator Index 执行只输出字段名 / 数量 / 布尔值的结构审计：第一层 76 records、20 个唯一 sample IDs / case indices 覆盖（以真实 SAFE 为准），第二层与第一层 token 回连，第三层与第二层 / 第一层双重回连；逐层核验对应 SAFE receipt 中的 index SHA 绑定。
3. 读取并审查 `preflight-package/scripts/r55_dev_source_preflight.py`、其测试及 `R55_OLD_R47_SOURCE_PREFLIGHT_SAFE.json`，确认该 preflight 是否真实证明 R55 原始 20-case IDs 对应 R47 冻结 Manifest。只报告 SAFE 聚合计数，不输出 ID / SHA / 正文。
4. 将 R55 第一层 `source_sample_id_private` 通过已验证的 R47 Sample → `metadata.story_id` 链映射到 P2 的 8 个 `story_id`，只输出 overlap / disjoint 计数。若任何 receipt、覆盖或绑定缺失，继续 UNKNOWN / HOLD。
5. 在精确身份与覆盖完整性确认后，再由 source-bound 证据开展语义变体排除；缺少 actual-sent 版本时仍为 UNKNOWN / HOLD。

本记录不授权读取 R50 正文、R47/R48/R55 私有答案或逐案评分，不授权数据库访问、数据修改、HF Job、模型请求、GPU、训练、正式提示包生成或模型晋升。

## 7. 当前 SAFE 边界

    database_accessed = false
    database_modified = false
    gpu_started = false
    hf_jobs_submitted = 0
    model_requests = 0
    private_values_emitted = false
    train_admitted = 0
    quality_v1_admitted = 0
    model_promoted = false
    P2_A = READY
    P2_BASE336_EXACT_ID = PASS
    P2_R50_EXACT_SOURCE_ID = PASS
    P2_R47_R48_R55_CODE_DEFINED_CROSSWALK = FOUND_NOT_EXECUTED
    P2_R47_R48_R55_EXACT_STORY_ID = UNKNOWN_HOLD
    P2_SEMANTIC_ISOLATION = HOLD
    P2_B_48_PROMPTS = NOT_GENERATED
    P2_C = HOLD


## 8. Owner Mac R55 三个 SAFE Prep 回执的文件元数据补充（2026-11-18）

Owner 回报以下文件均存在，且文件权限均为 0600（本次仅确认文件大小和权限，**未打开文件内容**）：

| SAFE 回执 | 大小 | 权限 | 本轮证据 |
|---|---:|---|---|
| R55_GOLD5_ARBITRATION_PREP_SAFE_COUNT_ONLY.json | 1,292 bytes | 0600 | PRESENT_METADATA_ONLY |
| R55_GOLD5_SECOND_AUDIT_PREP_SAFE_COUNT_ONLY.json | 1,598 bytes | 0600 | PRESENT_METADATA_ONLY |
| R55_GOLD5_THIRD_AUDIT_PREP_SAFE_COUNT_ONLY.json | 1,498 bytes | 0600 | PRESENT_METADATA_ONLY |

该 inventory 关闭了三个准备回执的**存在性未知**，但不等于已验证 SHA 绑定或记录完整性。实际 Schema / status、与三个 Coordinator 私有 Index 的内容 SHA256 比较、各 Index 内部 candidate-token 链、第一层 20 个历史案例覆盖以及 R55 旧 R47 来源关联，均未核验。

下一步应在 Owner Mac **只读**检查以下匹配关系（仅输出布尔值 / 聚合计数）：

1. 第一层 Prep 的 coordinator_index_sha256 对应第一层 Index 文件 SHA256。
2. 第二层 Prep 的 private_coordinator_index_sha256 对应第二层 Index 文件 SHA256。
3. 第三层 Prep 的 private_mapping_sha256 对应第三层 Index 文件 SHA256。
4. 三个 Index 的 schema、records 数量与本轮对应代码合同相符，第一层的 source_sample_id_private 可安全合并到 20-case historical source set；验证第二 / 第三层的 original candidate token 回连覆盖。
5. R47 Sample → canonical Test metadata.story_id 复合绑定仍需独立 SAFE；只有实际验证后才能计算 P2 × R47/R48/R55 的精确 overlap。

当前 P2_R47_R48_R55_EXACT_STORY_ID = UNKNOWN_HOLD，P2_SEMANTIC_ISOLATION = HOLD，P2_C = HOLD。不得据这些回执的文件大小或权限宣布 PASS。


## 9. Owner 本机 R55 三层索引与 Prep Receipt 实际 SAFE 核验（2026-11-18）

Owner 返回 `r60_r55_three_index_link_safe_v1`，状态为 **`R55_THREE_INDEX_LINK_AND_RECEIPT_PASS__P2_C_HOLD`**。此处为实际文件验证结果，不再仅为文件元数据：

| 阶段 | records | Schema 有效 | Prep 回执 Index SHA 匹配 | Candidate tokens 唯一 |
|---|---:|---|---|---|
| Arbitration | 76 | true | true | true |
| Second Audit | 68 | true | true | true |
| Third Audit | 46 | true | true | true |

第一层源身份检查：有效 source IDs=true；20 个 unique source samples、20 个 unique case indices；R47 冻结 Manifest 样本覆盖 20/20；extra=0，missing=0；case indices valid=true。

第二层：68 条全部回连第一层，`source_token_links_valid=true`。

第三层：`second_token_links_valid=true`、`first_token_links_valid=true`、`chain_consistent=true`。该 SAFE 实际核验了索引结构、三个回执的对应 SHA 和三层候选 token 链，**不需再重复执行这三项既有检查**。

非操作状态：database_accessed=false、database_modified=false、r50_opened=false、gpu_started=false、hf_jobs_submitted=0、model_requests=0、private_values_emitted=false。

**严格证据边界：** 这证明 R55 三层索引及 Prep 回执完整性，以及第一层对 R47 Manifest 的 20 个 Sample ID 的覆盖；不单独证明 R47 这些 Sample ID 与 canonical `metadata.story_id` 的复合绑定已执行，也不证明 P2 × R47/R48/R55 exact Story ID overlap=0。不代替 R55 旧 R47 source preflight 的其他可能约束；语义世界、actual-sent 和 Reviewer 独立性仍独立 HOLD。

下一最小动作：复用 `scripts/audit_v01_integrity.py::test_alignment_audit` 的样本绑定规则，只读验证冻结 canonical Test SHA / 20-row Prompt / Manifest / R48 Source Audit / P2 private Manifest，然后仅输出 P2 × R47/R48 exact Story ID overlap count。R55 第一层已有 20/20 的 Sample ID 覆盖，取得成功的 R47 Story ID 绑定后可据此继承这一批历史案例的精确身份集合，但不自动认定全部历史开发暴露范围已经覆盖。


## 10. Owner-local P2 × R47/R48/R55 精确 Story ID crosswalk SAFE（2026-11-18）

Owner 返回 `r60_p2_r47_r48_r55_exact_story_crosswalk_safe_v1`，状态：**`P2_R47_R48_EXACT_STORY_ID_DISJOINT__R55_BOUND_TO_R47_20__P2_C_HOLD`**。

实际 SAFE 结果：

| 检查 | 结果 |
|---|---:|
| Canonical Test 固定 SHA | true |
| R47 Prompt / Manifest 绑定 | true |
| R47 Sample → canonical Test → `metadata.story_id` 绑定 | true |
| R47 样本数 | 20 |
| R47 唯一 Story ID 数 | **2** |
| R48 canonical source SHA 绑定 | true |
| P2 来源 / 唯一 Story ID | 8 / 8 |
| P2 × R47/R48 exact Story ID overlap | **0** |
| R55 第一层对 R47 Manifest 覆盖（此前 SAFE） | 20/20 |

据已验证的 R55 三层 token 链（76 → 68 → 46）和第一层 20/20 Sample 覆盖，R55 三层索引所代表的这批派生记录可沿 `candidate token → source_sample_id_private → R47 sample_id → canonical Test metadata.story_id` 映射到同一 20-case 来源集合。因此，在**本次已验证的 R47/R48/R55 20-case 链**范围内，P2 与历史 Story ID 精确不相交；不得将此结论扩展为完整历史 exposure universe 的排除证明。

### 10.1 重要统计限制：20 samples 只有 2 个 Story IDs

R47 20 个 Prompt / Sample 仅对应 **2 个唯一 Story ID**。因此：
- 20 是 prompt/case 数，不是 20 个独立故事；
- R48 是同一批案例的四臂回顾性评估，不增加独立故事数；
- R55 的 76/68/46 是三层派生审计记录数，不是独立故事数，也不能当作独立样本量；
- 任何未来质量比较必须按 Story 聚类 / 分层解释，不得把同一 Story 下多个 Prompt 当成独立故事来夸大有效样本量或泛化能力。

这不改变精确 ID overlap=0 的事实，但显著限制这批历史材料对跨故事泛化质量的证明力。

### 10.2 门禁更新与保留项

本轮关闭：P2 × R47/R48 的 20-case exact Story ID overlap；通过已验证 R55 三层索引与该 20-case 的传递性来源映射，关闭同一链范围内的 P2 × R55 exact Story ID overlap。

仍然 HOLD：
- R47/R48/R55 的完整历史暴露 universe 是否已穷尽；旧 R47 source preflight 的附加约束尚未复核。
- 语义近似 / 隐藏 World alias / 同一 World 组件变体排除。
- actual-sent / delivered prompt 版本、时间点和上下文绑定。
- Base336 8 组 World 语义裁决及成员级 current/archived card/opening 证据。
- R50 完整 Protected / Reserved metadata roster 的覆盖完整性（R50 正文继续禁止访问）。
- Reviewer 独立性与 Owner freeze。

本轮 SAFE 边界：database_accessed=false、database_modified=false、r50_opened=false、gpu_started=false、hf_jobs_submitted=0、model_requests=0、private_values_emitted=false。

状态应精确记录为：
```
P2_R47_R48_R55_20_CASE_EXACT_STORY_ID = PASS_OVERLAP_0
P2_R47_R48_R55_FULL_EXPOSURE_CLOSURE = UNKNOWN_HOLD
R47_UNIQUE_STORY_COUNT = 2_OF_20_PROMPTS
P2_SEMANTIC_ISOLATION = HOLD
P2_C = HOLD
P2_B_48_PROMPTS = NOT_GENERATED
```

下一步不再重复 R47/R48/R55 精确 ID crosswalk，也不重跑 R55 Index SHA / token 链。转向最小化的**语义与完整性缺口盘点**：先只读审查旧 R47 source preflight SAFE / 脚本 / 测试的合同；并分别确认 Base336 card/opening 已有文件的真实 Schema / 覆盖缺口、R50 metadata-only roster 是否完整、actual-sent 证据是否存在。任何缺失仍 HOLD，不启动 GPU/HF、不读取 R50 正文、不生成真实 P2-B 提示包。
