# R58 A/B 13 条 HF GPU 文学盲审执行方案（未提交）

日期：2026-11-01  
状态：`A_PILOT_VALID__B_HOLD_NONEXACT_QUOTE__REPAIR_IMPLEMENTED__B_RETRY_APPROVAL_REQUIRED`

## 1. 目标与范围

对已完成 CPU Token 预检的 R58 13 条 blind pilot，分别运行 A/B 模型的独立文学审查。A/B 使用不同私有输入目录、不同输出目录、不同 HF Job；不挂载 Owner crosswalk，不读 R50，不训练，不自动授予 Quality-v1 准入。

Owner 已在 2026-11-01 明确批准 A/B 两个 H200 Pilot Job（各前 2 条、每个最多 2 小时，合计 GPU 预算约 ¥133.14）；此批准不包含剩余 11 条或训练。ChatGPT HF 连接已实际尝试向 `adradar` 提交 A Job，但 HF 返回 `403 Forbidden`，未获得 Job ID；随后只读检查 `adradar` Job 列表，没有发现新 Pilot。B 未提交。本次状态是平台权限阻塞，**不是缺少用户授权**。请优先检查当前连接对 `adradar` 的 GPU Job 提交权限；可使用已有 Mac HF CLI 以相同批准范围和固定命令启动，不需要再次申请这两个 Pilot 的用户授权。

每个槽位先运行 `--phase pilot` 的前 2 条。检查两条输出的结构、引用有效性和评审稳定性后，剩余 11 条必须另行审批，再运行 `--phase remaining`。不要把 13 条一次性提交。

## 2. 已固定模型与输入

| Slot | Model | Immutable revision | Private input |
|---|---|---|---|
| A | `Qwen/Qwen3-32B` | `9216db5781bf21249d130ec9da846c4624c16137` | `input_A-608d21e1/source.private.jsonl` |
| B | `zai-org/GLM-4-32B-0414` | `077b5c2f5c43bd3239fd605a0600229e8facbd4a` | `input_B-94c62666/source.private.jsonl` |

CPU Token 预检：A/B 各 13/13 PASS；最大 Prompt 分别 27,615 / 26,677；输出预留 2,400；上下文上限 32,768；均无超限。实际 staged runner 与 CPU 预检路径在 Transformers 4.57.1、`trust_remote_code=False` 下逐条比较，A/B 各 13/13 Token ID 序列完全一致。

## 3. 固定容器与 GPU

- Image：`vllm/vllm-openai@sha256:6ee133356d49ed24cee03dd0cda3d3980279a11c107ce3e752c89e76540f41c9`
- 对应 tag：`v0.32.0`，linux/amd64 manifest digest；不是 `latest`。
- 已在同一 digest 的 CPU-only HF Sandbox 中验证：vLLM 版本 0.32.0；`LLM`、`SamplingParams`、`StructuredOutputsParams`、`TokensPrompt` 均可导入；没有 CUDA 设备、没有加载模型、没有推理。
- vLLM 官方模型列表列出 `Qwen3ForCausalLM` 与 `Glm4ForCausalLM`（GLM-4-0414），与这两个模型架构匹配。
- GPU flavor：`h200`，141 GB VRAM，官方 Jobs 价格 $5/hour。
- 不选 `a100-large`：模型 safetensors 总量 A 约 65.52 GB、B 约 65.13 GB；现有 runner 将 `gpu_memory_utilization=0.80` 固定，A100 80 GB 的 80% 预算约 64 GB，低于权重文件体量，尚未计 KV cache 与运行时开销。H200 的 80% 预算约 112.8 GB，明显更合理。

## 4. 推理参数（由当前 runner 固定）

- `dtype=bfloat16`
- `max_model_len=32768`
- `max_num_seqs=1`
- `enforce_eager=True`
- `gpu_memory_utilization=0.80`
- `temperature=0`
- `max_tokens=2400`
- JSON Schema constrained output
- `trust_remote_code=False`
- 不允许自动重试；失败后检查 SAFE 错误码，不得自动重复计费提交。

## 5. 双层硬超时与预算

