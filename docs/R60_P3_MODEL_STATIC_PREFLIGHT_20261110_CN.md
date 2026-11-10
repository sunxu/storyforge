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
- `tokenizer_config.json`: `tokenizer_class=PreTrainedTokenizer`, `model_max_length=128000`; tokenizer embeds a template that strips prior `</think>` content and adds a `<think>` generation prefix.
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
