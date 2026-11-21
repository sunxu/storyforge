## 2026-11-21 Gold48 最新最小主线（覆盖过时 Provider / 签名 / 探针说明）

现有 `scripts/r60_gold48_gpu_cli.py` 已接通 Mac `ready`（只读远端文件 SHA、代码 SHA、完整 HF Job 历史排重、输出前缀为空、dry-run）与 `submit --execute`（必须另行明确批准真实 GPU 费用）。提交前使用现有 `OutputManager.write_safe` 生成 0600 Mac 私有一次性标记，超时/未知绝不重投。5 RO+1 RW，已取消动态 Provider 挂载和 Owner Ed25519；新 `r60_gold48_gpu_worker.sh` 直接复用历史成功的 hash-locked pip 安装和现有 Worker，不造 Runner/数据库。仍需 Owner 用 `approve-one-arm` 准备对应唯一 Run ID 的 12 份输入 Stage、上传当前 Git HEAD 的精确代码文件，之后再执行 `ready`。**当前正式 Worker 一次生成单臂 48 条，不是 1 条 Smoke；没有真实 GPU 费用授权时不调用 submit。** 完整命令及先决条件见 `docs/R60_GOLD48_OWNER_LOCAL_RUNBOOK_20261121_CN.md` 顶部。历史 HF CPU 验收不重做，冻结数据不变，真实 GPU Job/192 条输出未执行。

## 2026-11-21 最新 Owner 决策：取消 Gold48 GPU 的 Ed25519 强制签名

**正式生效**：单 Owner Mac 已明确取消为每臂 GPU 生成签发 Ed25519 私钥签名、登记公钥及其指纹的要求。新主线走 `scripts/r60_gold48_owner_generation_authority_cpu.py --mode approve-one-arm --explicit-owner-generation-authorization --approval-output <private-file>`，直接**复用原先的单臂 Scope/48 条/依赖镜像 SHA/有效期校验**，由 `OutputManager.write_safe` 创建不可覆盖的 0600 私有 JSON 批准文件。无私钥、无公钥：Gold48 Job 固定 RO Stage 只携带 `owner_authorization.private.json`，不需要 `owner_public.pem`。旧 `sign-one-arm` 和 Ed25519 验签可用于历史回执兼容，不再是生产前置条件；旧文档里要求注册公钥或阻塞在 Owner Pin 的描述以本节为准。

**保留边界**：唯一可信 Mac、HF Token 权限、显式执行参数、完整组织 Job 历史排重、Mac 本地 create-only 提交标记、不自动重投、唯一 Run ID、冻结 48 输入 SHA/四臂 Profile、Adapter RO+完整权重哈希、锁文件/镜像 Digest 约束、Job 本地一次性许可、结果与 Sidecar SHA，以及 Mac 独立 HF Inspect（在评测准入前）。**没有密码学验签，不能把此 JSON 当作不可伪造的签名**；Mac/HF Token 被盗的风险已由 Owner 选择接受。新回执的 `owner_authorization_method=OWNER_MAC_EXPLICIT`、`owner_ed25519_signature_verified=false`、`runtime_image_identity_source=OWNER_MAC_APPROVED_CONFIGURATION_ONLY__NOT_MEASURED` 明确说明这一边界。此前 Provider 动态证明也已撤除，不恢复。

**GPU 未获本条消息的执行授权**：更改签名门禁本身不代表允许提交 HF GPU Job、签发本次 Run ID 或进行真实模型调用。先完成代码/合成 CI，再沿用已跑通的 Mac HF CLI，针对具体镜像/角色/经 Owner 选定的 Run ID 另行显式授权 GPU Smoke；四臂共 192 新回答与 48 历史原始回答组成 240 对象质量评估，冻结输入不变。不新建数据库、通用 Runner、Provider 服务或其他签名系统。

## 最新决策（2026-11-21）：取消 Provider 动态交接，复用历史 HF Jobs 调用链

Owner 已明确选用单一 Mac 调度。正式 Gold48 运行不再等待每 Job 的独立 Provider Ed25519 动态证明：删除额外 `/input/provider:ro`、600 秒轮询等待、独立 Provider pin 前置要求；冻结输入 Stage 为 13 份，不附带 Provider 私钥/证书。**历史签名核验函数保留供旧证据审计，但新 GPU 生产路径不调用**。

