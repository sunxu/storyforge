# 2026-11-10 Owner Mac 文件准备回执与 CPU 预检实现更新

## 固定文件下载阶段：PASS

Owner Mac 已回传 `storyforge_r60_p3_model_files_safe_v1` SAFE，状态 `P3_PINNED_TOKENIZER_FILES_READY__NO_WEIGHTS`。回执核对结果：三模型固定 Revision 均匹配；每模型 6 个 allowlist 文件，共 18 个文件；合计 55,828,852 bytes。回执记录 `model_weights_downloaded=false`、`inference_calls=0`、`hf_jobs_submitted=0`、`gpu_started=false`。该 SAFE 是 Owner 回传的私有执行回执，不将原始 SAFE 文件或本地路径提交仓库。

**该阶段不等于 tokenizer/template CPU 预检通过。** 目前只确认下载器列出的文件与 SHA 记录已产生；本地 Transformers 加载、渲染与 token budget 仍待执行。

## CPU 预检脚本 v1 的范围缺口

复核 `scripts/r60_p3_cpu_model_preflight_v1.py` 后发现它每模型仅渲染一条短 prompt，未读取下载 SAFE 核验本地文件 SHA、未比较 embedded/standalone 模板、未执行 90 组 synthetic 中文多轮输入，也未检查共享上下文预算。因此不得使用该 v1 的 PASS 状态代表完整 P3 验收。

新增 `scripts/r60_p3_cpu_model_preflight_v2.py` 与 `tests/test_r60_p3_cpu_model_preflight_v2.py`。v2 增加：
- 对照下载 SAFE 逐文件验证本地 SHA-256 和文件大小；检查固定 Revision 与无模型权重。
- 每模型 90 组中文多轮 synthetic messages；检查 tokenizer token IDs、prompt token 分布和无静默截断预算。
- 实际比较 embedded 与 standalone Jinja 模板渲染，任何差异均报告 template-source HOLD。
- Qwen Thinking 显式开启；检查 GLM-Z1 synthetic 历史 think 内容剥离与可见正文保留。
- 以 32,768 为共同上下文上限，暂定输入 28,672 + 输出预留 4,096 的 CPU 预算边界测试。该分配仅是预检 envelope，不构成 P4 generation profile 或推理授权。
- 核验 R60 Rubric v2.1 response JSON Schema 的固定字段/三维维度合同。

finish_reason 的真实运行时行为无法在禁止 inference 的 P3 中观察；SAFE 明确标记 `DEFERRED_TO_P4_NO_INFERENCE_IN_P3`，不得伪称已实测。

Owner Mac 在现有下载目录执行（不重新下载）：

```bash
set -euo pipefail
cd /Users/keedle/workspace/storyforge-r60-ledger-diagnostics
source .venv-r60-p3/bin/activate
OUT="$HOME/.cache/storyforge/r60-p3-snapshots-20261110"
set +e
python scripts/r60_p3_cpu_model_preflight_v2.py \
  --snapshots-root "$OUT" \
  --download-safe "$OUT/R60_P3_MODEL_FILES_SAFE.json" \
  --input-budget 28672 \
  --output-budget 4096 \
  --context-ceiling 32768 \
  > "$OUT/R60_P3_CPU_PREFLIGHT_SAFE.json"
RC=$?
set -e
cat "$OUT/R60_P3_CPU_PREFLIGHT_SAFE.json"
printf 'P3_PREFLIGHT_EXIT=%s\\n' "$RC"
```

退出码 42 可能表示模板差异 HOLD 或其他 fail-closed 检查；仍需回传脱敏 SAFE 分析具体 reason。不要把 HOLD 当作脚本崩溃，也不要为追求 PASS 静默替换模板。该命令只加载本地 tokenizer，不加载模型权重、不调用 inference、不启动 GPU/HF Job。

