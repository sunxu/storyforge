# R60 P4 正式 Generation Profile：Owner 裁决与冻结准备（2026-11-10）

> 状态：`OWNER_ADJUDICATION_PACKET_READY__PROFILE_NOT_FROZEN`
> 本文件只整理已确认决定、真实 Runtime Smoke 证据和冻结前未决事项。它不代表 Owner 已批准本文件中的建议，不冻结 Profile，不授权正式推理、GPU 评估或训练。

## 1. 当前基线与执行边界

- 仓库：`sunxu/storyforge`；分支：`r60/p4-generation-eval-framework`。
- 本文基于代码 HEAD `929fe58857a201d10e4dc353ba0d6353de1da7c8`。
- P0/P1/P2-A/P2-B/P3 已完成；P3 三模型 18 个 Tokenizer/Config/Template 文件、Revision、模板 SHA 和 32,768 Token 预算已固定。
- 2026-11-10 已完成一次 Owner 单独授权的三模型真实 GPU Runtime Smoke：HF Job `adradar/6af2dbbdab34849891aaef1e`，A100-SXM4-80GB，3/3 PASS。SAFE 位于 `reports/r60/p4/R60_P4_RUNTIME_SMOKE_SAFE_20261110.json`。
- 本次 Smoke 仅使用一条内置合成提示，每模型 `max_input_tokens=256`、`max_new_tokens=32`。它验证模型加载、BF16、Tokenizer/Template 加载和短生成路径；不验证 28,672 输入 / 4,096 输出的长上下文显存余量，不验证真实评估案例，不构成正式推理授权。

当前仍必须保持：
- `profile_freeze_authorized=false`（等待 Owner 单独裁决）；
- `inference_authorized=false`；
- `gpu_authorized=false`（Smoke 的一次性授权已消费，不得视为持续授权）；
- `training_authorized=false`。

## 2. 已经由 Owner 确认的实验设计（不是 Profile 冻结）

| 项目 | 已确认内容 |
|---|---|
| 模型 A | `Qwen/Qwen3-32B`，Revision `9216db5781bf21249d130ec9da846c4624c16137`，Thinking，官方采样 `do_sample=true, temperature=0.6, top_p=0.95, top_k=20, min_p=0` |
| 模型 B | `zai-org/GLM-4-32B-0414`，Revision `8dea913c41b543527c2860fb6f3c15c202f24aeb`，主配置 `do_sample=true, temperature=1.0, top_p=1.0, top_k=50`。这是模型卡示例 `do_sample=true` 加显式 Transformers 4.57.1 中性基线，不宣称是 GLM 官方推荐超参数 |
| Challenger | `zai-org/GLM-Z1-32B-0414`，Revision `8eb2858992c1f749e2a6d4075455decc2484722d`，主配置 greedy `do_sample=false`；模型卡 sampling 表 `0.6/0.95/40` 仅作为 Development20 敏感性变体 |
| 采样对照 | GLM-4 greedy 仅用于 Development20；GLM-Z1 sampling 仅用于 Development20；Locked30 不得用于调参 |
| 随机种子 | base seed `42`；稳定样本顺序，记录 `base_seed + stable_input_index` 的 per-sample effective seed |
| Token 预算 | context ceiling `32,768`；input `28,672`；generation `4,096`，且 generation budget 包含 reasoning tokens |
| 截断 / Stop | 超过 input budget 拒绝，不静默截断；按 pinned EOS IDs 分类 `eos` / `length`；无法解释的停止原因 HOLD |
| Rubric | `r60_severity_rubric_v2_1`；同一评估输入使用相同 Rubric / 输出协议 |

采样决策来源：`docs/R60_P4_SAMPLING_POLICY_DECISION_20261110_CN.md` 和 `experiments/r60_quality/r60_sampling_decision_candidate_v1.json`。Owner 在 PR #30 讨论中确认的是实验设计，不是冻结或执行授权。

## 3. 三模型真实 Smoke 的证据边界

| 角色 | Smoke 观察 |
|---|---|
| A / Qwen3-32B | BF16、CUDA 驻留、模板与 Tokenizer 校验 PASS；短生成结束原因为 `length` |
| B / GLM-4-32B-0414 | BF16、CUDA 驻留、模板与 Tokenizer 校验 PASS；短生成结束原因为 `eos` |
| Challenger / GLM-Z1-32B-0414 | BF16、CUDA 驻留、模板与 Tokenizer 校验 PASS；短生成结束原因为 `length` |

注意：当前 Smoke 调用从 Profile 读取 `enable_thinking`。A 为 true；B 和 Challenger 在当前 Profile 中均为 null。因此 Challenger Smoke 并未验证采样决策文件提出的 `thinking=true` / `<think>` generation prefix。不能将 3/3 Runtime Smoke PASS 扩大解释为 GLM-Z1 Thinking 行为已经验收。