保留不可删的主线门禁：单 Owner Ed25519 签名（目前生产公钥 pin 仍未配置）、明确 GPU/推理授权、冻结 48 条输入及每臂 Profile、LoRA SHA 和 RO 挂载、依赖及镜像 digest 锁、本地一次性提交标记、OutputManager create-only、Owner 端下载 SHA 校验。**不得将 Owner 的镜像配置声明冒充 Provider 的独立测量**。新结果标记 `runtime_image_measured=false`、`provider_image_attestation_sha256=null`、`runtime_image_identity_source=OWNER_SIGNED_CONFIGURATION_ONLY__NOT_MEASURED`。Owner Mac 需要用已有 HF Inspect 核对实际 Job 的 image digest 与 Owner 签名，再决定质量评测准入；未经核验为 `IMAGE_INSPECT_PENDING`。

此次仅完成源代码简化和合成回归，不启动 GPU，不生成真实回答，不创建新授权服务。原文档中以 14/15 文件 Stage、动态 handoff 和 Provider 双签作为下一步的段落属于**历史已废弃路线**，请优先遵守本节。


# AGENTS.md

## 2026-11-21 Gold48 单 Owner Mac 调度简化策略（最新授权范围；优先于旧共享卷规划）

**2026-11-21 提交后 Provider 证明交接路径（代码与合成测试，HF 实测未验）**：冻结 Gold48 输入 RO Stage 中**删除**须提交后才可能存在的 Provider Attestation，严格仅接受 14 份固定输入；单 Run 独立 `/input/provider:ro` 预先准备 `handoff-pending.json`，Provider 根据新 Job 的真实 Inspect/Job ID 独立签名，**提交后**只添加 `provider_attestation.private.json`，Job 在 GPU 加载前有界等待 600s、原签名/当前 JOB_ID 校验和本地 0600 安全物化。未到达/无效一律 HOLD；不是 Provider 私钥注入、HF Bucket 授权锁或 GPU 批准。**该 HF 原生 RO 挂载新增文件的实时可见性尚未实测，必须先用合成 CPU 工作负载证明，不得直接正式 GPU**。


**当前 HF Job Provider 身份绑定更新**：原 `verify_provider_image_measurement` 已加强为对签名 `provider_job_id` 和 HF 注入 `JOB_ID` 的精确匹配，其他 Job 的真实签名一律 HOLD。当前 RO Stage 中证明须在提交前上传，但 JOB_ID 在提交后分配，因此仍缺**当前 Job 启动后证明交接**；不绕过门禁、不重复开发新的服务，也不提交正式 GPU。


**当前新增的唯一运行连接（代码与合成 CI 已验，实际 HF Job 未验）**：在现有 `gold48_runtime_gate.py` 新增 `materialize_gold48_ro_input`，调用既有 `InputManager.open_verified` 按 SHA 读取 RO 挂载内容，再以本地 0600 exclusive/create-only 写入 0700 POSIX scratch（不会修改远端输入）；生产 `run_authorized_gold48_production` 已在原 Worker 返回后调用 `deliver_gold48_private_result`。后者要求 Output、launch、identity 三份本地 0600 文件及 48 条 WorkerReceipt，使用既有 `OutputManager.write_safe` 创建本地 SHA256 manifest，按三文件→manifest-last 顺序使用 `hf buckets cp` 上传到私有 `experiments/r60-gold48/outputs/<run_id>/`，逐件远端回读验 SHA。失败 HOLD 且不自动生成重试；**Owner Mac 的独立下载验证仍未执行，Job 内输入物化入口还需被实际受控包装调用**。这只是受控传输，不是新 GPU 授权、全局锁或训练。



用户已明确选择**单台可信 Owner Mac 串行提交**，不引入 Supabase/PostgreSQL、新的分布式授权锁或通用提交器。优先复用现存 `r60_common2_wrapped_hf_cli.py` 的完整 HF Job 历史排重、唯一 Run ID、本地提交标记和单次 HF CLI 投递策略，以及 `r60_base336_gpu_cli.py` 的 RO/RW 挂载与 dry-run 参数兼容方法；**两个现有入口分别是 CPU-only submit 与 GPU dry-run，不能直接当作已经实现的 Gold48 GPU 正式提交入口。** 本轮将本地标记写入改为调用现有 `OutputManager.write_safe`（原子无覆盖、0600、文件和目录 fsync），不新增账本系统。之前 HF Bucket Job `6b00ca46efaf5e14f4b3f8ca` 在根目录 `0700` 前置门禁 HOLD，原双 Job 实验已停，不重跑；HF Bucket **只作冻结输入/Adapter/产物存储，不作跨 Job 授权锁**。

