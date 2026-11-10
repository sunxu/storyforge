# R60 P4 Runtime Fingerprints, Stop Tokens and Finish Reasons（2026-11-10）

## 1. P3 pinned file evidence is now bound into a P4 candidate

Machine-readable candidate:
`experiments/r60_quality/p4_generation_profile_candidate_v1.json`

The candidate binds all 18 files from `R60_P3_MODEL_FILES_SAFE.json` by model role, filename, SHA-256, and exact P3 model revision. It also binds the P3 download SAFE digest:

`52c3dcae10a0d715d72296ac078d0dfda523e902bb31bbdb2df5776f310581c5`

The top-level `tokenizer_hashes` values are the exact `tokenizer.json` hashes; `tokenizer_file_hashes` retains the complete six-file-per-model manifest. The validator rejects role/file-set drift, malformed hashes, mismatch between the top-level tokenizer hash and manifest, or mismatch between generation-config hash and the manifest.

## 2. Pinned stop-token configuration

The exact pinned `generation_config.json` files declare:

| Role | EOS token IDs | PAD token ID |
|---|---|---:|
| A / Qwen3-32B | 151645, 151643 | 151643 |
| B / GLM-4-32B-0414 | 151329, 151336, 151338 | 151329 |
| Challenger / GLM-Z1-32B-0414 | 151329, 151336, 151338 | 151329 |

The P4 backend now passes these IDs explicitly to `model.generate`; it does not rely on a runtime default GenerationConfig. The profile validator checks them against the pinned model/revision contract.

No extra string stop sequences are currently configured. This is a static configuration decision based on the pinned generation-config EOS IDs; it is not proof of observed runtime termination behavior.

## 3. Finish reason and truncation semantics

Transformers `generate()` does not provide a universal per-sequence `finish_reason` field in the tensor-only output used by the previous adapter. The adapter now returns structured sequences and classifies actual generated token IDs:

- `eos`: final generated token is one of the pinned EOS IDs.
- `length`: no EOS at the end and generated token count reaches `max_new_tokens`.
- `unrecognized_stop`: neither condition holds; the batch receipt becomes HOLD.

Length stops are preserved in the private output and counted in the SAFE receipt; they are not silently labelled as EOS. The private output records the effective per-sample seed (`base_seed + stable_input_index`) and finish reason. SAFE output contains counts only, never generated text.

Prompt tokenization retains the P3 policy: reject over-budget input; never silently truncate. The 4,096 generation budget includes reasoning tokens. A `length` finish reason is a generation-budget stop, not prompt truncation.

Actual EOS/length behavior of each model remains deferred until a separately authorized synthetic GPU smoke. No inference was used to establish runtime observations in this commit.

## 4. Runtime image and dependency lock

Candidate base image:

`docker.io/pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime@sha256:77f17f843507062875ce8be2a6f76aa6aa3df7f9ef1e31d9d7432f4b0f563dee`

Docker Hub identifies this as a Linux/amd64 image and publishes the manifest digest. It is recorded as a candidate only; the actual HF Jobs runtime has not been launched or validated against it. Source: https://hub.docker.com/layers/pytorch/pytorch/2.6.0-cuda12.4-cudnn9-runtime/images/sha256-77f17f843507062875ce8be2a6f76aa6aa3df7f9ef1e31d9d7432f4b0f563dee

P4 requires a GPU-generation dependency lock separate from the P3 CPU reviewer lock. Proposed inputs are in `requirements/hf-generation-eval.in`. PyTorch 2.6.0 is listed as a constraint to match the base image; the lock must be resolved under the same Python version and validated without replacing the image's CUDA-enabled torch build. Do not reuse `requirements/hf-quality-reviewer.lock` as the complete P4 runtime lock: it does not pin Accelerate or the CUDA PyTorch runtime.

The hash-locked dependency file has now been generated and committed at `requirements/hf-generation-eval.lock`. SHA-256: `81b0006536695f1552161302515f1f154d65b3b32a8520a34e774b4e518ceb4c`. It pins `torch==2.6.0` as a compatibility constraint, keeps the base image's installed `2.6.0+cu124` build, and pins NumPy 1.26.4 to avoid unreviewed NumPy 2.x upgrades in this PyTorch 2.6 runtime. The lock passed `pip install --dry-run --require-hashes` inside the digest-pinned image; torch remained `2.6.0+cu124` with CUDA build 12.4. The candidate profile now binds this exact lock SHA.

Still pending:
- validate actual Transformers/Accelerate imports and tokenizer snapshot load in the selected HF runtime;
- validate BF16 capability in an authorized HF GPU runtime (not in hosted CI);
- decide whether to freeze the generation profile and authorize a synthetic GPU smoke.

