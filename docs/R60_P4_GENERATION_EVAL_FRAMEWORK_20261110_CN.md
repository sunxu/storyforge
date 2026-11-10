# R60 P4 Generation Eval Framework（2026-11-10）

## 决策

采用方案 B：新建独立 storyforge_dataset.generation_eval，复用现有 HF Jobs Runtime；不改写 hf_runtime、token_preflight.py、旧 hf_job_guard.py 或训练 Runner。

## P3 实际前置结果

最近一次 P3 SAFE 状态为 P3_SYNTHETIC_CPU_PREFLIGHT_PASS__GENERATION_PROFILE_PENDING：

- 三个模型的 tokenizer / chat template 合成预检完成，90 条合成输入 × 3 个模型 = 270/270。
- 三模型 Revision 与模板来源已固定；A 使用 tokenizer 内嵌模板，B 与 challenger 使用独立 chat_template.jinja。
- 共享上下文上限 32,768 tokens；输入预算 28,672，生成预留 4,096。
- 本次仅做 CPU tokenizer/template 检查；没有下载模型权重、提交 HF Job、初始化 GPU 或执行推理。
- 运行依赖基线：transformers==4.57.1、sentencepiece==0.2.1、jinja2==3.1.6。

P3 PASS 只证明合成 tokenizer/template 路径可用，不代表逐模型 Generation Profile 已冻结，也不构成推理/GPU 授权。现有 P3 候选配置中的预算、seed、runtime digest、tokenizer hashes 与授权字段仍需正式写入并复核；不得仅凭 SAFE 摘要自动修改源配置。

## 当前实现范围

本阶段仅实现 P4 配置结构校验和 readiness assessment。它是 CPU-only 的配置检查，不导入 Transformers/PyTorch、不访问网络、不提交 HF Job、不下载权重、不运行推理或训练。

```bash
PYTHONPATH=src python -m storyforge_dataset.generation_eval \
  experiments/r60_quality/p3_model_profiles_candidate_v1.json
```

当前候选配置应返回 P4_PROFILE_INCOMPLETE_HOLD，并明确列出缺失的模型采样配置、预算、seed、runtime digest、tokenizer hashes 和授权字段。不会用 Qwen 参数替代 GLM 参数。

## 固定边界

- 模型与 revision 必须与 P3 冻结候选一致：A / B / challenger 三个角色，不允许 main 或自动升级。
- 每个模型单独 Generation Profile；不同模型的采样参数不可隐式继承。
- profile freeze、inference、GPU 三项授权必须分别显式为 true；训练授权不由本框架推导。
- 只有 context ceiling、input/output budget、seed、runtime digest、tokenizer hashes、模板 hash 和逐模型 sampling 参数完整时，assessment 才可报告 ready。
- SAFE assessment 仅输出角色名、状态和固定 blocker code，不输出模型仓库路径、prompt、输入、输出或凭据。
- readiness PASS 仍不等于 HF Job 已提交或推理已授权；提交必须经过后续独立 orchestrator 与 Owner 授权。

## 已知模型参数证据与未决项

- Qwen3-32B 官方模型卡给出 thinking 模式 temperature=0.6, top_p=0.95, top_k=20, min_p=0；当前 P3 候选已记录该配置。
- GLM-4-32B-0414 与 GLM-Z1-32B-0414 的模型卡示例/建议并不构成当前 R60 评估任务已批准的逐模型 generation profile。特别是 GLM-4 文档示例 do_sample=True，GLM-Z1 文档给出 temperature=0.6, top_p=0.95, top_k=40, max_new_tokens=30000，但这些不能自动覆盖既定评估设计或消解采样/greedy 冲突。因此两个 GLM profile 暂时保持未配置，等待明确 Owner 决策。
- 三模型 template hash 已在 P3 SAFE 结果中核验；P4 仍需核对各 tokenizer 的独立文件 hash、运行镜像 digest 与依赖锁 hash，再完成 profile freeze。
- training_authorized=false；P4 Generation Eval 不会启动训练。

## 下一阶段

1. 将 P3 最终 CPU SAFE 回执与三模型配置逐项对齐，确认 revision/template/tokenizer hash。
2. 解决 GLM-4 与 GLM-Z1 的采样模式冲突，冻结每模型独立参数。
3. 将 28,672 输入预算、4,096 生成预算、seed、runtime 镜像 digest 和依赖 lock 写入独立 P4 profile candidate，并完成校验。
4. 实现通用 worker（模型加载、输入校验、生成、输出隔离、SAFE 回执）及单 Job 计划生成器。
5. 本地/CI 合成测试全绿后，才提交一项独立的 HF GPU Synthetic Smoke；提交前再次核验 namespace、flavor、timeout、挂载和成本上限。