单 Owner 模式的唯一性来自**受控操作边界**：只有 Owner Mac 提交，提交前读取完整 HF 组织 Job 历史，使用本地持久 `O_EXCL` 标记阻止本机重投；提交结果不确定或 Job 失败后仍保留标记、不自动重试/换机器/换 namespace，必须独立批准新 Run ID。它**不提供针对其他独立 HF 提交者的全局互斥**；不能把 Mac 本地文件伪装为 GPU Job 的共享原子账本。现有 `gold48_runtime_gate.py` **已把原 HF Bucket 共享消费门禁收缩为当前 GPU Job 的 0700 本地 POSIX 私有消耗记录**，并显式拒绝 FUSE 作为本地输出；这仅在唯一可信 Owner Mac 提交前提下成立，不是跨 Job 分布式锁。**GPU Job 私有输入本地化、结果回传和正式可信签名仍未接通**，不能宣布可运行。下一步仅在实际 Owner/Provider 运行身份、私有输出交付与单独 GPU 授权明确后，最小范围适配已有入口，复用固定四臂 Loader、Worker 和签名校验，不重新搭建通用 Runner。

**严格不变**：冻结的 48 重建输入/48 原始回复、四臂生成 Profile、192+48 评价合同、Owner Ed25519 信任锚未登记状态、GPU/推理未授权、Quality-v1 准入为零。未经单独批准不提交 HF GPU Job、不签发生产授权、不计算模型权重。

---


## 2026-11-21 current R60 Gold48 handoff override — dataset and four-arm profile FROZEN

**This section is authoritative over all 2026-11-19/20 P2-C / Gold48 NOT_GENERATED / Owner freeze pending snapshots below.** Read the [2026-11-21 copy-ready next-agent prompt](docs/R60_BASE336_NEXT_AGENT_START_PROMPT_20261121_CN.md) and the **top** of [current P2 mainline handoff](docs/R60_BASE336_P2_QUALITY_EVAL_NEXT_AGENT_HANDOFF_20261119_CN.md) before doing more work. Continue active PR #31 branch `docs/r60-p2-r47-r48-r55-source-shape-audit-20261118`, current last-verified HEAD `4e03a6d1e8a7545a23394e213087b4b46aa551a8` (6/6 Actions PASS before documentation-only updates); always refresh live HEAD/CI.

**Actual completed Owner decisions and evidence:** Gold48 Owner-private SAFE `GOLD48_SCOPED_OWNER_FREEZE_COMPLETE__GENERATION_PROFILE_PENDING`, `owner_gold48_freeze=true`: exactly 48 reconstructed evaluation prompts from eight public Story sources / 25 Sessions, 42-case preregistered sensitivity excluding all six flagged cases only there, 48 separately SHA-frozen actual historical original Assistant replies. Input/original SHA, anonymized HF Stage, real HF CPU Tokenizer Job and Owner downloaded SAFE receipt have passed; do not rebuild, recover, tokenize, re-upload, re-sign or re-submit these. The input contract is `RECONSTRUCTED_EVALUATION_INPUT`; historical actual-sent prompt and full protected universe remain **UNVERIFIED**, explicitly risk-accepted within verified scope, not a general Held-out PASS. Original replies are descriptive fifth blind answer source, never generation input or guaranteed ground truth.

**Generation parameters also Owner-frozen separately:** `experiments/r60_quality/gold48_four_arm_generation_profile_frozen_v1.json` has `GOLD48_FOUR_ARM_PROFILE_FROZEN__RUNTIME_VALIDATION_PENDING`, `owner_generation_profile_freeze=true`. Models: pinned Qwen/Qwen3.8-27B base and R46 checkpoint-7, R54 checkpoint-16, R60 Base336 checkpoint-37 LoRAs on same revision. 48×4 generations (192), plus 48 separately frozen historical replies (240 blind scoring objects); 32K context / 2048 new tokens / thinking disabled / exact frozen per-case seed and sampling. **Do not use old P4 Qwen3-32B/GLM Frozen Profile.** Existing `src/storyforge_dataset/generation_eval/gold48_qwen35_loader.py` is a synthetic-CI-tested **thin** loader for `Qwen3_5ForConditionalGeneration` + PEFT; reuse `generation_eval.backend`, `generation_eval.worker`, `hf_runtime`, and shared Token core, without forking any of them.

**Next real gate**: bind existing three Adapter release SHA receipts to exact checkpoint bytes, pin compatible Qwen3.5 + PEFT runtime image/dependency lock, validate actual generation template/EOS/no truncation and four-arm GPU load smoke when *separately authorized*. Current `inference_authorized=false`, `gpu_authorized_by_this_document=false`, `training_authorized=false`, `quality_v1_admitted=0`, `model_promoted=false`. Existing permission for paid HF **CPU-only** technical preflights does **not** override frozen no-inference/no-GPU flags; obtain scope-specific approval before GPU/model calls. Do not restart old R50/R47/R48/R55/R58 audits, 204 Story/495-version semantics, candidate collection, CPU Gold48 Tokenizer, or Base336 training. Never expose private Stories, Gold replies, Owner mapping or per-case hashes.