每个 GPU Job：HF Jobs `timeout=2h`；容器内使用 GNU coreutils `timeout --signal=TERM --kill-after=30s 6600s`（110 分钟）包住 Python 命令。当前 reviewer CLI 没有 `--max-wall-seconds` 参数，不得假称已存在；用 shell timeout 提供第二层进程截止。

HF Jobs 官方按分钟计费，Starting/Running 阶段计费，build 阶段不计费。H200 $5/hour：

- **Pilot 2 条：** A、B 两个 Job，各最多 2 小时，GPU 费用上限 $20，按 2026-11-01 参考汇率 1 USD = ¥6.6568，约 **¥133.14**。
- **剩余 11 条：** 需 Pilot 结果经 Owner 审阅并另行批准；另两个 Job 最多 $20，约 ¥133.14。
- **完整 13 条 A+B：** 最多 4 个 Job、8 GPU-hours、$40，约 **¥266.27**。

以上为 GPU 硬件费用估算，不含可能的税费、支付渠道价差或汇率变化。Job 不暴露端口、不启用额外服务。A/B 可并行提交，合计上限不变。

## 6. 试运行命令

以下是 Owner 已批准的执行命令。ChatGPT 连接提交 A 失败（403），未启动 GPU；Mac HF CLI 可按相同命令继续。A/B 分开运行，输入只读，输出 Bucket 可写，每个 Job 仅处理前 2 条。提交成功后须先记录 Job ID 与状态，不可重复启动同一 slot。

### A — Qwen3-32B

```bash
hf jobs run --namespace adradar --name r58-a-pilot13 \
  --flavor h200 --timeout 2h --detach \
  -v hf://buckets/adradar/jobs-artifacts/input_A-608d21e1:/input:ro \
  -v hf://buckets/adradar/jobs-artifacts/output_A-6c62913b:/output \
  vllm/vllm-openai@sha256:6ee133356d49ed24cee03dd0cda3d3980279a11c107ce3e752c89e76540f41c9 -- \
  /bin/sh -lc 'set -eu; timeout --signal=TERM --kill-after=30s 6600s python3 /input/runner.py --slot A --model Qwen/Qwen3-32B --revision 9216db5781bf21249d130ec9da846c4624c16137 --input /input/source.private.jsonl --output-dir /output --phase pilot --max-model-len 32768 --max-output-tokens 2400'
```

### B — GLM-4-32B-0414

```bash
hf jobs run --namespace adradar --name r58-b-pilot13 \
  --flavor h200 --timeout 2h --detach \
  -v hf://buckets/adradar/jobs-artifacts/input_B-94c62666:/input:ro \
  -v hf://buckets/adradar/jobs-artifacts/output_B-4abd76e2:/output \
  vllm/vllm-openai@sha256:6ee133356d49ed24cee03dd0cda3d3980279a11c107ce3e752c89e76540f41c9 -- \
  /bin/sh -lc 'set -eu; timeout --signal=TERM --kill-after=30s 6600s python3 /input/runner.py --slot B --model zai-org/GLM-4-32B-0414 --revision 077b5c2f5c43bd3239fd605a0600229e8facbd4a --input /input/source.private.jsonl --output-dir /output --phase pilot --max-model-len 32768 --max-output-tokens 2400'
```

## 2026-11-01 A H200 首次提交及启动错误

Owner 使用 Mac HF CLI 提交 A，Job ID `6ae7615ac78863f9c62fb0de`；HF 返回 `ERROR exit 127`，running_secs=3，错误为 `timeout: failed to run command 'python': No such file or directory`。**未运行模型推理；输出 Bucket 没有生成 checkpoint。**

已在上述固定 digest 的真实 vLLM 容器、HF CPU Sandbox 核实：`python` 不存在，`/usr/bin/python3` 存在，`timeout` 存在；因此 A/B 命令统一使用 `python3`。还发现固定镜像中的 Transformers 为 `5.19.0`，不是 CPU 预检用的 4.57.1。使用实际 A/B staged `runner.py`、分别固定 Qwen/GLM revision 在该 vLLM 镜像中的 CPU-only `--preflight-only --phase pilot` 均已返回 `R58_HF_GPU_REVIEW_TOKEN_PREFLIGHT_PASS__NO_GPU_INFERENCE`，并未加载 GPU 模型。不能因此认定推理/显存完整兼容或所有 13 条跨运行时 Token IDs 相同。

