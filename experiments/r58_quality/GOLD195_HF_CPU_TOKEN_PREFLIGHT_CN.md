# R58 HF 私人语义审核 — 模型固定与 GPU 前 CPU token 检查

当前私人 132 条审核输入已经在 Owner Mac 上生成：
`$HOME/.local/share/storyforge/r58/hf-semantic-review132-v1/input132.private.jsonl`。
原回执 `HF_PRIVATE_INPUT132_PREPARED__NOT_UPLOADED`、四项本地合成测试 PASS。**这是本地准备完成，不代表模型运行或私人数据上传。**

## 固定公开模型

选用 `Qwen/Qwen3-32B`，通过 HF Hub 模型元数据核验的当前完整修订 SHA：

`9216db5781bf21249d130ec9da846c4624c16137`

HF API 模型元数据：https://huggingface.co/api/models/Qwen/Qwen3-32B

该模型 BF16 权重约 65.5GB；单 A100 80GB 剩余显存需容纳 CUDA/vLLM 开销和 KV cache，**尚未做 GPU 加载验证，存在 OOM 风险**。先检查真实文本 token 长度，才能决定 8192 上下文是否足够、是否应采用量化或更大显存组合。不要根据结构检测的 132 PASS 推断 token 上限或推理可行性。

## Mac：只跑 CPU tokenizer（可能下载公开 tokenizer，无私人文本外发）

~~~bash
git pull --ff-only
python3 -m pip install --user 'transformers>=4.51,<6' 'huggingface_hub>=0.35,<3'

R58_PRIVATE="$HOME/.local/share/storyforge/r58"

python3 -m unittest discover -s experiments/r58_quality \
  -p 'test_gold195_hf_review_cpu_token_preflight.py' -v

python3 experiments/r58_quality/gold195_hf_review_cpu_token_preflight.py \
  --private-input "$R58_PRIVATE/hf-semantic-review132-v1/input132.private.jsonl" \
  --model Qwen/Qwen3-32B \
  --model-revision 9216db5781bf21249d130ec9da846c4624c16137 \
  --max-model-len 8192 \
  --max-output-tokens 1200
~~~

> 若使用已有虚拟环境，请在该环境安装 Python 依赖，不必全局或 user 安装。 `pip` 只获取公开软件/模型 tokenizer；脚本不上传私有输入。结果终端只输出 SAFE 分布和超长条数（不含正文、Case ID、hash）。`token_hold > 0` 则必须调整设计或更换上下文方案，不能静默截断。

## GPU 之前需要确认的四件事

1. CPU token 预检的 `prompt_tokens_max`、`p95` 和 `token_hold`。
2. HF Job 容器镜像、vLLM/transformers 版本与 CUDA/A100 的实际兼容性，镜像与代码需固定不可变版本。
3. HF Job 创建时设置**平台 timeout**，并设置独立 `--max-wall-seconds`。模型加载耗时不受脚本处理循环的 wall-time 保护，所以平台 timeout 更关键。
4. 私人 bucket 数据写入需要独立上传确认；已获云端处理的原则性许可，但当前未请求立即上传。实际付费 GPU 校准 10 条与正式 132 条需要分别授权。

校准 10 条的当前 runner 是按源文件前十行执行，并非先前 10 世界的特殊选题；正式校准前应将这两种抽样定义统一。结果结构校验不能代替中文文学判断和截断安全的独立事实审核。Quality-v1=0、R50 不读、GPU/HF Job 不启动。