---


**2026-11-20 latest Owner scoped-independence authorization:** Owner approved `INDEPENDENT_WITHIN_VERIFIED_HISTORICAL_SOURCE_SCOPE` and *explicit disclosure of unknown historical training/test/teacher exposure*. This changes the **evaluation-admission scope policy**, not the evidence: `P2_C_SCOPED_POLICY=RISK_ACCEPTED` while `P2_C_FULL_UNIVERSE=UNVERIFIED`. Do not search indefinitely for an authoritative full Protected/Reserved/Dev/Teacher roster; do not call the 204 Story/495 version reviewed subset an exhaustive universe. Gold48 **private construction and freeze preparation** may proceed using the 48 previously matched full historical prefixes + real original replies, but a final 48-case hash-bound Owner freeze does not exist yet. Honor approved `RECONSTRUCTED_EVALUATION_INPUT`, original historical reply as descriptive fifth source only, flagged original Story with 48 primary / 42 paired sensitivity, private flagged-story-to-six-case binding at freeze. Do not mutate source texts, infer Pxx/Sxx identities from ordinal positions, or reuse the legacy three-message P2 public-prompt draft gate as if it certified full history. Actual paid inference/GPU/HF remains separately unauthorized. See `docs/evidence/R60_BASE336_P2_SCOPED_INDEPENDENCE_OWNER_DECISION_SAFE_20261120.json` and the **top** of `docs/R60_BASE336_P2_QUALITY_EVAL_NEXT_AGENT_HANDOFF_20261119_CN.md`; older strict all-universe requirements are historical, not a reason to repeat scanning.


**2026-11-20 Owner source-quality arbitration:** Owner has approved `OWNER_ACCEPTED_WITH_QUALITY_CAVEAT` for one Reviewer-flagged P2 public Story with a family/character naming residue. Keep the original Story revision, historical Prefix and Original Reference unchanged. Preregister **all 48 prompts** as the primary evaluation and the **remaining 42 paired prompts (exclude all six prompts from the flagged Story)** as a sensitivity analysis. Show both outcomes regardless of direction; distinguish source-inherent inconsistencies from model mistakes. The anonymous Reviewer flag-to-actual-Story and six Gold48 case identities must be verified privately, not inferred from P/S ordinals; private identity mapping is still pending. This approval closes the quality-risk policy decision ONLY, not historical authority/source isolation, formal Gold48 freeze, model authorization or `P2_C=HOLD`. SAFE decision: `docs/evidence/R60_BASE336_P2_SOURCE_QUALITY_OWNER_DECISION_SAFE_20261120.json`. For the active rules read the top of `docs/R60_BASE336_P2_QUALITY_EVAL_NEXT_AGENT_HANDOFF_20261119_CN.md`; lower old sections are historical.


**2026-11-20 Owner evaluation-input override:** Owner expressly approved `RECONSTRUCTED_EVALUATION_INPUT` for the R60 P2 Gold48 Quality-v1 evaluation, without accessing RolePlay production or requiring historical provider actual-sent bytes as an evaluation admission gate. `ACTUAL_SENT_PROMPT_BYTES=UNVERIFIED` stays true. Four model-generation arms share frozen reconstructed evaluation messages; the original historical assistant reply remains the fifth blinded scoring source but is only a *historical-context reference*, not demonstrably a byte-identical-prompt causal comparator. Previously verified 48 historical prefixes + 48 exact matched historical replies are available as candidates, but Gold48 is **not yet frozen**. The remaining P2-C blocks are source-exposure authority/difference review and one P2 source-quality arbitration. No new GPU/model calls, promotion, freeze, training, or change to sealed data is authorized. The up-to-date contract is at the top of `docs/R60_BASE336_P2_QUALITY_EVAL_NEXT_AGENT_HANDOFF_20261119_CN.md`; older 2026-11-19 text below is historical context.


**2026-11-19 Owner Gold/reference requirement:** The independent R60 Base336 P2 evaluation must compare model answers against the **same-prompt frozen original source Assistant reply (Gold)**, evaluated as an anonymously shuffled fifth response source, **not a fifth generation model**. The new P2 48 prompts are synthetic/unbuilt and currently have no verified matching original replies. Do not transplant old R48 Gold or call source Opening the answer; do not load private chats to make a Gold set. Strictly bind `frozen_prompt.messages == original_record.messages[:-1]`, source revision, rights and exposure; Gold is withheld from inference prompts and is not presumed correct. The current handoff details the mandatory Gold evidence HOLD: `docs/R60_BASE336_P2_QUALITY_EVAL_NEXT_AGENT_HANDOFF_20261119_CN.md`. All no-GPU/no-HF/Owner freeze gates remain in force.