## 当前授权状态

inference_authorized=false、gpu_authorized=false、training_authorized=false。当前提交不创建或运行任何 Hugging Face Job。


## P4.1：单模型 Job 计划生成器（已实现，未提交）

新增 `generation_eval.plan`，只生成确定性的单模型 HF Job 计划，不调用网络、不执行 subprocess、不提交 Job。

安全约束：

- namespace 固定为组织 `adradar`，拒绝个人 namespace fallback。
- 仅允许明确列出的 GPU flavor（A100 Large / H200 / RTX PRO 6000）；不自动选择或升级硬件。
- 镜像必须使用 SHA-256 digest，代码必须固定到 40 位 commit SHA。
- 输入仅允许项目 bucket 的 `/input:ro` 挂载；输出必须是独立 `/output:rw` 挂载。
- 输入/输出 bucket 路径不得相同或互相包含。
- 每个计划仅一个 attempt、detach、超时上限 60 分钟。
- 计划 SAFE 回执不输出 bucket 路径、镜像地址或命令行，不代表 Job 已提交。
- 现有 P3 候选仍未完成 profile freeze，实际调用计划生成器时应得到 HOLD；合成测试只验证完整假配置可以生成确定性计划。

命令行参数中的 image digest、flavor、timeout、bucket subpath、dataset manifest 和 code revision 都必须由后续经批准的执行配置显式提供，本阶段没有替用户选定这些运行参数。

### 尚未进入真实执行

Job 计划目前引用的 Worker 入口尚未交付，因此即使合成 profile 能通过，也不构成可提交的运行包。下一步需实现并测试通用 Worker、模型后端适配、输出隔离与 SAFE 运行回执；随后再增加单独的 GPU 提交守卫。不得直接使用计划中的 argv 绕过该守卫。



## P4.2：通用 Generation Worker API（已实现，合成后端验证）

新增 `generation_eval.worker.run_generation_batch`。Worker 与模型加载框架解耦，通过 `GenerationBackend` Protocol 接收后端实例：

- 严格校验 profile 已冻结且 inference/GPU 授权均显式为 true。
- 输入文件通过现有 HF Runtime 的 no-follow、文件类型、大小、SHA-256 校验。
- 输入 JSONL 严格限定为 `sample_id + messages`，校验角色、末尾 user 消息、ID 唯一性和消息数量。
- 逐条调用后端，并校验实际输入 token 数、生成 token 数不超过 manifest/profile 预算。
- 生成结果只写入独立私有文件，create-only、0600 权限；拒绝覆盖已有文件。
- SAFE 回执只返回模型角色、数量、字节数、SHA-256、权限和执行标志，不包含 prompt 或生成文本。
- Worker 不导入 Transformers/PyTorch，不负责模型下载或 Job 提交；模型后端必须实现 GPU 状态报告，真实 GPU adapter 尚未接入。

当前 Worker 仅使用 FakeBackend 完成合成测试。不能把 FakeBackend 测试解释为真实模型推理或 GPU 验收。

### P4.3 后续阻塞

1. 编写并冻结 Qwen / GLM 各自的 backend adapter，明确模型类、dtype、chat template 加载方式、设备映射与停止条件。
2. 将 P3 tokenizer/template 文件 hash、运行镜像 digest、依赖 lock hash 写入独立 P4 Frozen Profile；目前 P3 候选源文件仍保持未冻结状态。
3. 增加 Worker CLI 和独立 GPU Job submit guard；当前 Job Plan 只用于审查，不得直接执行其 argv。
4. 在完成 Owner profile freeze 和 GPU 授权后，才进行一个模型、一个样本的 Synthetic GPU Smoke。


## P4.3：Pinned Transformers Backend（已实现适配器，未加载权重）

新增 `generation_eval.backend.TransformersGenerationBackend`：

- 使用 `AutoTokenizer` / `AutoModelForCausalLM`，固定 model ID 与 revision；明确 `trust_remote_code=False`。
- Qwen 从 pinned tokenizer config 读取内嵌 chat template；GLM-4 / GLM-Z1 从独立模板文件加载。两条路径都必须匹配 P3 的 SHA-256。
- 固定 BF16 与 `device_map="auto"`；拒绝 CPU/disk offload，检查 CUDA 与 BF16 支持。
- 通过 tokenizer 的 `apply_chat_template` 进行真实 tokenization；按 profile sampling 参数生成，并返回实际 input/output token 数。
- 模型库仅在显式调用 `from_pretrained` 时延迟导入；profile、plan、CI 和 worker API 的合成测试不会下载模型权重。

