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