The base image digest is now verified by GitHub Actions on linux/amd64. The exact image reports Python 3.11.11, PyTorch 2.6.0+cu124, CUDA build 12.4; the hosted CI runner has no CUDA device, so this is a package/build contract check, not a GPU execution test. The profile now binds `runtime_digest=sha256:77f17f...f563dee`. `dependency_lock_sha256` remains null until the separate hash-locked dependency set is generated and validated. The profile therefore remains `P4_PROFILE_INCOMPLETE_HOLD`.

## 5. Authorization

All remain false:
- `profile_freeze_authorized`
- `inference_authorized`
- `gpu_authorized`
- `training_authorized`

No HF Job was submitted, no model weights were loaded, and no inference or training was run. The code changes are CPU/CI synthetic tests only.


## 6. Runtime-side file verification

The backend API now requires an explicit local tokenizer snapshot and its expected per-file SHA-256 map. It verifies all six allowlisted files before calling `AutoTokenizer.from_pretrained(local_files_only=True)`. The standalone GLM template is read from the same verified snapshot. The downloader uses the exact model revision and an `allow_patterns` list derived from the expected file map; it does not request model weights.

The generation model is still loaded only by the explicit `AutoModelForCausalLM.from_pretrained(model_id, revision=...)` call. A manifest mismatch fails before model loading. CI tests use synthetic local files and fake Transformers/Torch objects; they do not download tokenizer files or weights.


## 7. Single-GPU placement is explicit

The model loader now passes `device_map={"": 0}` rather than `device_map="auto"`. Each generation Job is intended for one allowlisted GPU flavor; model placement is forced onto CUDA device 0. This avoids an automatic CPU/disk offload decision during loading. The post-load device-map check remains as a second fail-closed guard. If the pinned 32B model does not fit the selected GPU in BF16, loading must fail; the runtime must not silently offload layers to CPU or disk.


## 8. 独立 Runtime Smoke 授权（2026-11-10）

Owner 已单独授权一次最小真实 GPU Runtime Smoke。机器配置仅新增 `runtime_smoke_authorized=true`；以下生产授权仍保持 false：

- `profile_freeze_authorized=false`
- `inference_authorized=false`
- `gpu_authorized=false`
- `training_authorized=false`

Smoke 使用独立入口 `storyforge_dataset.generation_eval.runtime_smoke`，不调用生产 Generation Worker。它按 A → B → challenger 顺序在同一 GPU 上逐个加载模型，每个模型仅处理同一条内置合成中文提示，`max_input_tokens=256`、`max_new_tokens=32`、seed 42。输出文本不写入日志或 SAFE 回执，只保留文本 SHA-256、token 数、结束原因、耗时、BF16/CUDA 状态和显存峰值。每个模型卸载后清理其本次 Hub cache，再加载下一个模型。

GPU flavor 限定为 `a100-large`，单 Job、单 attempt、60 分钟硬超时。只挂载项目 bucket 的独立 Smoke 输出目录为可写卷；不挂载训练集、不读取历史对话、不创建训练器或优化器。运行时镜像和依赖锁仍按 SHA-256 校验。此授权不冻结正式 Generation Profile，不批准 30 条评估集推理、正式批量推理或任何训练。

若任一模型加载、BF16、Tokenizer、模板校验或生成终止行为失败，回执为 HOLD；不自动更换硬件、dtype、模型 revision 或依赖版本。


## 9. HF Jobs 首次 GPU 提交阻塞（2026-11-10）

已使用已认证的 Hugging Face OAuth 上下文尝试在 `adradar` namespace 提交唯一一个 `a100-large` Job，固定运行镜像、代码 commit `d434996d1498c5a6472fe23bba33e55b3b2f23e9`、60 分钟 timeout，并只挂载独立 Smoke 输出前缀。Jobs API 返回 `403 Forbidden`，没有返回 Job ID。

提交后只读核对：
- Hugging Face Jobs 列表：0 个 Job；
- 预定输出 bucket 前缀：空；
- 因而没有 GPU 初始化、模型权重下载、推理或计费运行。

当前 OAuth 身份有 `jobs` scope，且在 `adradar` 组织具有 write role；但 API 的 403 未区分具体拒绝原因。Hugging Face 官方规则要求 Job 计费 namespace 有正的 compute credit balance；仍需组织管理员确认 `adradar` 的 Jobs compute credit balance / 组织 Jobs 可用状态。不得未经 Owner 另行确认改用个人 namespace 或其他计费主体。解除该账户级阻塞后，重试同一份已固定的 Smoke Job，不更改 GPU flavor、镜像、模型 Revision 或测试范围。

## 10. P4 三模型真实 GPU Runtime Smoke 完成（2026-11-10）