当前阶段：文件准备 PASS；CPU tokenizer/template/token-budget 仍 PENDING；GLM-Z1 模板来源与 decoding 冲突未解决；P4 未授权。

---
# 2026-11-10 公开模板文件复核补充（优先于下方原静态描述）

## GLM-Z1 embedded 与 standalone 模板存在明确行为差异

已通过 Hugging Face Hub 文件读取，在固定 revision `8eb2858992c1f749e2a6d4075455decc2484722d` 核对：

- `tokenizer_config.json` 内嵌 `chat_template`：对历史消息执行 `content.split('</think>')[-1].strip()`；`add_generation_prompt` 分支只输出 `<|assistant|>`，**不追加 `<think>`**。
- 独立 `chat_template.jinja`：同样清理历史消息中最后一个 `</think>` 之前的内容；但 generation prompt 输出 `<|assistant|>\n<think>`。
- 因而两者在生成前缀上不是等价模板。Transformers `AutoTokenizer.from_pretrained` 默认读取 tokenizer 配置中的 embedded template；若运行时不显式覆盖 `tokenizer.chat_template`，不能假设会使用独立 Jinja 文件。

**当前结论：GLM-Z1 template source = HOLD / OWNER DECISION REQUIRED。** 不能把原文中“embedded template 添加 `<think>`”当作事实，也不能静默选择 standalone。P3 CPU 渲染需分别执行两种来源并保存两者 SHA、渲染差异与 generation-prefix 结果；Owner 决定实际运行时来源后，才能固定 template SHA。

GLM-4 固定 revision `8dea913c41b543527c2860fb6f3c15c202f24aeb` 的 embedded 与 standalone 模板原始文本也并非逐字节相同：metadata 分支空白处理不同（embedded 在 `{{ meta }}` 后含额外空格）；必须用真实多轮/metadata synthetic messages 对比渲染，不能只比较文件是否存在。Qwen 当前仓库未列出独立 `chat_template.jinja`，使用 tokenizer embedded template。

本次只是读取公开 Hub 文本；**没有本地下载文件、没有计算本地 SHA-256、没有执行 Transformers/Jinja 渲染**。不得将静态差异诊断冒充 CPU preflight PASS。

## P3 代码与依赖执行基线

- GLM-4 候选 Revision 已在提交 `0f39b685edf82ccc980535d49491d658f7647b81` 修正为 `8dea913c41b543527c2860fb6f3c15c202f24aeb`；此前 profile 文件中的 `077b5c2f...` 是错误旧 pin。
- R60 P3 运行时使用 `requirements/hf-quality-reviewer.lock`：`transformers==4.57.1`、`sentencepiece==0.2.1`、`jinja2==3.1.6`。不要把 R59 的 `requirements/hf-cpu-tokenizer.lock`（Transformers 5.16.1）混作本轮依赖。
- 新增 `scripts/r60_p3_prepare_model_snapshots_v1.py`，仅按固定 revision 下载 allowlist 内 tokenizer/config/template 文件，并对文件计算 SHA-256；不允许下载模型权重。对应合成测试为 `tests/test_r60_p3_prepare_model_snapshots_v1.py`。
- 下载器代码和 revision profile 的 GitHub CI 通过，不代表本地模型 tokenizer/template 已执行。P3 状态仍为 `CPU_PREFLIGHT_PENDING`。

---
# 2026-11-10 后续状态补充：P2-B 已完成，P3 CPU 预检为当前主线

P2-B Owner Mac 官方 Verifier 已返回 `P2B_OWNER_REVIEW_COMPLETE__SEMANTIC_HOLDS_PRESERVED`：30/30 cases、90/90 semantic checks；57 SUPPORTS_VERDICT、33 INSUFFICIENT_CONTEXT、0 DOES_NOT_SUPPORT_VERDICT。Owner identity cryptographic attestation=false；private_values_emitted=false；quality_v1_admitted=0；training_authorized=false；gpu_started=false。

