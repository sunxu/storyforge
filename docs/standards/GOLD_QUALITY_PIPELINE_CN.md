# StoryForge Gold Quality Pipeline

## Purpose

One private append-only event Manifest for frozen source pins, legacy review evidence, historical exposure, incremental blind reviews, exclusions and adjudication. The CLI is an audit orchestrator, not a reviewer or training-admission shortcut.

Keep exact-target exposure, UUID exposure and semantic world-component isolation separate. Keep Gold87 selection evidence separate from its row metadata; keep Gold108 legacy five-dimension review separate from Quality-v1. Preserve Reviewer A/B disagreement as distinct events.

## Install and commands

```bash
python -m pip install -e .
storyforge-gold-quality inventory
storyforge-gold-quality verify-source --repo-root "$PWD"
```

Supported commands: `inventory`, `verify-source`, `import-history`, `import-exposure`, `append-review`, `append-exclusion`, `validate`, `report-safe`.

The private Manifest must live outside the Git checkout in a directory with mode 0700; the file is created with mode 0600. Writes are append-only and use no-follow file opening. Same-case target hash changes fail closed.

## Import contracts

- Gold87: one batch-level `LEGACY_SELECTION_EVIDENCE` event (87 cases, selection recorded, reviewer independence unproven) plus 87 row-level `SOURCE_METADATA` events (`independent_gold_review=NOT_RUN`, single Curator scores).
- Gold108: first run the existing `gold108_review_binding.py` and require its exact SAFE PASS status. Import 108 row-level `LEGACY_REVIEW` events and one batch-level binding receipt. Keep rubric `FIVE_DIMENSION_LEGACY`; `new_quality_v1=false`.
- Gold195 exposure: safe aggregate imports remain aggregate-only and set case-level exposure to `UNKNOWN_NOT_IMPORTED`. Row-level import requires the original R57 private ledger and the SAFE receipt from the same run proving source byte pins. No aggregate-to-row synthesis.
- Gold192: A/B/AI/adjudication events remain separate. The three unresolved-world exclusions are separate `EXCLUSION` events. Each review row carries six 1–5 scores and a reviewer role.

## Privacy and non-authorization

SAFE output contains counts only; never emit case IDs, story UUIDs, prose, alias maps or row-level target hashes. Quality-v1 admission remains zero; training, GPU and R50 access remain false. Tokenizer preflight continues to reuse only `src/storyforge_dataset/token_preflight.py`.

## 只读适配器：实际执行合同

统一入口现在提供 `run-check` 子命令，**只允许三个不需要私人文件路径参数的 SAFE 检查**：

| --check | 复用源码 | 只输出 |
| --- | --- | --- |
| `gold87-legacy-index` | `gold87_legacy_index_audit.py` | 已验证行数与身份数量 |
| `gold108-legacy-binding` | `gold108_review_binding.py` | 旧双审索引与证据绑定数量 |
| `gold195-target-source` | `gold195_target_source.py` | 目标结构验证数量 |

```bash
storyforge-gold-quality inventory
storyforge-gold-quality verify-source --repo-root "$PWD"
storyforge-gold-quality run-check --check gold108-legacy-binding --repo-root "$PWD"
storyforge-gold-quality run-check --check gold195-target-source --repo-root "$PWD"
```

执行器使用固定的源码相对路径和固定参数，校验脚本不为 symlink 且仍位于该 Git checkout，限定执行时间、CLI 返回状态、Schema、状态字符串和整数计数。任何失败均 HOLD；既有脚本的 stdout/stderr 原文**不会直接透传**到统一输出。

其余注册的 R57/R58 工具目前只是 *inventory 元数据*，不等于已接入可执行入口。涉及私人路径、逐案文本、审核写入、模型 Tokenizer 或冻结操作的工具，必须先定义显式输入与 SAFE 输出合同并单独增加回归测试；不能通过自由拼接任意命令运行。Tokenizer / Chat Template 预检只允许使用既有共享核心，并且真实模型特定工作只在 HF CPU 执行。

### SAFE 输出边界

- 已知批次仅输出 `gold87`、`gold108`、`gold192`、`gold195`；其他批次聚合为 `OTHER_PRIVATE_BATCHES`。
- 未知 decision / evidence_tier 标签聚合为 `OTHER`，不得把任意标签直接当作 JSON key 输出。
- SAFE 聚合不包含逐案 case_id、story UUID、target hash、原文、模型输出或自由文本。
- Gold87 Index `ACCEPT` 仍只是历史登记，不等于逐案独立审核；Gold108 五维双审与 Quality-v1 六维双审不得混为一谈。
- 目前没有任何私有数据导入，也没有使 Quality-v1 admission 非零。