## R60 Base336 training-after P2 Quality-v1 — current agent handoff override (2026-11-19)

The active **post-training independent evaluation** workflow is documented at [R60 Base336 P2 Quality-v1 next-agent handoff](docs/R60_BASE336_P2_QUALITY_EVAL_NEXT_AGENT_HANDOFF_20261119_CN.md), with a [copy-ready prompt](docs/R60_BASE336_NEXT_AGENT_START_PROMPT_20261119_CN.md). This supersedes the older R60 handoff text below only for **current P2 next steps**, not immutable training facts or project-wide policy. The active PR is #31 (development branch `docs/r60-p2-r47-r48-r55-source-shape-audit-20261118`); always check HEAD and CI.

**Do not deviate:** Finish P2-C independent semantic/source protection for the **8 new public P2 stories** (not the old eight Base336 World groups), then build 48 six-dimension prompts, then Base/Adapter paired blind quality review. Reuse already verified R50 50=46+4 provenance, pinned five R50 source worlds and P2 exact disjoint, R47/R48/R55 known dev20/two-story exact disjoint, old 38-Story evidence, and R58 five-scope empty CSV result. These have already been run and must not be repeated just to make progress. Base336 all-172 full source and historical actual-sent, other Protected/Reserved/Dev/training/teacher universes, reviewer independence and Owner freeze remain HOLD. R50 sealed contents and private chats remain off-limits. Owner authorizes scoped read-only StoryForge DB access without repeated approval; no DB writes or RLS relaxation. A new GPU/HF inference or training job still needs separate explicit authorization. P2-C HOLD, 48 actual prompts NOT_GENERATED, train/quality admission zero, model not promoted.


## Project
## Active R60 workstream override (2026-11-16)

The legacy v0.3 baseline below remains historical project context. The active R60 Base336 exploratory work is on `r60/common2-cpu2-owner`; read these before changing training, Quality or HF execution code:

- `docs/plans/R60_BASE336_CPU_PROOF_TRANSFER_NEW_AGENT_HANDOFF_20261116_CN.md`
- `docs/plans/R60_BASE336_FAST_GPU_EXPLORATORY_20261116_CN.md`
- `docs/standards/GOLD_QUALITY_PIPELINE_CN.md`
- `skills/storyforge-roleplay-sft/SKILL.md`
- `skills/storyforge-hf-jobs/SKILL.md`

The 293/43 final dataset has a real Owner SAFE PASS for strict transfer of the old HF CPU336 tokenizer/collator/R18 label-mask proof. Do not rerun CPU336, recreate the dataset or treat this engineering proof as Quality-v1 admission. Keep `quality_v1_admitted=0`, `train_admitted=0`; GPU is not submitted and requires separate scope-specific Owner authorization. Reuse the shared HF Runtime and token-preflight core; do not fork Quality Pipeline, collator or HF job infrastructure.


StoryForge is the training and evaluation pipeline for interactive narrative language models.

Current target:

- Base model: `Qwen/Qwen3.8-27B`
- Training method: QLoRA / SFT with ms-swift
- Accepted dataset: `data/compiled/v0.3`
- Token budget: `max_length=16384`
- Dataset split: 65 train / 15 validation / 20 held-out test
- Held-out test data MUST NOT be passed to training or validation.

Read these files before making training changes:

- `README.md`
- `docs/DATASET_V0_1.md`
- `docs/TRAINING_QWEN38.md`
- `configs/qwen38-27b-qlora-smoke.yaml`
- `configs/qwen38-27b-qlora-v0.1.yaml`

## Codex operating rules

### 1. Preserve dataset integrity

Do not modify raw or compiled datasets unless the task explicitly requires it.

Never commit:

- `data/raw/`
- `data/private/`
- `data/compiled/`
- model weights
- LoRA adapters
- checkpoints
- secrets
- SSH private keys
- Hugging Face tokens

These are intentionally excluded by `.gitignore`.

The held-out test set is for final evaluation only.

Do not use:

`data/compiled/v0.3/test.jsonl`

for:

- training
- validation
- hyperparameter selection
- checkpoint selection
- prompt tuning

### 2. Remote GPU safety

Remote GPU work must be auditable and reversible.

Before installing or training, collect:

```bash
hostname
uname -a
nvidia-smi
python3 --version
df -h
free -h
```

Do not:

- destroy or reformat disks
- alter firewall rules
- modify unrelated system services
- expose new public ports
- install secrets into the repository
- run destructive cleanup outside the StoryForge workspace
- terminate unrelated GPU processes without explicit approval

