# R60 Base336 P2：R47 / R48 / R55 历史暴露来源形态审计（2026-11-18）

## 1. 审计范围与结论

本记录基于 Owner 2026-11-18 提供的本机审计输出，以及仓库中 R47 / R48 / R55 对应的校验器和盲化构建代码。目标是确认历史暴露材料的可见结构和来源映射证据边界，不读取或复述历史故事、回复、答案密钥或逐案 Reviewer 内容。

本次本机检查：
- R47 / R48：解析 JSON / JSONL，仅输出文件元数据、Schema、顶层字段、数组计数和元素字段名；没有输出样本 ID、Prompt SHA、目标 SHA 或正文值。
- R55：仅列举文件名、字节数和权限；没有打开三个私有 Coordinator Index、SAFE 回执或 intake 文件。
- SAFE：database_accessed=false、database_modified=false、gpu_started=false、private_values_emitted=false；没有 HF Job 或模型请求提交。

**结论：R47 / R48 的 20 个旧测试案例可在 Prompt / Sample 层面交叉追溯，但当前可见 Manifest / Audit Schema 不提供经验证的 Story ID 映射。R55 已发现私有来源索引文件，但本轮只核验文件存在、大小和权限，未验证其实际 Schema、内容完整性、版本绑定或 20 案例覆盖。因此，P2 × R47/R48/R55 的精确 Story 身份排除仍为 UNKNOWN / HOLD；语义变体排除仍为 HOLD。**

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

因此，不能把 Sample ID、source line、JSONL 行序或 compiled Test 的通用 id 字段直接当作 Story ID，也不能仅凭 canonical Test SHA 反推出 P2 的 8 个来源是否曾出现在历史案例中。

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

仓库中的 scripts/v03_r55_gold5_event_arbitration.py 代码合同包含 Coordinator 私有索引字段，例如 source_sample_id_private、source_arm_private、response_sha256 和 case 索引。这只能说明代码设计预期存在 Sample 级回溯字段；本轮没有读取 Owner 本机索引文件，不能确认该文件实际符合当前代码 Schema、与 R47/R48 的版本绑定一致、覆盖全部 20 案例或覆盖全部 R55 暴露轮次。

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
| R47 | 当前公开审计结构没有 Story ID 映射 | 精确 P2 Story ID crosswalk UNKNOWN / HOLD；语义变体 HOLD |
| R48 | 绑定 R47 的同一 20 个旧 Prompt / Gold source bytes，但无可见 Story ID 映射 | 精确 P2 Story ID crosswalk UNKNOWN / HOLD；语义变体 HOLD |
| R55 | 本地发现三个私有 Coordinator Index，但本轮未读内容或 Schema | 精确身份及覆盖完整性 UNKNOWN / HOLD；语义变体 HOLD |

**不得将 P2 × Base336 / R50 的精确 ID 不相交结果扩展到 R47/R48/R55。** 同样不得将 JSON / SHA 不同、不同 Sample ID、不同文件名或不同文件大小视为语义独立证明。

## 6. 下一步最小动作

1. 在 Owner Mac 对三个 R55 私有 Coordinator Index 做只输出 schema、顶层字段、数组数量、元素字段名、版本 / receipt 绑定布尔值的只读结构审计；不输出任何 Sample ID、Story ID、作者映射、正文、逐案引文或哈希值。
2. 验证 R55 Index 是否完整引用同一冻结 R47 Sample Manifest 的 20 个 Sample ID，以及各轮暴露来源是否覆盖完整；只报告匹配数量、缺失数量、重复数量和版本一致性。
3. 单独寻找并验证 compiled_test.id、R47 sample_id 与 canonical 原始 Story ID 之间的真实来源绑定材料。不得用行序、source_line 或猜测字段语义拼接身份。
4. 若没有可验证的 Sample → Story 映射，P2 × R47/R48/R55 精确身份门禁继续 HOLD；不得把 R55 Sample 级索引当作 Story 级映射。
5. 在精确身份与覆盖完整性确认后，再由 source-bound 证据开展语义变体排除；缺少实际发送版本 / actual-sent 证据时仍为 UNKNOWN / HOLD。

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
    P2_R47_R48_R55_EXACT_STORY_ID = UNKNOWN_HOLD
    P2_SEMANTIC_ISOLATION = HOLD
    P2_B_48_PROMPTS = NOT_GENERATED
    P2_C = HOLD