### 测试与兼容

专用 `.github/workflows/gold-quality-pipeline.yml` 校验新代码 Ruff、冻结 Git Blob pin、统一 CLI 合成测试、SAFE 适配器合成测试与 R57 回归测试。全仓历史 Ruff 失败单独报告，不篡改不相关旧源码。

## Reviewer B 唯一有效版本（2026-11-02）

当前 Owner 指定的 Reviewer B 原始结果通过 SHA-256 固定为：

- 文件：`R58_GOLD192_REVIEWER_B_RESULTS_20261102(3).json`
- SHA-256：`bdd1980eacf9e21c08fb3e5ada482ea476f35c2018c6120e0f708718eda666e8`
- Schema / 状态：`r58_gold192_reviewer_b_results_v1` / `REVIEW_COMPLETE`
- 192 条；PASS 178、HOLD 12、REJECT 2；192 个 blind ID、target SHA 均唯一。

只在 Owner 私有环境运行：

```bash
storyforge-gold-quality import-reviewer-b \
  --input /private/path/R58_GOLD192_REVIEWER_B_RESULTS_20261102.json \
  --manifest /private/path/gold-quality-events.jsonl \
  --repo-root "$PWD"

storyforge-gold-quality reconcile-gold192 \
  --manifest /private/path/gold-quality-events.jsonl
```

导入器仅接受上述精确 SHA、Schema、状态、192 条数量、决策计数、唯一 blind ID / target SHA、完整六维分数、severe_flags 和 evidence_summary。原始 evidence_summary 只写入权限受限的私有 Manifest；SAFE 导入回执不输出逐案 ID、目标哈希、分数或文本。相同来源重复运行是幂等的；部分导入会 HOLD。

Reviewer A 与 B 的 blind ID 属于各自 reviewer 的局部编号，**不得假设相同**。统一仲裁按 target SHA-256 配对。所有缺少当前 canonical source SHA 的旧 Reviewer B 事件被标记为 superseded/unpinned 并排除在当前分歧计算之外；旧事件不会覆盖新版，也不会被解释成当前审核结论。

新版文件的 12 HOLD、2 REJECT 均原样保留。任何历史 REJECT 仍需仲裁；Reviewer B 的 PASS 不会清除 Reviewer A 的 REJECT，也不直接产生 Quality-v1 准入。RB-0001 的年龄字段冲突属于额外 Owner 核对项，不因其 PASS 自动关闭。

此流程只导入和核对审核证据；不验证角色卡在目标时点的生效版本，不完成世界身份/别名语义核验，不完成 Reviewer 独立性认证，不执行训练授权。

## R59 Quality-v1 SFT 数据工程主线（2026-11-03）

原生产 Provider 请求精确回放、Supabase Ledger 完整事件重建已经从新 LoRA 研发的前置门禁移除，旧 HOLD 仍保留且不能视为通过。为避免重新从生产数据库抄录正文，本 Pipeline 提供两个已注册的私有本机适配器；这里只做工具登记，不允许 `run-check` 在没有私人路径输入合同的情况下执行：

1. `r59.gold-source-stage`：使用 Owner 已导出的 `R59_SOURCE_CONTEXT_PRIVATE.jsonl`，搭配 SHA256 固定的 Owner 通用无卡 System Prompt。检查原始消息角色、完成状态与目标 SHA256，将上下文暂存为私有 `GOLD_SOURCE_STAGING_PRIVATE.jsonl`。世界组件、Review A/B、保护集证据均保持空缺，不能自动补 PASS。
2. `r59.sft-candidates`：只接收 Owner 私有审核过的 `storyforge-quality-v1-private-candidate-v1` JSONL，复用 `quality_v1.py` 的原六维门槛、完整批次重复和世界隔离检查；仅为结构 PASS 的样本编译 last-assistant-only loss，生成私有候选 + SAFE 汇总，永远标记候选非准入。

具体入口、权限、冻结限制和 SAFE 合同见 `docs/R59_GOLD_QUALITY_V1_SFT_CANDIDATE_COMPILE_CN.md`。现阶段不自动导出真正的 TRAIN / VALIDATION 冻结集；Reviewer 独立性、语义世界组件、来源证据和历史消息结构的 Owner 核对未完成时，`quality_v1_admitted=0`。实际 Qwen Tokenizer/Collator 仍只能在 HF CPU 使用共享预检工具；GPU 一律需要独立授权。


