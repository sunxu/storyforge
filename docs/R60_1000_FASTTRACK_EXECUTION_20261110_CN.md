# R60：已有 1000 条训练候选精筛加速执行书（2026-11-10）

## 2026-11-11：A25 第 7 条 XGrammar 状态机异常：保留 6 个 Checkpoint，受控切 Guidance 恢复

Owner Job：https://huggingface.co/jobs/adradar/6af372469737d9a9e0916d28

日志证据：\`CONTINUOUS_REVIEW_READY input_count=25\` → \`REAL_ENGINE_READY engine_init_count=1\` → \`FIRST_CHECKPOINT_GATE_PASS completed=1\` → \`vllm/v1/structured_output/backend_xgrammar.py:160 Failed to advance FSM for request 6 for tokens 92446\` → \`REVIEW_BATCH_HOLD completed=6 exception_class=ReviewError\` → \`CONTINUOUS_REVIEW_HOLD\`。已成功生成并校验**前 6 条**，第 7 条尚未生成有效 Checkpoint，当前 A25 **6/25**，不是 25/25。该 XGrammar 日志说明其 FSM 拒绝某个 token；相邻 \`ReviewError\` 的具体原因仍未被旧版 SAFE 日志暴露，不能断言 FSM 是唯一异常来源。vLLM v0.10.0 官方 \`GuidedDecodingParams\` 支持 \`backend="guidance"\`；使用其替代 XGrammar 是明确记载的解码后端改变，**不是声称相同生成结果的透明修复**。

**现状**：本次 Qwen 已证明 32K 配置、真实长提示处理、真实结构化审核的前 6 条及一个引擎连续运行成立。避免再次走下载/挂载直载；不修改既有 6 条审核数据。

**实现**：
- \`experiments/r58_quality/r60_a25_guidance_reviewer_patch.py\`（create-only, CPU）：把冻结 \`input_A/runner.py\` 复制到**新隔离 bundle**，仅将一处 \`GuidedDecodingParams(json=response_schema())\` 改为 \`GuidedDecodingParams(json=response_schema(), backend="guidance")\`。先后 AST parse，必须精确匹配一次；不修改模型、Prompt、temperature=0、2400 tokens、schema、评分/引文校验或已有 Checkpoint；记录 source/patched SHA。不可原地改冻结原件。
- \`r60_qwen_continuous_review.py\` 已新增 \`REVIEW_BATCH_HOLD.safe_reason_code\`（只允许经过审核的固定 ReviewError 字面值，否则 UNKNOWN），可判别输出不完整、JSON、引文修复等，而不输出内容。
- **原模型身份及 Checkpoint identity 保持** \`Qwen/Qwen3-32B@9216db5781bf21249d130ec9da846c4624c16137\`，源输入 SHA \`492f24f7...\`，原 \`read_checkpoint\` 验证 1–6 后才允许继续。不同后端生成结果不可未经说明地当作一项相同条件下的模型质量横比；报告时必须标记 1–6 为旧 XGrammar、7–25 为 Guidance。
- 原 \`--resume\` 只有输出目录文件全部为 \`review_0001.private.json\` 至 \`review_0006.private.json\` 连续且 6 条原版读回有效才会复用；若其中任何 Checkpoint 损坏/缺失/有非审核文件，直接 HOLD，不自动删除、覆盖或跳过。
- 不启用“失败后无限重试”：Guidance 不可用、模型输出校验失败或第七条再次出现状态机问题都停止，保留本轮输出。

### Owner Mac：先只读核对原输出目录（不启动 HF Job）

\`\`\`bash
hf buckets list \
  adradar/storyforge-training/evaluation-runs/r60-1000-pilot25-qwen-a-continuous-v1 \
  -R -h
\`\`\`

预期仅 6 个 \`review_0001.private.json\` 至 \`review_0006.private.json\`，没有第 7 个；若不符合，**停止，不运行后续命令**。不在 Mac 下载私有 Checkpoint；真正的内容验收由 Runner 在 H200 的 \`checked_prefix\` 执行。

### Owner Mac：CPU-only 新建恢复工具和隔离 Runner

\`\`\`bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
BASE="$HOME/.local/share/storyforge/r60/private"
PILOT="$BASE/r60-hf-quality-pilot25-vllm0100"
SRC="$PILOT/input_A_continuous"
DEST="$PILOT/input_A_guidance_resume"
TOOLS="$BASE/r60-qwen-guidance-resume-tools-v1"
REV="__A25_GUIDANCE_CODE_PIN__"
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
test -d "$SRC"
test ! -e "$DEST" || { echo A25_GUIDANCE_BUNDLE_EXISTS_HOLD; exit 42; }
test ! -e "$TOOLS" || { echo A25_GUIDANCE_TOOLS_EXISTS_HOLD; exit 42; }
umask 077
mkdir -m 700 "$DEST" "$TOOLS"
for name in source.private.jsonl token_core.py runtime_inputs.py runtime_resources.py; do
  cp "$SRC/$name" "$DEST/$name"
  chmod 600 "$DEST/$name"
done
for name in r60_a25_guidance_reviewer_patch.py r60_qwen32b_servercopy_localize.py r60_qwen_continuous_review.py; do
  git -C "$ROOT" show "$REV:experiments/r58_quality/$name" > "$TOOLS/$name"
  chmod 600 "$TOOLS/$name"
done
python3 "$TOOLS/r60_a25_guidance_reviewer_patch.py" \
  --source "$SRC/runner.py" --dest "$DEST/runner.py"
cp "$TOOLS/r60_qwen_continuous_review.py" "$DEST/r60_qwen_continuous_review.py"
chmod 600 "$DEST"/*.py
test "$(shasum -a 256 "$DEST/source.private.jsonl" | awk '{print $1}')" = \
  492f24f7cb6171481e0e6d176cfa862ec6f5223bdd7abc3cfb518335dc9ab069 || { echo A25_INPUT_SHA_HOLD; exit 42; }
python3 -m py_compile "$DEST"/*.py "$TOOLS"/*.py
\`\`\`

### Owner Mac：一次 H200 Job 恢复第 7–25 条（仅在准备和 CI PASS 后）

> 此处与新建输出目录不同：**明确复用原失败 Job 的 Checkpoint 输出目录，并启用 \`--resume\`**；H200 临时模型目录仍每次重新复制。先在同镜像上检查 \`guidance\` 后端依赖是否可 import，缺失则在复制大模型前 fail closed。不要无条件 pip 安装未固定版本的依赖。

\`\`\`bash
set -euo pipefail
BASE="$HOME/.local/share/storyforge/r60/private"
PILOT="$BASE/r60-hf-quality-pilot25-vllm0100"
TOOLS="$BASE/r60-qwen-guidance-resume-tools-v1"
IMG="docker.io/vllm/vllm-openai@sha256:05a31dc4185b042e91f4d2183689ac8a87bd845713d5c3f987563c5899878271"
hf jobs run --namespace adradar --name r60-qwen-a25-guidance-resume \
  --flavor h200 --timeout 90m --attempts 1 \
  -v "$PILOT/input_A_guidance_resume:/input:ro" \
  -v "$TOOLS:/code:ro" \
  -v "hf://buckets/adradar/storyforge-training/model-cache/qwen3-32b-9216db5-servercopy:/model-source:ro" \
  -v "hf://buckets/adradar/storyforge-training:/bucket:rw" \
  "$IMG" \
  sh -c 'set -eu; /usr/bin/python3 -c "import guidance" || { echo GUIDANCE_BACKEND_NOT_INSTALLED_HOLD; exit 42; }; mkdir -p /tmp/r60-model-local; LOCAL=/tmp/r60-model-local/qwen3-32b-9216db5; OUT=/bucket/evaluation-runs/r60-1000-pilot25-qwen-a-continuous-v1; test -d "$OUT" || { echo RESUME_OUTPUT_MISSING_HOLD; exit 42; }; /usr/bin/python3 -u /code/r60_qwen32b_servercopy_localize.py --skip-weight-sha --bucket-dir /model-source --local-dir "$LOCAL"; exec /usr/bin/python3 -u /input/r60_qwen_continuous_review.py --input /input/source.private.jsonl --output-dir "$OUT" --model Qwen/Qwen3-32B --revision 9216db5781bf21249d130ec9da846c4624c16137 --local-dir "$LOCAL" --case-limit 25 --batch-size 5 --max-model-len 32768 --max-output-tokens 2400 --wall-seconds 4800 --resume --confirm-paid-gpu'
\`\`\`

期望 \`REVIEW_PREFIX_VERIFIED count=6\` → \`BATCH_START start=7\` → \`REAL_ENGINE_READY\` → 后续 \`BATCH_COMPLETE\` → \`CONTINUOUS_REVIEW_COMPLETE completed=25 engine_init_count=1\`。恢复 Job 会重新初始化**一次**模型，不是复用已经结束的 H200 的模型实例。**如 Guidance 依赖缺失，先单独评估固定镜像方案，不应盲目再次运行 GPU。**

---


## 2026-11-11：GLM-4 B25 由 Hub 直载改为服务器端复制 + H200 本地加载 + 单引擎连续批次

**触发证据**：B25 Owner Job https://huggingface.co/jobs/adradar/6af36821ab34849891aca183 仅有 \`B25_GATE_READY\`，无权重、Tokenizer、真实引擎就绪/首条校验事件；不能判定具体卡点。旧 B25 直接从 \`zai-org/GLM-4-32B-0414\` 在线加载，存在与 Qwen 早期 Hub 直载相似的风险。项目已将修复实现提交，但**未运行 HF Job / 未取得 GLM B25 成功回执**。

**独立核对 GLM 固定源**：\`zai-org/GLM-4-32B-0414@8dea913c41b543527c2860fb6f3c15c202f24aeb\`，14 个 \`model-00001-of-00014.safetensors\` ～ \`model-00014-of-00014.safetensors\`，\`model.safetensors.index.json\`、\`chat_template.jinja\`、\`tokenizer.json\` 等。与 Qwen 的 17 分片不同，禁止复用 Qwen 文件清单/模型路径。

**新增源代码**：
- \`experiments/r58_quality/r60_glm4_servercopy_localize.py\`：固定 GLM commit 获取上游文件清单、14 分片及 index，Bucket 只读挂载复制到 H200 本地；默认完整 SHA 验证，Owner 此次授权用 \`--skip-weight-sha\`，只做文件大小、索引和固定上游元数据校验，标注 \`size-only-upstream-sha-declared\` 和 \`LOCAL_FILE_SIZE_CHECKED\`，不把仅大小校验说成 SHA 验证。每次 H200 Job 的临时磁盘不可复用。
- \`experiments/r58_quality/r60_glm4_b25_continuous_review.py\`：保留 **B25 冻结输入 SHA** \`01639568cf21a7b98356f2b3b74f567943b4a6844edb9230b58759789ab67fc9\` 和原 reviewer 模型身份/revision/schema/sampling/引文修复/回执；仅运行时 Tokenizer/Engine 重定向已校验本地模型目录，兼容 vLLM 初始化内部本地 Tokenizer 加载。单 H200 Engine 处理连续批次，首条原版 \`read_checkpoint\` 失败即停，每条输出 checkpoint 强制回读；\`--resume\` 只接受从第 1 条连续、无杂项、均验证有效的历史 checkpoint。初始化失败日志 \`REAL_ENGINE_INIT_HOLD exception_class\`，不得泄漏异常文本/私人内容。
- 本版本**只开放 B25 的 25 条**，不得假装已接受未知 SHA 的 B1000；要处理 B1000，必须在 Owner Mac 验证和冻结 B1000 输入 hash 后更新源代码及 CPU tests。

### 第一步：Owner Mac CLI 服务器端复制（无需 CPU/GPU Job）

\`\`\`bash
set -euo pipefail
SRC="hf://models/zai-org/GLM-4-32B-0414@8dea913c41b543527c2860fb6f3c15c202f24aeb/"
DST="hf://buckets/adradar/storyforge-training/model-cache/glm4-32b-8dea913-servercopy/"
# 目标必须是新的空目录，不要覆盖之前任何缓存
hf cp "$SRC" "$DST"
hf buckets list adradar/storyforge-training/model-cache/glm4-32b-8dea913-servercopy -R -h
\`\`\`

**Owner 验收**：\`✓ Copied\`、14/14 safetensors 文件、index、tokenizer、chat template 都在目标 Bucket。若报区域/权限/缺失分片，停止；不要回退 Hub 直载的 B25 Job，也不要启动旧 CPU Basic 50GB 临时盘的 stage 脚本。

### 第二步：Owner Mac CLI 新建独立 B25 执行 bundle（CPU-only）

\`\`\`bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
BASE="$HOME/.local/share/storyforge/r60/private"
PILOT="$BASE/r60-hf-quality-pilot25-vllm0100"
SRC="$PILOT/input_B"
DEST="$PILOT/input_B_continuous_local"
CODE="$BASE/r60-glm4-b25-local-tools-v1"
REV="205b946ba6bd9cb3c87304150b37e269c1ee80c7"
umask 077
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
test -d "$SRC"
test ! -e "$DEST" || { echo B25_LOCAL_BUNDLE_EXISTS_HOLD; exit 42; }
test ! -e "$CODE" || { echo GLM4_LOCAL_TOOLS_EXISTS_HOLD; exit 42; }
mkdir -m 700 "$DEST" "$CODE"
for file in runner.py source.private.jsonl token_core.py runtime_inputs.py runtime_resources.py; do
  test -f "$SRC/$file"
  cp "$SRC/$file" "$DEST/$file"
  chmod 600 "$DEST/$file"
done
git -C "$ROOT" show "$REV:experiments/r58_quality/r60_glm4_b25_continuous_review.py" > "$DEST/r60_glm4_b25_continuous_review.py"
git -C "$ROOT" show "$REV:experiments/r58_quality/r60_glm4_servercopy_localize.py" > "$CODE/r60_glm4_servercopy_localize.py"
chmod 600 "$DEST/r60_glm4_b25_continuous_review.py" "$CODE/r60_glm4_servercopy_localize.py"
python3 -m py_compile "$DEST/r60_glm4_b25_continuous_review.py" "$CODE/r60_glm4_servercopy_localize.py"
EXPECTED=01639568cf21a7b98356f2b3b74f567943b4a6844edb9230b58759789ab67fc9
ACTUAL="$(shasum -a 256 "$DEST/source.private.jsonl" | awk '{print $1}')"
test "$EXPECTED" = "$ACTUAL" || { echo B25_SHA_MISMATCH; exit 42; }
python3 "$DEST/runner.py" \
  --input "$DEST/source.private.jsonl" --output-dir "$PILOT/output_B" \
  --model zai-org/GLM-4-32B-0414 \
  --revision 8dea913c41b543527c2860fb6f3c15c202f24aeb \
  --verify-only
\`\`\`

### 第三步：Owner Mac CLI H200 单 Job，本地复制 + 5×5 条连续审核

\`\`\`bash
set -euo pipefail
BASE="$HOME/.local/share/storyforge/r60/private"
PILOT="$BASE/r60-hf-quality-pilot25-vllm0100"
CODE="$BASE/r60-glm4-b25-local-tools-v1"
IMG="docker.io/vllm/vllm-openai@sha256:05a31dc4185b042e91f4d2183689ac8a87bd845713d5c3f987563c5899878271"
hf jobs run --namespace adradar --name r60-glm4-b25-local-continuous \
  --flavor h200 --timeout 90m --attempts 1 \
  -v "$PILOT/input_B_continuous_local:/input:ro" \
  -v "$CODE:/code:ro" \
  -v "hf://buckets/adradar/storyforge-training/model-cache/glm4-32b-8dea913-servercopy:/model-source:ro" \
  -v "hf://buckets/adradar/storyforge-training:/bucket:rw" \
  "$IMG" \
  sh -c 'set -eu; test -x /usr/bin/python3 || exit 42; mkdir -p /tmp/r60-model-local; LOCAL=/tmp/r60-model-local/glm4-32b-8dea913; OUT=/bucket/evaluation-runs/r60-1000-pilot25-glm4-b-local-continuous-v1; if [ -e "$OUT" ]; then echo B25_LOCAL_OUTPUT_ALREADY_EXISTS_HOLD; exit 42; fi; /usr/bin/python3 -u /code/r60_glm4_servercopy_localize.py --skip-weight-sha --bucket-dir /model-source --local-dir "$LOCAL"; mkdir -p "$OUT"; exec /usr/bin/python3 -u /input/r60_glm4_b25_continuous_review.py --input /input/source.private.jsonl --output-dir "$OUT" --model zai-org/GLM-4-32B-0414 --revision 8dea913c41b543527c2860fb6f3c15c202f24aeb --local-dir "$LOCAL" --case-limit 25 --batch-size 5 --max-model-len 32768 --max-output-tokens 2400 --wall-seconds 4800 --confirm-paid-gpu'
\`\`\`

**验收事件** \`LOCAL_FILE_SIZE_CHECKED\` → \`LOCAL_WEIGHTS_READY full_weight_sha_verified=false\` → \`CONTINUOUS_REVIEW_READY\` → \`REAL_ENGINE_INIT_START\` → \`REAL_ENGINE_READY\` → \`FIRST_CHECKPOINT_GATE_PASS\` → \`BATCH_COMPLETE\`（5 批）→ \`CONTINUOUS_REVIEW_COMPLETE completed=25 engine_init_count=1\`。若仅 \`REAL_ENGINE_INIT_START\` 之后卡住，不要推测已生成；及时读取 Job INFO/ERROR 与脱敏 class，避免重复费用。B25 Checkpoint 合法不等于质量全部通过，更不等于训练准入。**ChatGPT 不提交 HF Job；由 Owner Mac CLI 执行。**

---


## 2026-11-11：A25 引擎初始化 HOLD 后，低开销复制 + 单 H200 连续批次审核（新执行入口）

**最新实测**：Qwen3-32B A25 Job `6af36c549737d9a9e0915d9f` 完成 `LOCAL_WEIGHTS_READY` 后进入 `A25_GATE_READY` → `A25_LOCAL_TOKENIZER_LOAD` → `A25_REAL_LOCAL_ENGINE_START`，vLLM INFO 记录 max_model_len=32768 与 chunked prefill=16384，随后冻结原审查器报 `HF_REVIEW_RUNTIME_ERROR`。**未出现 `A25_REAL_LOCAL_ENGINE_READY`、`A25_FIRST_GATE_PASS`，因此真实审核没有通过，A25=0/25（截至现有回执）**。这只能确定错误发生在模型初始化期间或其紧邻阶段，不能仅凭隐藏的通用错误码判定是显存、vLLM 参数还是模型。原审查器吞异常的原因是其自己的 SAFE redaction；不要假设权重损坏，不要重复同一个旧 Job。

### 已实施改动

1. `experiments/r58_quality/r60_qwen32b_servercopy_localize.py` 新增 `--skip-weight-sha`：在固定 Hub commit 的 24 文件 size/inventory、17 权重分片和 index 路径检查前提下，复制权重不再逐块计算 SHA256。小文本文件仍按实际内容记录 SHA（体积很小）。Manifest 增加 `integrity_mode: size-only-upstream-sha-declared`；`LOCAL_WEIGHTS_READY` 明确 `full_weight_sha_verified=false`。**原版完整 sha 校验模式仍是默认**；只在已经通过一次全 SHA 校验的 servercopy 目录、Owner 明确选择速度优先时开启；此举不能证明新副本与上游 SHA 完全一致。**数据源从未获得绕过固定 revision 的授权。**
2. `experiments/r58_quality/r60_qwen_continuous_review.py` 新入口：限定 `Qwen/Qwen3-32B@9216db5781bf21249d130ec9da846c4624c16137`，仅接受冻结 A25 25 条 SHA `492f24f7...` 或冻结 full A1000 SHA `687528efe...`；保留原 `runner.py` 的 prompt、sampling、JSON schema、引文修复、六维裁决、checkpoint record。将其 `AutoTokenizer.from_pretrained` / `vllm.LLM` 运行时参数改成本地路径并在**同一进程内复用唯一 Engine 实例**，循环 `--batch-size 25` 批次，逐条验证原版 `read_checkpoint`；首条验证失败立即终止，不生成第二条。打印 `BATCH_START`/`BATCH_COMPLETE` 和累计数，预算临界停止并输出 `REVIEW_WALL_BUDGET_HOLD`。
3. `--resume` 仅当输出目录中全部现有 Checkpoint 是从 0001 起的**连续有效前缀**时启用；原版 `read_checkpoint` 逐个校验 SHA、blind ID、input SHA、model/revision、policy 和响应，任何断档/未知文件/损坏直接 HOLD，不覆盖已写文件。**不同 Job 仍需各自加载一次模型**，同一个 Job 内的多批次不会重载。
4. 对于上次 `HF_REVIEW_RUNTIME_ERROR` 泛化问题，新入口在 `REAL_ENGINE_INIT_START` 后出现异常时打印脱敏 `REAL_ENGINE_INIT_HOLD` 和异常**类名**，以及 `REVIEW_BATCH_HOLD` 的固定阶段；不得输出异常消息、堆栈、路径或私有文本。还不能保证仅凭异常类名定位根因。
5. CPU 合成测试覆盖：25 条分五批只初始化 1 次 Engine；首条拒绝不生成第二条；中途异常不虚报完成；非连续 Checkpoint 拒绝恢复；完整前缀验证后继续；另验证 size-only 模式不会假称 SHA 完整性。
   
**重要门禁**：依然不能将 `A25` 的 25 条冻结输入和 `A1000` 原始输入混为一谈。先运行 25 条并验证，再用同一软件对 frozen 1000 source 启动更长作业；不能把 `--case-limit 1000` 配上 25 条输入。跨多 Job 恢复时每轮必须有单独的费用、最大时长授权与私有数据源验收。

### 2026-11-11 补充诊断：旧门禁可能误拒绝 vLLM 内部的本地 Tokenizer 调用

在冻结 A25 门禁实现复核中发现：旧 `AutoTokenizer.from_pretrained` 拦截器只允许 `model=Qwen/Qwen3-32B,revision=固定SHA`，但 vLLM 初始化真实本地权重时，**可能也使用 Transformers 请求本地 tokenizer 路径**。旧逻辑会抛出拦截器 Hold，再由冻结 reviewer 统一压成 `HF_REVIEW_RUNTIME_ERROR`。这是**高优先级、尚未以 H200 实测确认的可能原因**，不是已确定根因。

已修复新的连续审核入口以及历史 A25 门禁：允许且仅允许已验证的 `local_dir` 内部 tokenizer 调用，禁止加载任何意外模型或其他路径；CPU 合成测试已模拟引擎构造期间再次加载本地 tokenizer。新的日志会输出 `VLLM_INTERNAL_LOCAL_TOKENIZER`（不含路径）或 `REAL_ENGINE_INIT_HOLD exception_class=...`。本段覆盖本执行书内此前旧版 A25 命令；**新 Job 一律采用最新固定脚本，禁止再使用旧 A25 gate 版本重新支付 GPU 费用**。

### Owner Mac：新工具版本隔离安装（CPU-only）

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
BASE="$HOME/.local/share/storyforge/r60/private"
PILOT="$BASE/r60-hf-quality-pilot25-vllm0100"
DEST="$PILOT/input_A_continuous"
CODE="$BASE/r60-qwen-continuous-tools-v1"
REV="0c66c152934af104537209c7b72bb9fda3b38787"
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
test -d "$PILOT/input_A"
test ! -e "$DEST" || { echo A_CONTINUOUS_ALREADY_EXISTS_HOLD; exit 42; }
test ! -e "$CODE" || { echo CODE_ALREADY_EXISTS_HOLD; exit 42; }
umask 077
mkdir -m 700 "$DEST" "$CODE"
for name in runner.py source.private.jsonl token_core.py runtime_inputs.py runtime_resources.py; do
  cp "$PILOT/input_A/$name" "$DEST/$name"
  chmod 600 "$DEST/$name"
done
git -C "$ROOT" show "$REV:experiments/r58_quality/r60_qwen_continuous_review.py" > "$DEST/r60_qwen_continuous_review.py"
git -C "$ROOT" show "$REV:experiments/r58_quality/r60_qwen32b_servercopy_localize.py" > "$CODE/r60_qwen32b_servercopy_localize.py"
chmod 600 "$DEST/r60_qwen_continuous_review.py" "$CODE/r60_qwen32b_servercopy_localize.py"
python3 -m py_compile "$DEST/r60_qwen_continuous_review.py" "$CODE/r60_qwen32b_servercopy_localize.py"
ACTUAL="$(shasum -a 256 "$DEST/source.private.jsonl" | awk '{print $1}')"
test "$ACTUAL" = 492f24f7cb6171481e0e6d176cfa862ec6f5223bdd7abc3cfb518335dc9ab069 || { echo INPUT_SHA_HOLD; exit 42; }
python3 "$DEST/runner.py" --input "$DEST/source.private.jsonl" \
  --output-dir "$PILOT/output_A" --model Qwen/Qwen3-32B \
  --revision 9216db5781bf21249d130ec9da846c4624c16137 --verify-only
```