**该错误修复不扩大 Owner 已批准的 A/B 两个 Pilot（2+2 条）范围。** 任何重新提交前需核对同槽位没有新 Job 在运行；现有错误 Job 不得冒充评审完成。费用仍以累计 GPU 使用时间衡量，不重复运行已成功生成的 checkpoint。

## A H200 Pilot 实际验收（2026-11-01）

- A 组重试 Job：`6ae762910e0338d1bb7d82dc`，由 Owner 的 Mac HF CLI 提交，`--phase pilot` 仅前 2 条。运行器 SAFE 输出为 `R58_HF_GPU_REVIEW_PILOT_VALID`，决策 PASS 2、HOLD 0、REJECT 0；`quality_v1_admitted=0`、`training_authorized=false`。
- HF 私有输出目录已读取到 `checkpoint_00.private.json`（2226 字节）与 `checkpoint_01.private.json`（4773 字节）。HF CPU 只读沙箱调用与 GPU 原始 Runner 相同的 `read_checkpoint` 验证：两个 checkpoint 与 blind source、slot、模型、完整 revision 全部匹配；两个结果均 PASS；引用字段分别有 source 2/8 段、target 5/8 段。没有将私人引用原文写入日志或 GitHub；验证沙箱完成后已终止。
- 此验收证明两条 checkpoint 的结构及机器引用契约完整，不代表独立文学质量裁定；B GPU Pilot 尚未提交，也未批准剩余 11 条。

## B H200 Pilot 暂停与引用错误（2026-11-01）

- B 组实际 Runner 返回 `R58_HF_GPU_REVIEW_HOLD`，SAFE 错误码 `RESPONSE_NONEXACT_QUOTE`；`quality_v1_admitted=0`、`training_authorized=false`、`private_text_emitted=false`。
- 只读盘点 B 私人输出目录：仍只有 `.keep`、`r58_cpu_preflight_all13_safe.json`、`r58_rw_probe.txt`；不存在 `checkpoint_00.private.json` 或 `checkpoint_01.private.json`。因此 B **0/2 checkpoint，不能视为完成 Pilot**。
- 原始校验器要求 `specific_source_quotes` 中每段引用必须是可见历史某一条 user/assistant 消息的连续原文子串；`specific_target_quotes` 必须是目标回复的连续原文子串。任何一个引用不匹配就抛出该错误，且在 `save_checkpoint` 前失败；无法据此推断文学分数好坏。
- 在当前输出存储缺少失败模型原始响应的情况下，不能确定是哪段引用不匹配。不要补造引用、放松 exact quote 约束、把 B 标为 PASS，亦不要直接重跑付费 GPU。
- 后续优先复用现有校验器设计 **仅 SAFE 的字段级诊断与最多一次受控纠错**，保持人工证据可审计；先完成合成测试和可重复 CPU 检查，再考虑在已有 2 条 Pilot 范围内进行受控重试。重试所需新的 GPU 费用应事前向 Owner 报告，不自动扩大原有预算或启动剩余 11 条。

## 2026-11-02 引用诊断与一次受控纠错修复

