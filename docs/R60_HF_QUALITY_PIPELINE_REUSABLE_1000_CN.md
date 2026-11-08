# R60 真实 1000 候选 × Hugging Face × Gold Quality Pipeline（2026-11-08）

> **2026-11-08 Owner Mac 实测阶段更新（最新）**：`prepare` 已返回 `HF_QUALITY_BLIND_STAGE_READY__NOT_SUBMITTED`、`cases_staged=1000`；`audit` 已返回 `HF_QUALITY_DUAL_PARTIAL__NO_ADMISSION`、A=0、B=0、complete_pairs=0、HOLD=1000、PASS=0、REJECT=0。Owner crosswalk 没有上传到 HF，也没有实际模型推理。
> 已固定 A=`Qwen/Qwen3-32B@9216db5781bf21249d130ec9da846c4624c16137`、B=`zai-org/GLM-4-32B-0414@077b5c2f5c43bd3239fd605a0600229e8facbd4a`。
> **本文件第 2 节的 `prepare` 旧命令不需重跑**（重复运行会被拒绝）；第 3 节的直接 `hf jobs run -v 本地目录` 示例**不再使用**，因为 HF CLI 会隐式把私人小说内容上传到 `jobs-artifacts` Bucket，这不符合本仓库明确的组织项目 Bucket/Guard 约束。下一步请以 [已实测 Stage 后的 HF CPU Guard 执行书](R60_HF_QUALITY_CPU_PREFLIGHT_AFTER_STAGE_20261108_CN.md) 为唯一指引，先在 Owner 本地 `audit` 再只同步 `input_A`/`input_B` 至 `adradar/storyforge-training` 的新私有前缀，使用 `scripts/hf_job_guard.py` 做 dry-run/CPU-only 提交。不得上传 `owner/`，GPU 仍需单独授权。


状态：**公共 HF 审核工具与 R60 适配器已编写；尚未在 Owner Mac 真实 1000 条数据或付费 HF 上运行。** 当前真实冻结候选池 1000/1000，Quality=0、训练准入=0。

## 1. 复用设计

仓库已有 `r58_hf_gpu_literary_reviewer.py`、`r58_hf_gpu_review_stage.py`、`r58_gold195_pilot13_dual_review_validate.py`。它们具有 vLLM 模型加载、六维审核、原文引用验真、A/B 隔离和检查点的先例，但冻结于 Gold195 的 13 案与世界卡必需字段。R60 无可信历史卡，**不能伪造卡片已认证**以通过旧 Reviewer。

因此把可复用的新审核入口收敛到原 `storyforge_gold_quality` 包，R60 只保留业务输入适配：

| 文件 | 责任 |
|---|---|
| `src/storyforge_gold_quality/hf_literary_review.py` | 单模型 HF vLLM Worker：通用六维 JSON、严重 flags、连续原文引用检查、模型 40 位 SHA、无覆盖 checkpoint、CPU-only token 预检 |
| `src/storyforge_gold_quality/hf_blind_stage.py` | A/B 随机盲审输入及分离目录、Owner-only crosswalk、双方 checkpoint 验真、SAFE 双审汇总、输出原 Quality Pipeline 可导入的 A/B 文件 |
| `experiments/r58_quality/r60_hf_quality_adapter.py` | R60 唯一薄适配：复用 `r60_real_quality_batch.frozen_pool()` 对原 6 + 994、20 页和扩容回执验真，然后 `prepare/audit/export` |
| `storyforge-gold-quality hf-review-inspect` | 现有 Quality Pipeline 新增只读 HF 单模型验收入口；继续复用原有 `append-review` 和私有 Manifest |

早先的 `r60_real_ai_dual_review.py` / `r60_real_quality_batch.py` 保留历史本地审查兼容，不再作为 HF 主线推理实现。旧 R58 13 案冻结脚本仍不修改。新的公共合同采用既有六维最低分：中文表达4、人物一致4、NPC主动3、玩家自主4、规则忠实4、叙事连贯4；严重标志有一项 true 必须 REJECT，PASS 需要历史与目标的可验证连续子串。不能从三消息可见历史推断完整世界卡或者历史实际 System。

**唯一 Tokenizer Core**：`src/storyforge_dataset/token_preflight.py`，HF Worker 调用已有 `encode_chat` / `describe_token_lengths`，Owner stage 将其精确字节复制为 `token_core.py` 并绑定 SHA；同时从 `src/storyforge_dataset/hf_runtime/` 以原字节复制 `inputs.py` 和 `resources.py` 到双 Slot，Reviewer 只调用已有 `InputManager` 与 `ResourceGuard`，不重复实现读取/CPU 安全算法。Mac 本地不运行 Tokenizer。HF 工程与操作规范见 `docs/standards/HF_JOBS_ENGINEERING.md`、`skills/storyforge-hf-jobs/SKILL.md`、`docs/HF_JOBS.md`。

