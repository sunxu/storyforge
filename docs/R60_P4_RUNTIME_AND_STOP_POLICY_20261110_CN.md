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