## 4. 冻结前必须解决的配置 / 实现不一致

### 4.1 Development20 缺少主配置基线臂

当前采样候选把每个 `primary` variant 的 `evaluation_split` 设为 `p4_locked30`，而 GLM-4 greedy 与 GLM-Z1 sampling sensitivity variants 只设为 `development20`。这导致敏感性变体在 Development20 上没有同模型 primary baseline 可配对，无法严格估计 sampling-policy 差异。

建议：为 Development20 明确生成同模型 primary baseline。至少 GLM-4 primary sampling 与 greedy sensitivity 必须在同一 Development20 样本上成对运行；GLM-Z1 primary greedy 与 sampling sensitivity 同理。建议 Qwen primary 也在 Development20 跑一次，作为跨模型共同基线。Locked30 只跑冻结的 primary 配置，不参与调参。Owner 需确认 Development20 的确切 arm matrix 与运行次数。

### 4.2 GLM-Z1 Thinking / `<think>` 未落到正式 Profile 和 Backend

采样决策候选写明 Challenger `thinking=true`、`chat_template_generation_prefix="<think>"`；但 `p4_generation_profile_candidate_v1.json` 当前 `enable_thinking=null`，没有记录 prefix。当前 Backend 只把非 null 的 `enable_thinking` 传给 `tokenizer.apply_chat_template`，没有独立的 generation-prefix 字段或处理逻辑。

建议：Owner 明确 GLM-Z1 的正式目标是以 pinned standalone template 产生 `<think>` 起始的 assistant generation；随后在 Backend 中实现可验证、不会重复添加 prefix 的方式，并增加 CPU synthetic template-render/token-ID tests。不能只在 JSON 中写 `thinking=true` 而不证明实际输入 token 序列包含预期 prefix。

### 4.3 GLM-4 的 Thinking 语义仍写成 null

GLM-4 Profile 的 `enable_thinking=null` 当前代表不向 `apply_chat_template` 传该参数，但文档没有把它定义为明确的 `template_default` / no-extra-prefix 行为。建议 Owner 确认 GLM-4 主配置使用 pinned standalone template 的原生默认 assistant prefix，不额外注入 `<think>`，并将其作为显式可审计配置记录。

### 4.4 评估 Prompt / 输出 Schema 尚未绑定到 Profile

当前 Profile 绑定 Rubric 版本、模型与模板 hash，但仓库尚未形成并绑定唯一的 P4 evaluation prompt 文件、输出 JSON Schema 文件及其 SHA-256。仅绑定 Rubric 版本不足以证明三个模型收到完全相同的指令与结构约束。冻结前必须确定：system/developer/user prompt 结构、三维输出字段、引用证据字段、三态标签、拒答 / 证据不足表达、JSON 修复是否允许（建议不允许静默修复），以及 prompt/schema 的版本和 SHA。

### 4.5 32K 预算尚未在 A100 Smoke 中验证

本次 A100 Smoke 只使用 256 input / 32 output tokens。A100 上短 Smoke 的峰值显存约 60.7–61.1 GiB，不能证明 28,672 input + 4,096 generation 在单卡 80GB 上安全。既有 P4 执行计划把 1x H200 141GB 作为长上下文 32B BF16 的首选候选，A100 仅为有显存风险的低成本备选。Owner 需确认正式评估硬件 / 单模型 Job 预算；不能把本次 A100 Smoke 当作长上下文容量验收。

### 4.6 一次性 Smoke 授权需要关闭 / 标记已消费

当前 candidate JSON 中 `runtime_smoke_authorized=true` 是一次性授权，但 Smoke 已执行完成。冻结候选应将其标记为 `false` 或以不可复用的授权回执状态标记为 `CONSUMED`，避免后续任务把旧授权当成持续授权。正式 inference / GPU 仍保持 false。

### 4.7 Freeze-only Validator 尚未独立实现

`profiles.assess_profile` 目前只有 `generation` 与 `runtime_smoke` 两种 purpose；`generation` 同时要求 profile freeze、inference、GPU 三个授权均为 true。它没有一个可以在 inference/GPU 仍关闭时，单独验证“Profile 完整、可供 Owner 冻结审阅”的 freeze-review purpose。正式冻结前应增加 CPU-only `freeze_review` assessment：校验完整 Profile、sampling matrix、thinking/prefix、prompt/schema hashes、runtime/lock/model fingerprints，但不得要求或打开 inference/GPU/training 授权。

### 4.8 私有评估输出持久化路径尚未闭环

ChatGPT 直连 HF Jobs 已通过；Bucket RO 读取成功，但 ChatGPT 上下文下 Bucket RW / Xet write-token 仍 403。SAFE 可以从 Job logs 回收；真实评估生成正文属于私有产物，不得输出到 logs。进入真实案例评估前必须验证一个可写、可回收、权限受控的私有输出通道；不得以 SAFE log 回收替代私有输出存储。