## Batch-level review reconciliation receipts

The shared core accepts aggregate review-comparison receipts through
storyforge-gold-quality import-review-reconciliation. The first allowlisted
adapter is reviewer-a-b2-gold72, which imports the Owner-local output of
experiments/r58_quality/r60_reviewer_ab2_gold72_crosswalk.py.

~~~bash
storyforge-gold-quality import-review-reconciliation \
  --batch gold72 \
  --kind reviewer-a-b2-gold72 \
  --input "$CROSSWALK_SAFE" \
  --manifest "$OWNER_PRIVATE_MANIFEST" \
  --repo-root "$PWD"

storyforge-gold-quality report-safe --manifest "$OWNER_PRIVATE_MANIFEST"
~~~

Contract:

- The experiment adapter remains responsible for revalidating frozen Gold72
  staging, staging SAFE, Owner Evidence, canonical Reviewer A V3, B2 inputs,
  execution receipt and B2 audit SAFE, including exact target-identity joins.
- The shared core imports only the resulting aggregate SAFE. It does not
  duplicate the crosswalk algorithm, read case-level review rows, or generate
  synthetic case events.
- The receipt must have the exact allowlisted schema/status, 72-case totals,
  consistent A evidence-granularity / B2 decision / pair counts, six complete
  score-comparison dimensions, valid source SHA256 pins, and non-admission flags.
- The input SAFE must be outside the checkout, a regular non-symlink file with
  mode 0600, in a private parent directory with mode 0700. The append-only
  Manifest remains outside the checkout with its existing 0700/0600 contract.
- Exactly one canonical REVIEW_RECONCILIATION event is accepted for this
  batch/type. Reimporting the same receipt SHA is idempotent; a different
  receipt for the already-pinned canonical batch fails closed. Corrections
  require a separately reviewed migration/versioning decision, not overwrite.
- The private Manifest stores the receipt SHA and source pins for provenance.
  report-safe emits only aggregate counts and comparison metrics; it never
  emits source pins, receipt digests, case IDs, target hashes or review text.
- A/B2 agreement is evidence comparison only. Reviewer A independent dual
  review remains false; B2 execution attestation remains self-reported;
  cryptographic independence and B2 independence verification remain false.
  quality_v1_admitted=0, training_authorized=false, gpu_started=false,
  and r50_accessed=false are mandatory.

Synthetic coverage lives in tests/test_gold_quality_review_reconciliation.py.
The importer does not invoke the Owner-local crosswalk and does not access
production DB, private story text, HF, GPU or R50.

## R60 HF 文学双审可复用公共工具（2026-11-08）

统一 Quality Pipeline 已登记 `quality.hf-literary`、`quality.hf-blind-stage`，并新增只读子命令：

~~~bash
storyforge-gold-quality hf-review-inspect \
  --input /OWNER_PRIVATE/input_A/source.private.jsonl \
  --output-dir /OWNER_PRIVATE/output_A \
  --model Qwen/Qwen3-32B --revision <EXACT_40_HEX_COMMIT>
~~~

公共源代码在 `src/storyforge_gold_quality/hf_literary_review.py`、`hf_blind_stage.py`。两者共享已存在的六维门槛和三项严重标记语义、严格连续引用、私有分发、模型 revision 绑定和逐案不可覆盖 HF checkpoint；HF CPU Tokenizer 始终调用唯一核心 `src/storyforge_dataset/token_preflight.py`，仅在 HF CPU 执行模型特定 Tokenizer/Chat Template 预检。新 R60 适配器为 `experiments/r58_quality/r60_hf_quality_adapter.py`，只处理已经冻结的 1000 条来源验真及 `prepare/audit/export`；**不在 R60 自己开发新的模型推理或 Quality Manifest**。

HF 工作器由 Owner Mac 仅准备私有 A/B 输入及 Owner-only crosswalk；模型推理和数据上传必须另行批准，绝不可因工具可用而自动启动。`audit` 必须先核实两个 Reviewer 的 checkpoint SHA、模型、精确原文引用与来源匹配；`export` 仅在 1000×2 条审核完整后生成 A/B 私有 `append-review` 合同文件。随后以原有 `storyforge-gold-quality append-review --event-type BLIND_REVIEW` 分别导入现存唯一正式的私有 Manifest，保留 A/B 各自完整事件，不合并成单个无来源判决。`report-safe` 仅聚合，不公开个案。