ChatGPT 通过 Hugging Face Jobs 在 adradar namespace 成功创建并完成真实 GPU Job：

- Job: adradar/6af2dbbdab34849891aaef1e
- URL: https://huggingface.co/jobs/adradar/6af2dbbdab34849891aaef1e
- 状态：COMPLETED；Flavor：a100-large；GPU：NVIDIA A100-SXM4-80GB
- 固定镜像：sha256:77f17f843507062875ce8be2a6f76aa6aa3df7f9ef1e31d9d7432f4b0f563dee
- 代码：8e1e87fd923908f37635b5daac5d2bfe4548563e
- 依赖锁 SHA256：81b0006536695f1552161302515f1f154d65b3b32a8520a34e774b4e518ceb4c
- SAFE：RUNTIME_SMOKE_PASS，3/3；文件 4072 bytes；SHA256 5fbffdcd4058c150c323d57f599a409eb64d5b2b6512b95c4b5d08379b720c25
- SAFE 从 HF Job logs 回收；生成正文没有写入日志或 SAFE。
- 三模型均 BF16、CUDA 驻留；结束原因 A=length、B=eos、challenger=length。
- 未使用训练数据；未启动训练；生产 Profile 未冻结；正式批量推理仍未获授权。

### 对此前 403 诊断的修正

本次在同一个 adradar namespace 下，不挂载 Bucket 的 CPU Job 创建并完成；项目 Bucket RO 挂载并读取成功；Bucket 上传在 /api/buckets/adradar/storyforge-training/xet-write-token 返回 403；不挂载 Bucket 的 a100-large Job 则成功创建、启动并完成真实三模型 Smoke。

因此，组织 Jobs 创建权限和 GPU 计费能力已被真实执行证明可用。此前的 403 不能再归因于组织没有 Compute Credit 或没有 Jobs 权限；当前证据将问题定位到 ChatGPT 调用上下文的 Bucket 写入凭证 / RW 挂载路径。后续 SAFE 通过 Job logs 回收并提交 GitHub；在写入权限单独修复前，不要依赖 RW Bucket mount 或 hf buckets cp。

## 2026-11-10：HF OAuth App / Bucket RW 故障更新

ChatGPT Hugging Face Plugin v0.1.4，OAuth App ID `asdk_app_6ac752d4c640819191c206f9cb0dafad`，Version ID `asdk_app_v_225a5afb50248191aaab67016a94edc0`，RELEASED。连接器 `hf_whoami` scopes：`openid profile read-mcp read-repos jobs contribute-repos inference-api`；账号 `greenkeedle`，组织 `adradar` role=write。

Mac CLI 对同一组织 Bucket 的默认 RW mount `hf://buckets/adradar/storyforge-training:/output` 已真实验收：Job `6af2ee90ab34849891ab2f6e` 写入、读回 `PASS`、删除成功。ChatGPT 连接器无 Volume CPU Job `6af2ec43ab34849891ab279c` 成功，但带 RW Volume 提交返回 403。RO Job `6af2ec64ab34849891ab27f8` 仅提交被接受，未取得执行与读回证据。

因此，Bucket 普遍不可写、组织 Jobs 余额/创建权限整体故障已被对照实验排除。根因仍未确认：可能涉及 OAuth App capability / org grant / connector volume 参数序列化 / HF 服务端策略。缺少 `write-repos` 不得直接等同于 Bucket RW 权限缺失。

行动：要求 HF 检查上述 OAuth App 是否允许 Jobs 挂载既有私有组织 Bucket RW，核对 `adradar` grant，并解释对应 403。ChatGPT RW persistence 保持 HOLD；Mac CLI RW 仅是 Owner 受控临时路径。不得更换个人 namespace、索取长期 PAT、修改 ACL、配置 Trusted Publishers 或启动正式评估推理。

## 2026-11-10 补充证据：OAuth 授权确认页面截图（Owner 提供）

Owner 提供的 Hugging Face OAuth 授权页面截图显示：
- Repositories / Read repositories：读取用户可访问的私有及 gated repos。
- Repositories / Contribute to repositories：创建 repos 并管理由该 app 创建的 repos；页面明确注明 `Cannot access other repos`。
- Compute / Jobs：`Start Jobs on your behalf and read their status, logs and outputs`。
- Compute / Inference Providers：代表用户调用 Inference Providers。
- Account / MCP tools：读取 MCP tools。
- Organization grant 选择 `Grant ChatGPT the same access to selected organizations`，且 `Hong Kong Adradar Technology Limited` 已勾选（同时页面显示 Select all organizations 已勾选）。