Prefer a project-local Python virtual environment.

Do not use `sudo` unless it is strictly required and explicitly authorized.

### 2.1 Hugging Face execution boundary

All model-specific Tokenizer, Chat Template, token-budget and tokenizer/model-revision preflights MUST run in a Hugging Face CPU environment, not on the user's Mac. The Mac may prepare files, verify file integrity, stage/sync private inputs and inspect SAFE receipts; do not instruct the user to run model-specific tokenization locally.

- Pin the exact model ID, immutable revision and relevant runtime/template versions to the intended workload.
- Keep source text, world cards, blind-review packets, derived prompts, Owner crosswalks and case-level receipts in private storage. Do not expose them in GitHub, Job logs or chat.
- Outside private storage, emit only SAFE aggregate results. Never silently truncate history, modify frozen Gold, or treat Token PASS as literary quality approval or training admission.
- When the user explicitly requests a workflow requiring CPU tokenization/preflight, use the minimum necessary HF CPU execution within the requested scope; no separate per-Job cost authorization is required. This does not authorize GPU inference or training, which still require separate explicit approval.

### 2.2 Shared tooling policy

StoryForge has one shared Token preflight implementation: `src/storyforge_dataset/token_preflight.py`. New project-specific workflows must reuse it and keep differences in thin adapters; do not copy the shared algorithm into Skills, workers or round-specific scripts.

The complete technical contract—including adapter boundaries, cache identity, SAFE diagnostics, staging, verification and historical compatibility—is maintained in `docs/standards/HF_TOKEN_PREFLIGHT_REUSE_CN.md`. Follow the R58 Skill's execution order before changing tooling. Keep historical frozen scripts, private inputs, receipts and checkpoints unchanged.

Generic tokenizer checks do not replace real ms-swift `last_round` / data-collator label-mask validation. Neither kind of PASS independently grants literary quality admission or training authorization.

### 2.2.1 R59 context-window rebuild policy

The R59 16K context-window rebuild is a separate, explicit engineering step; the
original shape-preview builder MUST continue preserving the complete source
history. Never rewrite or overwrite the original Preview.

- Pin `Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` and
  `max_length=16384`; measure in Hugging Face CPU with ms-swift, not on the Mac.
- Keep the approved System Prompt and final target Assistant bytes unchanged.
- If the full history does not fit, remove only a leading prefix and begin the
  retained suffix at a complete User-message boundary. Preserve every later
  message in its original order; never delete middle messages or truncate text.
- Preserve the final User and target Assistant messages. Historical messages
  remain `loss=false`; only the final target remains `loss=true`.
- Preserve the original input-context SHA as provenance and recompute
  `input_messages_sha256` over the retained context.
- Use `experiments/r58_quality/r59_sft_context_window.py`; it reuses the
  existing preview validator and actual ms-swift Collator, and uses the shared
  `extract_input_ids` core. For standalone HF Jobs, mount the scripts directory
  and provide `token_core.py` as an exact byte-for-byte copy of
  `src/storyforge_dataset/token_preflight.py`.
- Any sample whose current User + target or complete eligible suffix cannot fit
  MUST HOLD. The operation is all-or-none for a batch and writes a new private
  create-only output; it never mutates source input.
- Context-window and actual Collator PASS are engineering checks only:
  `quality_v1_admitted=0`, `dataset_frozen=false`,
  `training_authorized=false`, `gpu_started=false` remain mandatory.
- Chinese execution runbook: `docs/R59_CONTEXT_WINDOW_CN.md`.

### 2.2.2 HF Jobs Runtime Skill

Before creating or changing any HF Job Runner, read `skills/storyforge-hf-jobs/SKILL.md` and its relevant references. Use `storyforge_dataset.hf_runtime` for shared context, paths, input/output, diagnostics, resources and receipt validation. Business-specific behavior belongs in thin adapters. Keep `src/storyforge_dataset/token_preflight.py` unchanged and reuse it as the only tokenizer core. The complete operational standard is `docs/standards/HF_JOBS_ENGINEERING.md`.

### 2.3 Hugging Face Jobs namespace and volume policy

StoryForge Hugging Face Jobs MUST use the organization namespace `adradar` and the
project bucket `hf://buckets/adradar/storyforge-training`. Do not silently fall back
to the personal namespace `greenkeedle` after an organization submission error.

For CPU jobs, use separate mounts:

- Every source/input mount MUST be explicitly read-only (`:ro`), mounted below
  `/input/` or `/scripts/`.
- The output mount MUST be a separate project-bucket prefix mounted at `/output`
  with explicit read-write mode (`:rw`).