这是**新批次公共 Card-independent 路线**；Gold195 R58 冻结旧 Reviewer 仍用于审查其历史旧批次，不能为 R60 虚构 `card_snapshot_suitable_for_offline_training=true`。PASS 仍只证明局部可见历史质量判断，R50/world/历史 System/CPU Collator/GPU 训练独立门槛不被改变。

完整命令、Hugging Face namespace `adradar`、独立 RO/RW volume、模型 pin、CPU/GPU 授权及 SAFE 验收见 `docs/R60_HF_QUALITY_PIPELINE_REUSABLE_1000_CN.md`。

## R60 Common2 包装通用System的HF CPU工程门禁（2026-11-12；尚未执行真实新Job）

此门禁是与Gold Quality Manifest相邻的**训练技术证据**，不是新的文学Reviewer或批次数据导入器。Common2质量双审PASS2是冻结旧证据；R27/R52冻结449字节通用System只作为`EXPLICIT_NEW_TRAINING_WRAPPER`独立新输入版本的建议，不得声称源历史真实发送Prompt有System。Owner已真实验收内存包装PASS2/2，原未加System的CPU2 PASS不得冒称本次新版输入Token/Collator PASS。

完整业务细节见[Wrapped HF CPU Quality Pipeline运行手册](../R60_COMMON2_WRAPPED_HF_CPU_QUALITY_PIPELINE_20261112_CN.md)；只读输入/唯一输出、doctor、共享Token核心和Runtime、失败停机及回执边界以`skills/storyforge-hf-jobs/SKILL.md`与`skills/storyforge-roleplay-sft/SKILL.md`为准。新增脚本只处理本批的System包装、私有Stage、真实R18/Swift Collator、聚合SAFE验收；**不增加Gold Pipeline的自由可执行命令、不自动append-review或import独立Quality-v1事件、不更改`quality_v1_admitted=0`与`train_admitted=0`。** 后续新批次应复用公共Stage/Guard/回执层，但按来源Schema实现独立薄适配器，且每批均有独立质量、语义隔离和发布裁决。

## 2026-11-12 REAL1000双Reviewer协议与Quality Pipeline复用

本段记录**模型HTTP协议兼容层**，不是新的文学质量Rubric或Quality-v1自动准入入口。冻结1000池Owner已通过`EXPANSION_TARGET_REACHED__NOT_ADMITTED`(seed6+994)。Common2 HF CPU包装System真实Collator与原始SAFE Receipt独立2/2 PASS，但与文学质量审核分轨。

唯一实现层次：
1. `experiments/r58_quality/r60_reviewer_transport.py`：纯函数`require_profile/build_body`，统一维护请求协议，严禁复制评分、tokenizer或私有回执算法。已登记`openai-chat`（旧默认）、`claude-proxy-top-system`（历史Claude 4Router要求顶层system且不支持强制json_object）、`deepseek-chat`（标准OpenAI消息system，避免套用Qwen Thinking参数）。
2. `r60_real_ai_dual_review.py`：复用原Quality-v1六维评分、三个严重布尔标记、schema校验和私有请求通道；只在`model_request`以显式`protocol`调用上述纯协议层，防止任何外部原文或不可信模型输出作为代码指令。
3. `r60_real_quality_batch.py`：两个独立`--protocol-a/b`固定到create-only私有Batch Config，每案对**相同**target/history作A/B独立请求并独占落盘；历史已初始化配置缺失protocol时兼容`openai-chat`，绝不覆盖原始回执、改变审阅者或混入旧批。
4. `r60_reviewer_protocol_probe.py`：默认无网络，`--execute`只发送固定合成3消息，至少分别取得每个服务端的一次实际JSON schema验证SAFE，先排除Claude代理顶层system差异、DeepSeek JSON成功率问题，再允许任何真实私有样本外发。其SAFE不输出prompt、HTTP响应、API Key、Endpoint URL或私有路径。
5. 质量/语义门禁不变：六维最低`4/4/3/4/4/4`；只有Owner确实确认模型独立性才能标记`owner_attested_independent_ai=true`，否则双模型均PASS仍HOLD。现有`reason_cn`字段不强制精确引用，不能用“JSON通过”宣称三维严重标记语义证据或世界设定隔离已验证。严重问题或无法确定的世界事实须按Rubric v2.1另行保留HOLD并进行证据级复核，不能直接由此产出`POSITIVE_GOLD_OWNER_APPROVED`。