## 2. Owner Mac：先在本地准备，**不上传、不启动 HF Job**

在 StoryForge 仓库根目录：

~~~bash
set -euo pipefail
set +x
umask 077
git fetch origin r60/gold192-history-v3-adapter
git switch r60/gold192-history-v3-adapter
git pull --ff-only origin r60/gold192-history-v3-adapter

BASE="$HOME/.local/share/storyforge/r60/private"
EXPAND="$BASE/r60-expand-first-600"
STAGE="$BASE/r60-hf-quality-first-1000"
python3 experiments/r58_quality/r60_real_expand_private.py inspect --output-dir "$EXPAND"
test ! -e "$STAGE"
~~~

须先检查 1000 候选 SAFE `EXPANSION_TARGET_REACHED__NOT_ADMITTED`，然后固定两种不同模型的**完整不可变 40 位 Revision**。R58 历史 Qwen pin 为 `9216db5781bf21249d130ec9da846c4624c16137`；GLM Revision 必须现场查询，不能猜测。只查询 Hub 元数据，不在 Mac 运行任何模型：

~~~bash
MODEL_A="Qwen/Qwen3-32B"
REV_A="9216db5781bf21249d130ec9da846c4624c16137"
MODEL_B="zai-org/GLM-4-32B-0414"
REV_B="$(python3 -c 'from huggingface_hub import HfApi; print(HfApi().model_info("zai-org/GLM-4-32B-0414").sha)')"
[[ "$REV_A" =~ ^[a-f0-9]{40}$ ]]
[[ "$REV_B" =~ ^[a-f0-9]{40}$ ]]

python3 experiments/r58_quality/r60_hf_quality_adapter.py prepare \
  --expand-dir "$EXPAND" --stage-dir "$STAGE" \
  --model-a "$MODEL_A" --revision-a "$REV_A" \
  --model-b "$MODEL_B" --revision-b "$REV_B"

python3 experiments/r58_quality/r60_hf_quality_adapter.py audit \
  --expand-dir "$EXPAND" --stage-dir "$STAGE"
~~~

`prepare` 应返回 `HF_QUALITY_BLIND_STAGE_READY__NOT_SUBMITTED`、`cases_staged=1000`。初始 `audit` 为 `HF_QUALITY_DUAL_PARTIAL__NO_ADMISSION`，0 个完成 A/B，1000 个 HOLD。

Owner 私有结构：

~~~text
r60-hf-quality-first-1000/        0700
  owner/                         仅 Owner，本目录绝不挂载到 HF
    owner_crosswalk.private.json   0600，真实 case_key 对映
    stage_manifest.private.json    0600，冻结来源/代码/模型/Tokenizer SHA
  input_A/                      独立盲审 A，HF :ro
    source.private.jsonl
    runner.py
    token_core.py
    runtime_inputs.py               # HF Runtime InputManager 原件
    runtime_resources.py            # HF Runtime ResourceGuard 原件
  output_A/                     HF 独立 :rw
  input_B/                      独立盲审 B，HF :ro
    source.private.jsonl
    runner.py
    token_core.py
    runtime_inputs.py
    runtime_resources.py
  output_B/                     HF 独立 :rw
~~~

随机盲 ID 仅消除直接 source ID，不会匿名化小说正文。原文件、世界/用户 ID、Owner crosswalk 不得上传至 public GitHub、Job log 或聊天。`prepare` 本身不提交 Job、不修改数据库、不产生 GPU 费用。

## 3. HF CPU Tokenizer 实测（实际需要时）

先按既有规范核对 `hf auth whoami`、组织 `adradar`、RO Volume、镜像和依赖。模型特定 Chat Template/Token 预检**只在 HF CPU**运行，审阅实际 1000 行，**不启动 GPU**。

例如在 Mac 以组织身份提交 A 的 CPU 预检（运行前核对当前 HF CLI 参数与依赖；B 使用 `input_B` 和 GLM pin）：

~~~bash
hf jobs run --namespace adradar --flavor cpu-basic --timeout 30m \
  -v "$STAGE/input_A:/input:ro" \
  python:3.11 /bin/sh -lc \
  "pip install --quiet 'transformers==4.57.1' 'huggingface_hub>=0.35' && \
   python3 /input/runner.py --input /input/source.private.jsonl \
   --output-dir /input --model '$MODEL_A' --revision '$REV_A' \
   --token-preflight-only --max-model-len 32768 --max-output-tokens 2400"
