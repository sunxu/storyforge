# StoryForge R60 P4 Generation Runtime & Evaluation Plan（2026-11-10）

> 状态：**PROPOSAL_ONLY__OWNER_AUTHORIZATION_REQUIRED**
>
> P3 CPU-only Tokenizer / Chat Template / Token Budget 已 PASS。本文只准备 P4，不代表允许创建 HF Job、加载权重、运行 inference、访问私有评估案例、训练或提交 GPU 任务。

## 1. P3 完成基线

权威 P3 结果见 `docs/R60_P3_MODEL_STATIC_PREFLIGHT_20261110_CN.md`。

- 最终代码 HEAD（P3 验收时）：`a94268355fc590587f117fec0e5bb3cb8cf6ec45`；五组 Actions 全部 PASS。
- SAFE：`storyforge_r60_p3_cpu_preflight_safe_v3`，状态 `P3_SYNTHETIC_CPU_PREFLIGHT_PASS__GENERATION_PROFILE_PENDING`。
- 三模型固定 Revision、模板来源/SHA、270 synthetic tokenization、28,672 input + 4,096 output = 32,768 context 已通过。
- 三模型 tokenizer/config/template 共 18 个文件；不包含权重。
- 本轮无模型权重加载、无 inference、无 HF Jobs、无 GPU、无真实私有案例 Tokenization。
- Profile 当前仍为 candidate；`profile_freeze_authorized=false`、`inference_authorized=false`、`gpu_authorized=false`、`training_authorized=false`。

## 2. P4 目标与非目标

目标：在固定运行时、显式 generation profile 和可复现 SAFE 记录下，验证三模型实际生成接口、Thinking 行为、stop/finish_reason、预算遵守情况，并在获准的数据范围内开展小规模盲评。

不做：
- 不做 SFT、LoRA、训练数据构建或质量准入。
- 不做 1,000 条批量审核。
- 不把 AI 自动评分直接转换成 Owner 裁决。
- 未获单独授权，不读取或上传任何真实私有案例。
- 不把 P3 的模板来源裁决误当作完整 Generation Profile 冻结。

## 3. P4 前必须完成的 Generation Profile 决策

以下均须形成版本化配置、来源依据和 Owner 明确确认；未解决时不得启动模型推理：

| 项目 | Qwen A | GLM-4 B | GLM-Z1 challenger |
|---|---|---|---|
| Revision | P3 已固定 | P3 已固定 | P3 已固定 |
| Chat Template | Embedded SHA 已固定 | Standalone SHA 已固定 | Standalone SHA 已固定，含 `<think>` |
| Thinking 行为 | `enable_thinking=true` 已有候选值 | 明确是否启用/如何表达 | 确认 standalone 的 Thinking prefix 与目标一致 |
| Sampling | 现有候选：temperature 0.6 / top_p 0.95 / top_k 20 / min_p 0 | 制定 GLM 专属策略，不继承 Qwen 参数 | 解决模型卡 greedy 示例与 sampling 表冲突 |
| Seed | 待定 | 待定 | 待定 |
| Input / output budget | 28,672 / 4,096 为 P3 共享候选预算；P4 执行策略待确认 | 同左 | 同左 |
| Runtime / engine | 固定容器、Python、Transformers、推理引擎版本及 digest | 同左 | 同左 |
| Stop / EOS | 明确 stop token、EOS IDs、截断策略 | 同左 | 同左 |
| Finish reason | P4 实测 | P4 实测 | P4 实测 |

特别说明：
- GLM-Z1 sampling-vs-greedy 是未解决的真实配置冲突；不能凭 P3 模板测试替 Owner 决定。
- GLM-4 的 sampling policy 不得简单复制 Qwen。
- 三个模型里 GLM-4 与 GLM-Z1 属同一 GLM4 模板/架构家族；评估报告不得把它们当成两个完全独立的模型家族证据。
- 任何 profile 的冻结均需独立授权；P3 candidate JSON 的授权布尔值继续保持 false。

## 4. Hugging Face 执行方式

