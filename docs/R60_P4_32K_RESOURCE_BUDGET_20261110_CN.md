# StoryForge R60 P4 32K 长上下文资源预算（2026-11-10）

> 状态：**ENGINEERING_ESTIMATE__NOT_GPU_AUTHORIZATION**
>
> 本文件用于 Owner 的 Profile Freeze Review。显存数字分为短输入实测、KV cache 理论计算和长上下文未验证估算；不把估算写成 32K GPU PASS。

## 1. 固定执行边界

- 三模型分别运行、单 GPU、batch size=1、串行，不并发加载。
- 共享上下文：32,768 tokens = 28,672 input + 4,096 generation；生成预算包含 reasoning tokens。
- BF16，不使用量化，不允许 CPU/disk offload。
- GPU 候选首选：1x NVIDIA H200 141GB。
- 每个模型独立 Job，硬超时 60 分钟；不自动重试、不自动换卡。
- 当前 profile_freeze / inference / GPU / training 授权全部 false；本预算不构成授权。

## 2. 已有短输入 GPU 实测基线

来源：`reports/r60/p4/R60_P4_RUNTIME_SMOKE_SAFE_20261110.json`，真实 A100-SXM4-80GB，固定镜像与代码 revision；每模型一条合成输入，输入 17–21 tokens，输出 9–32 tokens。

| 模型 | 峰值 allocated | 模型加载 | 本次总耗时 | 生成耗时 |
|---|---:|---:|---:|---:|
| Qwen3-32B | 61.05 GiB | 59.24 s | 64.39 s | 2.94 s / 32 tokens |
| GLM-4-32B-0414 | 60.67 GiB | 59.19 s | 61.54 s | 0.63 s / 9 tokens |
| GLM-Z1-32B-0414 | 60.67 GiB | 58.43 s | 62.18 s | 2.17 s / 32 tokens |

该结果证明三个模型在 A100 上完成过 BF16 短输入加载与生成；**没有测量 28,672-token prefill、4,096-token decode 或 32K 峰值显存**。短输入 Smoke 的 3/3 PASS 不得外推成 32K PASS。

## 3. 32K KV cache 理论估算

采用标准 BF16 K/V cache 粗算公式：

`KV bytes = 2 × layers × num_key_value_heads × head_dim × sequence_length × 2 bytes`

其中首个 2 表示 K 和 V；sequence_length=32,768；batch size=1。模型结构参数取各自固定 revision 的 config。

| 模型 | Layers | KV heads | Head dim | 32K KV cache |
|---|---:|---:|---:|---:|
| Qwen3-32B | 64 | 8 | 128 | 8.00 GiB |
| GLM-4-32B-0414 | 61 | 2 | 128 | 1.91 GiB |
| GLM-Z1-32B-0414 | 61 | 2 | 128 | 1.91 GiB |

这只是 KV cache 理论容量，不包含权重、CUDA context、prefill 临时张量、allocator fragmentation、logits、运行时与安全余量。GLM-Z1 与 GLM-4 使用相同 GLM4 架构配置。

## 4. 显存容量判断

把短输入实测峰值 allocated 与理论 32K KV cache 相加，作为非常粗略的对照，不当作实测：

| 模型 | 短输入峰值 | 加 32K KV cache 后的粗估 |
|---|---:|---:|
| Qwen3-32B | 61.05 GiB | 69.05 GiB |
| GLM-4-32B-0414 | 60.67 GiB | 62.58 GiB |
| GLM-Z1-32B-0414 | 60.67 GiB | 62.58 GiB |

- A100 80GB 约 74.5 GiB 标称容量。Qwen 粗估后只剩约 5.4 GiB；GLM 约剩 11.9 GiB。还未计入 32K prefill 临时峰值与显存碎片，因此 A100 不适合作为首轮 32K 验收的默认选择。
- H200 141GB 约 131.4 GiB 标称容量。按上述粗估，Qwen 仍有约 62 GiB 标称余量，GLM 约 69 GiB。H200 是更稳妥的首选候选，但仍必须通过获批后的真实 32K 实测才能定案。
- RTX PRO 6000 96GB 约 89.4 GiB 标称容量，理论余量介于 A100 与 H200 之间；不作为首轮首选，避免在未测长上下文时以更小余量换取较低单价。
- 不推荐直接使用 2x A100 替代 H200：虽然总显存标称 160GB，但需要额外验证 tensor parallel、模型切分、通信与运行时支持，不能仅按显存相加判断。