### Owner Mac：H200 单 Job，先 25 条正式审核并保留后续批次能力

```bash
set -euo pipefail
BASE="$HOME/.local/share/storyforge/r60/private"
PILOT="$BASE/r60-hf-quality-pilot25-vllm0100"
CODE="$BASE/r60-qwen-continuous-tools-v1"
IMG="docker.io/vllm/vllm-openai@sha256:05a31dc4185b042e91f4d2183689ac8a87bd845713d5c3f987563c5899878271"
hf jobs run --namespace adradar --name r60-qwen-a25-continuous-v1 \
  --flavor h200 --timeout 90m --attempts 1 \
  -v "$PILOT/input_A_continuous:/input:ro" \
  -v "$CODE:/code:ro" \
  -v "hf://buckets/adradar/storyforge-training/model-cache/qwen3-32b-9216db5-servercopy:/model-source:ro" \
  -v "hf://buckets/adradar/storyforge-training:/bucket:rw" \
  "$IMG" \
  sh -c 'set -eu; test -x /usr/bin/python3 || exit 42; mkdir -p /tmp/r60-model-local; LOCAL=/tmp/r60-model-local/qwen3-32b-9216db5; OUT=/bucket/evaluation-runs/r60-1000-pilot25-qwen-a-continuous-v1; if [ -e "$OUT" ]; then echo A25_CONTINUOUS_OUT_EXISTS_HOLD; exit 42; fi; /usr/bin/python3 -u /code/r60_qwen32b_servercopy_localize.py --skip-weight-sha --bucket-dir /model-source --local-dir "$LOCAL"; mkdir -p "$OUT"; exec /usr/bin/python3 -u /input/r60_qwen_continuous_review.py --input /input/source.private.jsonl --output-dir "$OUT" --model Qwen/Qwen3-32B --revision 9216db5781bf21249d130ec9da846c4624c16137 --local-dir "$LOCAL" --case-limit 25 --batch-size 25 --max-model-len 32768 --max-output-tokens 2400 --wall-seconds 4800 --confirm-paid-gpu'
```

期望 `LOCAL_FILE_SIZE_CHECKED`（而不是 `LOCAL_FILE_VERIFIED`）以及 `LOCAL_WEIGHTS_READY full_weight_sha_verified=false` → `CONTINUOUS_REVIEW_READY` → `REAL_ENGINE_INIT_START` → `REAL_ENGINE_READY` → `FIRST_CHECKPOINT_GATE_PASS` → `BATCH_COMPLETE` → `CONTINUOUS_REVIEW_COMPLETE completed=25 engine_init_count=1`。若 `REAL_ENGINE_INIT_HOLD`，保留 reason class，**不要再反复提交同参数 GPU**。必须返回真实日志与 Checkpoint 计数，不能当作质量准入。

**使用 full A1000 的下一步**：用已经固定 SHA `687528efe...` 的完整来源创建另一个私有隔离 bundle，绑定独立的输出目录、超时和成本上限。可设置例如 `--case-limit 100 --batch-size 25`，一个 Job 中连续 4 批 25 条且单次 vLLM 初始化；待 A25 首条真实运行证据 PASS 再操作。此处示例仅定义能力，**没有授权直接跑 1000**。HF Jobs 永远由 Owner Mac CLI 提交。

---


## 2026-11-11：A25 Qwen3-32B 单次 H200 本地权重加载与首条强制验收（可执行）

**目标**：接上已通过的真实 Qwen 本地权重 Smoke，保留 A25 固定的真实审核器身份与原始模型 revision；一条 GPU Job 内只初始化 1 次 vLLM，审核第 1 条并由**原审核器完整 `read_checkpoint`** 回读验证后，自动继续剩余 24 条。不会单独跑 1 条 Smoke，不会因为已经完成短生成就伪造 32K 审核通过。

新入口 `experiments/r58_quality/r60_a25_local_first_gate.py`：固定 `Qwen/Qwen3-32B@9216db5781bf21249d130ec9da846c4624c16137`、冻结 Pilot25 A SHA `492f24f7cb6171481e0e6d176cfa862ec6f5223bdd7abc3cfb518335dc9ab069`、25 条及 32768/2400 token；输出必须是**存在且为空**的新目录。通过函数包装仅将 `AutoTokenizer.from_pretrained` 与 `vllm.LLM` 的**运行时模型路径**重定向为当前 Job 上游 SHA 校验后的本地目录；审查器传入的原 model/revision 和写出的 Checkpoint identity 全程不修改。严格保持原 JSON Schema、SamplingParams、引文修复、评分政策，首条失败立即 HOLD，不执行下一条；成功完成 25 条才产生 `A25_ALL_VERIFIED`。失败不删除已经写入的 Checkpoint；原始 `input_A` 及 `output_A` 不变。

**警告**：原版 `r60_qwen32b_local_smoke.py` 只能证明短合成生成。此 A25 是真正的结构化审核，首条可能因 JSON Schema、模型回答质量或引文修复 HOLD。不可跳过门禁。若失败，不可在有已写 Checkpoint 的目录直接重新启动，也不得以“0/25”假定没有文件；应先核对已有 Checkpoint，再设计受控恢复流程。

### Owner Mac：CPU-only 准备隔离 A25 runner + 上传工具

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
BASE="$HOME/.local/share/storyforge/r60/private"
PILOT="$BASE/r60-hf-quality-pilot25-vllm0100"
DEST="$PILOT/input_A_localgate"
SRC="$PILOT/input_A"
TOOLS="$BASE/r60-a25-local-review-tools-v1"
REV="8a10077d91a44961d670b80373176e4e8cbc3fad"
umask 077
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
test -d "$SRC"
test ! -e "$DEST" || { echo A25_DEST_EXISTS_HOLD; exit 42; }
test ! -e "$TOOLS" || { echo A25_TOOLS_EXISTS_HOLD; exit 42; }
mkdir -m 700 "$DEST" "$TOOLS"
for f in runner.py source.private.jsonl token_core.py runtime_inputs.py runtime_resources.py; do
  test -f "$SRC/$f"
  cp "$SRC/$f" "$DEST/$f"
  chmod 600 "$DEST/$f"