- Never mount the whole project bucket read-write as a shortcut.
- Never make the output mount read-only; SAFE reports need a dedicated writable
  destination.
- Use a unique output prefix for each attempt to prevent overwriting prior receipts.

Use `scripts/hf_job_guard.py` for CPU submissions. It enforces namespace
`adradar`, CPU-only flavors, a bounded timeout, read-only inputs, one separate
read-write output, and one attempt. Without `--submit`, it performs validation only.
The tool does not fall back to a personal namespace, retry automatically, or submit
GPU jobs.

Known incident regression rules:

- HTTP 403 with a read-write source/input mount: inspect mount mode and organization
  permissions. The previously reproduced bucket-mount failure was resolved by
  mounting the input prefix `:ro` and using a separate output prefix `:rw`.
- HTTP 402 in the personal namespace: do not infer that the organization is out of
  balance and do not switch billing namespaces. Check the intended organization
  billing/permission state.
- A 403/402 MUST NOT trigger automatic namespace fallback, permission broadening,
  mount-mode broadening, retries, or GPU escalation.

A 403 from the ChatGPT HF connector MUST NOT be treated as proof that the
Mac-local HF CLI is broken. The 2026-11-01 Mac-local private Bucket RW smoke
and sync-back passed. For connector-only 403s, stop connector retries and use
the documented guarded Mac-local CLI route in `docs/HF_JOBS.md`; never
reconnect/retry blindly or change namespaces/mount permissions as a workaround.

The 2026-11-04 ChatGPT HF connector probe verified that organization CPU
submission and private Bucket RO mounts work, while private Bucket RW mounts
still return HTTP 403. For SAFE-only CPU preflights, prefer RO inputs and emit
only the SAFE aggregate receipt to Job stdout/logs; never print private sample
content. Mount a Bucket directory prefix (not an assumed file mount), then
assert the expected file with `test -f` before reading it. See the 2026-11-04
regression and mount-semantics sections in `docs/HF_JOBS.md`.

For the R59 Qwen3.8-27B ms-swift Python preflight, set
`USE_HF=true` before importing Swift because the pinned revision is a
Hugging Face commit SHA; ms-swift defaults to ModelScope otherwise. Install
`qwen-vl-utils==0.0.14`, `decord`, and `torchvision==0.29.2` for the
Qwen processor. See the R59 runtime contract in `docs/HF_JOBS.md`.

See `docs/HF_JOBS.md` for the verified incident record and invocation contract.

### 3. Training gate

Training is strictly staged.

#### Stage A — Environment qualification

Verify:

- NVIDIA GPU visible
- CUDA runtime usable
- sufficient free VRAM
- sufficient disk space
- repository is clean or local changes are documented
- Qwen tokenizer/model can be resolved
- ms-swift CLI is available

Recommended environment:

```bash
python3 -m venv .venv-train
source .venv-train/bin/activate

pip install -U pip
pip install -U ms-swift
pip install -U "transformers>=5.2.0" qwen_vl_utils decord
pip install -U bitsandbytes
```

Do not add DeepSpeed to the initial single-GPU smoke test.

#### Stage B — Dataset qualification

Run:

```bash
storyforge-dataset validate \
  data/raw/100条作品回答范例_完整上下文_JSONL_20260930 \
  --expected-selected 100
```

Then verify `data/compiled/v0.3` exists.

Run the following token analysis **in Hugging Face CPU (not on the Mac)**, using the corresponding private mounted inputs and pinned tokenizer revision:

```bash
storyforge-dataset analyze \
  data/compiled/v0.3 \
  --model Qwen/Qwen3.8-27B
```

Acceptance:

- 100 samples
- <= 16384 tokens: 100%
- max <= 16384
- no analyzer errors

Do not rebuild v0.3 unless required.

#### Label-mask qualification

StoryForge SFT supervises only the final Gold assistant response.

The training configs MUST use:

```yaml
loss_scale: last_round
```

Do not use ms-swift SFT's default loss strategy for StoryForge multi-turn samples because
the default also supervises historical assistant responses.

When auditing labels, Qwen/ms-swift may supervise assistant response suffix/control tokens
(e.g. response terminators). These template-owned suffix tokens are not history/system leakage.

A label-mask audit must distinguish:

- forbidden: system tokens
- forbidden: user tokens
- forbidden: historical assistant response tokens
- allowed: final Gold assistant content
- allowed: template-owned suffix/control tokens attached to the final response

If an audit reports a small number of leaked tokens, decode their exact token IDs and positions
before changing the training mask. Never waive the audit without identifying them.

#### Stage C — Smoke training

Run only:

```bash
CUDA_VISIBLE_DEVICES=0 \
swift sft configs/qwen38-27b-qlora-smoke.yaml
```