## 5. 运行时间预算

短 Smoke 的模型加载约 58–59 秒，但没有 28,672-token prefill 数据。短输出阶段的 tokens/s 也不能可靠线性外推到 4,096 tokens。

因此当前不声称有可信的 32K 单模型完成时间预测。采用可审计的**资源上限**：

| 项目 | 预算 |
|---|---:|
| 单模型硬超时 | 60 分钟 |
| 三模型串行总上限 | 180 GPU-minutes / 3 GPU-hours |
| 自动重试 | 0 |
| 超时后的自动扩容/换卡 | 禁止 |

首次获批的 32K synthetic runtime 验证应记录：模型加载秒数、prefill 秒数、首 token 延迟、prompt tokens/s、decode tokens/s、总耗时、峰值 allocated/reserved、OOM、finish_reason、实际计费分钟。只有这组数据才能形成下一版经验时间预算。

任一模型超时、OOM、出现 CPU/disk offload、runtime/revision/hash 不符、finish_reason 无法解释或 SAFE 无法持久化，立即停止本阶段，不自动重试。

## 6. 费用上限（按 Hugging Face Jobs 官方价格页）

2026-11-10 检索的参考价格：

| GPU | 显存 | 参考价 |
|---|---:|---:|
| 1x H200 | 141GB | $5.00 / GPU-hour |
| 1x A100 | 80GB | $2.50 / GPU-hour |
| 1x RTX PRO 6000 | 96GB | $2.75 / GPU-hour |
| 2x A100 | 160GB | $5.00 / GPU-hour |

建议按 H200 预算：

| 阶段 | 上限 | 费用上限 | 授权状态 |
|---|---:|---:|---|
| P4.1：三模型 32K synthetic smoke（每模型最多 1h） | 3 GPU-hours | $15 | 未授权 |
| P4.2：后续 synthetic runtime pilot（每模型额外最多 2h） | 6 GPU-hours | $30 | 未授权，需另批 |
| 失败定位预留 | 2 GPU-hours | $10 | 未授权，需另批 |
| **总预算封顶** | **11 GPU-hours** | **$55** | 分阶段批准，不得自动连续执行 |

上述仅为 GPU 运行费用上限，不含税费、存储、网络或其他额外计费项目；实际价格与 flavor 可用性必须在 Owner 提交前重新核验。达到任一阶段上限立即停止。当前本轮没有提交 HF Job，没有新增 GPU 运行，GPU 消耗 0 GPU-hours，GPU 费用 $0。

## 7. Owner 裁决建议

1. 将 H200 141GB 作为 32K 首选硬件候选；不将 A100 80GB 作为默认 32K 方案。
2. 仅在 Worker CLI / Bootstrap CPU-only 工程验收完成后，Owner 再单独决定是否批准 Profile Freeze。
3. Profile Freeze 与 32K GPU synthetic smoke 必须是两个独立授权决定；本文件不授权任何 GPU / inference。
4. 首次 GPU 任务只允许单模型、单样本、batch=1、合成输入；每模型最多 60 分钟，三模型串行，先完成一个模型并复核 SAFE 后再决定下一模型。
5. 不读取 Development20 / Locked30 私有案例，不执行 1000 条审核或 SFT。

## 8. 证据来源

- 固定模型配置：Qwen3-32B `config.json`（revision `9216db5781bf21249d130ec9da846c4624c16137`）；GLM-4-32B-0414 `config.json`（revision `8dea913c41b543527c2860fb6f3c15c202f24aeb`）；GLM-Z1-32B-0414 的固定配置见 P4 profile 文件清单。
- Runtime 实测：`reports/r60/p4/R60_P4_RUNTIME_SMOKE_SAFE_20261110.json`。
- 官方价格：<https://huggingface.co/docs/hub/en/jobs-pricing>，检索日期 2026-11-10。执行前重新核验。