## 5. Owner 需要逐项确认的决定

以下均为待确认，不应由 Agent 自动裁决：

1. **Development20 arm matrix**：是否按建议在相同 20 个 Development cases 上运行 Qwen primary、GLM-4 primary + greedy、GLM-Z1 primary + sampling？是否接受每条 case 的模型/variant 成对比较？
2. **Locked30 组成和用途**：是否确认 Locked30 = Gold72 Locked20 + R60 Severe10；仅运行冻结 primary 配置，不进行任何参数选择或 prompt 调整？
3. **GLM-Z1 Thinking**：是否确认正式生成必须按 pinned standalone template 以 `<think>` prefix 开始？允许实现显式 prefix 控制及 token-level 验证吗？
4. **GLM-4 Thinking**：是否确认使用 pinned template 原生默认行为，不额外传入 thinking flag 或 prefix？
5. **Prompt / Schema**：是否批准先制作一套三模型完全相同、版本化并 hash-pinned 的 P4 evaluation prompt 与 JSON Schema，供 Owner 审阅后冻结？
6. **预算和硬件**：是否保留 input 28,672 / generation 4,096（reasoning included）；正式真实案例评估优先按既有计划使用单模型串行 H200，另行核准预算？
7. **评估判定标准**：是否以 Owner reference 为最终依据，报告三维 SUPPORTED precision/recall/F1、INSUFFICIENT_CONTEXT detection、严重漏报/误报、Safety false negative、exact quote validity、semantic evidence support、schema completion、finish_reason、latency/cost；不设置未经 Owner 批准的自动胜出阈值？
8. **私有产物存储**：真实评估生成正文和逐案输出应写入哪个已验证私有位置？在 Bucket RW 修复前，是否授权采用独立、受控的 Owner Mac 同步回收路径；若未确认则不启动真实案例推理？

## 6. 冻结前执行清单（CPU-only）

- [ ] 将已批准的主实验 sampling 配置与 P4 Profile 做机器可验证的一致性检查。
- [ ] 修正 Development20 primary baseline / sensitivity variant 的配对矩阵。
- [ ] 将 GLM-4 / GLM-Z1 Thinking 行为和 generation prefix 写成显式配置，并补充 token-level synthetic tests。
- [ ] 生成并固定 P4 prompt、Rubric 引用、输出 Schema 文件及 SHA-256。
- [ ] 将实际 HF Runtime Smoke 结果回填到 Profile 元数据；把一次性 Smoke 授权标记为已消费。
- [ ] 选择正式长上下文 GPU flavor，并单独核对预算；不能沿用短 A100 Smoke 的显存结论。
- [ ] 实现 CPU-only freeze-review validator，确认 profile freeze 可独立于 inference/GPU 授权进行。
- [ ] 验证真实私有输出的安全持久化 / 回收路径，不将私有生成正文写入日志。
- [ ] 生成 `P4_PROFILE_OWNER_REVIEW_SAFE`，只报告配置版本、hash、阻塞项和授权状态。
- [ ] Owner 明确批准后，才把 `profile_freeze_authorized` 改为 true 并生成不可变 Frozen Profile SHA。

## 7. 冻结后仍需单独授权的工作

Profile freeze 不自动授权：
- Development20 synthetic / sensitivity inference；
- Locked30 held-out inference；
- 任何 GPU Job、硬件 flavor、timeout、费用上限和私有数据挂载；
- 任何 1,000 条批量审核、LoRA、SFT 或训练。

建议按 Development20 小批验证、结果回看、再单独申请 Locked30 的顺序执行。Locked30 不得用于采样、Prompt 或 Schema 调整。

## 8. 相关文件

- `experiments/r60_quality/p4_generation_profile_candidate_v1.json`
- `experiments/r60_quality/r60_sampling_decision_candidate_v1.json`
- `docs/R60_P4_SAMPLING_POLICY_DECISION_20261110_CN.md`
- `docs/R60_P4_GENERATION_EVALUATION_PLAN_20261110_CN.md`
- `docs/R60_P4_GENERATION_EVAL_FRAMEWORK_20261110_CN.md`
- `docs/R60_P4_RUNTIME_AND_STOP_POLICY_20261110_CN.md`
- `reports/r60/p4/R60_P4_RUNTIME_SMOKE_SAFE_20261110.json`

本文件状态必须保持 `OWNER_ADJUDICATION_PACKET_READY__PROFILE_NOT_FROZEN`，直到 Owner 决策和后续 CPU-only 复核全部完成。

## 2026-11-10 Owner 接受建议后的实施记录