采用 Hugging Face Jobs 作为一次性远程计算，不要求在 Owner Mac 下载 32B 模型权重，也不要求长期运行 Endpoint。

推荐执行方式（仅为获批后的方案）：
1. 使用固定 Docker image 或可复现 UV 环境；锁定 Python、Transformers、推理引擎和 CUDA 相关依赖。
2. 每个模型使用固定 Hub revision；运行时从 Hub 拉取权重到 Job ephemeral storage，记录 snapshot revision、文件清单、权重文件大小和 SHA/Hub LFS OID（若可得）。
3. 每个模型单独 Job，串行执行，避免三模型同时占用 GPU；任务结束后自动退出。
4. SAFE、日志和必要评估产物写入指定私有 HF Bucket / 获准的持久化位置；Job ephemeral disk 不作为唯一结果存储。
5. 所有 Job 设置硬 timeout、显式 flavor、唯一 run ID、代码 commit SHA、配置 SHA 和输出 manifest。
6. Job 启动前先确认账户正余额、硬件 flavor 当前可用性及当时价格；实际创建 Job 必须有 Owner 的单独明确授权。

HF Jobs 按所用硬件运行时间按分钟计费；Start/Running 才计费，Build 阶段不计费。硬件/价格会变化，执行前必须重新核验官方页面或 `hf jobs hardware` / Jobs API。

## 5. 初步硬件与资源预算（非授权报价）

官方 Jobs 价格页在 2026-11-10 检索到的候选规格：

| Flavor | GPU 显存 | CPU / RAM | 参考单价 | 本项目用途 |
|---|---:|---:|---:|---|
| 1x H200 | 141 GB | 23 vCPU / 256 GB | $5.00 / 小时 | **首选候选**：单个 32B BF16 模型串行验证 |
| 1x A100 | 80 GB | 12 vCPU / 142 GB | $2.50 / 小时 | 低成本备选；32B BF16 权重约 64GB，长上下文 KV cache 与 runtime 余量可能不足，须实测 |
| 2x A100 | 160 GB | 24 vCPU / 284 GB | $5.00 / 小时 | 备选；需额外验证 tensor-parallel 支持与启动开销 |
| 4x A100 | 320 GB | 48 vCPU / 568 GB | $10.00 / 小时 | 仅当单卡/双卡方案不满足显存或吞吐要求时考虑 |

硬件选择原则：
- 首轮优先试 1x H200 141GB，单模型、低并发、短输出；并非宣称已验证一定可加载。
- 32B 参数模型按 BF16 两字节权重粗算约 64GB，实际显存还需容纳 KV cache、CUDA context、临时张量和 runtime 开销。因此 A100 80GB 仅作有风险备选，不作为首选。
- 不默认使用量化，因为量化可能改变评估行为；若考虑量化，必须作为独立 profile 并经 Owner 批准。
- 不默认使用多 GPU；只有实测证明单 H200 不可行后再评估 tensor parallel。

### 建议的分阶段费用上限

| 阶段 | 工作 | H200 预算时长 | 费用上限 |
|---|---|---:|---:|
| P4.1 Smoke | 3 模型串行加载/接口 smoke，每模型最多 1 小时 | 3 GPU-hours | $15 |
| P4.2 Synthetic runtime pilot | 每模型最多额外 2 小时，验证生成参数、Thinking、stop/finish_reason 与预算 | 6 GPU-hours | $30 |
| 失败重试预留 | 仅限定位明确的环境/启动失败，最多 2 小时 | 2 GPU-hours | $10 |
| **合计硬上限** | 分阶段审批，不一次性预付或自动连续运行 | **11 GPU-hours** | **$55** |

该预算只估算 H200 GPU 运行时间，不含可能产生的网络、存储、税费或额外资源费用；按分钟计费的实际金额取决于真实启动/运行时长。每阶段到达上限即停止，不能自动升级硬件或延长任务。若阶段预算不足，先提交 SAFE 和成本实绩，等待 Owner 再授权。

### 后续真实案例盲评预算（不包含在 $55 内）