### 对诊断的影响
该截图确认授权界面确实授予 Jobs 和指定组织访问，但没有单独列出 Bucket / Storage write permission。`Contribute to repositories` 的界面描述明确限定为 app-created repositories，不能据此推导它允许写入既有 `adradar/storyforge-training` Bucket。结合 ChatGPT RW Job 403 与 Mac CLI 同 Bucket RW 成功，最值得 HF 核查的是：Jobs OAuth 授权是否包含对既有组织 Bucket 的 RW mount / Xet write-token 签发能力，或该能力是否需要 OAuth App 额外 capability / grant。

此截图仍不能单独证明根因：页面未展示底层 OAuth scopes、Bucket-specific permission model 或 403 服务端拒绝码。不得把“缺少 Bucket write scope”写成已确认事实。应向 Hugging Face 提供 OAuth App ID `asdk_app_6ac752d4c640819191c206f9cb0dafad`、Plugin v0.1.4、此授权页面截图、Mac CLI Job `6af2ee90ab34849891ab2f6e` 和 ChatGPT RW 403 对照，请其确认 Jobs token 是否能签发既有 Bucket 的 Xet write token。

### Owner 授权范围说明
截图中组织授权范围为选定组织（当前截图同时勾选 Select all organizations 与 Hong Kong Adradar Technology Limited）。后续若重新授权，应只选择完成 StoryForge 工作所需的 `Hong Kong Adradar Technology Limited`，除非 Owner 明确希望授权其他组织；本截图不构成要求扩大组织授权范围的理由。

## 2026-11-10 主线续进：Worker CLI / Job bootstrap 工程实现

Owner 已暂停 ChatGPT-HF OAuth / Bucket RW 故障排查，并将自行在 Mac CLI 执行 HF 任务。ChatGPT 不再提交 HF Job、不测试 Bucket、不更改 OAuth；后续只提供可复用代码、命令、SAFE schema 与回执审查。

当前分支 `r60/p4-generation-eval-framework` 正在完成 P4 Worker CLI / Job execution plan 闭环：
- `worker.py` 保持模型无关的 generation batch engine，不导入 torch / transformers / HF Hub。
- 新增独立 `worker_cli.py`，作为真正的 `python -m storyforge_dataset.generation_eval.worker_cli` 执行入口；必须先通过 Profile freeze/inference/GPU 授权检查，再校验依赖 lock、runtime、manifest、input SHA、输出目录和私有输出权限；未授权时只输出 SAFE HOLD，不加载模型。
- Job plan 固定从 GitHub codeload 下载精确 `code_revision` 的仓库归档，限制归档大小/文件数/解压总量并拒绝路径穿越、符号链接和特殊文件；不依赖 PyTorch 基础镜像预装 git。
- Job 启动后按 `requirements/hf-generation-eval.lock` 使用 `--require-hashes` 安装依赖，再执行独立 Worker CLI；输入挂载路径为 `/input/generation-profile.json`、`/input/manifest.json`、`/input/inputs.jsonl`，输出目录必须为 `/output` 的全新直接子目录。
- Worker 仅将私有生成正文写入 `/output/<run-id>/<role>-outputs.private.json`，create-only、0600；stdout 只输出 SAFE 元数据，不输出生成正文。
- 当前提交 `219fd80f35d8b8e3c2da8a1b2d64a8dddeae008c` 的 Repository CI 与 R60 Generation Eval CI 已 PASS；Runtime Image Candidate 正在执行，尚未报告最终结果。

此代码目前仍是执行入口工程候选，不代表正式 Profile 已冻结或获准执行。未完成实际容器启动/归档下载的无 GPU 验证、运行镜像验证、Owner 本地 HF 端到端执行及 32K 资源预算复核前，不提交正式评估 Job。

### 后续主线顺序
1. 等待当前 HEAD 的 Runtime Image Candidate 真实回执；失败按日志修复，不沿用旧 SHA 的 CI 结果。
2. 增加 Worker CLI 归档 bootstrap 的语法/边界测试及 CPU-only container entrypoint test；确认镜像不依赖未安装的 git。
3. 由 Owner 在 Mac CLI 进行无 GPU/无私有数据的执行入口检查；如需 HF Job，由 Owner 决定并执行。ChatGPT 不代为提交。
4. 复核输出目录契约、SAFE 回收方式和私有正文保管；HF Bucket RW 问题暂时不在 ChatGPT 执行范围内。
5. 完成 32K 长上下文显存/时间/费用上限证据后，生成最终 Profile Freeze Review 包，等待 Owner 单独批准 Profile Freeze。Freeze 不自动授权正式推理。

### 不变的授权边界
`profile_freeze_authorized=false`、`inference_authorized=false`、`gpu_authorized=false`、`training_authorized=false`。不启动 Development20 / Locked30 正式推理、1000 条审核或 SFT；不读取 Locked30 私有案例。