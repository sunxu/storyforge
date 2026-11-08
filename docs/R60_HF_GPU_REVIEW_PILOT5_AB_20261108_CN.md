# R60 真正文学盲审 A/B 各前五条：最小 GPU Pilot 执行基线（2026-11-08）

## 2026-11-08：A v2 H200 真正五条 Pilot 终态 COMPLETED；质量判定须校准（最新权威状态）

实际 HF [Job `6af056bb0e0338d1bb84ac8a`](https://huggingface.co/jobs/adradar/6af056bb0e0338d1bb84ac8a)（`r60-quality-gpu-pilot5-A-v2-01`，H200、固定 vLLM digest、`Qwen/Qwen3-32B@9216db5781bf21249d130ec9da846c4624c16137`），创建 `2026-11-08T11:02:19.731Z`，完成 `11:07:22.223Z`，最终 **COMPLETED**。真实模型权重 `17/17` shard 全部加载，GPU 推理及私有 Checkpoint 持久化完成。`/gpu-review-output-A-pilot5-v2-01` 新独立目录实际生成 `review_0001.private.json` 至 `review_0005.private.json` 五个 Checkpoint，全部为 v2 契约。

Job 最终 SAFE 是 `HF_REVIEW_PARTIAL__NO_ADMISSION`、`cases_total=1000`、`cases_completed=5`、`quality_decisions={PASS:0,HOLD:0,REJECT:5}`、`quality_v1_admitted=0`、`training_authorized=false`。这里的 `PARTIAL` **仅代表按计划审核前 5/1000，不代表运行失败**。独立只读查阅 5 个 checkpoint 的结构化字段，并对照冻结 A 输入前 5 条逐条比较 `blind_id` 及所有 `specific_source_quotes` / `specific_target_quotes`，身份及来源/目标严格连续子串检查 **5/5 通过**；未输出任何私有正文/引用/案例 ID。Checkpoint 包含 receipt/input SHA256 字段，但**尚未独立复算这两个 hash**，不可谎称已完成完整字节身份校验。

**质量校准重要异常：** A 模型 5/5 `REJECT`，所有 5 个 `serious_player_agency=true`；`hard_fact_or_ban=true` 为 2/5，`safety_exclusion=true` 为 2/5，六维评分完整。虽有严格真实引用，这仍只证明文本引用真实，不保证引用语义确实能够支持“严重侵犯玩家自主权”等判断。在没有独立 Reviewer B 结果与语义冲突仲裁之前，**绝对不能将这 5 个结果升级成已证实的真实训练数据 REJECT**；Quality-v1 准入仍 0。不能因为模型全判 REJECT 就放宽严重标记校验，也不能把原作者回复直接视为不合格。

**下一步主线优先级：** 使用同一个已上传公开 v2 Runner，先对原冻结 `input_B` 在固定目标 vLLM GPU 镜像执行一次严格 CPU-only B v2 Prompt Tokenizer 预检（独立输出、不覆盖历史 B CPU1 / GPU A）；成功后，再按 A 同样固定条件运行 Reviewer B 的前 5 条（H200 费用独立控制，禁止自动启动），保留 B 原始盲审独立性。只有拿到两侧结果才进行 Owner 私有 crosswalk 配对、模型间歧义 HOLD/校准、必要的审阅者进一步判定；正式 SFT 训练未授权。详见本次 [SAFE 汇总](evidence/R60_GPU_A_V2_PILOT5_COMPLETED_SAFE_20261108.json)。**不再重跑 A 这五条。**

---

## 2026-11-08：A Reviewer v2 固定 GPU 镜像 CPU 预检真实 PASS（最新阶段）

HF [Job `6af055ace6320c66fad7456d`](https://huggingface.co/jobs/adradar/6af055ace6320c66fad7456d)，`name=r60-gpuimage-cpu-token-A-reviewer-v2-01`，`adradar/cpu-basic`，创建 `10:57:48.396Z`、完成 `10:58:06.841Z`，实际状态 **COMPLETED**。与未来 H200 使用同一固定 vLLM image digest。先对 CPU ResourceGuard 原始环境检测，只有 `nvidia_visibility=FAIL`，`accelerator_profile/cuda_visibility/nvidia_device_nodes/runtime_no_cuda_import` 均 PASS；随后在无实际 GPU 设备的 CPU 容器中设 `NVIDIA_VISIBLE_DEVICES=void`，原样 ResourceGuard 所有检查 PASS，日志 `HF_CPU_RESOURCE_GUARD_PASS`。新版 Runner `reviewer-runner-v2/runner.py` 通过 `HF_REVIEWER_V2_CONTRACT_PASS`（包含 Checkpoint v2、`MODEL_SEVERE_EVIDENCE_HOLD` 和 `MODEL_NOTES_TOO_SHORT_HOLD`），冻结输入结构 `HF_REVIEW_INPUT_VERIFIED__NO_INFERENCE`。

实际 Prompt `Qwen/Qwen3-32B@9216db5781bf21249d130ec9da846c4624c16137` 的 1000/1000 CPU Tokenizer `HF_REVIEW_CPU_TOKEN_PREFLIGHT_PASS__NO_GPU`，`over_budget_count=0`、`max_model_len=32768`、`reserved_output_tokens=2400`、max-total=5581，prompt min/median/p95/max=`769/1205/2341/3181`。详见 [SAFE evidence](evidence/R60_GPUIMAGE_A_REVIEWER_V2_CPU1000_PASS_SAFE_20261108.json)。

A 的新版公开 Runner 与 GitHub 逐字一致；旧 H200 Pilot 输出目录 `gpu-review-output-A-pilot5-01` 中 `review_0001.private.json` 使用 v1 仅作历史保存。**不能复制该 v1 checkpoint 到新的 v2 私有输出**。新 A Pilot 只能选独立目录 `gpu-review-output-A-pilot5-v2-01`，原始冻结 A input 和新版 runner 均 RO 挂载。此 CPU PASS 不证明模型会按照新契约成功给出文学分数；付费 GPU 回归须明确独立提交、固定参数、最多 A 前 5 条，失败不自动重试，先有结果再决定是否启动 B。Quality-v1 admission=0，SFT 未授权。

---

## 2026-11-08 A Reviewer v2 远端代码核验（当前最新阶段）

Owner Mac 已用 `hf buckets cp` 将新 Runner 上传到 `hf://buckets/adradar/storyforge-training/quality-review/r60/r60-quality-cpu-20261108T082545Z/reviewer-runner-v2/runner.py`。ChatGPT 已通过 HF Bucket 的**真实 cat** 读取文件，与 GitHub 当前分支 `src/storyforge_gold_quality/hf_literary_review.py` 比较，**内容逐字一致（22,547 字符）**，包含 `storyforge_hf_literary_checkpoint_private_v2`，GitHub 文件 blob SHA `c183d8377878ca317db04a74c0fec546dfc78888`。A 的冻结 `input_A/source.private.jsonl`、`runtime_inputs.py`、`runtime_resources.py`、`token_core.py` 在 HF 均存在；新 A CPU 输出 `cpu-output-gpuimage-A-v2-01` 与新 GPU 输出 `gpu-review-output-A-pilot5-v2-01` 均尚不存在。HF 组织 Jobs 列表未见同名 v2 Job。

**下一闸门只允许 CPU**：A 使用固定 vLLM digest（与前一 A 同镜像成功 Job 一致），`cpu-basic`、12 分钟、一个新独立 RW 输出、原始输入与新版 Runner 只读，设置 `PYTHONPATH=/input`；第一时间检查 CPU ResourceGuard 原始 SAFE 字段，若除 `nvidia_visibility` 外有 FAIL 立即退出；仅在其它项都 PASS 时设置 `NVIDIA_VISIBLE_DEVICES=void`，再要求完整资源检查 PASS。执行公开依赖导入、Runner v2 静态契约自检、`--verify-only` 与 `--token-preflight-only` 1000 条，标准 `32768` 上下文 / `2400` 输出预算。须真实 HF Job 最终 COMPLETED + `HF_REVIEW_CPU_TOKEN_PREFLIGHT_PASS__NO_GPU` + over-budget=0，不能用单纯 upload/本地测试证明通过。

**后续限制**：新版 GPU A 5 条还未提交；如果 A v2 CPU 预检 PASS，再单独审核追加付费 H200 最小重评；旧 v1 Checkpoint 只存于旧输出，绝不挂载复用。B H200 仍不自动执行；Quality-v1=0、SFT training 未授权。

---

## 2026-11-08 A H200 首次真实文学审核结果：1 个旧契约 Checkpoint + 后续 MODEL_REASON_HOLD（最新）

真实 [HF Job `6af051150e0338d1bb84aad1`](https://huggingface.co/jobs/adradar/6af051150e0338d1bb84aad1) 使用单卡 H200、固定 vLLM SHA 和 `Qwen/Qwen3-32B@9216db5781bf21249d130ec9da846c4624c16137`，请求 `--start 1 --limit 5`，创建 `2026-11-08T10:38:13.808Z`、结束 `10:40:51.984Z`，**ERROR / exit 42**。实际模型权重 `17/17` 分片加载完成；推理已经执行，但 SAFE 为 `HF_REVIEW_HOLD`、`reason_code=MODEL_REASON_HOLD`。该码由旧验证器同时涵盖 `literary_quality_notes` 类型/长度与 `uncertainty` 类型不正确，**无法从旧日志进一步区分具体字段**，不得编造原模型输出。

HF 私有新输出目录只读列出 `review_0001.private.json`（847 字节），无 `review_0002..0005`。第 1 条已先完成旧 v1 校验并成功写入 Checkpoint；安全元数据检查该记录 `position=1`、模型/Revision 一致、六维评分存在、`decision=REJECT`、三个严重标记均真，但 `specific_source_quotes` 和 `specific_target_quotes` 都是空列表（两者数量均为 0）。**现有 v1 验证器只强制 PASS 原文引用、不强制严重 REJECT 引用；故该 REJECT 缺少可靠证据，不应直接计入真实质量淘汰，也不能认为 1/5 Quality PASS。** 当前尚未执行基于原输入的独立 `read_checkpoint` 全量验证；必须保留这条历史 v1 文件、不覆盖，不公开模型原文或私人标识。

**代码修复（GitHub 新版，尚未分发/运行到 HF）：** 在 `src/storyforge_gold_quality/hf_literary_review.py` 将 Checkpoint 契约从 `storyforge_hf_literary_checkpoint_private_v1` 提升到 `v2`，让旧 v1 Checkpoint 不能静默混用；将旧 `MODEL_REASON_HOLD` 拆分为 `MODEL_NOTES_TYPE_HOLD`、`MODEL_NOTES_TOO_SHORT_HOLD`、`MODEL_UNCERTAINTY_TYPE_HOLD`；对严重 REJECT 要求至少一条严格目标正文原文引用，缺失则 `MODEL_SEVERE_EVIDENCE_HOLD`；提示词明确文学说明至少 8 个非空白字符。合成测试新增旧 v1 Checkpoint 拒绝复用、无证据严重 REJECT HOLD 和说明子码分类，禁止自动补造引用/评分、禁止修改旧历史模型判断。

**下一闸门（未执行）**：先完成新版代码 synthetic CI，使用只读冻结 A/B 输入与独立新脚本/输出前缀准备 v2 Pilot，先验证参数与对应 Tokenizer。仅在明确批准追加 H200 GPU 运行费用与确认没有同名 Job 后，才考虑新的 A Pilot 重评；本轮固定的原 5 条旧任务因错误已结束，不能把旧 `review_0001.private.json` 继续当作新版 v2 质量准入，也不应自动启动 B 或完整 1000 条。公开 [本次 SAFE 证据](evidence/R60_GPU_REVIEW_A_PILOT5_FIRST_RUN_SAFE_20261108.json) 已留存。

---

## 2026-11-08 B 同镜像 CPU 1000/1000 PASS：A/B 双槽技术闸门达成（最新）

Hugging Face [B Job `6af04fda0e0338d1bb84aa61`](https://huggingface.co/jobs/adradar/6af04fda0e0338d1bb84aa61) 经实际 inspect 和 SAFE logs 验证终态 **COMPLETED**（`2026-11-08T10:32:58.362Z` 创建，`10:33:29.455Z` 完成）。与 A 修复任务同一个固定 vLLM digest、`cpu-basic`、`NVIDIA_VISIBLE_DEVICES=void` 仅在无真实 GPU 设备节点时设置，完整原样 ResourceGuard 检查全部 PASS。B 1000/1000 Tokenizer `HF_REVIEW_CPU_TOKEN_PREFLIGHT_PASS__NO_GPU`，超预算 0；prompt Token min/median/p95/max=`673/1099/2306/3550`，输出预留 2400，最大总 token 5950，`max_model_len=32768`，`gpu_started=false`、`training_authorized=false`。见 [B SAFE](evidence/R60_GPUIMAGE_B_CPU1000_ENVFIX_PASS_SAFE_20261108.json)。A 同镜像 [Job `6af04eb10e0338d1bb84a9e1`](https://huggingface.co/jobs/adradar/6af04eb10e0338d1bb84a9e1) 亦已 1000/1000 PASS。

**状态已升级**：A/B 两槽已经在目标 GPU 镜像环境做过真实 CPU Tokenizer 核验，故不再重复 CPU Job；下一个执行步骤是分别对原冻结 A/B 的前 5 条使用 H200 跑真实模型推理，独立输出目录、单槽单次提交、35min 硬超时、Checkpoint 私有保存与逐字引用严格验证。原先本文的“先运行 A/B 同镜像 CPU 检查”是历史操作，**不得再重复提交**。CPU PASS 不能证明 GPU runtime 的模型加载、显存、评审格式必定 PASS，故应先 A 的小批次，真实完成并审计后再 B，任何 HOLD 不得自动重试。SFT 与完整 1000 条没有批准。

---

## 2026-11-08 A 同镜像 CPU ResourceGuard 修复完成（最新权威状态）

实际 HF [Job `6af04eb10e0338d1bb84a9e1`](https://huggingface.co/jobs/adradar/6af04eb10e0338d1bb84a9e1)，`name=r60-gpuimage-cpu-token-A-envfix-02`，`adradar`、`cpu-basic`、相同固定 vLLM digest，创建 `10:28:01.186Z`，结束 `10:28:30.021Z`，**COMPLETED**。

原始检查：`accelerator_profile=PASS`、`cuda_visibility=PASS`、`nvidia_device_nodes=PASS`、`runtime_no_cuda_import=PASS`，**仅 `nvidia_visibility=FAIL`**。因此此前 A/B 的 CPU ResourceGuard HOLD 可以归因于这个 vLLM 镜像的 NVIDIA 可见性默认环境，而**不是实际 GPU 设备节点暴露**。shell 只在 `cpu-basic`、确认其余所有检查通过后设置 `NVIDIA_VISIBLE_DEVICES=void`，不修改任何公共资源守卫逻辑；完整 ResourceGuard 再检查每个子项全部 PASS，日志 `HF_CPU_RESOURCE_GUARD_PASS`。依赖导入 `HF_GPUIMAGE_DEPS_PRESENT` 亦 PASS。

随后在真实冻结 A 1000 条上返回 `HF_REVIEW_CPU_TOKEN_PREFLIGHT_PASS__NO_GPU`：`cases_checked=1000`（5 pilot + 995 remaining）、`over_budget_count=0`、`max_model_len=32768`、`reserved_output_tokens=2400`、`max_total_tokens=5524`、prompt min/median/p95/max=`712/1148/2284/3124`，`gpu_started=false`。独立公开 [SAFE evidence](evidence/R60_GPUIMAGE_A_CPU1000_ENVFIX_PASS_SAFE_20261108.json) 已记录。原先 A/B 的 `HF_CPU_RESOURCE_GUARD_HOLD` 和失败 Job 保留为历史故障，不再重试 A。

**下一步 B（尚未完成同镜像修复检查）**：按与 A 完全一致的双重 ResourceGuard、`NVIDIA_VISIBLE_DEVICES=void`、固定 B 模型 `zai-org/GLM-4-32B-0414@077b5c2f5c43bd3239fd605a0600229e8facbd4a` 在新独立输出 `cpu-output-gpuimage-token-B-02` 进行 CPU-only Tokenizer 检查。Job 名 `r60-gpuimage-cpu-token-B-envfix-02`；先 dry-run、避免同名重复提交、一次尝试，等待 B 真实 COMPLETED。两槽同镜像都 PASS 后才具备**考虑** A/B 前 5 条真正 H200 Reviewer Pilot 的技术条件；GPU 推理仍未运行，SFT 训练仍不授权。

---

## 2026-11-08：A/B 同镜像 CPU 预检触发资源闸门（最新进度，覆盖下面旧待提交段落）

已只读 inspect/logs 确认先前通过 Owner Mac 提交的两个 **CPU-basic** Job 都已完成为 **ERROR / exit 42**：A `6af04c570e0338d1bb84a91e`（10:17:59–10:18:08 UTC）、B `6af04c58e6320c66fad7416c`（10:18:00–10:18:10 UTC）。均先输出 `HF_GPUIMAGE_DEPS_PRESENT`，随后仅输出 `HF_REVIEW_HOLD / HF_CPU_RESOURCE_GUARD_HOLD`；还未运行真实 Tokenizer。**因此前文“GPU 镜像 CPU 已通过才可 GPU”硬门槛尚未完成，GPU Job=0，模型评审=0；旧标准 CPU 镜像 A/B 1000/1000 PASS 保持有效**。

代码/上传镜像资源检查 `ResourceGuard.check_cpu_only()` 检查 `ACCELERATOR`、`CUDA_VISIBLE_DEVICES`、`NVIDIA_VISIBLE_DEVICES`、`/dev/nvidia*` 和 `torch.cuda` 模块是否已导入；上次只设置 `CUDA_VISIBLE_DEVICES=''`。GPU 镜像中继承的 `NVIDIA_VISIBLE_DEVICES` 可能非 CPU 值，但目前只拿到了聚合 HOLD，**尚未证实具体子检查**。不要因为是 CPU-basic 就放宽设备检查；不要取消 Guard；不要重复直接提交相同命令；不要将此描述成 Tokenizer、模型或源数据错误。

**修复策略**：只在单个 A CPU Job 里读出 SAFE 的资源 `checks` 字典；若失败项**除** `nvidia_visibility` 外还存在任何项目，立即退出 `HF_CPU_RESOURCE_UNEXPECTED_HOLD`，不读取私有输入。仅当没有其它失败项时，在 CPU Job shell 显式 `export NVIDIA_VISIBLE_DEVICES=void`，重新运行完整、原样的 ResourceGuard，仍必须全部 PASS；此处理不取消 `/dev/nvidia*` 实际设备检查，也不修改 `ACCELERATOR`。之后在同一固定 vLLM 镜像中才运行真正 A 的 Tokenizer，须取得 HF `COMPLETED`、`cases_checked=1000`、`over_budget_count=0`。**先 A 单槽新输出，完成后才 B；不再 A/B 同时盲重试**。新任务名建议 `r60-gpuimage-cpu-token-A-envfix-02`、新独立输出 `cpu-output-gpuimage-token-A-02`，所有原失败 Job/输出保留。

SAFE 聚合证据保存到 [`docs/evidence/R60_GPUIMAGE_CPU_GUARD_HOLD_SAFE_20261108.json`](evidence/R60_GPUIMAGE_CPU_GUARD_HOLD_SAFE_20261108.json)。该子资源探针仅公开固定字段的 PASS/FAIL、标准错误码，不输出环境变量原始值或用户私人内容。

---

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