P4.3 暂不定量、不报价。必须先确认：
- 使用哪一批已获准的案例、数量和字段范围；
- 数据是否允许进入 HF Job 环境，及是否使用私有 Bucket 挂载；
- 三模型是否全部生成，评估输入/输出 Token 上限；
- 盲化、随机顺序、结果保存、AI Advisory 与 Owner final 的隔离方式；
- 是否需要第二阶段 GPU 预算。

未经这些确认，不读取、不上传、不推理任何真实私有案例。

## 6. P4 执行顺序与验收

### P4.0 — Profile freeze review（无 GPU / 无 inference）

- 完成上表所有模型特定决策。
- 固定 runtime/container digest、依赖 lock、generation config、seed、budget、stop/EOS。
- 对 GLM-Z1 sampling-vs-greedy 冲突形成有来源的决策记录。
- 生成 profile manifest 与 SAFE dry-run。
- Owner 单独批准 profile freeze 后，才可进入 P4.1。

### P4.1 — Synthetic smoke（需要单独 GPU / inference 授权）

- 每次只启动一个模型的 H200 Job。
- 仅使用合成 prompt；每模型最多 3 个 smoke prompt，短输出上限 256 tokens。
- 验证模型加载、首 token、输出结构、Thinking 前缀/关闭行为、EOS/stop 和 finish_reason。
- 保存 Job ID、flavor、实际运行分钟数、runtime digest、模型 revision、配置 SHA、SAFE。
- 任一模型失败即停止该模型，不自动切换参数或硬件。

### P4.2 — Synthetic runtime pilot（需要单独追加授权）

- 每模型最多 10 个固定 synthetic prompts。
- 先验证 4,096 output budget 的执行与停止行为；必要时先使用较小 max_new_tokens 逐级增加。
- 报告 token/s、首 token 延迟、总耗时、峰值显存、OOM、finish_reason、结构有效率。
- 不用此 pilot 结果替代内容质量盲评。

### P4.3 — Blind evaluation（另行授权）

- 先确定案例范围和数量，建议从小批开始；不能自动使用全量 1,000 条。
- 三模型共用完全相同输入、Rubric v2.1、输出 Schema、预算和盲化流程。
- 输出只作为模型比较证据；Owner 复核与训练准入仍按独立流程执行。
- 真实案例评估所需 GPU 费用另行估算、单独批准。

## 7. 费用控制与停止条件

- Job 必须设置 timeout；每模型独立 Job；禁止 daemon/常驻 Endpoint。
- 禁止在失败后自动重试整个模型下载或无限重试；仅允许预算内、原因明确的重试。
- 每次提交前显示 flavor、预计小时数、费用上限、模型 revision 和数据范围，等待 Owner 明确授权。
- 任何 OOM、模型 Revision 不符、runtime digest 不符、输出协议错误、finish_reason 不可解释或 SAFE 缺失，立即停止该阶段。
- 不允许自动扩大 context、改变 sampling、切换量化或更换硬件来绕过失败。
- GPU job 完成后检查并确认停止，核对最终计费时长。

## 8. 当前授权状态

| 能力 | 当前状态 |
|---|---|
| P3 CPU-only preflight | PASS |
| P4 Generation Profile freeze | NOT AUTHORIZED |
| HF GPU Job submission | NOT AUTHORIZED |
| Model weights download to remote Job | NOT AUTHORIZED |
| Inference | NOT AUTHORIZED |
| Private-case evaluation | NOT AUTHORIZED |
| 1,000-case batch review | NOT AUTHORIZED |
| SFT / training | NOT AUTHORIZED |

**当前允许的工作仅限：文档、静态配置审查、合成测试代码和资源预算准备。** 任何 P4 实际执行均须 Owner 后续单独授权。

## 9. 官方 HF 资源依据（执行前重新核验）

- Jobs 运行和管理：<https://huggingface.co/docs/huggingface_hub/main/en/guides/jobs>
- Jobs Pricing：<https://huggingface.co/docs/hub/en/jobs-pricing>
- Jobs Configuration / hardware flavor：<https://huggingface.co/docs/hub/en/jobs-configuration>

检索日：2026-11-10。本文价格为当日官方页面参考价，不构成账户报价或资源可用性保证。
