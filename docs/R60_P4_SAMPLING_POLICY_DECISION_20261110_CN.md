# R60 P4 逐模型采样策略与敏感性实验（2026-11-10）

## 决策范围

本文件将 Owner 对建议方案的确认落实为**实验设计**，不代表冻结 Generation Profile，也不授权真实推理、GPU Job、批量审核或训练。

引入 GLM-4 与 GLM-Z1 的目的，是为 Qwen 提供独立的质量审核对照与推理挑战者，检验 Player Agency、Hard Rule、Safety 三类严重判断中的漏报、误报、证据不足识别和引用语义支持能力。GLM-4 与 GLM-Z1 同属 GLM4 架构家族，不得作为两个独立模型家族进行多数投票。

## 逐模型主实验建议

| 角色 | 解码方式 | 参数 | 依据与限制 |
|---|---|---|---|
| A / Qwen3-32B | Thinking + sampling | do_sample=true, temperature=0.6, top_p=0.95, top_k=20, min_p=0 | 遵循 Qwen3 官方 Thinking 模式建议 |
| B / GLM-4-32B-0414 | sampling | do_sample=true, temperature=1.0, top_p=1.0, top_k=50 | 模型卡示例使用 do_sample=true，但未给采样值；显式记录 Transformers 4.57.1 的中性默认值，避免依赖隐式运行时默认。这不是 GLM 官方推荐超参数 |
| Challenger / GLM-Z1-32B-0414 | greedy | do_sample=false，不传 temperature/top_p/top_k/min_p | 采用模型卡 greedy 示例作为稳定基线；其 Thinking 模板仍以 <think> 启动 |

GLM-4 的正式主配置不采用此前讨论的 greedy：其模型卡推理示例使用 do_sample=true。由于模型仓库 generation_config 未固定 temperature/top_p/top_k，不能把 Qwen 参数移植到 GLM-4。本方案使用显式、可追溯的中性基线，并把 GLM-4 greedy 仅作为 Development20 敏感性对照。

GLM-Z1 的模型卡同时给出 greedy 示例与 sampling 表。本方案不把两种文档证据强行解释成唯一正确答案：greedy 作为主实验稳定基线，官方 sampling 表（temperature=0.6、top_p=0.95、top_k=40）作为 Development20 敏感性对照。两种设置使用相同的 prompt、Rubric、Schema、上下文和输出预算。

## 开发集敏感性实验

- GLM-4：Development20 上比较主配置 sampling 与 greedy。
- GLM-Z1：Development20 上比较主配置 greedy 与模型卡 sampling 表。
- Qwen：保持官方 Thinking sampling，不增加额外调参臂。
- 所有变体使用 base seed=42、稳定样本顺序，并记录实际 per-sample seed。
- Development20 只用于解码敏感性分析；不得读取 Locked20 / Severe10 Owner labels，不得据其调参。
- 如果开发集结果导致调整主配置，必须在任何 Locked30 推理前冻结新 Profile，并记录 profile SHA。

## 评估指标

按三维严重审核结果分别计算 SUPPORTED precision/recall/F1、INSUFFICIENT_CONTEXT 检测、误报漏报逐案分析、安全 SUPPORTED 漏报、精确引用有效率、语义证据支持率。另报告 JSON Schema 完整率、finish_reason、截断率、延迟和 GPU 成本。模型一致率只作辅助，不代替 Owner 参考裁决。

GLM-4 与 GLM-Z1 同属一个架构家族；三模型比较不等于三个独立家族投票。最终双模型选择须结合 Owner reference、模型互补性、严重漏报风险、误杀、运行成本和稳定性。

## 预算与边界

当前 P3 已验证共同上下文 ceiling=32,768，input budget=28,672，generation budget=4,096。生成预算包含模型内部 reasoning token；不得把可见 JSON 正文预算误当成总生成预算。若 Thinking 输出经常耗尽预算，应在开发集阶段重新评估统一预算，并在锁定集运行前重新冻结，不得静默截断。

- 固定模型 revision 与 P3 已选模板来源/SHA。
- seed=42 是实验设计建议，不是已验证的跨硬件逐位确定性保证。
- 当前 HF Runtime image digest、依赖 lock SHA、完整 tokenizer 文件 hash 与 P4 预算/profile 绑定仍需核验。
- profile_freeze_authorized=false
- inference_authorized=false
- gpu_authorized=false
- training_authorized=false

本次新增文件：
- `experiments/r60_quality/r60_sampling_decision_candidate_v1.json`
- `src/storyforge_dataset/generation_eval/sampling.py`
- `tests/test_generation_eval_sampling.py`

CPU-only 验证命令：
```bash
PYTHONPATH=src python -m pytest -q tests/test_generation_eval_sampling.py
```

通过只表示采样实验设计契约有效，不代表模型推理或参数效果已验证。