Safety 第21、22条经 Owner 二次裁决均为 INSUFFICIENT_CONTEXT，原始 SUPPORTED 与审计记录保留；其他88项未改，Rubric v2.1 未改。不得重审 P2-B 或向模型输入泄露 held-out 数据。

因此本文件原有静态 revision 事实继续有效；状态仍为 `STATIC_HUB_METADATA_REVIEW_COMPLETE__CPU_PREFLIGHT_PENDING`。CPU tokenizer/template/token-budget 执行尚未完成。本阶段只做本地 CPU、固定 revision 文件下载、hash、模板渲染和 synthetic token budget；不下载权重、不做 inference、不提交 HF Job/GPU。GLM-Z1 sampling 与 greedy 文档冲突必须在 profile 冻结前明确解决。

# R60 P3 三模型静态版本与模板预检（2026-11-10）

> 状态：`STATIC_HUB_METADATA_REVIEW_COMPLETE__CPU_PREFLIGHT_PENDING`。本文件只记录 Hugging Face Hub 公开元数据、模型卡、配置文件与 Chat Template 的只读核查；没有下载模型权重，没有运行 tokenizer，没有执行模型推理，没有提交 HF Job/GPU。

## 1. 固定候选与 Hub revision

以下为本次核查时各仓库 `main` 对应的完整 40 位 commit SHA。后续实验必须使用 revision SHA，不得使用可变的 `main`。

