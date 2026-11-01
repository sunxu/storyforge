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
- 新增 4 个合成测试，覆盖字段级诊断、隐私、单次纠错成功、纠错失败不写 checkpoint、非引用字段不可修改。HF CPU-only Sandbox 执行 `test_r58_hf_gpu_literary_reviewer`：10 tests，全部 PASS；未加载模型权重、未推理、未使用 GPU。
- 新代码提交：`2e290484b92a660c75a32b2f11773ff03fd10f0b`；Skill v0.1.3、技术规范及 SAFE Manifest 已更新，Manifest 中四个变更文件 SHA256/bytes 已复核匹配。
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