Owner 已接受本文件中的实验矩阵与 GLM Thinking 建议。已落实到分支候选配置和 CPU-only 合约：

- 三个模型均增加 `development_primary`，与各自 Locked30 primary 使用相同采样策略、但只在 Development20 运行。
- GLM-4 greedy sensitivity 与其 Development20 primary 配对；GLM-Z1 sampling sensitivity 与其 Development20 greedy primary 配对。
- Locked30 明确 `primary_only`，禁止用于采样调优。
- GLM-Z1 Profile 明确 `thinking_mode=explicit_generation_prefix`、`generation_prefix=<think>`；Backend 在 chat template 之后确保该 prefix 只出现一次，并计入 input token budget。
- GLM-4 明确 `thinking_mode=template_default`，不额外注入 prefix。
- Qwen 明确 `thinking_mode=api_flag`，沿用 `enable_thinking=true`。
- 已新增统一 Prompt 候选及输出 JSON Schema 候选，并把其 SHA-256 绑定进 P4 candidate；二者状态仍为 `OWNER_REVIEW_PENDING`，因此 freeze_review 仍 HOLD。
- 已将一次性 Runtime Smoke 授权标记为 `CONSUMED_2026-11-10`，并关闭 `runtime_smoke_authorized`。
- 新增 `freeze_review` CPU-only assessment purpose；它独立于 inference/GPU 授权，但要求 Prompt/Schema 完整且 Owner contract approval 明确。

新增文件：
- [统一评估 Prompt 候选](R60_P4_EVALUATION_PROMPT_CANDIDATE_V1_CN.md)
- [评估输出 Schema 候选](../experiments/r60_quality/r60_p4_evaluation_output_schema_candidate_v1.json)

**仍未完成 / 未授权：** Prompt 与 Schema 的最终 Owner 审批、真实长上下文硬件选择、私有输出持久化通道验证、正式 Profile 冻结、Development20 inference、Locked30 inference、GPU 与训练。


## 2026-11-10 Owner 对评估契约的正式批准

Owner 已明确批准统一评估 Prompt v1 与 Output JSON Schema v1。批准对象由以下 SHA-256 唯一标识：

- Prompt：`51465853db6a2b61a9f87b1e9d5f23f7f02bd2c98b5a0d6a8ab2ec61322346e1`
- Output Schema：`e6371bf3319affcae190b6ccb9a1b8ce778bae440a91eefe39a65b2586930d70`

该批准仅覆盖评估指令与输出结构，不等于 P4 Generation Profile 冻结，不授权读取真实评估案例、模型推理、GPU Job、Locked30 或训练。机器可读 Profile 将 `evaluation_contract_status` 更新为 `OWNER_APPROVED`，但 `profile_freeze_authorized`、`inference_authorized`、`gpu_authorized`、`training_authorized` 继续保持 false。

## 2026-11-10：Owner 批准评估契约与联合 Freeze Review

Owner 已批准 Prompt v1 与 Output JSON Schema v1。批准只针对这两份内容，分别以 Profile 中记录的 SHA-256 为准；未授权 Profile freeze、真实数据访问、推理、GPU Job、Locked30 或训练。

新增/完善的 CPU-only Freeze Review 入口：

    PYTHONPATH=src python -m storyforge_dataset.generation_eval \
      experiments/r60_quality/p4_generation_profile_candidate_v1.json \
      --purpose freeze_review

该入口同时校验：
- P4 Profile 的三模型 Revision、Tokenizer/Template/Generation Config fingerprints、EOS/PAD、sampling 与 token budget；
- Owner-approved Prompt/Schema receipt 与两份文件的 SHA-256；
- Development20 primary/sensitivity arm matrix 与 Locked30 primary-only 禁调参约束；
- Profile freeze、inference、GPU、training 授权继续关闭。

通过时输出 P4_FREEZE_REVIEW_READY_NOT_FROZEN，只代表 CPU 配置检查通过，不会冻结 Profile，不会创建 HF Job，也不会加载权重或启动推理。CI 将保存不含私有案例或生成正文的 SAFE artifact：r60-p4-freeze-review-safe。

仍待解决：
1. 正式长上下文硬件 / 单模型运行预算的 Owner 确认。H200 是当前候选，不是已授权资源。
2. HF Bucket /output:rw 对本 P4 Job 的真实可写性与回收路径验证。历史 Bucket 中存在旧评估产物，证明该 Bucket 曾被写入，但不等于本次运行身份和挂载已验证。此前 ChatGPT 直连 Xet 写入曾返回 403；不得把该路径标为当前已验收。
3. 当前 Job plan 引用的 python -m storyforge_dataset.generation_eval.worker CLI 交付及端到端本地/合成验收。
4. 以上完成后再由 Owner 单独决定是否冻结 Profile；Freeze 不自动授权推理或 GPU。

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