2026-11-11历史DeepSeek QD20：官方`deepseek-flash`有效16/20、阿里云百炼`qwen3.7-flash`有效18/20，配对完整14/20；与Claude+Codex的双PASS候选中3条争议随后独立复核PASS0/HOLD2/REJECT1，不足以指定正式最优Reviewer。Owner本轮授权当前真实1000 Quality Reviewer的全部私有数据外发，远端HTTPS仍需`--allow-remote-review`作为审计标记；不自动授权全量1000运行、GPU或SFT。

对应执行Runbook：`docs/R60_REAL1000_PILOT5_START_20261112_CN.md`第8节。两个模型合成协议远程SAFE全部PASS后，才允许运行一次真实同源5案`advance --max-cases 5`；随后对严重标记的实际证据进行复核和统计，再决定25条扩批。可复用Skill为`skills/storyforge-real-quality-review/SKILL.md`。以上状态仅是代码/文档交付，真实远端合成API探针与5条批量SAFE未实际取得，不得标PASS。

### 2026-11-12 公开HTTP错误状态保留策略

通用请求层只输出固定允许的`MODEL_HTTP_400_HOLD`/`401`/`403`/`404`/`408`/`413`/`429`/`500`/`502`/`503`/`504`，其他HTTP/网络故障保持`MODEL_TRANSPORT_HOLD`。这些错误码同时由`r60_real_quality_batch.py`逐案回执重放验证器和合成API探针SAFE使用，禁止回显 HTTP URL、Error Body、Header、密钥或原文。400用于定位协议/字段被拒，401/403用于认证与权限，429用于限流，不是质量REJECT。网络失败也不得被统计为真实HOLD内容质量，应区分`model_attempt_hold_counts`与`quality_decisions`。

### 双模型同时不可用的不可覆盖回执保护

当两个Reviewer均返回传输HOLD或以上固定HTTP错误、**没有一份有效审核**时，`advance`返回`BOTH_REVIEW_MODELS_UNAVAILABLE`并在本案例写盘前停止，保留上次完整checkpoint序列可恢复。避免把429/500工程故障固化为永久文学质量HOLD。仅一个模型失败时仍逐案保存部分审核与真实错误码（决策HOLD），不自动二次请求、不补造评分；后续纠错必须独立版本化，不能覆盖已有文件。合成测试覆盖两429无回执、单429可重放。

### 2026-11-12 Reviewer密钥与DeepSeek历史协议

新REAL1000双审A/B密钥变量分别固定`R60_CLAUDE_KEY` / `R60_DEEPSEEK_KEY`，不使用旧的R60_REVIEW_A/B_KEY。历史QD20源码`r60_real1000_qwen_deepseek20_live.py`的DeepSeek默认`https://api.deepseek.com` + `deepseek-flash`、历史密钥变量`DEEPSEEK_API_KEY`，请求显式`temperature=0`及`thinking={"type":"disabled"}`；旧QD20执行器不修改。合成协议探针当前可用性才是新一轮实际请求的依据。

### 合成探针JSON结构分阶段诊断（2026-11-13）

当前首轮远端SAFE：Claude 4Router `REVIEWER_PROTOCOL_HOLD / MODEL_JSON_INVALID`，DeepSeek官方 `REVIEWER_SYNTHETIC_API_PASS__NO_PRIVATE`。**DeepSeek已经通过，不再重复请求。** 为避免对真实1000池进行不必要重试，`model_request(..., diagnose_json=True)`仅供合成probe显式执行1次；固定SAFE细分：`MODEL_ENVELOPE_JSON_INVALID`（HTTP 200响应体非JSON）、`MODEL_CONTENT_MISSING_OR_NONSTRING`（OpenAI choices[0].message.content缺失或非字符串）、`MODEL_CONTENT_JSON_INVALID`（message.content不是可解析JSON）、`MODEL_REVIEW_SCHEMA_INVALID`（已解析模型对象字段/类型不符合冻结六维合同）。诊断只处理结构，不输出响应、原文、URL、模型内部推理、密钥或私有路径。正式批量审核仍使用原通用`MODEL_JSON_INVALID`，评分/严重标志门槛一律不降级。Claude无私有内容探针复核取得更细错误码后再讨论最小协议修复；真实5案继续HOLD。
