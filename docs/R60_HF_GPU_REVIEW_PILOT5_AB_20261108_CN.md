# R60 真正文学盲审 A/B 各前五条：最小 GPU Pilot 执行基线（2026-11-08）

## 当前事实与范围

- 原冻结 Bucket 根：`hf://buckets/adradar/storyforge-training/quality-review/r60/r60-quality-cpu-20261108T082545Z`。原 `input_A/source.private.jsonl`、`input_B/source.private.jsonl` 各含 1000 条独立盲审输入，`diagnostic-runner-v3/runner.py` 复用统一 `hf_literary_review.py`；既有文件均只读挂载，绝不上传 Owner crosswalk。
- A CPU [`6af045fb0e0338d1bb84a4ce`](https://huggingface.co/jobs/adradar/6af045fb0e0338d1bb84a4ce)，B CPU [`6af047a70e0338d1bb84a5ed`](https://huggingface.co/jobs/adradar/6af047a70e0338d1bb84a5ed)：两个不同模型的 1000/1000 Tokenizer PASS，均 over-budget=0；这是 `transformers==4.57.1` CPU 运行环境结果，**不等于真实 vLLM GPU 镜像的 Tokenizer 一致**。
- 模型 A：`Qwen/Qwen3-32B`、revision `9216db5781bf21249d130ec9da846c4624c16137`。
- 模型 B：`zai-org/GLM-4-32B-0414`、revision `077b5c2f5c43bd3239fd605a0600229e8facbd4a`。
- 执行意图：**仅** A/B 各第 1–5 条文学质量评审（`--start 1 --limit 5`），模型独立、只写到各自私有新输出 Bucket，不运行 SFT、不提升 Quality-v1 准入、不自动重跑、不处理第 6–1000 条。
- 与 R58 复用同一个已验证的 vLLM 镜像 **不可变 digest**：`vllm/vllm-openai@sha256:6ee133356d49ed24cee03dd0cda3d3980279a11c107ce3e752c89e76540f41c9`（R58 在该镜像里确认 `python3` 而非 `python`，且 CPU/GPU Tokenizer Runtime 版本有差异）；`h200` 一卡 141GB，参数 `dtype=bfloat16`、`gpu_memory_utilization=0.80`、`max_model_len=32768`、`max_output_tokens=2400`、`temperature=0`、JSON Schema constrained。
- 单槽 HF 超时 `35m`，内层 GNU timeout `2050s`、`--kill-after=20s`，Worker wall guard `1800s`；按 HF 官方当前 [H200 $5/h](https://huggingface.co/docs/hub/en/jobs-pricing)，两槽合计 70 分钟硬件计费**理论上限约 $5.84**（按分钟计费；不包括异常重试、额外资源、税费），任何失败都 HOLD，禁止自动追加 Job。

## 实际执行进度

2026-11-08 ChatGPT 连接的 HF `run` 尝试提交 **CPU-only GPU 镜像兼容性检查**，HF 返回 **403 Forbidden**，未拿到 Job ID；随后只读组织 Job 列表，没有找到 `r60-gpuimage-cpu-token-A-20261108`。因此**不能说 CPU 镜像验证已运行，亦不能说 GPU Pilot 已启动**。沿用 R58 已验证的 Owner Mac `hf 2.4.0` 受控 CLI；无需个人 namespace fallback。

## 第一闸门：真实 vLLM 镜像上的 CPU-only Tokenizer（不启动 GPU）

在 Owner Mac 运行以下命令（或直接使用聊天中的完整命令），先 A 后 B；每一槽的模型不可混用，输出前缀互不相交：

```bash
set -euo pipefail
set +x
ROOT="hf://buckets/adradar/storyforge-training/quality-review/r60/r60-quality-cpu-20261108T082545Z"
IMG="vllm/vllm-openai@sha256:6ee133356d49ed24cee03dd0cda3d3980279a11c107ce3e752c89e76540f41c9"
for SLOT in A B; do
  if [ "$SLOT" = A ]; then MODEL="Qwen/Qwen3-32B"; REV="9216db5781bf21249d130ec9da846c4624c16137"; else
    MODEL="zai-org/GLM-4-32B-0414"; REV="077b5c2f5c43bd3239fd605a0600229e8facbd4a"; fi
  CMD="set -eu
export CUDA_VISIBLE_DEVICES=''
export PYTHONPATH=/input
export TOKENIZERS_PARALLELISM=false
export HF_HUB_DISABLE_PROGRESS_BARS=1
python3 -c 'import jinja2, sentencepiece; print("HF_GPUIMAGE_DEPS_PRESENT")'
python3 /scripts/runner.py --input /input/source.private.jsonl --output-dir /output --model $MODEL --revision $REV --token-preflight-only --max-model-len 32768 --max-output-tokens 2400"
  hf jobs run --namespace adradar --name "r60-gpuimage-cpu-token-$SLOT-20261108" \
    --flavor cpu-basic --timeout 12m --attempts 1 --detach --dry-run \
    -v "$ROOT/input_$SLOT:/input:ro" \
    -v "$ROOT/diagnostic-runner-v3:/scripts:ro" \
    -v "$ROOT/cpu-output-gpuimage-token-$SLOT-01:/output:rw" \
    "$IMG" -- /bin/sh -lc "$CMD"
  # 删除 --dry-run 才会产生实际 CPU Job；确认无同名 Job 后每槽只提交一次。
done
```

**硬闸门**：每一槽必须获得实际 HF Job ID、HF Job 最终 `COMPLETED`，并在日志中有 `HF_GPUIMAGE_DEPS_PRESENT` + `HF_REVIEW_CPU_TOKEN_PREFLIGHT_PASS__NO_GPU`、`cases_checked=1000`、`over_budget_count=0`。任一槽失败/HOLD，不得启动对应 GPU；不要依赖本机 v4.57.1 CPU PASS 来跳过此闸门。

## 第二闸门：最小真实 GPU 文学审核

镜像 CPU 闸门 A/B 各自完成后，采用同一镜像不可变 digest、同一模型 revision、各自新的独立输出（例：`gpu-review-output-A-pilot5-01`、`gpu-review-output-B-pilot5-01`），每槽执行：

```bash
hf jobs run --namespace adradar --name "r60-quality-gpu-pilot5-${SLOT}-01" \
  --flavor h200 --timeout 35m --attempts 1 --detach --dry-run \
  -v "$ROOT/input_$SLOT:/input:ro" \
  -v "$ROOT/diagnostic-runner-v3:/scripts:ro" \
  -v "$ROOT/gpu-review-output-$SLOT-pilot5-01:/output:rw" \
  "$IMG" -- /bin/sh -lc \
  "set -eu
export PYTHONPATH=/input
export TOKENIZERS_PARALLELISM=false
export HF_HUB_DISABLE_PROGRESS_BARS=1
timeout --signal=TERM --kill-after=20s 2050s python3 /scripts/runner.py \
 --input /input/source.private.jsonl --output-dir /output \
 --model $MODEL --revision $REV --start 1 --limit 5 \
 --max-model-len 32768 --max-output-tokens 2400 \
 --max-wall-seconds 1800 --confirm-paid-gpu"
```

检查 dry-run 后**才手动移除 `--dry-run`** 提交；不可让同一命令重复执行付费 Job。没有输入或输出目录交叉挂载，没有用户上传，禁止使用 GPU 上的网络外发私有内容。GPU Job 的状态 `COMPLETED` 只代表 Worker 正常返回；逐条 checkpoint 必须通过 `read_checkpoint` 对 `blind_id/input_sha256/model/revision/receipt_sha256` 和逐字引用再验证。某一条 `HOLD` 时保留已有 1–4 个有效 checkpoint，不盲目重跑；勿打印私有引用、模型回复或 traceback。

**审查口径**：`HF_REVIEW_PARTIAL__NO_ADMISSION` 是 Pilot 的正常统计类别（只处理前 5/1000），并不自动意味着失败。必须区分 `cases_completed` 的全部 1000 vs 5 Pilot，存量 995 仍未审核。A/B 独立完成至少所选样本有效 checkpoint 后才进行 Owner 私有 crosswalk 的配对与质量判定；绝不把 Token PASS 或 A/B 单槽决策计为 Quality-v1 train admission。