| Role | Repo | Revision SHA | Architecture | Parameters | Native context evidence |
|---|---|---|---|---:|---|
| A baseline | [Qwen/Qwen3-32B](https://huggingface.co/Qwen/Qwen3-32B/tree/9216db5781bf21249d130ec9da846c4624c16137) | `9216db5781bf21249d130ec9da846c4624c16137` | Qwen3ForCausalLM / qwen3 | 32.762B | Model card: 32,768 native; config max_position_embeddings=40,960; YaRN up to 131,072 |
| B baseline | [zai-org/GLM-4-32B-0414](https://huggingface.co/zai-org/GLM-4-32B-0414/tree/8dea913c41b543527c2860fb6f3c15c202f24aeb) | `8dea913c41b543527c2860fb6f3c15c202f24aeb` | Glm4ForCausalLM / glm4 | 32.566B | config max_position_embeddings=32,768 |
| Challenger | [zai-org/GLM-Z1-32B-0414](https://huggingface.co/zai-org/GLM-Z1-32B-0414/tree/8eb2858992c1f749e2a6d4075455decc2484722d) | `8eb2858992c1f749e2a6d4075455decc2484722d` | Glm4ForCausalLM / glm4 | 32.566B | config max_position_embeddings=32,768 |

The three repositories are public and list Transformers as the supported library. Qwen is Apache-2.0; both GLM repositories are MIT. GLM-Z1 is a reasoning-tuned derivative in the GLM-4 family, not an independent model family.

## 2. Read-only configuration findings

### Qwen3-32B

- `config.json`: `model_type=qwen3`, `torch_dtype=bfloat16`, `max_position_embeddings=40960`, 64 layers, hidden size 5120.
- `tokenizer_config.json`: `tokenizer_class=Qwen2Tokenizer`, `model_max_length=131072`; chat template exposes `enable_thinking`.
- `generation_config.json`: `do_sample=true`, temperature 0.6, top_p 0.95, top_k 20; EOS IDs 151645 and 151643.
- Model card explicitly says native context 32,768 and recommends Thinking mode with temperature 0.6 / top_p 0.95 / top_k 20 / min_p 0. It explicitly warns against greedy decoding for Thinking mode.
- Proposed profile requirement: set `enable_thinking=true` explicitly; do not rely on wrapper defaults.

### GLM-4-32B-0414

- `config.json`: `model_type=glm4`, `torch_dtype=bfloat16`, `max_position_embeddings=32768`, 61 layers, hidden size 6144.
- `tokenizer_config.json`: `tokenizer_class=PreTrainedTokenizer`, `model_max_length=128000`; tokenizer embeds a ChatGLM-format template.
- Repository also contains a separate `chat_template.jinja`; both must be hash-pinned and their rendering equivalence tested rather than assumed.
- `generation_config.json` only supplies EOS IDs, pad ID and Transformers version; it does not pin temperature/top_p/top_k.
- Model-card inference example uses `do_sample=true` and `max_new_tokens=1024`, but does not specify sampling values. Do not copy Qwen parameters into this profile.

### GLM-Z1-32B-0414

- `config.json`: same GLM4 architecture family, `torch_dtype=bfloat16`, `max_position_embeddings=32768`, 61 layers, hidden size 6144.
- `tokenizer_config.json`: `tokenizer_class=PreTrainedTokenizer`, `model_max_length=128000`; embedded template strips content before the last `</think>` in each message. **It does not append `<think>` in its generation-prompt branch**; the separate `chat_template.jinja` does append `<think>`. See the 2026-11-10 template-source discrepancy below.
- Repository also contains a separate `chat_template.jinja`; both must be hash-pinned and rendered in CPU tests.
- `generation_config.json` only supplies EOS IDs, pad ID and Transformers version.
- Model card's sampling table recommends temperature 0.6 / top_p 0.95 / top_k 40 / max_new_tokens 30000, but its inference example instead sets `do_sample=false` and `max_new_tokens=4096`. This is a real documented configuration conflict; do not silently choose one.

## 3. Shared constraints and unresolved profile decisions

1. A conservative shared native context ceiling is 32,768 tokens; this is supported by Qwen's stated native context and both GLM configs. Do not treat tokenizer `model_max_length=128000/131072` as proof of native model context.
2. The exact shared prompt budget, output budget, truncation behavior and stop/finish-reason handling remain to be frozen in the model profile before inference.
3. Qwen Thinking sampling can follow its explicit model-card guidance, with `enable_thinking=true`.
4. GLM-4 sampling values are not pinned by its repository generation config. A GLM-specific policy must be chosen; do not inherit Qwen defaults.
5. GLM-Z1 has conflicting model-card guidance (`do_sample=false` example vs sampling table). This requires an explicit Owner decision or an evidence-backed resolution before freezing the profile.
6. GLM-4 and GLM-Z1 share the GLM4 architecture/template family; they are not independent-family votes. Evaluation report must state this.

## 4. Remaining CPU-only preflight

Not yet executed:

- Download only tokenizer/config/template files at the exact pinned revisions; record SHA-256 for `tokenizer.json`, `tokenizer_config.json`, `chat_template.jinja` (where present), `config.json`, and `generation_config.json`.
- Run local CPU-only tokenizer load and chat-template render tests for each model, including Chinese multi-turn messages, explicit system/user roles, generation prompt, Qwen thinking on, GLM-Z1 thinking prefix, and no-thinking-content history.
- Compare tokenizer-embedded template and standalone Jinja template where both exist; any mismatch is a HOLD until the runtime's selected source is explicitly pinned.
- Verify model-specific Transformers support and package versions without importing weights or initializing CUDA.
- Run token-budget tests on synthetic text only. No held-out P2-B text or Owner labels may enter this work.

## 5. Execution boundary

This is static metadata review only. No model weights downloaded; no tokenizer execution; no model calls; no HF jobs; no GPU; no private calibration data used; no training or admission authorized.

Sources: Hugging Face model cards and repository files at the exact revisions linked above:
- Qwen: `README.md`, `config.json`, `generation_config.json`, `tokenizer_config.json`.
- GLM-4: `README.md`, `config.json`, `generation_config.json`, `tokenizer_config.json`, `chat_template.jinja`.
- GLM-Z1: `README.md`, `config.json`, `generation_config.json`, `tokenizer_config.json`, `chat_template.jinja`.