~~~

期望 `HF_REVIEW_CPU_TOKEN_PREFLIGHT_PASS__NO_GPU`，`cases_checked=1000`、`over_budget_count=0`、`gpu_started=false`。SAFE 汇总可打印日志，无须 RW 输出。任何超预算、模型加载或模板异常均 HOLD；不得本地绕过 CPU 门禁。此处仅是执行说明，本轮尚未实际提交。

## 4. HF GPU Pilot：**必须单独批准成本后才能启动**

沿用 R58 已设计的两个独立 H200 Job；A 与 B 各自只读自己的 input，私有 output 单独回收。`vllm/vllm-openai:v0.11.0` 只是既有测试目标镜像，真实运行前必须核对版本/digest 与 Qwen、GLM 相容性，并给出超时/最大 GPU 花费。

只有在收到明确 GPU 推理授权后才考虑执行以下**示意命令**（5 条 A Pilot；B 模型、输入输出完全分离）：

~~~bash
hf jobs run --namespace adradar --flavor h200 --timeout 45m \
  -v "$STAGE/input_A:/input:ro" \
  -v "$STAGE/output_A:/output:rw" \
  vllm/vllm-openai:v0.11.0 python3 /input/runner.py \
  --input /input/source.private.jsonl --output-dir /output \
  --model "$MODEL_A" --revision "$REV_A" \
  --start 1 --limit 5 --max-model-len 32768 \
  --max-output-tokens 2400 --max-wall-seconds 1200 \
  --confirm-paid-gpu
~~~

Job 成功不代表回执已经回到 Owner Mac。按 CLI 给出的**实际 HF 私有 Bucket sync 命令**回收 `review_0001.private.json` 等文件；核对模型 SHA、文件字节与逐案引用。后续每批靠 `--start`/`--limit` 和不可覆盖 checkpoint 续跑，失败不静默重试/补分。GPU Job 不执行 SFT。

## 5. 回收后接入原 Gold Quality Pipeline

Owner Mac 可以只读检查单个 Reviewer：

~~~bash
storyforge-gold-quality hf-review-inspect \
  --input "$STAGE/input_A/source.private.jsonl" \
  --output-dir "$STAGE/output_A" \
  --model "$MODEL_A" --revision "$REV_A"

python3 experiments/r58_quality/r60_hf_quality_adapter.py audit \
  --expand-dir "$EXPAND" --stage-dir "$STAGE"
~~~

`audit` 对 1000 条冻结来源、Owner crosswalk、独立 A/B 文件、代码 SHA、模型 revision、原文引用、六维和严重 flags 全量验真，输出只有 SAFE PASS/HOLD/REJECT 汇总，`quality_v1_admitted=0`。

只有 A 与 B **均完成 1000 条**后，才能调用：

~~~bash
python3 experiments/r58_quality/r60_hf_quality_adapter.py export \
  --expand-dir "$EXPAND" --stage-dir "$STAGE"
~~~

导出仅在 `owner/` 内创建 `reviewer_A_pipeline.private.jsonl` 与 `reviewer_B_pipeline.private.jsonl`，状态 `HF_QUALITY_PIPELINE_PRIVATE_IMPORT_READY__NOT_IMPORTED`；不自动修改 Manifest。

Owner 核对输出并选择**原有唯一、私有 0700 目录中的正式 Gold Quality Manifest**（不要另建竞争副本），然后各导入一次：

~~~bash
storyforge-gold-quality append-review --batch r60-real \
  --event-type BLIND_REVIEW \
  --input "$STAGE/owner/reviewer_A_pipeline.private.jsonl" \
  --manifest "$MANIFEST" --repo-root "$PWD"

storyforge-gold-quality append-review --batch r60-real \
  --event-type BLIND_REVIEW \
  --input "$STAGE/owner/reviewer_B_pipeline.private.jsonl" \
  --manifest "$MANIFEST" --repo-root "$PWD"

storyforge-gold-quality validate --manifest "$MANIFEST"
storyforge-gold-quality report-safe --manifest "$MANIFEST"
~~~

保留两个 Reviewer 的**独立事件**，不把双审数据覆盖成一个结论。不审 R50 正文，不假设不同模型代表独立训练来源。质量 PASS 只作为后续候选池；世界组件/R50 完整元数据排除、实际 System/上下文、CPU Tokenizer/Collator、Owner 准入与 GPU 训练授权全都单独验收。

## 6. 完成边界

本轮仅完成公共工具、R60 适配与合成测试；**没有**接触 Owner 1000 条私人正文、没有提交 HF CPU/GPU、没有产出任何真实 Review PASS。原 Gold、R50、RolePlay、数据库和训练都未修改。