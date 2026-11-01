# R58 A/B 13 条 HF GPU 文学盲审执行方案（未提交）

日期：2026-11-01  
状态：`OWNER_APPROVED__HF_CONNECTOR_403_BLOCKED__NO_GPU_JOB_STARTED`

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
  /bin/sh -lc 'set -eu; timeout --signal=TERM --kill-after=30s 6600s python /input/runner.py --slot A --model Qwen/Qwen3-32B --revision 9216db5781bf21249d130ec9da846c4624c16137 --input /input/source.private.jsonl --output-dir /output --phase pilot --max-model-len 32768 --max-output-tokens 2400'
```

### B — GLM-4-32B-0414

```bash
hf jobs run --namespace adradar --name r58-b-pilot13 \
  --flavor h200 --timeout 2h --detach \
  -v hf://buckets/adradar/jobs-artifacts/input_B-94c62666:/input:ro \
  -v hf://buckets/adradar/jobs-artifacts/output_B-4abd76e2:/output \
  vllm/vllm-openai@sha256:6ee133356d49ed24cee03dd0cda3d3980279a11c107ce3e752c89e76540f41c9 -- \
  /bin/sh -lc 'set -eu; timeout --signal=TERM --kill-after=30s 6600s python /input/runner.py --slot B --model zai-org/GLM-4-32B-0414 --revision 077b5c2f5c43bd3239fd605a0600229e8facbd4a --input /input/source.private.jsonl --output-dir /output --phase pilot --max-model-len 32768 --max-output-tokens 2400'
```

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