Smoke acceptance requires all of:

- model loads successfully
- 4-bit quantization succeeds
- dataset parses successfully
- forward pass succeeds
- backward pass succeeds
- no CUDA OOM
- training loss is finite
- validation step succeeds
- LoRA checkpoint is saved
- adapter can be reloaded
- one inference sample succeeds

Record:

- GPU model
- peak VRAM
- step time
- total smoke wall time
- package versions
- output/checkpoint path
- any warnings

If smoke fails, STOP.

Do not start the baseline run after a failed smoke.

Fix only the minimum necessary issue and rerun smoke.

#### Stage D — Baseline training

Baseline training may start only after Stage C passes.

Command:

```bash
CUDA_VISIBLE_DEVICES=0 \
swift sft configs/qwen38-27b-qlora-v0.1.yaml
```

Before starting baseline training, re-check GPU memory and disk space.

Do not change hyperparameters merely to improve training loss.

With 65 training samples, overfitting risk is high.

### 4. Evidence

Create local evidence under:

```text
runs/<run-id>/
```

At minimum save:

```text
environment.txt
nvidia-smi-before.txt
pip-freeze.txt
command.txt
stdout.log
stderr.log
nvidia-smi-after.txt
summary.md
```

The `summary.md` must state:

- PASS / FAIL
- exact Git commit
- exact config file
- exact dataset path
- exact base model
- GPU type
- peak VRAM if available
- training steps completed
- final/observed loss
- checkpoint path
- unresolved warnings/issues

Do not commit large logs, model weights, datasets, or checkpoints unless specifically requested.

### 5. Source control

Before modifying source:

```bash
git status --short
git rev-parse HEAD
```

Keep changes scoped.

Run:

```bash
ruff check .
pytest -q
```

before committing code changes.

Do not rewrite history or force-push.

Do not modify `main` history destructively.

### 5.1 Artifact delivery (GitHub first)

For project code, tests, standards, runbooks and SAFE receipts, deliver changes through the existing GitHub feature branch / PR with commit SHA and validation status. Do not package tools as ZIP by default. ZIP is reserved for an explicit user request for compressed/offline handoff. Keep PRIVATE records and per-case review queues out of GitHub. See `docs/standards/PROJECT_ARTIFACT_DELIVERY_GITHUB_FIRST_CN.md`.

### 6. Decision rules

If the remote GPU has less memory than expected, do NOT silently reduce `max_length` or change the dataset.

Report the constraint first.

If `16K` smoke OOMs, acceptable next experiments are, in order:

1. enable/verify gradient checkpointing
2. verify batch size is 1
3. inspect quantization actually loaded in 4-bit
4. consider memory-efficient attention if compatible
5. only then propose a shorter max_length or length-bucket strategy

Do not change the accepted Dataset v0.3 content merely to make training fit.

### 7. Completion condition

The task is not complete merely because a training process started.

For smoke training, completion means the Stage C acceptance criteria are satisfied.

For baseline training, completion means:

- training exits successfully
- final adapter/checkpoint exists
- validation completed
- evidence summary is written
- no held-out test data was used during training/selection

## R60 Base336 GPU implementation handoff (2026-11-17)

The P0 293/43 Collator proof transfer is complete. Do not rerun CPU336, recreate the split or rerun the Collator. The active next step is Owner Mac private Stage and HF read-only READY/dry-run using `docs/plans/R60_BASE336_FAST_GPU_EXPLORATORY_20261116_CN.md`.

Implemented entrypoints:
- `scripts/r60_base336_gpu_contract.py`
- `scripts/r60_base336_gpu_stage.py`
- `scripts/r60_base336_gpu_worker.py` and `scripts/r60_base336_gpu_worker.sh`
- `scripts/r60_base336_gpu_cli.py`

Reuse the shared Common2 dependency bundler, HF Runtime, `hf_job_runner.py` evidence/inference/GPU monitor helpers, Common2 remote Bucket listing and paginated Job-history helper. Do not fork tokenization, R18 mask, Gold Quality, CPU Guard or HF Runtime. R54 code is reference only; never copy its 31/9 data, 16-step config or whole-Bucket RW mount.

The Stage root and every nested directory must be mode 0700; files must be 0600. Local verification checks all modes and rejects symlinks. Worker preflight must validate the HF-provided JOB_ID, Run Key/Scope, and writable output mount before dependency installation.
The GPU CLI intentionally has no submit action. Its dry-run Scope is `DRY_RUN_NOT_AUTHORIZED`; the worker refuses that Scope. Keep GPU Job count 0 until separately authorized. Quality-v1 and train admission remain 0.
