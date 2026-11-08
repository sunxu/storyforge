# R60 HF CPU A Job 已提交但远程失败：安全诊断与继续执行（2026-11-08）

## 2026-11-08 v3 提交不确定：本机 Hugging Face CLI 版本不兼容（最新结论）

Owner Mac 的 `r60-quality-cpu-A-diagnostic-v3` Guard 报 `SUBMISSION_UNCONFIRMED_CHECK_ORG_JOBS` / `HF_JOB_SUBMISSION_FAILED`。ChatGPT HF 连接器只读核查 `adradar` Jobs 列表，未见本次 v3 Job。Owner 运行 `hf version` 得到 `huggingface_hub 0.36.2`，`hf jobs run --help` 仅显示 `--detach`（与完整 Guard 需求不匹配）。

已核对 Hugging Face [`v0.36.2` 精确版本 CLI 源码](https://github.com/huggingface/huggingface_hub/blob/v0.36.2/src/huggingface_hub/cli/jobs.py)：`hf jobs run` 缺失 `--name`、`--attempts`、`-v/--volume`，也没有 `--dry-run`。**这足以解释该本地 CLI 不可能成功解析当前 Guard 提交命令，构成高度可信的原因；没有原始 stderr，仍不能证明实际 v3 失败只来自它。** 先前 v2 Job 成功创建，因此要检查当时和现在调用的 `hf` 是否来自不同 PATH / Python 环境。

已修复公共 `scripts/hf_job_guard.py`：
- 增加 `--check-hf-cli`：仅调用 `hf jobs run --help`，检查全部提交所需 flag 是否存在，不认证、不上传、不执行 Job；
- 缺失 flag 返回 `PREFLIGHT_HOLD / HF_CLI_UNSUPPORTED_OPTIONS` 并只列出公开 CLI flag 名；帮助获取失败则 `HF_CLI_HELP_UNAVAILABLE`；
- **`--submit` 前强制执行同样的 CLI flag 检查**，阻止重复将不兼容客户端误报成远端提交问题；
- 默认仅做参数 Policy 检查时仍为 `PREFLIGHT_PASS_NOT_SUBMITTED`（其意义不包括实际 CLI 兼容性）；只有增加 `--check-hf-cli` 且 `hf_cli_compatible=true` 才同时证实本机 CLI 支持提交参数。

**不建议直接修改 StoryForge 训练 Python 环境**。在 Owner Mac 安装一套单独的 HF CLI 工具环境，用户需决定执行本机包安装（不会创建 HF Job）：

~~~bash
set -euo pipefail
set +x
type -a hf
hf version

CLI_ROOT="$HOME/.local/share/storyforge/tools/hf-cli"
python3 -m venv "$CLI_ROOT"
"$CLI_ROOT/bin/python" -m pip install --upgrade "huggingface_hub>=1,<2"

# 必须检查新 CLI 的真实参数，而不是仅相信版本号
"$CLI_ROOT/bin/hf" jobs run --help | grep -E -- \
  '--name|--attempts|--detach|--namespace|--volume|--dry-run'
~~~

用新 CLI 来复检**原已写好的 v3 参数**，但不提交：

~~~bash
# 继续使用上一节已经固定的 INROOT 和 CMD 变量，
# 或重新执行上一节仅定义变量的代码，不执行 HF Job。
PATH="$CLI_ROOT/bin:$PATH" python3 scripts/hf_job_guard.py \
  --namespace adradar --name r60-quality-cpu-A-diagnostic-v3 \
  --flavor cpu-basic --timeout-minutes 45 \
  --input-volume "$INROOT/input_A:/input:ro" \
  --input-volume "$INROOT/diagnostic-runner-v3:/scripts:ro" \
  --output-volume "$INROOT/cpu-output-A-diagnostic-v3:/output:rw" \
  --image python:3.11 \
  --check-hf-cli \
  -- /bin/sh -lc "$CMD"
~~~

预期 `PREFLIGHT_PASS_NOT_SUBMITTED` 且 `hf_cli_compatible=true`。这个命令不添加 `--submit`，绝对不会创建 HF Job。原 v3 失败回执及远端旧输入均保持不变；未获得明确进一步指令前不提交另一次 CPU 或 GPU、不得重发失败作业。

---

## 2026-11-08 实际 diagnostic-v2 结果与 v3 定向修复（覆盖前述 v2 待运行描述）

已由 Owner 提交 Job [`6af039530e0338d1bb849aa7`](https://huggingface.co/jobs/adradar/6af039530e0338d1bb849aa7)，组织 `adradar`，`cpu-basic`，运行 2026-11-08T08:56:51Z–08:59:05Z，终态 `ERROR`，退出 42。实际 HF SAFE 日志：

~~~json
{"schema":"storyforge_hf_literary_safe_v1","status":"HF_REVIEW_INPUT_VERIFIED__NO_INFERENCE","cases_total":1000,"cases_completed":0,"private_values_emitted":false,"training_authorized":false}
{"schema":"storyforge_hf_literary_safe_v1","status":"HF_REVIEW_HOLD","reason_code":"HF_CPU_CHAT_TEMPLATE_HOLD","private_values_emitted":false,"training_authorized":false}
~~~

**确认 1000 条盲输入全部通过格式合同验证；实际 Qwen Tokenizer 加载过程没有触发 `HF_CPU_TOKENIZER_LOAD_HOLD`，错误位于共享 Chat Template/Token ID 编码步骤，不是文学质量 REJECT，具体子原因仍 UNKNOWN。** 缺少 PyTorch 的普通日志不能确定原因。暂停 B，不对原失败 Job 重试。

新的公共 Reviewer 不实现第二套 Tokenizer 算法，直接复用 `src/storyforge_dataset/token_preflight.py`。v3 在 `cpu_token_error_code` 里只保留其 allowlist 成员，例如 `HF_CPU_CHAT_TEMPLATE_RENDER_FAILED_TYPE_ERROR`、`HF_CPU_CHAT_TEMPLATE_RENDER_FAILED_VALUE_ERROR`、`HF_CPU_TOKEN_IDS_INVALID`，拒绝泄露来源异常、原文、Token IDs 或任意长错误消息。所有其他异常仍统一 `HF_CPU_CHAT_TEMPLATE_HOLD`；只增强安全原因码，不更改数据、不降低拒绝门槛。

### Owner Mac v3：仅制作/同步新的无私有正文 Python 代码

原冻结 `input_A` / `input_B`、旧 `diagnostic-runner-v2`、全部正式 HF/Owner 映射不变。不要把 v3 覆盖 v2，也不要重新上传真实正文。

~~~bash
set -euo pipefail
set +x
umask 077

git fetch origin r60/gold192-history-v3-adapter
git switch r60/gold192-history-v3-adapter
git pull --ff-only origin r60/gold192-history-v3-adapter

BASE="$HOME/.local/share/storyforge/r60/private"
INROOT="hf://buckets/adradar/storyforge-training/quality-review/r60/r60-quality-cpu-20261108T082545Z"
V3="$BASE/r60-hf-cpu-diagnostic-runner-v3"

test ! -e "$V3"
install -d -m 700 "$V3"
install -m 600 src/storyforge_gold_quality/hf_literary_review.py "$V3/runner.py"
hf buckets sync "$V3" "$INROOT/diagnostic-runner-v3"
~~~

### A v3 CPU 诊断：先 Dry-run

与 v2 保持一致，**只替换脚本目录与输出前缀**，不重新上传任何 1000 条输入；两个输入各 RO（原 A 来源挂 `/input`，新代码挂 `/scripts`），独立 RW 新输出：

~~~bash
CMD="set -eu
export CUDA_VISIBLE_DEVICES=''
export TOKENIZERS_PARALLELISM=false
export PYTHONPATH=/input
python3 -m pip install --quiet --no-cache-dir 'transformers==4.57.1' 'huggingface_hub>=0.35,<3'
python3 /scripts/runner.py --input /input/source.private.jsonl   --output-dir /output --model Qwen/Qwen3-32B   --revision 9216db5781bf21249d130ec9da846c4624c16137   --verify-only
python3 /scripts/runner.py --input /input/source.private.jsonl   --output-dir /output --model Qwen/Qwen3-32B   --revision 9216db5781bf21249d130ec9da846c4624c16137   --token-preflight-only --max-model-len 32768 --max-output-tokens 2400"

python3 scripts/hf_job_guard.py   --namespace adradar --name r60-quality-cpu-A-diagnostic-v3   --flavor cpu-basic --timeout-minutes 45   --input-volume "$INROOT/input_A:/input:ro"   --input-volume "$INROOT/diagnostic-runner-v3:/scripts:ro"   --output-volume "$INROOT/cpu-output-A-diagnostic-v3:/output:rw"   --image python:3.11   -- /bin/sh -lc "$CMD"
~~~

此命令默认只返回 `PREFLIGHT_PASS_NOT_SUBMITTED`，**不提交新付费 CPU Job**。只有确认 Job v2 已结束、运行配置合理且 Owner 决定再执行一次 CPU 诊断，才给 Guard 补 `--submit`；版本已强制 `--detach`，返回 Job ID。失败原样保留，不能自动重试或切 GPU。真实 Tokenizer 总量 PASS 之前不得提交 B/GPU。

---

## 真实故障结论：不是提交被拒绝

Owner Mac 的旧 `hf_job_guard.py` 输出 `SUBMISSION_REJECTED / HF_JOB_SUBMISSION_FAILED`。只读查询组织 `adradar` 真实 HF Job 后确认：

- **真实 Job 已创建**：`6af033d10e0338d1bb84941e`，组织 `adradar`，创建者 `greenkeedle`
- Name `r60-quality-cpu-A-20261108-082545`，镜像 `python:3.11`，Flavor `cpu-basic`；开始 2026-11-08T08:33:21Z，结束 08:33:55Z，约 34 秒
- Job 状态 `ERROR`，远程进程退出码 `42`。日志中已出现 pip 依赖安装完成、Transformers 对缺少 PyTorch 的非致命提示，然后只有安全回执：`HF_REVIEW_HOLD / HF_REVIEW_RUNTIME_ERROR`。
- **这不是 HF API 提交失败**。原 Guard 默认使 `hf jobs run` 跟随远程日志，将远程程序退出码 42 当作 CLI 提交失败。此问题已通过 `hf_job_guard.py` 新增 `--detach` 修复。
- **当前具体根因还不明**，因为旧 Worker 将各阶段未知异常全部归为 `HF_REVIEW_RUNTIME_ERROR`；不能断言是 Qwen Tokenizer、网络、CPU 资源、挂载或数据结构问题。
- 暂未观测到本批次对应的 Reviewer B CPU Job。**禁止重复提交原 A Job，禁止直接把失败解释为质量不通过或升级 GPU。**

这次故障未执行任何 AI 文学评分，Quality PASS/训练准入仍然为 0，R50 未访问。

## 已落实的工具修复

1. `scripts/hf_job_guard.py`：只有 `hf jobs run --detach` 返回 0 才报告 `JOB_SUBMITTED`，不会再把远程进程失败归类为提交错误；非零且缺失 Job ID 视为 `SUBMISSION_UNCONFIRMED_CHECK_ORG_JOBS`，人工核对组织列表，禁止自动重试。
2. `src/storyforge_gold_quality/hf_literary_review.py`：新增安全失败阶段码 `HF_REVIEW_INPUT_RUNTIME_HOLD`、`HF_CPU_TOKENIZER_IMPORT_HOLD`、`HF_CPU_TOKENIZER_LOAD_HOLD`、`HF_CPU_CHAT_TEMPLATE_HOLD`、`HF_CPU_TOKEN_SUMMARY_HOLD`、`HF_CPU_PREFLIGHT_RUNTIME_HOLD`。绝不打印私有正文、模型异常消息、路径、token IDs 或回溯。
3. 合成回归覆盖远程日志码误判的防护、Tokenizer/load/template 故障原因分级、未知输入阶段错误的安全回执。
4. **冻结旧 A/B 私有 Stage 与 Bucket 输入不变**。旧 `input_A/runner.py` 也不覆盖或重写；新代码单独存放在新增的 diagnostics-only RO 脚本前缀，避免打破 Owner Stage SHA 和原始证据。

## Owner Mac 无付费步骤：检查并上传**只有代码**的新脚本

以下使用用户已上传的固定前缀和原 Revision；工作目录必须是同步后的 StoryForge R60 源码根目录：

~~~bash
set -euo pipefail
set +x
umask 077

git fetch origin r60/gold192-history-v3-adapter
git switch r60/gold192-history-v3-adapter
git pull --ff-only origin r60/gold192-history-v3-adapter

INROOT="hf://buckets/adradar/storyforge-training/quality-review/r60/r60-quality-cpu-20261108T082545Z"
BASE="$HOME/.local/share/storyforge/r60/private"
DIAG="$BASE/r60-hf-cpu-diagnostic-runner-v2"

# 原输入不能覆盖；仅创建一个与既有 Stage 分离的新 0700 代码目录
test ! -e "$DIAG"
install -d -m 700 "$DIAG"
install -m 600 src/storyforge_gold_quality/hf_literary_review.py "$DIAG/runner.py"

# 此命令只上传一份无私有正文的 Python Reviewer 源代码；
# 不上传本地 owner 映射、tokenizer 输入或原 1000 条源文件
hf buckets sync "$DIAG" "$INROOT/diagnostic-runner-v2"
~~~

## 诊断 Job A：先 dry-run，不自动重试

原 `input_A` 继续挂载在 `/input:ro`；新增无私有正文的代码挂载在 `/scripts:ro`。`PYTHONPATH=/input` 使诊断 Runner 仍使用已冻结的 `token_core.py`、`runtime_inputs.py`、`runtime_resources.py`，保持共享 Tokenizer/Runtime 核心的来源一致。使用一个新的、与失败 Job 区分的输出路径。**这里只做 HF CPU**。

~~~bash
INROOT="hf://buckets/adradar/storyforge-training/quality-review/r60/r60-quality-cpu-20261108T082545Z"

CMD="set -eu
export CUDA_VISIBLE_DEVICES=''
export TOKENIZERS_PARALLELISM=false
export PYTHONPATH=/input
python3 -m pip install --quiet --no-cache-dir 'transformers==4.57.1' 'huggingface_hub>=0.35,<3'
test -f /input/source.private.jsonl
test -f /scripts/runner.py
python3 /scripts/runner.py --input /input/source.private.jsonl \
  --output-dir /output --model 'Qwen/Qwen3-32B' \
  --revision '9216db5781bf21249d130ec9da846c4624c16137' --verify-only
python3 /scripts/runner.py --input /input/source.private.jsonl \
  --output-dir /output --model 'Qwen/Qwen3-32B' \
  --revision '9216db5781bf21249d130ec9da846c4624c16137' \
  --token-preflight-only --max-model-len 32768 --max-output-tokens 2400"

python3 scripts/hf_job_guard.py \
  --namespace adradar \
  --name r60-quality-cpu-A-diagnostic-v2 \
  --flavor cpu-basic --timeout-minutes 45 \
  --input-volume "$INROOT/input_A:/input:ro" \
  --input-volume "$INROOT/diagnostic-runner-v2:/scripts:ro" \
  --output-volume "$INROOT/cpu-output-A-diagnostic-v2:/output:rw" \
  --image python:3.11 \
  -- /bin/sh -lc "$CMD"
~~~

上述应仅返回 `PREFLIGHT_PASS_NOT_SUBMITTED`，`input_mounts=2`、`gpu_allowed=false`、输入全 RO、输出独立 RW。**先检查，不要自动执行付费 Job。**

在确认首次 Job 已结束、代码脚本挂载存在、同意另开一次 CPU 诊断 Job 后，对同一命令添加 `--submit` 才实际执行。新版 Guard 将通过 `--detach` 及时返回提交回执和 Job ID；用 `hf jobs logs adradar/JOB_ID` 检查结果，`HF_REVIEW_INPUT_VERIFIED__NO_INFERENCE` 应先出现，然后是 `HF_REVIEW_CPU_TOKEN_PREFLIGHT_PASS__NO_GPU` 或明确的安全分阶段 HOLD。不得在未知故障下自动重跑。

**B 的 CPU 任务保持 HOLD**，直到 A 给出可解释的模型 Tokenizer SAFE 或确定修复方向。

## 额外边界

从云端日志看 `None of PyTorch...` 是 Transformers 的环境信息，**尚不能确定它就是根因**。本 CPU 预检只需要 Tokenizer、不加载 32B 模型权重，不应通过自动加 GPU、私有日志打印或禁用安全校验解决。HF Bucket 原 A/B 1000 个真实用户正文已上传，继续留在既有组织私有前缀；本轮不增加正文副本。