- B 的原始 SAFE 结果为 `R58_HF_GPU_REVIEW_HOLD` / `RESPONSE_NONEXACT_QUOTE`；B 输出 Bucket 没有两个 checkpoint。旧 Runner 未保存首次失败的原始生成响应，不能回溯确认具体哪段引用失败。
- 新 Runner 已加入 `QuoteValidationError`：SAFE 仅记录 case index、quote field、quote index、允许搜索的 source candidate count 和是否尝试纠错；不保存或输出引用文本。
- 仅引用精确性错误触发一次纠错。纠错 Prompt 使用同一原始评审输入和首次 JSON，重新计算 Token ID 与上下文预算；同一 Schema/模型/采样参数只再生成一次。纠错只允许修改两个引用列表，所有非引用字段逐字段保持完全一致。
- 纠错再次失败、预算超限、输出截断、JSON 无效或其他字段变化时 HOLD；失败响应不保存 checkpoint，不放宽严格连续子串规则。
- 新增 4 个合成测试，覆盖字段级诊断、隐私、单次纠错成功、纠错失败不写 checkpoint、非引用字段不可修改。HF CPU-only Sandbox 执行 `test_r58_hf_gpu_literary_reviewer`：11 tests，全部 PASS；未加载模型权重、未推理、未使用 GPU。
- 新代码提交：`2e290484`、`3f71783a`、`7b54f77d`、测试 `d1560625`；Skill v0.1.3、技术规范及 SAFE Manifest 已更新，Manifest 中四个变更文件 SHA256/bytes 已复核匹配。
- B 私人 STAGE 尚未刷新，新 Runner 尚未进入 B GPU Job。刷新前仍须确认 B 没有新 checkpoint；A 已有的两个有效 checkpoint 不得覆盖。B 再次提交属于额外付费 GPU Job，之前 B Job 已发生过运行费用，因此须先向 Owner 明确报告新增费用上限并取得批准。剩余 11 条和训练均未获授权。

## 7. 结果门禁

1. 两个 Job 完成后先核验状态、时长、日志 SAFE 摘要与输出 Bucket 文件清单。
2. 必须存在各自两个私有 checkpoint；每个 checkpoint 必须匹配对应 slot、source SHA、model 和完整 revision。
3. 只读取不含正文的 SAFE 计数作第一轮完整性检查；逐案评审结果保留在各自私有输出目录。
4. A/B 两个 Pilot 都通过结构/引用/证据核验后，向 Owner 汇报差异与风险。
5. 未获得第二次明确授权，不启动 `remaining` 阶段。任何 Token PASS、Job 完成或单模型 PASS 都不代表训练准入。

## 8. 官方资料

- HF Jobs pricing：<https://huggingface.co/docs/hub/jobs-pricing>
- HF Jobs timeout/volumes：<https://huggingface.co/docs/hub/jobs-configuration>
- vLLM Docker image digest：<https://hub.docker.com/layers/vllm/vllm-openai/v0.32.0/images/sha256-6ee133356d49ed24cee03dd0cda3d3980279a11c107ce3e752c89e76540f41c9>
- vLLM supported models：<https://docs.vllm.ai/en/latest/models/supported_models/>
- USD/CNY reference 2026-11-01：<https://www.currencybeacon.com/rates/USD/CNY>

## 2026-11-02 B 更新 Runner 的 CPU-only 预检

最新 GitHub Runner 与共享 Token 核心已在固定 vLLM 镜像中对 B 的 pilot 输入执行预检，模型 revision 固定为 077b5c2f5c43bd3239fd605a0600229e8facbd4a，结果 PASS，planned=2。该检查不加载权重、不执行推理、不产生 GPU 费用。B 输出目录仍无 checkpoint；任何付费 GPU 重试须另行取得 Owner 费用批准。

## 2026-11-02 B 组首轮 GPU 重试与第二版引用修复

### 首轮重试结果

- Job `6ae76bc3c78863f9c62fb5c4` 因镜像内没有 `python` 命令启动失败；未执行评审。
- Job `6ae76c010e0338d1bb7d8608` 因时间参数解析为 1 秒而超时；未执行评审。
- 正式首轮 Job `6ae76c1e0e0338d1bb7d8614` 使用 H200、GLM-4-32B-0414 完成模型加载，并处理第 1 条。SAFE 返回 `R58_HF_GPU_REVIEW_HOLD`，字段 `specific_target_quotes`、quote index 0；自由文本纠错仍不精确。运行约 104 秒，未保存任何 checkpoint，第二条未执行。旧 B 输出和 A 两个 checkpoint 均未改动。

### 第二版修复

