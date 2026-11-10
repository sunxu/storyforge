# R60：已有 1000 条训练候选精筛加速执行书（2026-11-10）

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