### 三个模型的官方仓库配置核对

| 模型 | 架构 | 权重 dtype | 模型配置 context |
|---|---|---|---:|
| Qwen3-32B | Qwen3ForCausalLM | BF16 | 40,960 |
| GLM-4-32B-0414 | Glm4ForCausalLM | BF16 | 32,768 |
| GLM-Z1-32B-0414 | Glm4ForCausalLM | BF16 | 32,768 |

因此共享 32,768 token ceiling 不超过三个模型中的最小模型 context。

采样证据：

- Qwen3-32B 模型卡对 thinking 模式明确建议 `do_sample=true`、temperature 0.6、top_p 0.95、top_k 20、min_p 0；并明确警告不要使用 greedy decoding。候选 A 的采样设置与该建议一致。
- GLM-4-32B-0414 的 README 推理示例设置 `do_sample=true`，但模型仓库的 generation_config 没有给出 temperature / top_p / top_k 默认值。不能把 Qwen 参数直接移植给它。
- GLM-Z1-32B-0414 的 README 参数表建议 temperature 0.6、top_p 0.95、top_k 40；但同一 README 的 generate 示例使用 `do_sample=false`。这是明确的文档内部冲突，不能由代码替 Owner 裁决。
- GLM-4 与 GLM-Z1 的 generation_config 仅固定 eos_token_id / pad_token_id，没有可据以冻结采样模式的默认参数。

因此 GLM 两个 profile 继续 HOLD。后端已支持两种采样模式，但不会替模型选择模式或参数。

### 尚未验收

本次没有真实导入 Transformers、下载权重、初始化 CUDA 或运行模型。当前后端通过 FakeTorch / FakeTransformers 做接口合成测试；还需在实际 HF GPU 环境验证版本兼容、模型加载、模板 tokenization、显存占用和生成结果。


## 2026-11-10 采样策略决策补充

Owner 已确认按建议推进采样方案。逐模型主实验配置、GLM-4/GLM-Z1 Development20 敏感性对照及约束见 [R60 P4 Sampling Policy Decision](R60_P4_SAMPLING_POLICY_DECISION_20261110_CN.md) 与机器可读候选 `experiments/r60_quality/r60_sampling_decision_candidate_v1.json`。该决定只批准实验设计，不冻结 Generation Profile；所有 inference/GPU/training 授权仍为 false。GLM-4 主配置已校正为 `do_sample=true`，与其模型卡示例一致；GLM-Z1 greedy 与官方 sampling 表分别作为主基线和 Development20 对照。


## 2026-11-10：P4 Profile Evidence Binding 与 Stop Policy

新增 `experiments/r60_quality/p4_generation_profile_candidate_v1.json`，将 P3 SAFE 中三个模型的 18 个文件 SHA-256、generation_config SHA、EOS/PAD token IDs、模板来源与采样参数绑定到 P4 候选配置。P4 validator 会校验文件集合、哈希交叉一致性、revision 对应的 EOS/PAD IDs，以及不支持的自定义 stop sequence。

Generation Backend 现在只从已验证的本地 tokenizer snapshot 加载 tokenizer：下载器只允许请求 manifest 中的六个文件，固定 revision；snapshot 的每个文件在 AutoTokenizer local-only 加载前重新校验 SHA-256。模型权重仍只会在显式调用 pinned `AutoModelForCausalLM.from_pretrained` 时加载。

Worker/Backend 已增加 EOS / length / unrecognized-stop 分类、显式 EOS/PAD token 传递、per-sample effective seed 和 SAFE finish-reason 计数。未识别停止原因会使批次 HOLD；达到 `max_new_tokens` 会单独统计，不会伪装为 EOS。

运行镜像候选及 CPU-only Docker contract workflow 见：
- `experiments/r60_quality/p4_generation_profile_candidate_v1.json`
- `requirements/hf-generation-eval.in`
- `.github/workflows/r60-p4-runtime-image-candidate.yml`
- `docs/R60_P4_RUNTIME_AND_STOP_POLICY_20261110_CN.md`

候选 runtime digest 尚未被 HF Jobs 验证，GPU generation lock 尚未生成；profile 的 `runtime_digest` 和 `dependency_lock_sha256` 保持 null，所有授权仍关闭。此阶段没有提交 HF Job、下载权重、执行推理或训练。