- 修复从自由文本重写改为受限候选索引：模型只能输出 `candidate_index`；程序只从目标回复或可见历史单条 user/assistant 消息中提取原文句段，并替换失败引用位置。
- 候选最多 128 条，每条 8–300 字；不截断候选集合，不使用 unapproved_card；索引必须为有效整数。只允许一次纠错，最终仍执行原始严格连续子串校验。
- HF CPU 合成测试 `test_r58_hf_gpu_literary_reviewer`：12/12 PASS，覆盖目标引用端到端修复、来源候选、字段隔离和无效索引 HOLD。
- 新 B 私有输入与输出独立保存于 `hf://buckets/adradar/storyforge-r58-b-retry-20261102/input_B_retry2_20261102` 和 `.../output_B_retry2_20261102`。原始 674,509 字节输入与旧 B 输入字节一致；旧失败尝试目录保留。
- 固定 vLLM 镜像中最新 B Runner CPU-only Token 预检 PASS，planned=2；未加载模型权重、未推理、未使用 GPU。
- Skill 更新至 v0.1.4，技术规范已更新；本次修复不扩大评审范围、不启动剩余 11 条、不授予训练准入。

### 已批准预算执行约束

Owner 已批准本次 B 组 H200 重试总预算上限 ¥66.57（按 H200 $5/h、汇率 6.6568、总计不超过 2 小时估算）。前述两个启动失败约 8 秒和 4 秒，首轮实际评审约 104 秒。第二版 GPU Job 的 timeout 限为 117 分钟，连同前述运行时间，理论总时长不超过 2 小时。只运行 pilot 前两条；若 HOLD、失败或预算达到上限即停止，不自动扩大范围。

### 2026-11-02 第二版 B Pilot 最终结果

- Job `6ae76fef0e0338d1bb7d87ac` 使用 H200 + GLM-4-32B-0414，候选索引纠错 Runner。总运行约 109 秒后退出。
- `checkpoint_00.private.json` 已写入。独立 HF CPU SAFE 审计通过原始输入和模型 revision 调用 `read_checkpoint` 复核：checkpoint identity PASS、exact quote validation PASS、decision=PASS、6 个评分维度、source/target quote 各 1 条。
- 第 2 条未生成 checkpoint，SAFE reason `RESPONSE_SEVERE_MUST_REJECT`：模型输出的 severe flag 与 decision 不一致。未自动修改 decision，未降低门禁。
- B Pilot 目前只有 1/2 checkpoint 有效，整体 HOLD；不执行剩余 11 条，不启动训练。A 两个 checkpoint 与旧 B 输出保持不变。
- 本次 H200 Job 总耗时按 8.5s + 4.3s + 103.7s + 109.3s 估算为 225.8 秒；按 $5/h、汇率 6.6568，估算 GPU 费用约 ¥2.09（最终账单以 HF 为准），低于 Owner 批准的 ¥66.57 上限。到此停止本轮 GPU 重试，不自动追加 Job。

### 2026-11-02 下一步：严重标记 SAFE 诊断增强（CPU-only）

- 只读检查确认，旧 Job 的 `RESPONSE_SEVERE_MUST_REJECT` 只表示至少一个 severe flag=true 且 decision!=REJECT；旧 SAFE 未保留具体 flag 名称和 decision，原始模型响应未持久化，无法从旧 Job 还原。
- 原始 B 第 2 条输入的结构检查确认：三种严重标记名称传入 Prompt，但没有逐项阈值定义；该信息需要结合后续 SAFE 具体 flag 与样本证据判断，不能预先推断根因。
- Runner 新增 `SevereDecisionMismatch`，SAFE 仅输出 `case_index`、`model_decision`、`active_severe_flags`、`active_severe_flag_count`；不输出任何原始模型文本或故事内容。
- HF CPU 合成测试 12/12 PASS，覆盖 PASS/HOLD 与 active flag 的不一致、REJECT 与 active flag 的合法组合及 SAFE 隐私边界。
- Skill 更新至 v0.1.5；完整规则更新至 `docs/standards/R58_GPU_REVIEW_QUOTE_VALIDATION_CN.md`。
- 尚未创建新的私有 STAGE，尚未提交新 GPU Job；第 1 条 checkpoint 保留不动，剩余 11 条不启动，训练仍未授权。