done
git -C "$ROOT" show "$REV:experiments/r58_quality/r60_a25_local_first_gate.py" > "$DEST/r60_a25_local_first_gate.py"
git -C "$ROOT" show "$REV:experiments/r58_quality/r60_qwen32b_servercopy_localize.py" > "$TOOLS/r60_qwen32b_servercopy_localize.py"
chmod 600 "$DEST/r60_a25_local_first_gate.py" "$TOOLS/r60_qwen32b_servercopy_localize.py"
python3 -m py_compile "$DEST"/*.py "$TOOLS"/*.py

EXPECTED=492f24f7cb6171481e0e6d176cfa862ec6f5223bdd7abc3cfb518335dc9ab069
ACTUAL="$(shasum -a 256 "$DEST/source.private.jsonl" | awk '{print $1}')"
test "$ACTUAL" = "$EXPECTED" || { echo A25_SHA_MISMATCH; exit 42; }
python3 "$DEST/runner.py" \
  --input "$DEST/source.private.jsonl" \
  --output-dir "$PILOT/output_A" \
  --model Qwen/Qwen3-32B \
  --revision 9216db5781bf21249d130ec9da846c4624c16137 \
  --verify-only
```

预期：`HF_REVIEW_INPUT_VERIFIED__NO_INFERENCE`、`cases_total=25`；没有新 GPU 费用。复制目标必须为空目录且仅保留当前 Pilot25 必需文件。旧 `input_A` 不修改。

### Owner Mac：单个 H200 Job（含本地复制校验 + A25 1→25 审核）

```bash
set -euo pipefail
BASE="$HOME/.local/share/storyforge/r60/private"
PILOT="$BASE/r60-hf-quality-pilot25-vllm0100"
TOOLS="$BASE/r60-a25-local-review-tools-v1"
IMG="docker.io/vllm/vllm-openai@sha256:05a31dc4185b042e91f4d2183689ac8a87bd845713d5c3f987563c5899878271"

hf jobs run --namespace adradar --name r60-qwen-a25-local-firstgate \
  --flavor h200 --timeout 90m --attempts 1 \
  -v "$PILOT/input_A_localgate:/input:ro" \
  -v "$TOOLS:/code:ro" \
  -v "hf://buckets/adradar/storyforge-training/model-cache/qwen3-32b-9216db5-servercopy:/model-source:ro" \
  -v "hf://buckets/adradar/storyforge-training:/bucket:rw" \
  "$IMG" \
  sh -c 'set -eu; test -x /usr/bin/python3 || exit 42; mkdir -p /tmp/r60-model-local; LOCAL=/tmp/r60-model-local/qwen3-32b-9216db5; OUT=/bucket/evaluation-runs/r60-1000-pilot25-qwen-a-local-firstgate; if [ -e "$OUT" ]; then echo A25_OUTPUT_ALREADY_EXISTS_HOLD; exit 42; fi; /usr/bin/python3 -u /code/r60_qwen32b_servercopy_localize.py --bucket-dir /model-source --local-dir "$LOCAL"; mkdir -p "$OUT"; export R60_A25_LOCAL_MODEL_DIR="$LOCAL"; exec /usr/bin/python3 -u /input/r60_a25_local_first_gate.py --input /input/source.private.jsonl --output-dir "$OUT" --model Qwen/Qwen3-32B --revision 9216db5781bf21249d130ec9da846c4624c16137 --start 1 --limit 25 --max-model-len 32768 --max-output-tokens 2400 --max-wall-seconds 3000 --confirm-paid-gpu'
```

预期 SAFE 事件顺序：`LOCAL_DISK_PREFLIGHT` → `LOCAL_WEIGHTS_READY` → `A25_GATE_READY` → `A25_REAL_LOCAL_ENGINE_READY` → `A25_FIRST_GATE_PASS` → `A25_ALL_VERIFIED`（25）及原 runner 的 `HF_REVIEW_COMPLETED__NO_ADMISSION`。其中 `A25_FIRST_GATE_PASS` 仅是第一条技术/语义回执有效，不代表其 `quality_decision=PASS`；最后 `A25_ALL_VERIFIED` 是 25 份正确 Checkpoint，不是 25 份可训练准入。正式 Owner 裁决、与 B25 对齐、训练授权仍独立。

**本轮 ChatGPT 不调用 HF Job**；H200 只有 Owner Mac CLI 可启动。GPU 起动之前须核对相应修订的 CI PASS，以及独立输入校验。已经完成的 Qwen H200 短 Smoke 不会通过此 Job 自动继承临时本地权重，因此单 Job 内再次执行本地 Bucket → disk 顺序复制校验；不能误以为复用上一 Job 的临时盘。

---


## 2026-11-11：Qwen3-32B 本地真实 vLLM Smoke 实测 PASS

Owner Mac 提供 HF Job https://huggingface.co/jobs/adradar/6af366749737d9a9e0914f2a 的真实 SAFE：
```json
{"elapsed_sec":35.2,"event":"REAL_ENGINE_READY","private_values_emitted":false,"schema":"storyforge_r60_qwen32b_local_smoke_safe_v1"}
{"elapsed_sec":35.9,"event":"REAL_GENERATE_DONE","generated_tokens":32,"private_values_emitted":false,"schema":"storyforge_r60_qwen32b_local_smoke_safe_v1"}
```
**结论**：已成功跨过先前真实权重加载卡住的阶段，当前 H200/vLLM 镜像从已经本地化的固定 Qwen3-32B 权重加载成功，并完成非私有 32-token 合成生成。这两项耗时基于该 smoke 内部开始计时，**不含 Bucket 到本地复制和校验时间**。该结果也不代表 32K 满长度推理压力测试、Rubric JSON structured output、A25 真实审核或质量准入已经通过。A25 = 0/25（截至这份回执），Qwen CPU 原先 50GB eviction 及其替代路径历史证据保留。

**下一执行入口**：不要再重复 Dummy、CPU 大权重上传或单独短生成 Smoke。必须基于现有已验证的 `r60_qwen32b_servercopy_localize.py` 实现**同一 H200 Job 内本地化一次、初始化审核器 vLLM 一次、先第 1 条通过原审核器 Checkpoint 校验后继续 2–25 条**。审核器仍以冻结 `Qwen/Qwen3-32B@9216db5781bf21249d130ec9da846c4624c16137` 身份写入回执，而本地加载路径指向校验完成的本地目录；切勿将 `model=` 路径直接改成模型 ID 导致 checkpoint/revision 契约破坏。第一条真实 JSON/schema 与 policy 校验失败必须停止，不能继续 24 条。独立的新 Runner 副本及 CPU 合成测试验收完成前不要提交 A25 H200。

---


## 2026-11-11：Qwen3-32B 固定 revision 服务器端复制 PASS，H200 校验加载入口 v2

**Owner Mac 已实际执行成功** `hf cp`：`hf://models/Qwen/Qwen3-32B@9216db5781bf21249d130ec9da846c4624c16137/` → `hf://buckets/adradar/storyforge-training/model-cache/qwen3-32b-9216db5-servercopy/`，并列出 17 个 `model-xxxxx-of-00017.safetensors`、`model.safetensors.index.json`、`config.json`、`tokenizer.json`、`tokenizer_config.json`、`vocab.json`、`merges.txt` 等 24 个源文件。HF 服务端复制避免了 CPU Basic 挂载写入缓存累积触发 50GB Pod 驱逐的问题。**列表不能代替内容 SHA 和真实加载**。

**修复上版执行书的衔接错误**：原 `r60_qwen32b_weight_stage.py --mode localize` 要求源 Bucket 内有 `r60_weights_verified_manifest.json`，服务器端复制并不会自动生成该 Manifest。故上版 H200 localize 命令不可直接使用。新增 `experiments/r58_quality/r60_qwen32b_servercopy_localize.py`：在 H200 Job 通过 `HfApi.model_info(..., revision=固定 SHA, files_metadata=True)` 获取上游文件尺寸、17 个权重分片的 LFS SHA256；从只读 Bucket mount 逐个顺序读取并流式写到 H200 本地目录，检查总容量 +20GiB 空余、每个大小与上游权重 SHA，最后检查 index 覆盖关系，在**本地**生成旧 smoke 可兼容的 `r60_weights_verified_manifest.json`，输出 `LOCAL_WEIGHTS_READY`。仅用上游可查询 SHA 验证权重；tokenizer/config 无 LFS 哈希时记录实际本地流 SHA，不能宣称其上游来源已独立校验。

HF 官方当前 H200 Flavor 标称约 3TB ephemeral disk（https://huggingface.co/docs/huggingface_hub/main/en/guides/jobs），与 CPU Basic 的 50GB 不同，但仍需以 Job 中实际 `shutil.disk_usage` 门禁为准。**这次不允许将权重复制到 CPU Basic 本地磁盘**。

### Owner Mac 准备 v2 两脚本（CPU-only）

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
BASE="$HOME/.local/share/storyforge/r60/private"
BUNDLE="$BASE/r60-qwen32b-servercopy-localize-v2"
REV="b2858aa19b187e721f603ae1891b64bd3f938f24"
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
test ! -e "$BUNDLE" || { echo ALREADY_EXISTS_HOLD; exit 42; }
umask 077
mkdir -m 700 "$BUNDLE"
for file in r60_qwen32b_servercopy_localize.py r60_qwen32b_local_smoke.py r60_qwen32b_weight_stage.py; do
  git -C "$ROOT" show "$REV:experiments/r58_quality/$file" > "$BUNDLE/$file"
  chmod 600 "$BUNDLE/$file"
done
python3 -m py_compile "$BUNDLE"/*.py
```

### H200 单 Job：localize 校验后直接真实模型合成生成（不访问 A25 私有输入）

```bash
set -euo pipefail
BUNDLE="$HOME/.local/share/storyforge/r60/private/r60-qwen32b-servercopy-localize-v2"
IMG="docker.io/vllm/vllm-openai@sha256:05a31dc4185b042e91f4d2183689ac8a87bd845713d5c3f987563c5899878271"
hf jobs run --namespace adradar --name r60-qwen32b-servercopy-real-smoke \
  --flavor h200 --timeout 90m --attempts 1 \
  -v "$BUNDLE:/code:ro" \
  -v "hf://buckets/adradar/storyforge-training/model-cache/qwen3-32b-9216db5-servercopy:/model-source:ro" \
  "$IMG" \
  sh -c 'set -eu; test -x /usr/bin/python3 || exit 42; mkdir -p /tmp/r60-model-local; /usr/bin/python3 -u /code/r60_qwen32b_servercopy_localize.py --bucket-dir /model-source --local-dir /tmp/r60-model-local/qwen3-32b-9216db5; exec /usr/bin/python3 -u /code/r60_qwen32b_local_smoke.py --local-dir /tmp/r60-model-local/qwen3-32b-9216db5 --confirm-paid-gpu'
```

**验收** `LOCAL_DISK_PREFLIGHT`（必要磁盘容量 +20GiB）→ 每文件 `LOCAL_FILE_VERIFIED` → `LOCAL_WEIGHTS_READY` → `REAL_ENGINE_READY` → `REAL_GENERATE_DONE`。没有以上两条真实模型事件不得称 Qwen 模型问题解决。不能因为 Dummy PASS 或 server-side copy PASS 就提前恢复 A25。当前仍未由 ChatGPT 提交 HF Jobs，Owner Mac CLI 执行边界保持不变。失败必须留存 SAFE 原因码，禁止对相同条件重复提交 GPU。

---


## 2026-11-11：CPU Weight Stage Job 被驱逐；禁止重试旧下载方案，改 Hub 服务端复制

**真实失败回执**：HF Job `6af35a879737d9a9e0913000`；`SHARD_VERIFIED` 停于 15/24；Pod `ERROR: ephemeral local storage usage exceeds ... 50G`。此前 `STAGE_START` 合计 24 个文件/61.04GiB。**这是确定的容器临时存储超额失败**，不能据此断言权重损坏或 Hub 下载错误。旧 `r60_qwen32b_weight_stage.py --mode stage` 使用可写 Bucket 挂载，虽然每次只有一片的 Python 数据流，挂载层可能保留本地 writeback/cache，积累到 50GB 超额；此前声称该方案不会受到 ephemeral 容量影响属于错误假设。

**禁止事项**：不要原命令重新提交 CPU Job；不要将已经输出 `SHARD_VERIFIED` 的文件视为已经在远端持久化（缺少 `STAGE_COMPLETE` Manifest）；不要覆盖/删除旧 `/model-cache/qwen3-32b-9216db5/` 残留，先保留并后续核验。旧下载流程保留作历史诊断，不再推荐运行。

**改进路径：HF Hub 提供 repo → Bucket 的服务端复制**（https://huggingface.co/docs/hub/storage-buckets#copying-files-between-repos-and-buckets）。对 Xet 托管模型文件，以远端内容哈希复制，不从 Mac/CPU Job 下载整套模型；需源/目标存储区域兼容，非 Xet 小文件可能经客户端复制。修复命令由 Owner Mac CLI 执行，不需新 HF Job：

```bash
set -euo pipefail
hf --version
# 使用已有授权登录状态；不要将 token 打印到日志
SRC="hf://models/Qwen/Qwen3-32B@9216db5781bf21249d130ec9da846c4624c16137/"
DST="hf://buckets/adradar/storyforge-training/model-cache/qwen3-32b-9216db5-servercopy/"
# 使用独立新目录，禁止覆盖之前 50GB eviction 的原目录；
# 仅在确认此目标目录原先不存在后执行：
hf cp "$SRC" "$DST"
hf buckets list adradar/storyforge-training/model-cache/qwen3-32b-9216db5-servercopy -R -h
```

HF URI `@<commit>` 为官方固定 revision 语法：https://huggingface.co/docs/huggingface_hub/en/package_reference/hf_uris；`hf cp` 是 `hf buckets cp` 同义命令。若复制失败提示区域不同或版本不支持，请保留错误、停止；不要自动回退到旧的 50GB CPU 挂载写入方案。目录复制可能包含额外非权重文件，需要下游筛选实际 model config/tokenizer/必要 `*.safetensors` 而非猜测 24 个原文件总集。

**完成标准分层**：`hf cp` 退出码 0 + Bucket 列表只是复制路径初验；后续还需要生成并验证新的 Manifest（文件集合、固定 revision、大小、LFS/Xet 内容关联），不能直接把旧 `r60_weights_verified_manifest.json` 假造或挪用；然后由 H200 确认足够本地容量，进行真实模型加载。若 H200 容器本地磁盘也不足以放 61+GiB 权重，则须先解决 GPU 磁盘容量问题，不能绕过 +20GiB 余量门禁。

**背景**：此前 3/3 PyTorch/Transformers P4 短生成 Smoke 已通过，并不说明新的 vLLM H200 权重链路通过。服务端复制避免重复下载，但不自动解决 vLLM 真实加载。

---


## 2026-11-11：B25 单次加载、首条 Checkpoint 硬门禁（Owner 已授权推进）

**目标**：使用既有冻结的 B25 GLM-4-32B 输入，一次 H200 Job 内运行 1→25 条。第 1 条产出后使用**原审核器** `read_checkpoint` 校验，校验不通过时立即停止、第 2 条不得生成；通过后在**同一 `inference()` 进程、同一个 LLM 实例**继续执行 2–25 条，不额外启动 1 条 Smoke Job，不重复加载模型。每条均进行同样的原版 Checkpoint 回读核验。只要任何条失败，禁止产生 `B25_ALL_VERIFIED`。

### 已实现、测试和边界

- `experiments/r58_quality/r60_b25_single_engine_gate.py`：严格固定角色 B 模型 `zai-org/GLM-4-32B-0414`、完整 revision `8dea913c41b543527c2860fb6f3c15c202f24aeb`、独立冻结 Pilot25 输入 SHA256 `01639568cf21a7b98356f2b3b74f567943b4a6844edb9230b58759789ab67fc9`；`start=1,limit=25,max_model_len=32768,max_output_tokens=2400`，必须明确 `--confirm-paid-gpu`；输出路径必须是既存**空目录**。
- 通过模块级 wrapper 挂钩 `inference` 和 `write_checkpoint`，调用冻结原版真实 `inference` 一次，且严格要求 Checkpoint 按序 1→25；每个 Checkpoint 写入后立即复用原版 `read_checkpoint(path, pos, row, model, revision)`，执行 SHA、blind ID、输入绑定、revision、response semantic 等校验；`B25_FIRST_GATE_PASS` 只有第 1 条通过才会输出，之后同一函数继续 24 条。全部通过才输出 `B25_ALL_VERIFIED`。
- `tests/test_r60_b25_single_engine_gate.py` CPU 合成测试：一次 engine 初始化模拟、首条失败立刻停、途中失败不虚报 25、scope mismatch fail-closed。最终 CI 状态必须按最新提交核实。
- **不修改旧 `input_B` 文件**；此脚本必须放到一个独立 `input_B_gate` 副本中，和 `runner.py`、`source.private.jsonl`、`token_core.py`、`runtime_inputs.py`、`runtime_resources.py` 相邻。不能把原始 A25 已验证输入误用到 B25；两组输入 SHA 不同。
- P4 三模型旧 Smoke 是 PyTorch/Transformers 的**短合成生成**，并不证明 `GLM-4-32B` 已在当前 vLLM 0.10.0 structured decoding 路径加载成功。若此 Job 卡在模型权重，**不重试同参数；优先采用已完成的持久化下载方案为 GLM-4 建立本地权重再加载**。B25 所有 Checkpoint 只能存于私有 HF Bucket；失败不能越过首条门禁或将 0/25 误报为训练准入。

### Owner Mac：隔离复制冻结 B25 输入 + 安装 gate（CPU-only）

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
BASE="$HOME/.local/share/storyforge/r60/private"
PILOT="$BASE/r60-hf-quality-pilot25-vllm0100"
SRC="$PILOT/input_B"
DEST="$PILOT/input_B_gate"
REV="2453e1c562724f87d4fb1f049eb7e8cb098ab799"
umask 077
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
test -d "$SRC"
test ! -e "$DEST" || { echo B25_GATE_DEST_EXISTS_HOLD; exit 42; }
mkdir -m 700 "$DEST"
for file in runner.py source.private.jsonl token_core.py runtime_inputs.py runtime_resources.py; do
  test -f "$SRC/$file"
  cp "$SRC/$file" "$DEST/$file"
  chmod 600 "$DEST/$file"
done
git -C "$ROOT" show "$REV:experiments/r58_quality/r60_b25_single_engine_gate.py" > "$DEST/r60_b25_single_engine_gate.py"
chmod 600 "$DEST/r60_b25_single_engine_gate.py"
python3 -m py_compile "$DEST/r60_b25_single_engine_gate.py"
shasum -a 256 "$DEST/source.private.jsonl"
# 必须等于 01639568cf21a7b98356f2b3b74f567943b4a6844edb9230b58759789ab67fc9

python3 "$DEST/runner.py" \
  --input "$DEST/source.private.jsonl" --output-dir "$PILOT/output_B" \
  --model zai-org/GLM-4-32B-0414 \
  --revision 8dea913c41b543527c2860fb6f3c15c202f24aeb \
  --verify-only
```

### 单次 B25 GPU Job（不可与 Qwen A25 输出同目录）

```bash
set -euo pipefail
PILOT="$HOME/.local/share/storyforge/r60/private/r60-hf-quality-pilot25-vllm0100"
IMG="docker.io/vllm/vllm-openai@sha256:05a31dc4185b042e91f4d2183689ac8a87bd845713d5c3f987563c5899878271"
hf jobs run --namespace adradar --name r60-glm4-b25-firstgate \
  --flavor h200 --timeout 90m --attempts 1 \
  -v "$PILOT/input_B_gate:/input:ro" \
  -v "hf://buckets/adradar/storyforge-training:/bucket:rw" \
  "$IMG" \
  sh -c 'set -eu; test -x /usr/bin/python3 || exit 42; OUT=/bucket/evaluation-runs/r60-1000-pilot25-glm4-b-firstgate; if [ -e "$OUT" ]; then echo B25_OUTPUT_ALREADY_EXISTS_HOLD; exit 42; fi; mkdir -p "$OUT"; exec /usr/bin/python3 -u /input/r60_b25_single_engine_gate.py --input /input/source.private.jsonl --output-dir "$OUT" --model zai-org/GLM-4-32B-0414 --revision 8dea913c41b543527c2860fb6f3c15c202f24aeb --start 1 --limit 25 --max-model-len 32768 --max-output-tokens 2400 --max-wall-seconds 3000 --confirm-paid-gpu'
```

**必须同时验收** `B25_GATE_READY`、`B25_FIRST_GATE_PASS`、`B25_ALL_VERIFIED`、原审核器 `HF_REVIEW_COMPLETED__NO_ADMISSION`、`cases_completed=25`。遇到 `B25_GATE_HOLD` 或超过资源预算，要停止并保留输出，不删除已写 Checkpoint、不把重复运行写到原目录。**HF Job 仍由 Owner Mac CLI 提交；本轮 ChatGPT 只写了代码/测试/文档。**

---


## 2026-11-11：固定权重持久化与真实模型本地加载（新增执行路径）

### 已知证据与目标

此前 H200 Dummy `DUMMY_ENGINE_READY` 耗时 28.5s；该次 CPU `CACHE_PROBE` 返回 `PINNED_SNAPSHOT_NOT_LOCAL`，只代表该 Job 的默认 HF Cache 未命中；前面真实 Trace2 卡在 safetensors 权重加载附近。Hugging Face Hub 上固定的 `Qwen/Qwen3-32B@9216db5781bf21249d130ec9da846c4624c16137` 约 65.5 GB、17 个 safetensors shard。目标是 **先把官方固定 revision 的权重可靠存入持久 Bucket，再复制到 H200 本地磁盘，经逐文件 SHA256 核验后加载真实模型**，杜绝 CPU Job 和 GPU Job 之间误以为共享临时 Cache 的问题。

### 实现内容

- `experiments/r58_quality/r60_qwen32b_weight_stage.py`：两种模式：
  - `stage`：CPU Job；先通过 Hub model_info 固定 commit sha、枚举权重/必要 tokenizer/config 文件，并取得 shard 的官方 LFS SHA256 和 size，逐个 HTTP stream 到 HF Bucket，8 MiB 分块做 SHA256 与大小核对；每个完整 shard 通过 `.r60-partial` 原子改名；写入 `r60_weights_verified_manifest.json` 作为最终完成标记。已通过完整文件的 SHA 可在下一轮 CPU Job 复用；若发现完整文件大小或哈希不匹配，fail-closed，不自动覆盖。普通小文件如上游未提供 LFS SHA，则记录流式下载得到的 SHA；这不是来自上游的独立 SHA 认证。
  - `localize`：GPU Job 的 CPU 阶段；读取 Bucket Manifest 与 safetensors index，预检本地磁盘剩余空间必须高于文件总大小 + 20GiB，逐文件流式复制到本地路径并按 Manifest SHA256 校验，全部完成后才打印 `LOCAL_WEIGHTS_READY`。Bucket 挂载只作为顺序读取来源，**vLLM 不直接从 Bucket mount 执行随机读取**。
- `experiments/r58_quality/r60_qwen32b_local_smoke.py`：独立本地权重真实加载 + 1 条**非私有合成 Prompt** 推理测试；加载时关闭 Hub/Transformers 在线访问，模型路径、tokenizer 路径指向本地目录；要求先有 `LOCAL_WEIGHTS_READY` 与 Manifest，期望 `REAL_ENGINE_READY`、`REAL_GENERATE_DONE`，不生成质量审核决策、无 Checkpoint、也不输出模型回答。此测试不是 A25 的真实案例审核验证。
- `tests/test_r60_qwen32b_weight_stage.py`：CPU 合成完整性、原子分片复制、缺片/坏 SHA、目录越界与非覆盖测试。
- **注意**：只提交了代码、测试及可复用操作步骤；**从未在本轮由 ChatGPT 提交任何新的 CPU 或 GPU Job**。没有真实 Hub 65GB 下载证据；R60 品质审核状态保持 0/25。用户已总批准相关费用，但 Owner 仍通过 Mac CLI 提交 HF Jobs。
- 官方依据：`https://huggingface.co/docs/hub/jobs-configuration`（HF Jobs mount 默认惰性下载）、`https://huggingface.co/docs/huggingface_hub/package_reference/file_download`（固定 commit 与本地下载）、`https://huggingface.co/docs/hub/storage-buckets-access`（HF Bucket）。
  
### 一、Mac 准备脚本目录（不修改 Owner 私有审查数据）

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
REV="89f5acec76d1735006a360cec671b2b55f595932"
BUNDLE="$HOME/.local/share/storyforge/r60/private/r60-weight-stage-tools"
umask 077
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
test ! -e "$BUNDLE" || { echo BUNDLE_ALREADY_EXISTS_HOLD; exit 42; }
mkdir -m 700 "$BUNDLE"
for name in r60_qwen32b_weight_stage.py r60_qwen32b_local_smoke.py; do
  git -C "$ROOT" show "$REV:experiments/r58_quality/$name" > "$BUNDLE/$name"
  chmod 600 "$BUNDLE/$name"
done
python3 -m py_compile "$BUNDLE"/*.py
```

### 二、CPU Job 下载并校验固定权重到持久 Bucket（首次执行，可能产生约 65.5GB 下载与存储）

```bash
set -euo pipefail
BUNDLE="$HOME/.local/share/storyforge/r60/private/r60-weight-stage-tools"
hf jobs run --namespace adradar --name r60-qwen32b-weight-stage \
  --flavor cpu-basic --timeout 8h --attempts 1 \
  -v "$BUNDLE:/code:ro" \
  -v "hf://buckets/adradar/storyforge-training:/bucket:rw" \
  python:3.12 \
  sh -c 'set -eu; python -m pip install -q "huggingface_hub>=0.35,<2" "requests>=2.32,<3"; mkdir -p /bucket/model-cache/qwen3-32b-9216db5; exec python -u /code/r60_qwen32b_weight_stage.py --mode stage --bucket-dir /bucket/model-cache/qwen3-32b-9216db5'
```

验收：日志最后必须有 `STAGE_COMPLETE`（或者后续同一目录的 `STAGE_ALREADY_VERIFIED`）；Bucket 出现固定目录下 `r60_weights_verified_manifest.json` 与所有预期 shards。单条 `SHARD_VERIFIED` 不能视为全部完成。若首次失败，允许在同一目录重新提交 CPU Job 继续，已通过 SHA 核验的完整 shard 不重下；暂不启动 GPU。

### 三、H200 从持久 Bucket 复制到本地磁盘并执行真正模型加载 Smoke（不读取 A25 私有输入）

```bash
set -euo pipefail
BUNDLE="$HOME/.local/share/storyforge/r60/private/r60-weight-stage-tools"
IMG="docker.io/vllm/vllm-openai@sha256:05a31dc4185b042e91f4d2183689ac8a87bd845713d5c3f987563c5899878271"
hf jobs run --namespace adradar --name r60-qwen32b-local-weight-smoke \
  --flavor h200 --timeout 90m --attempts 1 \
  -v "$BUNDLE:/code:ro" \
  -v "hf://buckets/adradar/storyforge-training:/bucket:ro" \
  "$IMG" \
  sh -c 'set -eu; echo LOCAL_LOAD_START; mkdir -p /tmp/r60-local; /usr/bin/python3 -u /code/r60_qwen32b_weight_stage.py --mode localize --bucket-dir /bucket/model-cache/qwen3-32b-9216db5 --local-dir /tmp/r60-local/qwen3-32b-9216db5; exec /usr/bin/python3 -u /code/r60_qwen32b_local_smoke.py --local-dir /tmp/r60-local/qwen3-32b-9216db5 --confirm-paid-gpu'
```

本命令有 fail-closed 磁盘预检；如果 H200 的 `/tmp` 容量不够，请不要更改或降低 +20GiB 余量要求来强行运行；换到经容量证据确认的本地盘后再重试。期望 `DISK_PREFLIGHT`、`LOCAL_WEIGHTS_READY`、`REAL_ENGINE_READY`、`REAL_GENERATE_DONE`；其中任何一个失败都不能宣布解决。

### 四、后续：A25 正式审核

**仅当上述真实本地模型 Smoke PASS** 才回到 A25 正式任务。必须再准备隔离的 runner 副本，使其在 `AutoTokenizer.from_pretrained`、`LLM(model=...)` 处都使用同一已经本地化并校验的目录，同时保持原始 `model/revision` 用于 checkpoint 来源校验；新 runner 的 AST patch 必须配合合成测试，不能把加载路径改动误写成模型 revision 变动。后续的 A25 第 1 条真实审核及 Checkpoint 写入必须在同一次 H200 加载后验证，避免再次重复 65GB 模型加载。

### 不可声称的事项

- HF Bucket 里的文件可读，不等于本地 SSD 全部页读取成功；
- `LOCAL_WEIGHTS_READY` 不等于模型推理成功；
- 合成 `REAL_GENERATE_DONE` 不等于 A25 审核已完成；
- `STAGE_COMPLETE` 也不能视作 SHA256 全仓库（包含未知非权重文件）的证明；仅覆盖选择的配置、Tokenizer 与 Safetensors 文件集合。

---


## 2026-11-11：同一 Dummy Job 默认缓存未命中（仅限定目录）

Owner 追加真实 SAFE 日志：
```json
{"event":"CACHE_PROBE","private_values_emitted":false,"schema":"storyforge_r60_weight_isolation_safe_v1","shards_expected":null,"shards_present":0,"status":"PINNED_SNAPSHOT_NOT_LOCAL"}
```
紧接着 `CACHE_NOT_VERIFIED`、`DUMMY_ENGINE_START`，该 Job 的后续日志已单独证实 `DUMMY_ENGINE_READY`（elapsed 28.5s）。探针检查的是**本次 H200 容器默认 HF 缓存中、固定 revision 的 snapshot**，它不验证 `HF_HUB_CACHE` 以外目录、以前 Job 的临时缓存、Hub 网络连接和模型文件是否损坏。因此只能说默认缓存缺失，不能断言权重从未下载，或将其直接判为全部故障根因。

**执行策略更新**：不再尝试同配置直接重跑 A25；先设计持久权重准备并检查磁盘容量、精确 revision、safetensors shard/index 数量及完整性，区分下载、远程文件 I/O 与真实 CUDA loader 阶段；H200 仅在权重准备与本地磁盘空间预检通过后，从**本地**快照加载、确认 `ENGINE_READY` 和首个真实 checkpoint。注意每个 H200 Job 的临时文件系统并不保证共享，持久 HF Bucket 应作为复制来源而不是未经测量直接 mmap safetensors 的路径。保持 A/B 盲审核及冻结源不变。

---


## 2026-11-11：H200 Dummy 引擎完成，转入真实权重路径排障

Owner 提供最新真实实验回执：
```json
{"elapsed_sec":28.5,"event":"DUMMY_ENGINE_READY","private_values_emitted":false,"schema":"storyforge_r60_weight_isolation_safe_v1"}
```

**结论与边界**：固定 Qwen3-32B revision 的 vLLM `load_format="dummy"` 已在 H200 完成引擎构造，说明基础 vLLM 引擎启动、模型配置以及部分 CUDA 初始化路径工作正常；**未读取真实权重，也未执行实际模型生成、Checkpoint 或质量审核**。不能因此证明真实权重损坏、网络/文件系统问题已被定位，也不能完全排除真实权重路径中的 CUDA/显存问题。

**下一步优先级**：

1. 获取该 Dummy Job 同一次执行中的 `CACHE_PROBE` 结果（若存在）。即使报告 `PINNED_SNAPSHOT_NOT_LOCAL`，只能证明那个容器的缓存未命中；不同 HF Jobs 之间缓存不能假定共享。
2. 不重新提交原 A25。先构造可以复用的**真实权重准备/缓存检查**流程，固定 Qwen3-32B model revision，检查索引、分片大小和完整性；评估工作目录磁盘空间，避免直接从可能的远程 FUSE 目录 mmap 读取 60+GiB safetensors。优先使用经验证的本地磁盘快照进行 vLLM 加载，避免每次初始化重新下载。
3. 真正验证路径：固定同样镜像、模型 revision 与推理设置，先完成 `ENGINE_READY`，再完成 `GENERATE_DONE`，最后通过 `review_0001.private.json` 的完整性校验。若仅 Dummy PASS 而真实本地权重仍阻塞，再追查 loader / mmap / CUDA 和 `/proc` 诊断数据。
4. A25/ B25 都只能按其各自冻结的输入 stage 进行，不可将 A 的前 25 条直接视为与 B 前 25 条已对齐；正式全量 1,000 审核仍需 Rubric v2.1 校准与质量准入验证。

**状态**：Dummy H200 **PASS**；真实 A25 完成 `0/25`，1000 候选质量准入仍为 0；不宣称根因修复，不重复付费执行相同失败命令。用户已批准后续收费，具体 HF Job 仍由 Owner Mac CLI 提交。

---


## 2026-11-11：A25 Trace2 权重加载卡点：v3 隔离诊断与根因分流

> 验证更新（2026-11-11）：权重隔离探针与安全 `/proc` 心跳代码已经提交；当前验证提交 `504e7796664f87b652e4a7bddc06822b04fddf9d`，`CI=PASS`、`R58 scoped synthetic=PASS`、`R60 Generation Eval CI=PASS`，P4 Runtime Image Candidate 查询时仍 in_progress。修复过一处 CPU 合成测试夹具错误（原测试把已存在的临时目录误认为不存在），不是生产探针故障。尚无任何 dummy H200 实测回执，不能声称根因已解决。



### 与前面三次运行的实质区别

第一次 A25 在 shell `exec python` 因 `python: not found` 失败，审核代码从未启动；第二次 `/usr/bin/python3` 可启动，但仅靠 GPU VRAM≈64GiB 与 0 日志不能判明卡点；第三次 Trace2 的 25 条私有输入、Tokenizer 与 25 条 Prompt 编码均已通过，`ENGINE_INIT_START` 已出现，vLLM INFO 记录了 `Loading model from scratch` 和 `Using model weights format ['*.safetensors']`，直到 210 秒没有 `ENGINE_READY`，子进程一直 S 睡眠、累计 CPU 秒几乎不变、GPU 利用率 0%，Checkpoint 仍 0。**这只能说明最后可见日志停在加载权重附近，不等于确定权重文件本身坏了**；下一步需区分网络/磁盘、同步等待、CUDA/运行时兼容性。

### 当前新增代码和判定能力（不改变审核 Rubric、数据、模型）

- `experiments/r58_quality/r60_pilot_diagnostic_launcher.py`：保留原 30s 心跳与 5 个 AST 阶段标记，增加 Linux `/proc/<pid>/wchan` 内核等待状态的允许类别（`FILE_IO_WAIT / SYNC_WAIT / NETWORK_OR_POLL_WAIT / TIMER_WAIT / OTHER_WAIT / UNKNOWN`）以及所有 vLLM 子进程累计磁盘 `read_bytes/write_bytes` MiB。**仅类别和数值，禁止打印原始 wchan、进程环境、私有路径/正文**。计数在容器权限限制下可能不可用；`S` 状态本身并不代表死锁。
- `experiments/r58_quality/r60_vllm_weight_isolation_probe.py`：独立探针，两个显式模式：
  1. `--mode cache`：不启动 GPU、不下载模型，只检查**当前执行环境**下固定 Qwen3-32B revision 的 Hugging Face cache 是否存在 `model.safetensors.index.json`，索引中的分片是否齐全、每个能否读取头尾各 4KiB，输出分片数量、总权重 GiB 与样本读取时间，不输出权重路径。**这不是完整 SHA256 完整性证明，也不能预测所有页读取是否正常**。
  2. `--mode dummy --confirm-paid-gpu`：在固定 H200/vLLM 镜像上以相同模型 revision、max_model_len 32768、dtype BF16、enforce_eager 等参数构造 LLM，但使用 `load_format="dummy"`，不读真实权重、不审核数据、不生成 Checkpoint。返回 `DUMMY_ENGINE_READY` 仅证明**跳过权重情况下引擎初始化可完成**，不等于真实推理 PASS。若 dummy 也卡住，优先排查 CUDA、vLLM 子进程/驱动；若 dummy PASS 而真实权重仍卡，优先排查权重路径、文件系统及模型 loader。
- `tests/test_r60_vllm_weight_isolation_probe.py`：纯 CPU 合成索引的完整、缺片、路径越界/无效索引拒绝测试；未启动收费 GPU。
- 参考 vLLM 0.10.0 官方 Troubleshooting：模型下载挂起与磁盘文件读取挂起需分别定位；推荐先在本地磁盘完整下载，并可用 `load_format=dummy` 跳过权重分离问题。参考：https://docs.vllm.ai/en/v0.10.0/usage/troubleshooting.html
- **可靠性原则**：不能声称问题已经彻底解决；仅在真实权重 `ENGINE_READY` + 至少一个真实 `GENERATE_DONE` + Checkpoint 校验后，才视为故障解除。用户已总体授权收费，但仍由 Owner 在 Mac CLI 发 HF Jobs，不通过 ChatGPT HF 连接器提交。

### Owner Mac CPU-only 准备（不会修改已冻结输入；只在诊断副本增加新探针）

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
PILOT="$HOME/.local/share/storyforge/r60/private/r60-hf-quality-pilot25-vllm0100"
REV="289e1d21649b522c21dcfd7aa82b0de204d90a08"
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
umask 077
PROBE="$PILOT/input_A_trace2/r60_vllm_weight_isolation_probe.py"
test ! -e "$PROBE" || { echo WEIGHT_PROBE_ALREADY_EXISTS_HOLD; exit 42; }
git -C "$ROOT" show "$REV:experiments/r58_quality/r60_vllm_weight_isolation_probe.py" > "$PROBE"
chmod 600 "$PROBE"
python3 -m py_compile "$PROBE"
```

**注意：在 Mac 上执行 `--mode cache` 只检查 Mac 的本地缓存，不能证明 HF H200 容器里的缓存存在。即使 CPU 和 H200 Job 用相同镜像，如果没有挂载相同的持久化缓存，也不能假设它们共享模型文件。**

### 建议的下一次隔离验证（不要立刻重新执行 A25 正式审核）

先在 **15 分钟封顶、单次尝试** 的 H200 Job 里执行 `cache` 快速检查（允许返回 42），然后执行 `dummy` 跳过权重探针。这个操作会产生 GPU 费用，但不下载整套模型权重用于正式审核、不产生任何审核样本结果：

```bash
set -euo pipefail
PILOT="$HOME/.local/share/storyforge/r60/private/r60-hf-quality-pilot25-vllm0100"
IMG="docker.io/vllm/vllm-openai@sha256:05a31dc4185b042e91f4d2183689ac8a87bd845713d5c3f987563c5899878271"
hf jobs run --namespace adradar --name r60-a25-dummy-weight-isolation \
  --flavor h200 --timeout 15m --attempts 1 \
  -v "$PILOT/input_A_trace2:/input:ro" \
  "$IMG" \
  sh -c 'set -eu; test -x /usr/bin/python3 || exit 42; echo WEIGHT_ISOLATION_START; /usr/bin/python3 -u /input/r60_vllm_weight_isolation_probe.py --mode cache || echo CACHE_NOT_VERIFIED; exec /usr/bin/python3 -u /input/r60_vllm_weight_isolation_probe.py --mode dummy --confirm-paid-gpu'
```

若 `DUMMY_ENGINE_READY`，后续应先通过 **可持久化的 HF Bucket/CPU Job 下载权重和 SHA/大小校验**，再在 H200 上将权重完整复制到**本机容器真实本地磁盘**并从本地路径加载；不应直接在 Bucket FUSE 上做 mmap 随机读取。要先验证 H200 本地磁盘剩余空间，再设计下载/复制作业与原 revision 的离线校验。若 dummy 失败，则不下载 65GiB 权重，优先排查镜像/驱动/多进程配置。**不要把 dummy 结果当作实际审核器或模型可用性的结论**。

---


## 2026-11-11：Trace2 CPU 准备 HOLD 根因定位及修复

Owner 实际返回 `R60_TRACE_A25_PREPARE_HOLD` / `INFERENCE_ANCHOR_COUNT_HOLD`，GPU=0、HF Job=0、私有内容未输出。此错误是**诊断准备器的 AST 检测假设不完整**，不是模型加载失败或 A25 训练数据问题。

原 R60 审核器使用 `result = engine.generate(...)[0].outputs[0]`，生成调用在 Python AST 中嵌套于 Subscript/Attribute 节点；早期 Trace2 准备器只处理 `ast.Assign.value` 直接等于 `ast.Call`，因此未识别 GENERATE 锚点。现已修补诊断准备器：有限层数解包 `Subscript` / `Attribute`，只允许直接链上的 `engine.generate`，不会误把 `other_func(engine.generate(...))` 当生成锚点；锚点不匹配时 SAFE `reason_code` 附上 5 个阶段的匹配计数，不打印故事正文。合成测试已覆盖原审核器实际的链式调用。

**修复固定代码**：`cf678c5208a7e46d552241f228d2b079ee4e32b5`；回归测试 `87d40c9b1275b79ee190315a9c2aa155f65a2ff5`。需以最新 GitHub CI 结果为准，尚未收到 Mac 私有 Trace2 准备 PASS 回执。

执行方式与本文件前述 Trace2 步骤相同；仅将前述 `REV` 更新为 `87d40c9b1275b79ee190315a9c2aa155f65a2ff5`。因 create-only 的准备器在所有校验通过后才创建目标目录，之前这次 HOLD 不应创建 `input_A_trace2`；若目录已经存在，保留现场并拒绝覆盖。先准备、verify-only，再提交新的 A25 Job；不能把 CPU 准备 PASS 解释为已完成审核。

---


## 2026-11-11：第二次 A25 因 vLLM 初始化疑似停滞取消；改为精确阶段诊断 v2

Owner 明确已停止 Job `6af34cdb9737d9a9e0910ddb`，其日志在 330.4s 时仍 `ENGINE?` 未区分、`GPU VRAM=63319 MiB`、`GPU util=0%`、`主 Python CPU 秒=22.2`、`checkpoints_written=0`。这组事实**不能**单独证明 GPU 死锁，旧 v1 心跳只统计主 Python 进程，未解析 vLLM 子进程，也没有区分 `AutoTokenizer.from_pretrained`、`LLM(...)` 和 `generate`。停机动作已由 Owner 完成，暂停再次重复相同命令。

### v2 诊断变更（仅新副本）

- `experiments/r58_quality/r60_pilot_trace_prepare.py`：要求已固定 A25 输入 SHA256 `492f24f7cb6171481e0e6d176cfa862ec6f5223bdd7abc3cfb518335dc9ab069`；从原 `input_A` **创建新 `input_A_trace2` 目录**，原始 25 条输入、四个运行模块与审核器代码保持原样；对新副本通过 AST 识别 5 个代码位置（Tokenizer 加载、Prompt Token 编码、`LLM(...)` 引擎构造、SamplingParams、`engine.generate`），各前后插入 `_r60_diag_event` 标记；如果代码结构或源 SHA 不符合预期则 HOLD，避免直接猜测旧源码行号；仅将新副本中的 `VLLM_LOGGING_LEVEL` 从 WARNING 改到 INFO（`disable_log_stats=True` 保留，不输出逐请求正文）；不更改模型 revision、采样参数、审核 rubric 或 Checkpoint 格式。
- `experiments/r58_quality/r60_pilot_diagnostic_launcher.py`：新增从 `/proc` 汇总**子进程**数量、CPU 总时间、常驻内存、R/S/D/Z 等状态计数，所有字段均为数值/枚举，不打印命令行或环境变量；向新 AST 标记提供 `worker._r60_diag_event=set_stage` 回调。30s 的 HEARTBEAT 与原有 CPU/GPU/NVIDIA SMI 指标保留。vLLM 原生子进程若不属于 main 进程树则可能无法统计，属于诊断盲区。
- `tests/test_r60_pilot_trace_prepare.py`：合成 CPU-only 校验 SHA、5 个标记位置、私有目录权限、重复目录拒绝、源码漂移失败、原冻结输入和 runner 不变。此前 `tests/test_r60_pilot_diagnostic_launcher.py` 仍覆盖无私有输出、Checkpoint 事件。
- **当前已提交 GitHub，但未取得 CI PASS/Owner Mac CPU-only prepare PASS。任何失败继续 fail-closed，不应直接重提 GPU。**

### Owner Mac 安装 v2 准备器与最新版 launcher（均为 CPU-only）

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
BASE="$HOME/.local/share/storyforge/r60/private"
PILOT="$BASE/r60-hf-quality-pilot25-vllm0100"
REV="8c6b2317d266b958b87d2fd7ac0e525d718e06ae"
umask 077

git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
PREP="$BASE/r60_pilot_trace_prepare.py"
LAUNCH="$BASE/r60_pilot_diagnostic_launcher_v2.py"
test ! -e "$PREP" && test ! -e "$LAUNCH" || { echo PRIVATE_DIAG_TOOL_EXISTS_HOLD; exit 42; }
git -C "$ROOT" show "$REV:experiments/r58_quality/r60_pilot_trace_prepare.py" > "$PREP"
git -C "$ROOT" show "$REV:experiments/r58_quality/r60_pilot_diagnostic_launcher.py" > "$LAUNCH"
chmod 600 "$PREP" "$LAUNCH"
python3 -m py_compile "$PREP" "$LAUNCH"

python3 "$PREP" \
  --source-dir "$PILOT/input_A" \
  --dest-dir "$PILOT/input_A_trace2" \
  --launcher-file "$LAUNCH"

python3 -u "$PILOT/input_A_trace2/r60_pilot_diagnostic_launcher.py" \
  --input "$PILOT/input_A_trace2/source.private.jsonl" \
  --output-dir "$PILOT/output_A" --model Qwen/Qwen3-32B \
  --revision 9216db5781bf21249d130ec9da846c4624c16137 \
  --verify-only
```

准备器期望 `R60_TRACE_A25_PRIVATE_READY__NO_GPU`、`anchors={"tokenizer":1,"encode":1,"engine":1,"params":1,"generate":1}`，无 HF Job/费用；本地 verify-only 应出现 BOOT、INPUT_VERIFIED、RUNNER_EXIT exit_code=0。

### Owner Mac v2 A25 GPU Job（在本地校验 PASS 后）

与旧 Job 相同模型、镜像、H200、超时 90m、attempts 1；**新的唯一 Bucket 输出目录** `r60-1000-pilot25-vllm0100-a-trace2`，绝不删除旧 `a`、`a-diag1`：

```bash
set -euo pipefail
PILOT="$HOME/.local/share/storyforge/r60/private/r60-hf-quality-pilot25-vllm0100"
IMG="docker.io/vllm/vllm-openai@sha256:05a31dc4185b042e91f4d2183689ac8a87bd845713d5c3f987563c5899878271"
hf jobs run --namespace adradar --name r60-quality-a25-trace2 \
  --flavor h200 --timeout 90m --attempts 1 \
  -v "$PILOT/input_A_trace2:/input:ro" \
  -v "hf://buckets/adradar/storyforge-training:/bucket:rw" \
  "$IMG" \
  sh -c 'set -eu; echo TRACE2_SHELL_START; test -x /usr/bin/python3 || exit 42; test -f /input/r60_pilot_diagnostic_launcher.py || exit 42; OUT=/bucket/evaluation-runs/r60-1000-pilot25-vllm0100-a-trace2; if [ -e "$OUT" ]; then echo OUTPUT_ALREADY_EXISTS_HOLD; exit 42; fi; mkdir -p "$OUT"; exec /usr/bin/python3 -u /input/r60_pilot_diagnostic_launcher.py --input /input/source.private.jsonl --output-dir "$OUT" --model Qwen/Qwen3-32B --revision 9216db5781bf21249d130ec9da846c4624c16137 --start 1 --limit 25 --max-model-len 32768 --max-output-tokens 2400 --max-wall-seconds 3000 --confirm-paid-gpu'
```

GPU 日志以 `TOKENIZER_LOAD_START`、`TOKENIZER_LOADED`、`TOKEN_ENCODING_START/DONE`、`ENGINE_INIT_START`、`ENGINE_READY`、`GENERATE_START`、`GENERATE_DONE`、`CHECKPOINT_WRITTEN` 为关键。若一直停留 `ENGINE_INIT_START`，结合子进程 `R/S/D/Z` CPU 时间变化与 vLLM INFO 日志进一步定位。无论是否收费授权，必须先获得新准备器 SAFE PASS；若 v2 运行仍僵住，不再未经原因分析便循环重提同配置。

---


## 2026-11-11：A25 Job 已手动停止；增加详细 SAFE 心跳日志并准备受控重跑

Owner 报告 A25 Job `6af346e9ab34849891ac4e65` 已停止。此前状态 `RUNNING`、`CPU 0%`、`GPU 0%`、`GPU VRAM 64/144 GB`、`hf jobs logs` 空、输出 Bucket 子目录空。**不能凭显存 64GB 断言模型已完成初始化；未验证任何 Checkpoint，正式审核进度仍 0。** 用户已明确授予后续付费调用总体批准，但按此前约定 HF Jobs 仍由 Owner Mac CLI 执行；不经由受限 ChatGPT HF 连接器提交。

### 新增可复用诊断器与单测

- `experiments/r58_quality/r60_pilot_diagnostic_launcher.py`：纯 Python 标准库，作为 *原审核器的外部入口*；它动态导入同目录 **不变的** `runner.py`，仅包装 `read_input`、`inference`、`write_checkpoint` 发出安全事件，不读取正文日志或修改模型生成参数。
- 启动立即发 `BOOT`，之后每 30s `HEARTBEAT`（允许列表化 stack phase、进程 CPU 秒与峰值 RSS、`nvidia-smi` 可用时 GPU 利用率和显存）。若调用在原生 C/CUDA 中，则 stack phase 只到 `OTHER_OR_NATIVE_WAIT` / `INFERENCE_FUNCTION`，**并不能识别所有内部 CUDA 阶段**。
- 出现事件：`READ_INPUT`/`INPUT_VERIFIED`、`INFERENCE_ENTER`、`CHECKPOINT_WRITTEN`、`INFERENCE_SUMMARY`、`RUNNER_EXIT`。异常仅输出允许的状态码；不记录私有历史、blind_id、target、引用、模型生成文本、路径或异常信息。
- `tests/test_r60_pilot_diagnostic_launcher.py`：合成 runner 的分阶段事件、Checkpoint、保留原文件和私有内容脱敏测试。通过本地合成运行路径验证逻辑；仓库 CI 结果仍待核对。
- **仍然需要使用 `/usr/bin/python3 -u`**：旧 `python` 不存在；`-u` 使 Python 不缓冲输出。shell 首条 `echo` 用于区分入口解释器错误。

### Owner Mac 安装独立诊断器到现有 A25 私有 stage

**只复制新增入口，不运行任何 GPU，也不修改旧 runner 或冻结 25 行输入。**

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
PILOT="$HOME/.local/share/storyforge/r60/private/r60-hf-quality-pilot25-vllm0100"
REV="1c22148380c7525abc5e47ba7e7b76b4ba62866c"
TARGET="$PILOT/input_A/r60_pilot_diagnostic_launcher.py"
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
test ! -e "$TARGET" || { echo DIAGNOSTIC_LAUNCHER_ALREADY_EXISTS_HOLD; exit 42; }
umask 077
git -C "$ROOT" show "$REV:experiments/r58_quality/r60_pilot_diagnostic_launcher.py" > "$TARGET"
chmod 600 "$TARGET"
python3 -m py_compile "$TARGET"
python3 "$TARGET" --input "$PILOT/input_A/source.private.jsonl" \
  --output-dir "$PILOT/output_A" --model Qwen/Qwen3-32B \
  --revision 9216db5781bf21249d130ec9da846c4624c16137 --verify-only
```

上面在 Mac CPU-only 模式测试入口，期望 `BOOT`、`INPUT_VERIFIED`、`RUNNER_EXIT exit_code=0` 与原 `HF_REVIEW_INPUT_VERIFIED__NO_INFERENCE`。**旧 `--verify-only` 不导入 vLLM、不启动 GPU**。

### A25 新的真实 GPU Job 启动命令（Owner Mac 执行，已得到总体付费授权）

使用一个新的唯一目录 `a-diag1`，保留 `a` / `a-retry1` 历史目录（不删除、也不从旧目录误计 checkpoint）：

```bash
set -euo pipefail
PILOT="$HOME/.local/share/storyforge/r60/private/r60-hf-quality-pilot25-vllm0100"
IMG="docker.io/vllm/vllm-openai@sha256:05a31dc4185b042e91f4d2183689ac8a87bd845713d5c3f987563c5899878271"
hf jobs run --namespace adradar --name r60-quality-a25-diag1 \
  --flavor h200 --timeout 90m --attempts 1 \
  -v "$PILOT/input_A:/input:ro" \
  -v "hf://buckets/adradar/storyforge-training:/bucket:rw" \
  "$IMG" \
  sh -c 'set -eu; echo DIAG_SHELL_START; test -f /input/r60_pilot_diagnostic_launcher.py || { echo LAUNCHER_NOT_FOUND_HOLD; exit 42; }; OUT=/bucket/evaluation-runs/r60-1000-pilot25-vllm0100-a-diag1; if [ -e "$OUT" ]; then echo OUTPUT_ALREADY_EXISTS_HOLD; exit 42; fi; mkdir -p "$OUT"; exec /usr/bin/python3 -u /input/r60_pilot_diagnostic_launcher.py --input /input/source.private.jsonl --output-dir "$OUT" --model Qwen/Qwen3-32B --revision 9216db5781bf21249d130ec9da846c4624c16137 --start 1 --limit 25 --max-model-len 32768 --max-output-tokens 2400 --max-wall-seconds 3000 --confirm-paid-gpu'
```

新 Job 每 30 秒应看到至少一个 `HEARTBEAT`，典型输出只含 `event`、`elapsed_sec`、`stage`、`stack_phase`、CPU/RAM/GPU 数值。**如果 `BOOT` 后无心跳，优先诊断容器/进程被外部终止，而不是按正常模型加载处理。** 任何私有回执和 checkpoint 仍留在 HF Bucket。任务成功前不提交 B25。

---


## 2026-11-11：首个 A25 Job ERROR 127，容器找不到 `python`，无推理

Owner Mac 返回：
```
job: https://huggingface.co/jobs/adradar/6af346279737d9a9e090f98b
sh: 1: exec: python: not found
stage: ERROR
exit code: 127
```

**定案**：旧执行命令在 vLLM Docker 镜像内 `sh -c '... exec python /input/runner.py ...'`，但镜像未提供 `python` 命令。此故障发生在加载模型、运行审核器之前；不能推断 vLLM 模型加载、GPU 占用或 Checkpoint 写入成功。虽然没有发生推理，HF 启动阶段资源可能已计费，不能声称零费用。Hugging Face 官方 [Jobs Docker images](https://huggingface.co/docs/hub/jobs-images) 针对 `vllm/vllm-openai` 使用系统 Python `/usr/bin/python3`；此版本仅根据示例路径提出修复，精确固定 Digest 的解释器路径仍建议在实际镜像中快速检查。

**最小修复**：在已通过的 A25 命令中将 `exec python /input/runner.py` 改为 `exec /usr/bin/python3 /input/runner.py`，保留镜像 SHA、模型 revision、`--limit 25`、`--attempts 1`、`--timeout 90m` 及输出 Bucket 根挂载。**不要重新创建 Pilot25，不要改旧冻结数据，不要修改旧 Job 的输出为成功。**

正式再次提交前，当前已存在上次 Job 尝试创建的 `/bucket/evaluation-runs/r60-1000-pilot25-vllm0100-a` 目录；上一次命令 `mkdir -p "$OUT"` 后才执行 Python，所以它很可能已创建、可能为空。**原命令中的 `if [ -e "$OUT" ]; then ... HOLD` 会挡住下一次提交；严禁无检查删除原目录。** 续跑使用新唯一目录 `r60-1000-pilot25-vllm0100-a-retry1`，保留旧目录与原 Job 的诊断证据，仍然拒绝目录覆盖。如果旧 A Job 没有启动推理，不必下载新数据，也不必重做 1000 条 token preflight。

Owner Mac 如需检查 0 GPU 的镜像 Python 路径，可用本机 Docker（会拉取镜像层，可能体积大），或 HF CPU Job，命令示例：
```bash
hf jobs run --dry-run --namespace adradar --flavor cpu-basic --timeout 10m --attempts 1 \
  docker.io/vllm/vllm-openai@sha256:05a31dc4185b042e91f4d2183689ac8a87bd845713d5c3f987563c5899878271 \
  sh -c 'command -v python3; test -x /usr/bin/python3; /usr/bin/python3 --version'
```
dry-run 只检查格式，不会证实解释器存在。若本机或 CPU 实测证明解释器存在，则可再付费 A25。模型架构/vLLM 参数的真实兼容性仍未知。

**直接 A25 二次提交建议**（仅 Owner Mac 执行；这是新的收费 Job，必须重新明确成本授权，不应自动提交）：

```bash
set -euo pipefail
PILOT="$HOME/.local/share/storyforge/r60/private/r60-hf-quality-pilot25-vllm0100"
IMAGE="docker.io/vllm/vllm-openai@sha256:05a31dc4185b042e91f4d2183689ac8a87bd845713d5c3f987563c5899878271"
hf jobs run --namespace adradar --name r60-quality-a25-pilot-retry1 \
  --flavor h200 --timeout 90m --attempts 1 \
  -v "$PILOT/input_A:/input:ro" \
  -v "hf://buckets/adradar/storyforge-training:/bucket:rw" \
  "$IMAGE" \
  sh -c 'set -eu; test -x /usr/bin/python3 || { echo PYTHON3_NOT_FOUND_HOLD; exit 42; }; OUT=/bucket/evaluation-runs/r60-1000-pilot25-vllm0100-a-retry1; if [ -e "$OUT" ]; then echo OUTPUT_ALREADY_EXISTS_HOLD; exit 42; fi; mkdir -p "$OUT"; exec /usr/bin/python3 /input/runner.py --input /input/source.private.jsonl --output-dir "$OUT" --model Qwen/Qwen3-32B --revision 9216db5781bf21249d130ec9da846c4624c16137 --start 1 --limit 25 --max-model-len 32768 --max-output-tokens 2400 --max-wall-seconds 3000 --confirm-paid-gpu'
```

不得自动启动 B25；待 A25 真实成功后，对 `review_XXXX.private.json` 做私有回收、输入 SHA 和 blind_id 校验，再按 Owner crosswalk 对齐。

---


## 2026-11-11：Owner 已批准并提交 A25 真实 H200 Job（最终状态待回执）

用户明确批准此前约定的 A25 H200、timeout 90m、attempts 1 单次收费任务，并提供已提交 HF Job：
- Job ID：`6af346279737d9a9e090f98b`
- URL：https://huggingface.co/jobs/adradar/6af346279737d9a9e090f98b
- 角色：A / `Qwen/Qwen3-32B`
- 范围：独立 Pilot25 25 条（据前一份 dry-run/已批准配置；**任务实际启动配置尚未由 HF 回执再次核验**）
- 已知 Pilot25 源 SHA：`492f24f7cb6171481e0e6d176cfa862ec6f5223bdd7abc3cfb518335dc9ab069`；Model revision：`9216db5781bf21249d130ec9da846c4624c16137`
- 当前状态：`JOB_SUBMITTED__RESULT_PENDING`。不能因 URL 存在就宣称推理成功、Checkpoint 已保存或已有 PASS/REJECT。
- **禁止**重提 A25 或自动提交 B25；先验 Job 状态、SAFE 日志、`review_XXXX.private.json` 存储与 SHA/来源校验。若失败，有结果时分析失败路径/已落盘 checkpoint 后再决定续跑。

Owner Mac 只读查看状态和日志（按本机 HF CLI 支持的子命令）：

```bash
hf jobs inspect 6af346279737d9a9e090f98b
hf jobs logs 6af346279737d9a9e090f98b
```

若 `inspect` 子命令不可用，先 `hf jobs --help` 确认当前 CLI 对应命令；不要将私有模型回复正文或 Token 粘贴到公共 issue。仅汇报 Job state、exit status、SAFE JSON、output checkpoint 计数。现有 1000 正式质量审核统计仍 `0/1000`，除非新 GPU checkpoint 校验并与 Owner crosswalk 对齐，才更新进度。

---


## 2026-11-11 Owner A25 HF Job dry-run PASS；收费运行前改为可靠 Bucket 根挂载

Owner Mac 返回 HF CLI dry-run 配置，镜像 Digest、A25 本地只读目录、模型固定 revision、H200、90m、单次尝试、`--start 1 --limit 25` 均解析正确，明确 `Job not submitted`。这一结果是**命令解析 PASS**，不是 GPU/可写 Bucket PASS。

HF 官方 [Jobs Configuration](https://huggingface.co/docs/hub/jobs-configuration) 和 [HF URI](https://huggingface.co/docs/huggingface_hub/en/package_reference/hf_uris) 支持 Bucket 根挂载与子目录路径，但 dry-run 不保证子目录已创建或可写。为减少首次真实 Job 因输出目录不存在失败，固定使用已存在 Bucket 根路径 `hf://buckets/adradar/storyforge-training:/bucket:rw`，在容器内创建唯一实验路径 `/bucket/evaluation-runs/r60-1000-pilot25-vllm0100-a`，并在启动阶段拒绝已有 `review_*.private.json`，保持 create-only 与断点证据完整。

**建议 Owner Mac 单次批准后执行的 A25 方案**（不是 ChatGPT 自动提交；H200 90m 为硬超时，非已确认报价）：

```bash
set -euo pipefail
PILOT="$HOME/.local/share/storyforge/r60/private/r60-hf-quality-pilot25-vllm0100"
IMAGE="docker.io/vllm/vllm-openai@sha256:05a31dc4185b042e91f4d2183689ac8a87bd845713d5c3f987563c5899878271"
OUT="/bucket/evaluation-runs/r60-1000-pilot25-vllm0100-a"
hf jobs run --namespace adradar --name r60-quality-a25-pilot \
  --flavor h200 --timeout 90m --attempts 1 \
  -v "$PILOT/input_A:/input:ro" \
  -v "hf://buckets/adradar/storyforge-training:/bucket:rw" \
  "$IMAGE" \
  sh -c 'set -eu; OUT=/bucket/evaluation-runs/r60-1000-pilot25-vllm0100-a; if [ -e "$OUT" ]; then echo OUTPUT_ALREADY_EXISTS_HOLD; exit 42; fi; mkdir -p "$OUT"; exec python /input/runner.py --input /input/source.private.jsonl --output-dir "$OUT" --model Qwen/Qwen3-32B --revision 9216db5781bf21249d130ec9da846c4624c16137 --start 1 --limit 25 --max-model-len 32768 --max-output-tokens 2400 --max-wall-seconds 3000 --confirm-paid-gpu'
```

**说明**：上方不使用 `--dry-run`，因此会提交收费 Job；只有 Owner 明确批准此固定资源与上限后由 Owner Mac 执行。新输出目录不存在才创建，不覆盖旧结果；Job 异常失败时请先回传 Job ID + SAFE 日志，**不要重提任务/新建另一目录来规避失败**，避免重复收费或丢失阶段证据。此预防方案可能不能处理所有底层目录权限与 Bucket 挂载问题，需以真实运行结果为准。

计算成本：根据 HF H200 当前实际每小时价格 × 最多 1.5 小时估算每 Job 上限，A/B 是独立两次，自动重试=1。用户最终决定是否运行前，应在 Mac 确认价格、可用额度。

---


## 2026-11-11 A Pilot25 输入真实 verify-only PASS；取消单条收费 Smoke

Owner Mac 在独立 Pilot25 A 分片上得到 `HF_REVIEW_INPUT_VERIFIED__NO_INFERENCE`，`cases_total=25`、`cases_completed=0`、`training_authorized=false`、`private_values_emitted=false`。这只验证 A 的 25 个审核输入，B 的独立分片仍需要在 B 第一次执行前 verify-only；不再做重复的 1000 条输入预检。

用户明确表示希望**直接 25 条，跳过独立 1 条真实 GPU Smoke**：32B 模型启动和权重加载属于较大固定成本，使用同一次加载连续审 25 条、并以逐条 checkpoint 记录成功/失败更经济。此更改不等于允许 GPU Job 自动提交或取消成本限制。

已核实 vLLM 0.10.0 的 API 为 `GuidedDecodingParams(json=...)` 和 `SamplingParams(guided_decoding=...)`，准备器修补方向正确（[v0.10.0 官方 API](https://docs.vllm.ai/en/v0.10.0/api/vllm/sampling_params.html)），但模型权重加载/上下文以及可写 bucket 仍须在实机确认。

### A 25 条 Job 参数改动（运行命令需经 Owner dry-run）

- `--start 1 --limit 25 --max-wall-seconds 3000`，不是 limit 1。
- `hf jobs run --flavor h200 --timeout 90m --attempts 1`（时长为**上限**，不是实际预计成本）。
- 本地挂载仅 `input_A` 的 25 行独立私有目录；独立 A 输出 HF bucket 路径；输出不能上传/暴露回公开 GitHub。
- `-v` HF bucket **子目录**挂载语义需先确认；禁止把未经验证的子目录当作一定存在。即使 Job 返回 `HF_REVIEW_COMPLETED__NO_ADMISSION` 也须私有 checkpoint 读回并与原始 source/crosswalk 对齐，才计算 1000 进度。
- 对 B 的 25 条也需要独立启动和输出。由于原始 A/B 1000 输入独立洗牌，两个前 25 并非严格配对样本，不能按 `complete_pairs=25` 上报。

**范围现状**：A Pilot25 verify-only PASS，A/B 模型实际审核均 0、HF Job 未启动。下一阶段进行明确的 dry-run 与人工成本上限确认，然后由 Owner Mac 手动执行 A25 GPU Job，避免再做 1-case 付费任务。

---


## 2026-11-11 Owner Pilot25 私有分片正式 PASS，下一步只需轻量结构校验与 Job dry-run

Owner Mac 最新实际回执：
```json
{"schema":"storyforge_r60_pilot25_vllm0100_prepare_safe_v1","status":"R60_PILOT25_PRIVATE_STAGED__GPU_NOT_AUTHORIZED","cases_per_role":25,"source_cases_per_role":1000,"model_roles":["A","B"],"image":"docker.io/vllm/vllm-openai@sha256:05a31dc4185b042e91f4d2183689ac8a87bd845713d5c3f987563c5899878271","runner_api":"vllm0100_GuidedDecodingParams_PATCHED_COPY","original_input_sha256":{"A":"687528efe5081ac8ce32dcb88f575b3e59d9e7536baf6bd5ec1563283e455320","B":"2898dc355c8348140192dc018d9632b1877d216763d077a83f9530845b954139"},"pilot_input_sha256":{"A":"492f24f7cb6171481e0e6d176cfa862ec6f5223bdd7abc3cfb518335dc9ab069","B":"01639568cf21a7b98356f2b3b74f567943b4a6844edb9230b58759789ab67fc9"},"original_inputs_unchanged":true,"hf_jobs_submitted":0,"gpu_started":false,"inference_started":false,"training_started":false,"private_values_emitted":false}
```

**状态**：两侧各 25 个独立盲审输入已安全准备；原 1000 完全不变，未产生推理或费用。不能把该状态解释为审核了 25 条。

### Owner Mac 一次性本地校验（无需再次 1000 token preflight）

```bash
set -euo pipefail
BASE="$HOME/.local/share/storyforge/r60/private"
PILOT="$BASE/r60-hf-quality-pilot25-vllm0100"
for ROLE in A B; do
  case "$ROLE" in
    A) MODEL=Qwen/Qwen3-32B; REV=9216db5781bf21249d130ec9da846c4624c16137 ;;
    B) MODEL=zai-org/GLM-4-32B-0414; REV=8dea913c41b543527c2860fb6f3c15c202f24aeb ;;
  esac
  python "$PILOT/input_$ROLE/runner.py" \
    --input "$PILOT/input_$ROLE/source.private.jsonl" \
    --output-dir "$PILOT/output_$ROLE" \
    --model "$MODEL" --revision "$REV" --verify-only
done
```

期望各返回 `HF_REVIEW_INPUT_VERIFIED__NO_INFERENCE`、`cases_total=25`。

### HF Jobs 无费用配置演练（先 A 1-case）

正式收费前先验证 dry-run 在当前 Mac CLI 能解析容器命令、只含 A 的 25 条输入与单独的 HF bucket 输出卷；**dry-run 不代表 GPU runtime 通过，也不得作为付费提交凭证**。

```bash
set -euo pipefail
BASE="$HOME/.local/share/storyforge/r60/private"
PILOT="$BASE/r60-hf-quality-pilot25-vllm0100"
IMG="docker.io/vllm/vllm-openai@sha256:05a31dc4185b042e91f4d2183689ac8a87bd845713d5c3f987563c5899878271"
OUT="hf://buckets/adradar/storyforge-training/evaluation-runs/r60-1000-pilot25-vllm0100-a:/output:rw"

hf jobs run --dry-run --namespace adradar \
  --name r60-pilot25-a-smoke1 \
  --flavor h200 --timeout 60m --attempts 1 \
  -v "$PILOT/input_A:/input:ro" -v "$OUT" \
  -e HF_HUB_DISABLE_PROGRESS_BARS=1 \
  "$IMG" -- \
  python /input/runner.py \
    --input /input/source.private.jsonl \
    --output-dir /output --model Qwen/Qwen3-32B \
    --revision 9216db5781bf21249d130ec9da846c4624c16137 \
    --start 1 --limit 1 --max-model-len 32768 \
    --max-output-tokens 2400 --max-wall-seconds 1800 \
    --confirm-paid-gpu
```

**不要**仅去掉 `--dry-run` 立即运行：先检查独立远端输出目录是否已存在/为空、是否与别的任务冲突、H200 成本预算、vLLM 运行时和 Qwen3/B 模型架构支持，再由 Owner Mac 自行决定/明确激活一次性 GPU。这里的 `--confirm-paid-gpu` 只是旧 runner 的命令行门禁，不是项目授权。

- 文档和启动演练只使用 Owner 已提供的模型 revision、镜像 SHA、固定 stage 路径。仓库从未收到数据正文、blind IDs、输出或 HF Token。
- 因旧 stage 的 A/B `blind_id` 按模型独立随机分配，两个 25-case pilot 通过 `case_count=25` 并不能自动证明两侧前 25 是相同源 case；需根据 Owner 本地 `owner_crosswalk.private.json` 做对应源索引的纯本地集合核对，不能把双模型同时审前 25 当作严格同案配对证据。
- 输出 Checkpoint 写入新 HF bucket 私有路径，**不会自动**写回原始 Mac staging；必须 Owner 下载、SHA/来源复核后以保留原序号与 blind ID 的 create-only 方式对齐到原始 1000 账本，不能仅凭 Job 日志累计 `model_a_reviewed`。
- 1000 精筛仍需要 Rubric v2.1 的 30-case 三模型校准决定正式准入策略；pilot 是审核稳定性/耗时/成本证据，不是人工校准集。

---


## 2026-11-11 Pilot25 `KW_0` 根因已确认：准备器正则转义错误

Owner 用只读 grep 证实 staged `input_A/runner.py`：
- 第 338 行：`from vllm.sampling_params import StructuredOutputsParams`；
- 第 361 行：`structured_outputs=StructuredOutputsParams(json=response_schema())`。

`TYPE_2__KW_0` 并非源文件缺少关键词，而是此前准备器写错了 Python 正则：`r"\\\\bstructured_outputs\\\\s*="` 在源码中对 `\\b` / `\\s` 双重转义，匹配的是字面反斜线，不是 word boundary / whitespace。**这属于准备器实现缺陷，不能把错误归因于冻结的源 runner。** 已修正三处相同模式（识别、替换、残留检验）为 `r"\\bstructured_outputs\\s*="` / `r"\\bstructured_outputs(?=\\s*=)"`，保留只改新副本与所有 fail-closed 检查；新增直接回归 `KW_0` 测试。

- 实际修复代码：`ce81cb784c7141d457f094e17a8717ebd09ea7d7`；
- 测试提交：`66c55385936defd2be091b6b7609f3fc0fd1ca8e`；
- `CI` 尚未确认 PASS，真实 private staging 尚未重新生成。此前 HOLD 不涉及任何 GPU Job。

Owner Mac 执行最新固定提交的纯 CPU 准备器：

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
BASE="$HOME/.local/share/storyforge/r60/private"
REV="66c55385936defd2be091b6b7609f3fc0fd1ca8e"
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
git -C "$ROOT" show "$REV:experiments/r58_quality/r60_pilot25_vllm0100_prepare.py" > "$BASE/r60_pilot25_vllm0100_prepare.py"
chmod 600 "$BASE/r60_pilot25_vllm0100_prepare.py"
python3 "$BASE/r60_pilot25_vllm0100_prepare.py" \
  --source-stage "$BASE/r60-hf-quality-first-1000" \
  --pilot-stage "$BASE/r60-hf-quality-pilot25-vllm0100"
```

如返回 `R60_PILOT25_PRIVATE_STAGED__GPU_NOT_AUTHORIZED`，再核对新 `input_A/B/runner.py --verify-only` 各为 25/25；**不得对完整 1000-stage 重做 CPU token 预检，也不得把这些技术 PASS 当作审核质量 PASS。**

---


## 2026-11-11 Pilot25 PATCH_3 HOLD 定位并修复旧代码布局假设

Owner 新诊断 `R60_PILOT25_PREPARE_HOLD`：`VLLM0100_PATCH_CONTRACT_CHANGED__ROLE_A__PATCH_3__COUNT_0__RUNNER_SHA256_d06adef6c28826d505d8dfe9e6920e840ecb18fe3d23256dd3b2d559956cd7d0`。证明旧 stage 内 A 审核器找不到期待的 **引文修复路径精确字面串**；并不说明整个引文修复功能不存在或数据库数据错误。未生成 Pilot25 staging，GPU/Job 均为 0。

**修复策略**：废除对引文修复函数完整字面布局的强制匹配，改为对旧 vLLM API 的 `StructuredOutputsParams` 类名、`structured_outputs=` 参数名进行受约束批量替换；验证唯一旧 import、至少一次 JSON sampling 参数、替换总数和无旧 API 残留，并用 `ast.parse` 做 Python 语法检查；修改对象**只限新 Pilot25 runner 副本**，原始 1000 stage 不动。加入含/不含旧引文修复分支的合成测试以及异常导入拒绝测试。参照 vLLM v0.10.0 官方 API：https://docs.vllm.ai/en/v0.10.0/features/structured_outputs.html

GitHub 当前准备器及测试修订 HEAD：`35ebb082e4ea5fcab4a6de2756494d2670d04f6e`。**CI 尚无已确认 PASS 回执；真实私有 stage 重新准备也尚未完成。**

Owner Mac 重新取指定提交并运行 create-only 纯 CPU 准备：

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
BASE="$HOME/.local/share/storyforge/r60/private"
REV="35ebb082e4ea5fcab4a6de2756494d2670d04f6e"
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
git -C "$ROOT" show "$REV:experiments/r58_quality/r60_pilot25_vllm0100_prepare.py" > "$BASE/r60_pilot25_vllm0100_prepare.py"
chmod 600 "$BASE/r60_pilot25_vllm0100_prepare.py"
python3 "$BASE/r60_pilot25_vllm0100_prepare.py" \
  --source-stage "$BASE/r60-hf-quality-first-1000" \
  --pilot-stage "$BASE/r60-hf-quality-pilot25-vllm0100"
```

成功标准 `R60_PILOT25_PRIVATE_STAGED__GPU_NOT_AUTHORIZED`，A/B 各 25 行，原始源 1000 行无变化，`hf_jobs_submitted=0`；若仍 HOLD，输出原因码即可，不读私有正文或覆盖原数据。在 GPU 花钱之前仍要对副本 `--verify-only`，使用 pinned 镜像做专门 runtime 兼容检查；不得直接进行全量 1000 审核。

---


## 2026-11-11 Pilot25 prepare HOLD：staged runner 与预期 API 源码可能不同（fail-closed）

Owner Mac 在新建 Pilot25 的 CPU-only 准备器上得到 `R60_PILOT25_PREPARE_HOLD`、`reason_code=VLLM0100_PATCH_CONTRACT_CHANGED`、`hf_jobs_submitted=0`、`gpu_started=false`。此回执没有产生任何收费任务。准备器原先要求旧 `runner.py` 的 4 处 vLLM API 精确匹配，每处恰好出现 1 次。

已核对 GitHub `r60/gold192-history-v3-adapter` 当前 `src/storyforge_gold_quality/hf_literary_review.py` 四处目标文本都恰好 1 次。因此更可能是旧 1000 staging 内打包的 runner 和 GitHub 当前源码不一致；尚不能确定具体偏差，**不得直接强制替换或跳过校验**。

已提交准备器诊断改动 `0bd8f742a8f88af5037bfe521f7713f5a998d165`：下一次失败 SAFE 的 `reason_code` 将包含 `ROLE_A/B`、`PATCH_1..4`、`COUNT_0/2..` 以及原 runner SHA256，不打印源码/故事正文。Owner 在 Mac 重新取得该提交的脚本后，再运行原 prepare 命令：

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
BASE="$HOME/.local/share/storyforge/r60/private"
REV="0bd8f742a8f88af5037bfe521f7713f5a998d165"
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
git -C "$ROOT" show "$REV:experiments/r58_quality/r60_pilot25_vllm0100_prepare.py" > "$BASE/r60_pilot25_vllm0100_prepare.py"
chmod 600 "$BASE/r60_pilot25_vllm0100_prepare.py"
python3 "$BASE/r60_pilot25_vllm0100_prepare.py" \
  --source-stage "$BASE/r60-hf-quality-first-1000" \
  --pilot-stage "$BASE/r60-hf-quality-pilot25-vllm0100"
```

这仍是 CPU-only、create-only 和 fail-closed；若旧目标目录已经存在，会报告 `DEST_ALREADY_EXISTS`，不得覆盖。根据返回的 ROLE/PATCH/COUNT 和 runner SHA，再制定只修改新副本且保存旧证据的兼容方案。**在修复及独立 CI 通过前不生成收费 HF Job。**

---


## 2026-11-10 首批 25 条私有分片：vLLM 0.10.0 API 修复与可复用代码已落库

Owner Mac 确认镜像 `docker.io/vllm/vllm-openai:v0.10.0` 的 manifest Digest 为 `sha256:05a31dc4185b042e91f4d2183689ac8a87bd845713d5c3f987563c5899878271`。这只是**镜像内容 SHA pin**，尚未证明实际 CUDA/vLLM GPU 环境能正确加载三模型，也没有支付 HF GPU。

**已核对的确定性 API 不匹配**：vLLM v0.10.0 离线 JSON schema 生成接口为 `GuidedDecodingParams` + `SamplingParams(guided_decoding=...)`；旧 R60 1000 质量审核器使用 `StructuredOutputsParams` + `structured_outputs=`（包括引文纠错分支）。不能直接用旧审核器启动该容器，否则面临导入或参数错误。官方 0.10.0 文档：https://docs.vllm.ai/en/v0.10.0/features/structured_outputs.html

新增可复用的纯 Python 标准库准备器：

- `experiments/r58_quality/r60_pilot25_vllm0100_prepare.py`：从现有完整 1000 条 A/B stage 各复制首 25 条，原序号和 blind ID 保持不变；对 **复制出来的** `runner.py` 做 4 个 exact-match API 变换，包含原始结构化输出和引文纠错路径；private 输入/代码仍 0600、新目录 0700；重复使用同一输出目录拒绝；发现原始已写 checkpoint 则拒绝；不会改旧 stage 或模型输出、不会 HF 提交。
- `tests/test_r60_pilot25_vllm0100_prepare.py`：用合成 1000 条测试 25 分片、原始文件不变、断点重复拒绝与 API 漂移 fail-closed。
- **这些属于刚提交的代码，CI PASS 与 Owner Mac 私有准备回执目前尚未获取；不能声称实际 Pilot25 包已准备好。**

Owner Mac 获取当前分支新增准备器并执行（**不下载模型，不提交 Job，不收费**）：

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
BASE="$HOME/.local/share/storyforge/r60/private"
BRANCH="r60/p4-generation-eval-framework"
STAGING="$BASE/r60-hf-quality-pilot25-vllm0100"
SCRIPT="$BASE/r60_pilot25_vllm0100_prepare.py"

git -C "$ROOT" fetch origin "$BRANCH"
git -C "$ROOT" show "origin/$BRANCH:experiments/r58_quality/r60_pilot25_vllm0100_prepare.py" > "$SCRIPT"
chmod 600 "$SCRIPT"
python3 "$SCRIPT" \
  --source-stage "$BASE/r60-hf-quality-first-1000" \
  --pilot-stage "$STAGING"
```

只有在 `R60_PILOT25_PRIVATE_STAGED__GPU_NOT_AUTHORIZED` 且 `cases_per_role=25`、原始 `1000`、输入 SHA 与 code-patch fingerprint 保持可验证后，才可以提议 **一次单角色 1-case GPU/JSON smoke**，随后首批 25 A/B；Job 仍需固定 H200/时间/预算、镜像运行时检查和 Owner 单次授权。输出必须先独立回收和 `read_checkpoint` 核验，才可安全导入原始 1000 的前 25 个序号；不把 Pilot25 staging 的 `quality_pass` 直接写成 1000 的完成计数。**严禁**直接覆盖旧 source 或 `output_A/B`。

> 注意：旧审核器即使 `--limit 25` 也完整读取其输入 JSONL，因此独立 25 行 staging 是真实避免上传全 1000 的必要步骤，不只是减少推理条数。旧双审六维 `storyforge_hf_literary_visible_history_v1` 不能替代 Rubric v2.1 的严重校准，30×3 校准仍是放大与质量准入的必要门槛。

---


## 2026-11-10 Owner Pilot25 Mac CLI / stage 检查 PASS

Owner 已在 Mac 验证已有 A/B stage 文件、非链接输入、输出目录存在，并成功读取 `hf jobs run --help`；`status=R60_1000_PILOT25_LOCAL_INTERFACE_CHECK_PASS`。CLI 确认原生支持 `--dry-run`、`--flavor h200`、`--timeout`、`--attempts 1`、本地私有目录 `-v LOCAL_DIR:/MOUNT_PATH[:ro|:rw]`。**此项仅为静态接口与目录核验，不代表已上传、启动或执行审核。**

下一个 blocker 是 **明确固定旧 vLLM 运行时的具体 image SHA256**，并验证 vLLM 与 `vllm.SamplingParams(structured_outputs=StructuredOutputsParams(...))` 以及 Qwen3/GLM-4-0414 的兼容性；原 H200 32K synthetic 采用 transformers，不能直接重复使用它的镜像来声称 vLLM 完整可执行。vLLM 官方支持 `Glm4ForCausalLM`，但不代表任意旧镜像和依赖版本经过实际运行验收。正式 25 条 pilot 的镜像仍 `UNPINNED`，故目前 `GPU_JOB_NOT_SUBMITTED`。尤其注意：旧 runner 的 `read_input()` 每次会读取完整 1000 条；即使 `--limit 25`，HF 输入仍包含 1000 条，需要 Owner 明确确认范围或创建经过审计、独立哈希的 25-case staging，**禁止**假称只向 HF 提交 25 条。

优先走 **单模型 1-case 运行环境/格式最小探测 → 各模型 25 条 pilot → 30 条 v2.1 校准 → 扩大 1000 审核**，且不把前两批的旧 policy 六维输出当作校准结论。若模型 1-case 探测不能在明确的资源预算内完成则 HOLD，不自动重试。复用现有 `runner.py` / `checkpoint`，不再重复 source audit / verify-only / 1000-token CPU 预检。

---


## 2026-11-10 Owner 1000×2 tokenizer CPU 预检：A/B 均 PASS；进入首批 25 GPU 审核执行准备

Owner Mac 使用现有 `runner.py --token-preflight-only` 对冻结的 A 和 B 两侧各 1000 条完整审核输入执行真实 tokenizer 预检，原始 SAFE 关键数据：

| 参数 | A Qwen3-32B | B GLM-4-32B |
| --- | ---: | ---: |
| `cases_checked` | 1000 | 1000 |
| `prompt_tokens_min` | 712 | 673 |
| `prompt_tokens_median` | 1148 | 1099 |
| `prompt_tokens_p95` | 2284 | 2306 |
| `prompt_tokens_max` | 3124 | 3550 |
| `reserved_output_tokens` | 2400 | 2400 |
| `max_total_tokens` | 5524 | 5950 |
| `max_model_len` | 32768 | 32768 |
| `over_budget_count` | 0 | 0 |

两者 `status=HF_REVIEW_CPU_TOKEN_PREFLIGHT_PASS__NO_GPU`、`gpu_started=false`、`training_authorized=false`、`private_values_emitted=false`。

**裁决：`R60_FROZEN_1000_A_B_INPUT_AND_TOKEN_PREFLIGHT_PASS__REVIEW_NOT_STARTED`。** 输入结构和 token 预算已齐，不再重复；模型审核仍 0/1000，1000 HOLD 均为未审核。

### 现在真正的阻塞项（工程）

已核对旧审核器 `src/storyforge_gold_quality/hf_literary_review.py`：

- `--start 1 --limit 25` 能只为前 25 个序号产生审核；`read_input()` 仍校验完整 1000 条、不会将全 1000 条自动提交到模型推理；
- `inference()` 对每条使用固定 pinned model revision + `vllm.LLM` / `SamplingParams(temperature=0,max_tokens=2400,structured_outputs=JSON schema)`，单条 checkpoint 为 create-only，重跑前先复核已完成 checkpoint；
- 必须传 `--confirm-paid-gpu` 才进入 GPU 代码路径。这个参数**不是** Owner 对任意 GPU 批次的预算批准，本阶段还需独立固定 Job 输入、输出位置、镜像 digest、依赖、时长、预算、回执与不重复运行控制；
- 已完成的 PyTorch/transformers H200 32K synthetic smoke **不能证明 vLLM 和 `StructuredOutputsParams` 在该镜像中可用**；先检查旧运行时与依赖，不以 synthetic PASS 直接提交 25 条付费任务；
- 旧审核 policy 为 `storyforge_hf_literary_visible_history_v1`，正式 30-case `r60_severity_rubric_v2_1` 仍须独立校准误判/漏判。旧六维质量审核只是可训练候选判断的一个关卡，不等于训练准入；
- 加速顺序：固定 25-case A/B pilot 单次 Job 计划 → Owner Mac 手动提交 → checkpoint/结构化 JSON/异常 EOS 统计 → 通过后批次 100/500/1000；未拿到校准结果，不扩大或直接训练。Challenger 优先复核分歧，而非直接给 1000 条全量三审。

### Owner Mac 下一次无成本运行时核查

```bash
set -euo pipefail
STAGE="$HOME/.local/share/storyforge/r60/private/r60-hf-quality-first-1000"

# 只读核验旧 stage 的 runner / token source 和输出目录。
for ROLE in A B; do
  test -s "$STAGE/input_$ROLE/runner.py"
  test -s "$STAGE/input_$ROLE/token_core.py"
  test -s "$STAGE/input_$ROLE/source.private.jsonl"
  test -d "$STAGE/output_$ROLE"
  test ! -L "$STAGE/input_$ROLE/source.private.jsonl"
done
# 显示本地 HF CLI 及运行参数接口；不创建 Job。
hf jobs run --help | head -80
echo "R60_1000_PILOT25_LOCAL_INTERFACE_CHECK_PASS"
```

只读输入核验成功并不代表 vLLM 环境已可执行：必须在独立 Job 计划中 pin vLLM 兼容镜像/依赖、回收路径与费用后再正式付费。

---


## 2026-11-10 Owner 已确认 A/B 1000 条审核输入：两侧 verify-only PASS

Owner Mac 已执行现有私有 stage 的 `runner.py --verify-only`：

```json
{"cases_completed":0,"cases_total":1000,"private_values_emitted":false,"schema":"storyforge_hf_literary_safe_v1","status":"HF_REVIEW_INPUT_VERIFIED__NO_INFERENCE","training_authorized":false}
```

A/B **各自返回完全相同 SAFE**。**当前裁决 `R60_1000_A_B_REVIEW_INPUT_STRUCTURE_PASS__TOKEN_PREFLIGHT_PENDING`**，尚未调用模型、未审核任何一条。无须再做一次 `--verify-only`。

### 下一步：一次性对全部 1000 条执行各模型真实 tokenizer CPU-only 长度核验

旧审核 runner 有现成的 `--token-preflight-only`，在 Mac 本地读取已冻结的 1000-case 私有输入，只下载/载入固定 revision 的 tokenizer，不加载模型权重、不推理。由于旧 runner 的 `read_input` 始终读取全源，此命令**核验全部 1000 条而不是 25 条**，便于一次性找出超出 32K 预算的比例，不按未经确认的 token 尺寸提交 GPU。该操作可能花费较长 CPU 时间，但不购买 HF 资源。

```bash
set -euo pipefail
export CUDA_VISIBLE_DEVICES=""
export NVIDIA_VISIBLE_DEVICES="none"
STAGE="$HOME/.local/share/storyforge/r60/private/r60-hf-quality-first-1000"

python "$STAGE/input_A/runner.py" \
  --input "$STAGE/input_A/source.private.jsonl" \
  --output-dir "$STAGE/output_A" \
  --model "Qwen/Qwen3-32B" \
  --revision "9216db5781bf21249d130ec9da846c4624c16137" \
  --max-model-len 32768 --max-output-tokens 2400 \
  --token-preflight-only

python "$STAGE/input_B/runner.py" \
  --input "$STAGE/input_B/source.private.jsonl" \
  --output-dir "$STAGE/output_B" \
  --model "zai-org/GLM-4-32B-0414" \
  --revision "8dea913c41b543527c2860fb6f3c15c202f24aeb" \
  --max-model-len 32768 --max-output-tokens 2400 \
  --token-preflight-only
```

如出现 `HF_REVIEW_CPU_TOKEN_BUDGET_HOLD__NO_GPU`，必须统计超预算数，不静默截断；如出现 `HF_CPU_TOKENIZER_IMPORT_HOLD` 等依赖错误则 HOLD 并修复本地 Python 环境，而不是改冻结审核输入。只有预检合格后才准备 **25 条 pilot、每角色单模型独立 Job 的成本/时长/Checkpoint/Schema**；旧 vLLM runner 的 GPU 运行环境与已跑通的 PyTorch transformers H200 smoke 不同，需要单独核验镜像/依赖/显存再由 Owner Mac CLI 手动提交。

**重要**：现有旧 A/B 六维审查可复用，但不能以旧审查的结果冒充 Rubric v2.1 的校准分数；新版 30 条三模型严重问题判定仍为正式放大批次的前置 gate。1000 条完成审核之后仍需 Quality-v1 最终准入，不自动训练。

---


## 2026-11-10 Owner 最新只读 audit：1000 冻结源完整，审核 0/1000

Owner Mac 已实际执行旧双审 adapter 的 `audit`，收到 SAFE：

```json
{"cases_total":1000,"complete_pairs":0,"model_a_reviewed":0,"model_b_reviewed":0,"paid_gpu_submitted":false,"private_values_emitted":false,"quality_decisions":{"HOLD":1000,"PASS":0,"REJECT":0},"quality_pass":0,"quality_v1_admitted":0,"r50_body_accessed":false,"r50_complete_exclusion_verified":false,"reviewer_independence_cryptographically_proven":false,"schema":"storyforge_r60_hf_quality_adapter_safe_v1","status":"HF_QUALITY_DUAL_PARTIAL__NO_ADMISSION","training_authorized":false,"world_isolation_verified":false}
```

**解释：0 完成，1000 HOLD 是未审核状态，不是 1000 条质量不达标。** Frozen 1000 源与旧 stage 的相互验收已通过；当前目标应直接从它们出发，不重新做 Supabase 抽取、不要再次 `prepare`。

### 下一步 Owner Mac：双模型旧审核包纯 CPU 结构预检（不调用模型、不用 GPU）

该命令使用旧 stage 内自带的 `runner.py`，对两个完整 1000-case 输入文件分别执行 `--verify-only`；只读、零收费。**这不能代替 Rubric v2.1 的 30 条准确率校准，也不能授予任何批量 GPU。**

```bash
set -euo pipefail
STAGE="$HOME/.local/share/storyforge/r60/private/r60-hf-quality-first-1000"

for ROLE in A B; do
  case "$ROLE" in
    A) MODEL="Qwen/Qwen3-32B"; REV="9216db5781bf21249d130ec9da846c4624c16137" ;;
    B) MODEL="zai-org/GLM-4-32B-0414"; REV="8dea913c41b543527c2860fb6f3c15c202f24aeb" ;;
  esac
  python "$STAGE/input_$ROLE/runner.py" \
    --input "$STAGE/input_$ROLE/source.private.jsonl" \
    --output-dir "$STAGE/output_$ROLE" \
    --model "$MODEL" --revision "$REV" --verify-only
done
```

预期每侧 `HF_REVIEW_INPUT_VERIFIED__NO_INFERENCE` 且 `cases_total=1000`、`cases_completed=0`。任何 HOLD 保留原始 stage、禁止覆盖。**注意 reviewer v1 基于完整 1000 源的 4 消息结构、可见历史和目标回复，与 R60 30-case v2.1 严重裁决的输出 schema 并不等价。**

### 下一步的正式推理准备

审核端应先把 `S`（Rubric v2.1 严重判定校准）30×3 的模型输入、输出 JSON schema、人工标签隔离和统计门槛验证通过，再启动 A/B 审核者的旧六维质量分批推理。第三模型优先做争议例复核，**不用先运行 1000×3**。旧 `hf_literary_review.py` 虽支持 `--start` / `--limit` 和 1000 条 staged 输入的 checkpoint 断点，但其 GPU 运行函数基于 vLLM，**不能直接将 H200 PyTorch 32K synthetic 的环境和费用视为该 runner 的已验收运行环境**，需另做 vLLM / 资源/预算 CPU-only 静态检查后才会提出单次收费 Job。

---


## 0. 唯一业务目标与当前事实

**目标**：尽快将 Supabase 已粗筛并冻结的约 1000 条真实互动故事历史候选转为经过质量审查、可以用于 StoryForge SFT 的高质量数据；不要扩展为故事生成模型选秀。

已核对同仓库既有工程分支 `r60/gold192-history-v3-adapter`：
- 数据验证入口 `experiments/r58_quality/r60_real_quality_batch.py:frozen_pool`，严格要求 1000 条、扩展页与原始 seed 的 SHA/结构一致；
- 已有审查层 `experiments/r58_quality/r60_hf_quality_adapter.py` 支持 `prepare/audit/export` 三个动作；
- 核心 `src/storyforge_gold_quality/hf_blind_stage.py` 绑定 A/B 各 1000 的独立盲 ID、双模型输出目录和 Owner 本地映射；`audit` **不调用模型**；
- 审核器 `src/storyforge_gold_quality/hf_literary_review.py` 六维：中文文笔、人物一致性、NPC 主动性、玩家自主权、规则遵守、叙事连贯；严重标记：`serious_player_agency`、`hard_fact_or_ban`、`safety_exclusion`；现有质量阈值分别为 4/4/3/4/4/4；
- 既有 staging 根据 Owner 旧回执，位于 `~/.local/share/storyforge/r60/private/r60-hf-quality-first-1000`，冻结 source 扩展目录为同一 private 根下的 `r60-expand-first-600`（以此目录自身配置和文件哈希核验结果为准）；
- 2026-11-08 的已知结果：1000 staged，`model_a_reviewed=0`、`model_b_reviewed=0`、`complete_pairs=0`、`HOLD=1000`、`quality_v1_admitted=0`、`training_authorized=false`。**上述是历史回执，不代表 11 月 10 日实时情况**。
- 当前三模型 32K synthetic GPU 3/3 PASS，不等于审核准确率达标。尤其 B 7 tokens 是被要求输出一句话的 smoke，不应视为审核短输出故障。

### 关键区别

现有 1000 条 pipeline 用 **双模型 A/B 的六维训练质量审核**；R60 **新冻结 Rubric v2.1 + Gold/Owner 30 案例** 用于对三模型严重维度（Hard Rule、Player Agency、Safety）准确率校准。可复用双审工程和 1000 条固定数据，**不可直接声称六维旧 policy 与 v2.1 等价**。第三模型 challenger 优先用于 30 案例校准与冲突复审，不强制让全部 1000 条变成三模型三次全量推理。

## 1. 立即执行的 Owner Mac 本地只读诊断（不收费、无模型调用）

先在 Mac 上使用原 worktree（不要触碰已消费的 H200 三次任务、不要重新 prepare 或覆盖任何 staging）。运行：

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge-r60-ledger-diagnostics"
BASE="$HOME/.local/share/storyforge/r60/private"
STAGE="$BASE/r60-hf-quality-first-1000"
EXPAND="$BASE/r60-expand-first-600"
cd "$ROOT"
test -f experiments/r58_quality/r60_hf_quality_adapter.py
test -d "$STAGE" && test -d "$EXPAND"
PYTHONPATH="$ROOT/src" python experiments/r58_quality/r60_hf_quality_adapter.py audit \
  --expand-dir "$EXPAND" \
  --stage-dir "$STAGE"
```

仅粘贴 stdout 的 SAFE JSON，不分享 `owner_crosswalk.private.json`、blind IDs、全文或密钥。如 worktree 不在上述路径，用已有包含 `r60_hf_quality_adapter.py` 的工作区，不改变冻结 staging；若文件不存在则上报 HOLD，不以原始数据库重建 1000 条。

### 预期能确认

- 当前 `cases_total`、`complete_pairs`、A/B reviewed、PASS/HOLD/REJECT、`quality_v1_admitted`；
- 现有 candidate pool 与 stage manifest 有无 SHA 变化；
- 现有 runner 与 Source、model pins 是否仍一致；
- 如果 `complete_pairs>0`，复用既有结果，不重复付费审核。

**注意**：上面当前状态未知，任何结果在返回 SAFE 前只可标记 `CURRENT_1000_AUDIT_PENDING`。

## 2. 30 条 calibration 不得阻塞 1000 条静态检查，但必须阻止“未经校准直接准入”

并行核对 P2-B Locked20 + Severe10 的 30 个已裁决案例，以及 Rubric v2.1 的 Prompt/Schema SHA。三模型严格同案分别审核并冻结预测，再与 Owner 30/90 的明确标签对齐、报告每维误判/漏判/弃判；`INSUFFICIENT_CONTEXT` 只计 HOLD，不能伪造明确标签。**如无结构化三维输出，既有 `generation_eval.worker_cli` 的自由文本输出不得直接当成审核预测**。

30 条校准不要求把历史 1000 条 source 重新获取，亦不要求重新跑三模型 32K synthetic smoke。

## 3. 最快进入 1000 精筛的分批策略

- **第 0 批（CPU-only）**：只读 audit 冻结数据，计算当前真实待审数量、审核器是否已经具备双模型 A/B 分槽 JSON Schema/引用证据校验。复用旧证据，避免重算。
- **校准批**：原样 30 条严格三模型盲审；先 3–5 个 development 结构检查（不能拿 locked labels 做 prompt 调参），再完整 30；结构化结果与新版 Rubric v2.1 对齐。需要收费 Job 时，Owner Mac CLI 提交，固定预算/单次尝试/不自动重试。
- **1000 批处理**：固定 A/B 主审：100 条一组，先 25 条技术 pilot，通过格式、停止、证据引用与成本核验后再扩至 100/500/1000，已完成数不重复计算。严重证据确凿者 REJECT，证据不足或两模型分歧者 HOLD，双 PASS 且六维达标者只进 **可准入候选队列**，需执行 Quality-v1 最终准入 verifier 才能写 `admitted`。Challenger 只审分歧/HOLD（先以 30 条校准证明有价值），避免 1000×3 全量花费。
- **结果导出**：已有适配器只有 `complete_pairs == 1000` 才允许执行 `export`，因此不提前运行；仍由 Owner 控制独立导入 Gold Quality ledger，不改 Frozen 原文或历史标签。

任何用于生产训练的 case 必须满足四消息上下文技术条件、目标回复真实完成、无严重规则/玩家自主权/安全问题及质量阈值；未检验来源时不能自称已审。这份执行书仅调整筛选进度优先级，不改变旧 frozen 样本、旧模型输出或官方 Owner 裁决。

## 4. 明确授权边界

用户 2026-11-10 说「按建议推进，尽快进行 1,000 条候选的精筛」：**现授权推进 1000 条精筛项目的准备与后续实施目标**；不等于批准任何不设上限的收费 GPU Job、自动重试、实际 SFT 训练、修改生产数据库或自动将 HOLD 标记为可训练。

执行类里程碑：
- `1000_FROZEN_AUDIT`：WAIT_OWNER_SAFE。
- `P4_30_THREE_MODEL_CALIBRATION`：准备中，正式模型输出尚无。
- `P6_1000_FINE_SCREEN`：目标获用户明确确认，但本轮实际审核数据 **尚未开始/未得到当前 SAFE 证明**。
- `QUALITY_V1_ADMISSION`：HOLD，不能从双 PASS 自动提升。
- `TRAINING`：未授权。

## 5. 已发现的技术缺口

现存 `hf_literary_review.py` policy 是 `storyforge_hf_literary_visible_history_v1`，不是新冻结的 `r60_severity_rubric_v2_1`。历史 `r60_hf_quality_adapter.py` 仅支持 A/B 两个独立 slot，且 checkpoint/export 依赖旧 runner。下一步只在新 revision 增加 **v2.1 严重问题审核薄适配层**，不要覆盖已准备的 1000 输入或修改旧 checkpoint 语义；新评审只对还没有被审过的批次运行。
