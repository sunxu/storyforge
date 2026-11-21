# Gold48 Owner Mac：最新 11 份 Stage → HF `ready` 最短操作（2026-11-21）

## 2026-11-22 J1 官方 DeepSeek API 已准备；J2 运行期间不换本地代码

Owner 当前决定：先完成 J2 GLM-5.2 / DeepInfra 的 240 条正式评分，同时准备 J1 DeepSeek 官方 API，禁止停止/重跑/污染进行中的 J2。已实际核查并复用 StoryForge 历史成功入口 experiments/r58_quality/r60_real1000_qwen_deepseek20_live.py，以及其原有协议模块 experiments/r58_quality/r60_reviewer_transport.py 的 deepseek-chat 构造器：固定官网 https://api.deepseek.com/chat/completions、deepseek-flash、非思考 thinking.type=disabled、JSON object 输出。六维评分及逐字引用校验仍由冻结 gold48_hf_judge.py 的 judge_one 执行；原单条入口 gold48_judge_step.py 的 attempt/score 锁、严格引用归位、脱敏诊断和全局串行锁继续沿用，J2 默认路径不变。

仅新增薄适配 src/storyforge_gold_quality/gold48_j1_official.py：官方 HTTPS POST 一次、禁跟随重定向/环境代理、响应格式转换为旧 judge_one 所需、Owner create-only 修订文件 owner/GOLD48_J1_OFFICIAL_REVISION_PRIVATE.json。修订绑定冻结 lock 文件 SHA 与 Judge 源码 SHA，明确区分冻结的 J1 DeepSeek-V4.1-Flash / Fireworks 和新实际 deepseek-flash / deepseek-official / DeepSeek-V4.1-Flash-1017（官方升级版本不应当默认为冻结 HF 的完全同权重）。官方不接受原 HF strict json_schema，而通过 JSON-object 响应和包含原评分 Schema 的系统提示实现协议转换，原 validate_score 仍严格验收。每条正式评分的 marker、score、execution 审计明确记录实际 Provider / 模型 / 修订 SHA，不能伪称 HF。不会上传 Owner 映射。

切换计划：J2 跑完之前不要在 Owner Mac 原工作目录 git pull，也不要运行新 J1。完成 J2 后拉取通过 CI 的最新提交，在 Owner Mac 仅执行 PYTHONPATH=src python3 -m storyforge_gold_quality.gold48_j1_official --root "$ROOT" --prepare 进行零 API 的 create-only 修订。现有 reviews/J1/002.attempt.private.json 是 403 历史 HOLD，不得覆盖；在无活跃评分进程时，仅将 reviews/J1 整目录 mv 至 reviews/J1-pre-official-20261122（若目标已存在则 HOLD），新建 0700 的 reviews/J1，保留全部原始证据而不触碰 reviews/J2。再使用历史 R60_DEEPSEEK_KEY，按 --execute --position N --approve-private-transfer --approve-paid-calls 逐项执行 J1，不允许自动重试同一失败项。完整 480 份评分未到齐前仍禁止解盲，quality_v1_admitted=0。费用不再作为 Owner 的审批阻塞，但密钥隐私、防重和流水证据不放宽。

---


## 2026-11-22 最新 Owner 决定：重置 reviews，从零重新执行正式双 Judge（不以费用为阻塞）

**只重置评分输出，不重建匿名输入。** 冻结 240 条匿名输入 `reviewers/GOLD48_BLIND_240_PRIVATE.jsonl`、`owner/GOLD48_JUDGE_LOCK_PRIVATE.json`、Owner crosswalk 和所有训练/生成证据不动。Owner 已批准数据外发及收费，明确要求不再以预算额度为审批阻塞；仍保持 J1/J2 唯一 240 项、一次串行调用、防重复标记、私人日志脱敏、不得解盲。锁中 `max_cost_usd` 是历史备案，非运行时实际计费硬限制，后续账单仍由 HF 管理。

现有 `gold48_judge_step.py` 最小修订，不动被冻结 SHA 绑定的 `gold48_hf_judge.py`：J1/fireworks-ai 请求仅增加 `extra_body={thinking:{type:disabled}}`，J2/deepinfra 请求仅增加 `extra_body={reasoning_effort:none}`，保留 2048 输出 token 和六维结构。严格逐字引用若只错放于 source/target 字段，则在返回 `judge_one` 前确定性归位、不创造引用、不改任何分数/严重标记/文字；每条非空正式评分生成 `NNN.execution.private.json` 保存执行修订、原始模型响应 SHA 和归位计数，再写正式 `NNN.score.private.json`。不匹配原文的虚构引用继续 HOLD，禁止偷偷修正。禁用原始 HF_DEBUG，不允许自动重试不确定的付费调用。Fireworks 是否接受禁思考参数需以首次真实 J1 请求验证，不能预设。**本次完整重评为新的执行批次**；历史 J1/J2 的失败请求及 J2/002 的诊断修复不能当作本批次正式得分。

重启前确保所有评分进程已停止。Owner Mac 使用 create-only 唯一归档路径，在原私有 ROOT 下将 `reviews` 整个 `mv` 为 `reviews-archive-pre-restart-20261122`（若已存在则 HOLD，不覆盖），随后 `mkdir -m 700 reviews reviews/J1 reviews/J2`。**禁止直接 `rm -rf`**：旧版 `_recovery` 内有人工重试授权、原始含隐私 HF_DEBUG 日志、两名评审的 attempt/diagnostic、J2/002 诊断原始输出及离线修复证据；它们应保留私有只读供溯源。不得把原始 debug 日志外传。

重置后只调用现有单项 CLI，按位置 1..240 对 J1、J2 分别评分，发生任何 HOLD 则停止并保留 attempt/diagnostic；不要继续无监督并发，亦不需要新增通用 Runner 或额外无私有校准。CLI 仍要求 `--approve-private-transfer --approve-paid-calls`，但 `--confirm-hf-spending-cap` 可省略；用户已经明确授权正式外发和付费。必须逐批核对最终 480 份有效评分、478 个潜在 AI Judge 得分与 2 个无回复固定规则分数，所有记录冻结后才可解盲。

---

## 2026-11-22 实际故障：J1/002 已重评一次仍 HOLD；后续禁用原始 HF_DEBUG

Owner 已明确授权 Gold48 私有文本外发与真实付费，且 `GOLD48_JUDGE_CONFIG_LOCKED__NO_API_NO_TRANSFER` 已在 Owner Mac 正式 create-only 冻结。先前 J1/001、J2/001 空回复固定评分各一份 PASS（0 API）；J1/002 首次正式请求和单次人工授权重评均 `JUDGE_API_OR_FORMAT_HOLD`，现有新 `002.attempt.private.json`、无 `002.score.private.json`。原始失败 attempt 已留在私有 `_recovery`，不能再删除或重试这项，也不得把异常误记为质量 1 分；费用未知，仍无任何有效 AI Judge 评分。

Owner 上传的私有 HF_DEBUG 日志只显示 GET 模型 Provider 映射及一次 `POST .../fireworks-ai/.../chat/completions`，没有 HTTP 响应状态/SDK 异常类/JSON 内容诊断，**无法确定根因**。`HF_DEBUG=1` 会写出匿名小说原文，请勿继续使用、上传或分享这类原始日志。此前 HF 平台有额外请求，Owner 已说明其中包含另一次人工测试，不能据此称本次 SDK 自动重试。

本次仅改动 `gold48_judge_step.py`，**不动被冻结 SHA 绑定的 `gold48_hf_judge.py`**：未来每次正式请求若失败，写 create-only `reviews/J1/NNN.diagnostic.private.json`（或 J2），只记录 `api_exception/http_status/exception_class/provider_request_id` 或 `api_response_received/choices_present/content_chars/json_valid/finish_reason`；从不记录 HF Token、小说、候选答案、HTTP body、异常 message。CLI 在 `HF_DEBUG=1` 时直接 HOLD，不发请求。diagnostic 与 attempt 都是 Mac 私有 0600，日志仅做错误分型，不代表评分有效；未完成的评分仍禁止自动重试。**新版本无法追溯已发生的 J1/002 两次旧请求的真实错误**。

下一步可从尚未消费的匿名条目继续**真实 Gold48 评分**以收集安全故障分型，建议先 J2/002（不同 Provider）单条执行且保持组织实际费用限制生效；这不是额外校准。不要运行本页旧的 J1/002 或 J1/001 示例，也不要自动循环 478 项。发生新 HOLD 即停止，依据私有 `*.diagnostic.private.json` 的脱敏字段判定；如 J2 PASS，则继续依既定评分计划，保留 J1/002 缺口由独立审计处置，解盲仍禁止。当前 `quality_v1_admitted=0`。

---


## 2026-11-22 Owner 直接推进：跳过 AI Judge 无私有数据校准

Owner 已明确决定跳过独立的无私有数据模型校准，不得把格式试验当作正式评分前置。已有匿名包 240/240 PASS，且 GOLD48_JUDGE_CONFIG_PREFLIGHT_PASS__NO_OUTPUT_NO_API 已通过；不重跑匿名包、SHA、生成或此前离线预检。

下一步直接使用前文现有 GOLD48_JUDGE_CONFIG_PRIVATE.json 和离线 gold48_judge_lock 入口，加 --out 指向 ROOT/owner/GOLD48_JUDGE_LOCK_PRIVATE.json，仅一次 create-only 冻结；预计 GOLD48_JUDGE_CONFIG_LOCKED__NO_API_NO_TRANSFER。若锁已存在则停止，不重复覆盖。模型继续使用 J1 DeepSeek-V4.1-Flash / fireworks-ai，J2 GLM-5.2 / deepinfra，温度0、2048输出 tokens、预算示例25美元；锁定前 Owner 须核实实际 CFG，不能凭此前 SAFE 推断配置明细。

新单项执行入口是 python3 -m storyforge_gold_quality.gold48_judge_step，参数为 --pack、--lock、--output-dir、--reviewer J1/J2、--position 1..240。该入口只复用现有 gold48_hf_judge.judge_one；每次请求前写 0600 create-only attempt marker，成功写私有评分，空回复固定评分不产生 API，失败/超时不自动重试、不跳过、也不提供批量自动重试。需由 Owner 在 ROOT/reviews/J1 与 ROOT/reviews/J2 建 0700 目录，评分原文不得写公开仓库。

**外发/计费仍未授权。** 实际执行前须 Owner 明确批准 HF Inference Providers 向 fireworks-ai/deepinfra 转发当前私有语料，批准本次真实计费，并核实 adradar 组织或资源组已设置有效的 Inference Providers 费用硬限额。配置的 max_cost_usd 仅为记录，并不自动约束 HF 账单；CLI 的 --confirm-hf-spending-cap 是 Owner 声明而非远程校验。经上述批准后单项 CLI 还需显式传入 --approve-private-transfer --approve-paid-calls --confirm-hf-spending-cap，并在进程环境独立提供 GOLD48_HF_INFERENCE_TOKEN。**未完成这些步骤不得发真实 API。**

固定最多 239 非空回答×2模型=478 次潜在付费、1 空回答×2固定评分；模型收费后 cost_usd 为 null，表示未经 HF 官方账单核账，不能算作0。所有评分与来源键保持隔离，全部评分私有冻结前不得解盲。参考 HF 官方组织账单/支出限制：https://huggingface.co/docs/inference-providers/pricing

---

## 2026-11-22 真正当前下一关：匿名包 PASS → 离线 Judge 合同（不调用 API）

**Owner Mac 实际最新 SAFE**：`GOLD48_240_BLIND_OBJECTS_PREPARED__NO_JUDGE_CALLS`，48 题 ×5 来源 240 项已在私有域成功生成，7 条 `length` 和 1 条空回复完整保留；评分 0/240、API 0、$0、未解盲、`quality_v1_admitted=0`。**不要重复打包，也不要覆盖已经存在的匿名包/Owner key。** 此节覆盖下方旧的「创建私有包」命令。

已新增 `src/storyforge_gold_quality/gold48_judge_lock.py`：**只在本地读取**现成 reviewer 匿名包和单独的两评审模型配置，核对 240 个随机 ID、48 个同题历史各五份、1 个空回复及私有文件权限；将匿名包 SHA 和六维 Judge 代码 SHA、两个不同的模型与 Provider、预算上限、零重试/单并发、无回复机械评分绑定到 create-only `0600` Owner 合同。**此工具没有 HF 网络/付费调用，不打开 Owner 来源映射，生成合同也不代表允许外发或自动计费**。未来真实调用前还需确认各 Provider 的严格 JSON Schema 能力、实际费用/硬预算门禁和 Owner 对 HF/OpenRouter/后端 Provider 的私有语料外发授权；该合同本身不能代替这几个签收。

**以下模型/费用仅为供 Owner 审批的候选配置，不是已锁定的实际评审者，也不是当前价格保证**。若 Owner 选择不同模型，先改配置，不改代码。冻结前不得借此触发任何 API。

```bash
set -euo pipefail
umask 077
cd ~/workspace/storyforge
BRANCH=docs/r60-p2-r47-r48-r55-source-shape-audit-20261118
test "$(git branch --show-current)" = "$BRANCH"
test -z "$(git status --porcelain)"
git fetch origin "$BRANCH"
git merge --ff-only "origin/$BRANCH"

ROOT="$HOME/.local/share/storyforge/r60/private/gold48-quality-v1-blind-20261122"
PACK="$ROOT/reviewers/GOLD48_BLIND_240_PRIVATE.jsonl"
CFG="$ROOT/owner/GOLD48_JUDGE_CONFIG_PRIVATE.json"
LOCK="$ROOT/owner/GOLD48_JUDGE_LOCK_PRIVATE.json"
test -f "$PACK"
test ! -e "$CFG" && test ! -L "$CFG"
test ! -e "$LOCK" && test ! -L "$LOCK"
# Owner 确认具体模型/Provider/预算后才保留此配置；以下是候选值
cat > "$CFG" <<'JSON'
{"schema":"storyforge_r60_gold48_judge_config_private_v1","reviewers":[{"reviewer_id":"J1","model":"deepseek-ai/DeepSeek-V4.1-Flash","provider":"fireworks-ai","temperature":0,"max_tokens":2048},{"reviewer_id":"J2","model":"zai-org/GLM-5.2","provider":"deepinfra","temperature":0,"max_tokens":2048}],"max_cost_usd":25.0}
JSON
chmod 600 "$CFG"
PYTHONPATH=src "$HOME/.local/share/storyforge/venvs/r60-owner/bin/python3" \
  -m storyforge_gold_quality.gold48_judge_lock --pack "$PACK" --config "$CFG"
# 审核离线预检、安全边界及候选选择之后，才另行执行同一命令并添加 --out "$LOCK"
```

期望只读 `GOLD48_JUDGE_CONFIG_PREFLIGHT_PASS__NO_OUTPUT_NO_API`，计数 `planned_paid_judge_scores=478`、`fixed_no_response_scores=2`、`api_calls=0`。这里的 478 是**两名不同 AI 评审各评 239 个非空答案**的潜在次数；1 个空答案由两名评审的固定规则分别登记，共 480 个最终评分格（每个评分格又含六维），**尚未评分、尚未付费、也不能宣称 AI Reviewer 已独立完成审查**。Reviewer 独立性和未来争议处理仍需 Owner 显式确认。

---


## 2026-11-22 停止 GPU 执行流程：Owner Mac 当前只做盲评资料交接

**本节优先于下方 2026-11-21 的 `ready/submit`、Stage 上传、GPU 进度与“某臂尚待生成”记录。** 四臂 Base/R46/R54/R60 各 48/48 已真实生成；HF Jobs 均 `COMPLETED`，Owner Mac 各 4 份结果文件独立下载、SHA 与结构审计均 PASS。正式 Run ID、Job ID、停止原因及不可越过的盲评边界见 [现行任务书顶部](R60_BASE336_P2_QUALITY_EVAL_NEXT_AGENT_HANDOFF_20261119_CN.md)。

**不要再次运行** `scripts/r60_gold48_gpu_cli.py submit/ready`、`r60_gold48_gpu_result_audit.py`、旧 Stage `sync` 或新 GPU Job；原始结果、私有 `0700/0600` 目录保持不变。现有结果目录为 `~/.local/share/storyforge/r60/private/gold48-owner-results/<run_id>/`；原始历史回答不在 HF GPU Stage，须由 Owner Mac 已冻结私有原件读取，绝不从公开资料猜造。**Owner Mac 真实只读 SAFE 与后续 240 项匿名打包均已 PASS**；下方关于再次打包的旧说明及命令仅作历史审计，**不要执行**。当前动作已由本文最顶部的离线 Judge 合同步骤取代，正式评分及外发授权仍 HOLD。

**2026-11-22 新签收的真实 SAFE（只记录聚合，不写入私有原文）**：`GOLD48_48X5_SOURCE_PREFLIGHT_PASS__NO_OUTPUT_NO_JUDGE`；`cases=48`、`answers=240`、`stories=8`、`sessions=25`、`main_cases=48`、`sensitivity_cases=42`、`length_answers_retained=7`、`no_visible_reply_answers_retained=1`。评分 `0/240`、HF API 调用 0、费用 $0；`owner_mapping_uploaded=false`、`quality_v1_admitted=0`。预检并未创建正式盲评包，不能把 PREP PASS 写成已生成包或已评分。

**仅在 Owner Mac 上执行一次**（沿用上述成功预检命令中已经设置的九个实际私有绝对路径；不公开路径、文件或内容；如果目标目录已存在则 HOLD，不覆盖）：

```bash
set -euo pipefail
umask 077
cd ~/workspace/storyforge
BRANCH=docs/r60-p2-r47-r48-r55-source-shape-audit-20261118
test "$(git branch --show-current)" = "$BRANCH"
test -z "$(git status --porcelain)"
git fetch origin "$BRANCH"
git merge --ff-only "origin/$BRANCH"
: "${GOLD48_FREEZE:?}" "${GOLD48_INPUT:?}" "${GOLD48_INPUT_MANIFEST:?}"
: "${GOLD48_ORIGINAL:?}" "${GOLD48_LOCATORS:?}" "${GOLD48_BASE:?}"
: "${GOLD48_R46:?}" "${GOLD48_R54:?}" "${GOLD48_R60:?}"
OUT="$HOME/.local/share/storyforge/r60/private/gold48-quality-v1-blind-20261122"
test ! -e "$OUT" && test ! -L "$OUT"
PYTHONPATH=src "$HOME/.local/share/storyforge/venvs/r60-owner/bin/python3" \
  -m storyforge_gold_quality.gold48_blind \\
  --freeze "$GOLD48_FREEZE" \\
  --input "$GOLD48_INPUT" \\
  --input-manifest "$GOLD48_INPUT_MANIFEST" \\
  --original "$GOLD48_ORIGINAL" \\
  --locators "$GOLD48_LOCATORS" \\
  --base "$GOLD48_BASE" \\
  --r46-v02 "$GOLD48_R46" \\
  --r54-v03a "$GOLD48_R54" \\
  --r60-base336 "$GOLD48_R60" \\
  --out "$OUT"
```

期待**仅打印** `GOLD48_240_BLIND_OBJECTS_PREPARED__NO_JUDGE_CALLS` 和相同的 SAFE 计数。Reviewer 匿名文本在 `$OUT/reviewers/GOLD48_BLIND_240_PRIVATE.jsonl`；Owner 来源映射与包 SHA 在 `$OUT/owner/GOLD48_COORDINATOR_KEY_PRIVATE.json`（均 0600，目录 0700）。**Owner key 不得发送给评审模型或上传共享 Bucket/Git；Reviewer 文本在明确外发许可前也不发送 HF。** 如果此次写入失败，不重新执行 create-only，也不清理覆盖已写私有文件；先查单一 HOLD 原因。完成后下一关才是冻结六维 rubric、缺失回复固定规则、AI Judge 模型/Provider/温度/max_tokens、独立评审数量/分歧方案、总费用上限和第三方数据处理授权，再允许真实 API 调用。

**特殊凭据提示**：近期一次 R60 结果审计最初因本地推理用 `HF_TOKEN` 覆盖 Bucket 凭据而在 `HfApi.list_bucket_tree` 遇到 `BucketNotFoundError`；改用可读组织私有 Bucket 的既有登录凭据后 Owner 审计通过。日后对 Inference Providers 与私有 Bucket 使用分离的凭据作用域，禁止公开任何 Token。`owner_mac_job_image_inspect_verified=false` 和独立签名状态仍 false；Quality-v1 评分/晋升未开始。下文 GPU 命令只用于历史溯源，**当前不得按其重新生成**。

---


**本节为现行 Mac 执行说明；下面从“历史执行笔记”起均只用于追溯，不可照旧执行。** 使用 PR #31 的实时 HEAD / CI 与实际 Owner SAFE 回执，不再以旧 HEAD 或静态 README 的“尚未启动 GPU”状态为准。Base 48/48 已完成 GPU 生成和 Owner 四文件下载审计；R46 首次 GPU Job 在 Adapter `lora_alpha=128.0` 严格类型检查处 HOLD，旧 Run ID 禁止重投。已针对历史浮点配置做最小 Loader 修复和回归测试，后续新 Run ID 必须使用含该修复的当前代码 Bundle。

**证据边界**：Owner Gold48 48 条输入与 48 条原始回复/冻结 SHA 已签收；历史 HF CPU Tokenizer 48/48 SAFE PASS（`6b00971aefaf5e14f4b3b24a`，Run Key `r60-gold48-cpu-20261120T182842Z-e5de137532a1`）。该 CPU Job **只有 SAFE**，没有 `GOLD48_TOKEN_PREFLIGHT_PRIVATE.json`。修复后 `scripts/r60_gold48_gpu_worker_entry.py::STAGED` **恰好 11 份**，已去掉 `token_preflight.private.json`，不得伪造或要求补生成。GPU Loader 在固定 `Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` 使用 Tokenizer 并比对同一不可变 revision 的 `chat_template.jinja`，随后才加载模型权重。固定公开模板与该 revision 的 `tokenizer_config.json.chat_template` 已独立只读比对为完全一致（模板 8,952 字节），**Base 实际 GPU/Owner 下载审计已通过；R46/R54/R60 的真实适配器推理仍须分别完成 GPU 和 Owner 审计**。

**Stage 现行精确 11 文件**：`frozen_profile.json`、`owner_freeze.private.json`、`adapter_bindings.private.json`、`input_manifest.private.json`、`input.private.jsonl`、`r46_evidence.private.json`、`r54_evidence.private.json`、`r60_evidence.private.json`、`owner_authorization.private.json`、`runtime_lock.hashes`、`runtime_contract.json`。以代码 `STAGED` 为准，文件名**不能多也不能少**。可信 Mac 私有目录及父目录权限 0700、源文件 0600；绝不包含历史 Original 回复。未授权新 Run ID 不自动创建，已有 create-only 产物不重建/不覆盖。

**权限和最短路径**：Mac **不安装** `transformers`/`torch`/`peft`，不在 Mac 运行模型 Tokenizer/Chat Template/Token 预算；HF CPU 历史 PASS 不重跑。已取消 Provider 动态证明/0700 FUSE 原子账本/Owner Ed25519 强制签名，改由单 Owner Mac 的 `approve-one-arm` 0600 create-only 审批、既有 HF 权限、Job 历史与本地一次性提交标记，旧签名逻辑仅兼容历史审计。不使用 Supabase/PostgreSQL、不开新 Runner、不重复 CPU 探针、不修改冻结 Profile、不重复 48 输入与 204 Story/495 版本/R50 等历史审计。**这次文档/接手授权不是 GPU 费用批准**；`ready` 无 GPU，`submit --execute` 是**单臂完整 48 条正式生成**（不是 1 条廉价 Smoke），需 Owner 针对本次模型/Run ID/GPU 预算和范围另外明确批准。未知/失败不自动重试。真实 GPU PASS 后再按另行授权进入 192 生成、Owner 下载 SHA/Inspect、240 对象盲评和 Quality-v1 决议。当前 `quality_v1_admitted=0`、未晋升。

## 运行时进度日志（新 GPU Job 生效，已有旧 Job 不追溯补写）

当前 HEAD 的 `scripts/r60_gold48_gpu_worker.sh` 与 `scripts/r60_gold48_gpu_worker_entry.py` 在 **execute** 路径向 HF Job stdout 输出安全 JSONL（`schema=storyforge_gold48_gpu_progress_safe_v1`）。`check`/本地 `ready` 不生成逐条推理日志。必须使用新的代码 Bundle 提交新 Run ID；只更新 Git 不会改写已经启动或结束的 HF Job。

- **启动/加载/交付阶段**：`bootstrap_started`、`stage_preflight_passed`、`dependencies_installed`、`stage_verified`、`inputs_materialized`、`preflight_started`、`preflight_passed`、`model_loading_started`、`model_loaded`、`result_delivery_started`、`result_delivered`；如果 Dispatcher 抛异常则发送 `execution_halted` 和上一个安全阶段名。启动阶段的 `startup_elapsed_seconds` 与 Python 入口的 `elapsed_seconds` 从不同起点计时，不能直接相加。
- **逐条生成**：生成前 `generation_started`（0/48）；每条开始 `case_started`，完成并通过本地结构检查后 `case_completed`；日志只含从 1 开始的顺序索引、`completed`、`total=48`、`percent`、本条耗时、生成累计耗时、基于已完成样本的粗略 `eta_seconds`、安全的 `finish_reason`。不输出 Story/Session/样本私有 ID、输入/回答、逐条 SHA、密钥或敏感路径。
- **完成与验收的边界**：`generation_finished_unpublished` 是“48/48 已在内存中生成”的进度，不代表私有结果已存盘；`private_output_written` 是 Worker 的本地 create-only 输出；`result_delivered` 是远端 RW Bucket 交付阶段完成。正式成功仍以 `GOLD48_ONE_ARM_GENERATED_AND_TRANSFERRED__OWNER_AUDIT_PENDING` SAFE、HF Job `COMPLETED` 和 Owner 独立下载 SHA 审计为准。任何 `HOLD` 均不得自动重投原 Run ID。

查看 Hugging Face Job 页面的 Logs，按 `event=case_completed` 即可追踪 1/48 至 48/48；每条只在生成结束后出具完成事件，**不是模型内部逐 token 流式事件**。进度/ETA 是非持久辅助观测值，不能替代原始冻结输出及 Quality-v1 准入审计。

## 1. 只读核对已有本地资料，不重复 create-only 工作

在可信 Owner Mac 上执行（不会启动 GPU）：

```bash
set -euo pipefail
umask 077
cd ~/workspace/storyforge
BRANCH=docs/r60-p2-r47-r48-r55-source-shape-audit-20261118
git fetch origin "$BRANCH"
git switch "$BRANCH"
git pull --ff-only origin "$BRANCH"
export SHA="$(git rev-parse HEAD)"
export PYTHONPATH="$PWD/src"
export BUCKET='hf://buckets/adradar/storyforge-training'
export CODE_URI="$BUCKET/preflight/r60/gold48/runtime-code/$SHA"
command -v hf
hf auth whoami
python3 scripts/r60_gold48_gpu_cli.py --help
# 按已有 Owner SAFE 确认此次 Run ID、Role 与本地 0700 Stage，不凭空生成
# export RUN_ID='已签收的唯一RunID'
# export ROLE='base'
# export STAGE='/绝对路径/0600私有文件所在的0700目录/已签收的RunID'
```

本地 `STAGE` 的末级必须等于 `RUN_ID`，它与父目录均 0700，**恰好 11 份** 0600 私有文件。上面的 `PYTHONPATH` 仅用于既有不触碰模型的 Mac CLI；**禁止在 Mac 安装 Transformers/PEFT/Torch 或重新跑 Tokenizer**。

## 2. 如确认代码 Bundle/Stage 尚未上传，再补传准确缺件

- 代码 Bundle：从**当前 Git HEAD** 的干净跟踪文件 `git archive HEAD scripts/r60_gold48_gpu_worker.sh scripts/r60_gold48_gpu_worker_entry.py src/storyforge_dataset` 物化到新的安全本地目录。不要打包整个私有 Mac 目录或把未跟踪文件/Owner 私有原文提交 GitHub。
- 私有 Stage：只有 `STAGED` 对应上述 11 个文件、Owner 已签收且允许为本 Run ID 上传时，才把整个干净目录同步到 `$BUCKET/preflight/r60/gold48/gpu/runs/$RUN_ID`。缺失的 `GOLD48_TOKEN_PREFLIGHT_PRIVATE.json` **无需寻找、重建或上传**。
- 均使用现有 `hf buckets sync "$SOURCE" "$DEST" --dry-run` 先审阅上传计划；确认无误后 `hf buckets sync "$SOURCE" "$DEST" --ignore-existing`。**ignore-existing 不校验远端已有同名内容**，必须由下一步 `ready` 逐文件 SHA 检查。已存在且完整的文件不重复同步。

## 3. 唯一下一关：真实只读 `ready`

把下列尖括号替换为 **Owner 实际已签收且已存在** 的值，不得把示例当真实路径；下面命令**不启动 GPU**：

```bash
python3 scripts/r60_gold48_gpu_cli.py ready \
  --run-id "$RUN_ID" --role "$ROLE" \
  --stage "$STAGE" \
  --code-prefix "$CODE_URI" \
  --adapter-r46-v02 '<R46 ckpt-7 已签收 Bucket 目录>' \
  --adapter-r54-v03a '<R54 ckpt-16 已签收 Bucket 目录>' \
  --adapter-r60-base336 '<R60 ckpt-37 已签收 Bucket 目录>'
```

**仅拿到实际** `GOLD48_GPU_MAC_STAGE_CODE_AND_CLI_READY__NO_JOB` **才算 READY**；否则把 SAFE 的确切 HOLD 码交给 Agent，只修那个阻塞。CLI 会检查 11 份 Stage 私有文件 SHA、当前 HEAD 的十个核心代码文件 SHA、无重复 Job、远端结果为空与 HF CLI dry-run。

## 4. GPU/后续评测边界

**本次文档任务不授权收费任务。** 现有 `submit --execute` 将发起**一整个生成臂 48 次推理**，不是单案 Smoke；必须由 Owner 单独批准具体 Run ID、GPU 资源/费用和执行范围。真实 HF Inspect、Qwen3.5+PEFT/CUDA 完整加载、输出下载/Sidecar/Manifest SHA 后另行准入四臂 192 生成与 240 对象盲评。失败或超时不得自动重投，已有 Mac 本地 0600 create-only marker 保留并查 HF 历史。

---

## 历史执行笔记（以下旧门禁、12/13/14/15 文件数和命令均已失效，不得用作下一步）

# Gold48 Owner 本地：已冻结输入物化、Adapter 签收、单独签名授权

## 0. 2026-11-21 Owner 已选单机简化调度（最高优先级）

### Gold48 RO 输入本地化与私有结果交付（代码已接，真实 Job 待验）

- 已在**原** `gold48_runtime_gate` 中加 `materialize_gold48_ro_input(source, target, expected_sha256)`：复用 `InputManager` 的 O_NOFOLLOW/长度限制/精确 SHA，再在 Job-local 0700 根写 0600 的 create-only 文件并 fsync、读回；用于解决 HF FUSE 只读文件不保存 POSIX 模式的问题。这个函数**必须由未来经 Owner 批准的 Job 包装在生产 pre-GPU 预检前调用**；当前尚无专门 GPU 提交动作，不可将工具函数的 CI 成功当成真实 HF 输入挂载 PASS。
- `run_authorized_gold48_production` 已在原 `run_gold48_generation_batch` 后直接调用 `deliver_gold48_private_result`。默认固定输出位置为私有 Bucket `hf://buckets/adradar/storyforge-training/experiments/r60-gold48/outputs/<run_id>/`，必须按 `<role>.private.json`、`<role>.private.json.launch.private.json`、`<role>.private.json.identity.private.json`、`<role>.private.json.result-sha256-manifest.private.json` 顺序上传；最后一个 SHA256 manifest 在本地由已有 `OutputManager` 原子发布，远端使用 `hf buckets cp` 而非要求 FUSE POSIX 原子性。每份传输后下载到本地 scratch 再校验 SHA 和字节数。**不能将已上传部分结果或单一 Job 回读当成 Owner 已签收**。
- 若上传、回读、完整性或私有目录检查失败，状态为 HOLD，绝不自动重跑模型。正式评测需要 Owner Mac 再使用既有 `hf buckets cp` / 下载 SHA 审计流程确认四个 Run ID 的每份远端文件、48 条与原始 Frozen 输入绑定。所有真实 GPU/Provider/Owner 签名公钥授权仍独立 HOLD；**本轮只完成 CPU 合成代码与 CI，尚无真实 HF 交付验收。**



**2026-11-21 最新已完成代码适配**：`gold48_runtime_gate.py` 的旧 HF Bucket / FUSE 共享消费根已换成当前 HF Job 的 **本地** `/tmp/storyforge-gold48-private/spent`（预先创建 0700）。`OutputManager` 仍负责 0600、原子不覆盖、文件及目录 fsync；运行进程按 `/proc/self/mountinfo` 拒绝 FUSE/远程文件系统作为消费根或生成私有输出。签名验收、Provider 身份、依赖锁、RO Adapter 挂载、Loader SHA 和 Worker 约束均未删除。此消费记录**只在当前 Job 生命周期内有效**；跨 Job 防重复依赖唯一可信 Owner Mac 的本地持久提交标记和完整 HF Job 历史，不能宣称全局分布式互斥。

**尚缺正式交付**：现有 Mac 的 CPU-only submit 和 Base336 GPU dry-run 并非 Gold48 GPU 正式提交；远程 `:ro` 证据/签名文件可能报告非 0600，必须经 SHA 校验安全复制到本地 0600 后校验；Job-local 输出与 Sidecar 必须完整送达私有 HF Bucket，再由 Owner Mac 下载验 SHA。尚未完成输出上传回收闭环、Provider/Owner 独立可信指纹注册与 GPU 授权，**不可启动真实推理**。不使用 Supabase/PostgreSQL，不重跑 HF Bucket 0700 探针。



不引入 Supabase/PostgreSQL 或新分布式锁；唯一调度者是可信 Owner Mac。复用 `r60_common2_wrapped_hf_cli.py` 的完整组织 Job 历史排重、标记先于提交、失败留标记，以及 `r60_base336_gpu_cli.py` 的 GPU 命令 dry-run 和镜像/挂载检查。Mac 本地提交标记已经改由 **既有** `OutputManager.write_safe` 发布（0600、原子拒绝覆盖、文件及目录 fsync），不复制写入算法。每臂唯一 Run ID；提交结果不确定时查旧 Job，不自动重试；真正的重新执行需要 Owner 新授权及新 Run ID。

本地 Mac 标记是**单一 Owner 可信边界**下的防重复提交，不能证明多个 HF Job 全局互斥；HF Bucket 仅作为输入/结果对象存储。历史第 7/13 节的远端共享目录 `0700` 与跨 Job 消耗账本方案不再是选用的执行架构，保留供审计追踪；**现有 `gold48_runtime_gate.py` 的旧强门禁尚未替换，绝不能在 HF Job 中直接绕过。** 下一步只有在 Owner 完成生产签名密钥注册、Provider 身份/实际输出交付边界核对以及单独 GPU/推理授权后，才能对旧强门禁做与单 Owner 流程相匹配的最小、有回归测试的安全适配。**本节不签发授权，不启用真实推理或新 CPU 探针**。


**仅用于执行本次已存在的代码和文件。** 无历史重审、无新 Tokenizer/SHA HF Job、不访问 R50 sealed、不自动 GPU。所有输入留在 Owner Mac，按既有目录的权限执行；仓库和 CI 不存私有回执内容。

## 1. 核对本地文件（不重构）

**2026-11-21 Owner 本地已验收（由 Owner 提供的 SAFE 回执）**：冻结输入已物化；目录 0700、输入/Manifest 0600、完整输入 SHA、48 条顺序与逐案 SHA 均 PASS；`OWNER_INPUT_SHA_ACCEPTANCE: PASS`。Adapter 绑定已签收为 `OWNER_GOLD48_ADAPTER_BINDING_ACCEPTED__MOUNT_UNVERIFIED`。**不得再次运行 create-only 物化和绑定签收，除非另立新的运行范围并获得 Owner 明确批准。** 此处仅记录 SAFE 状态，不存私有内容。Provider 挂载与真实远端权重仍 UNVERIFIED。

以下为 Owner 实际确认的文件位置，**不要**把私有文件复制进 Git 仓库或打印 JSON 内容：

```sh
umask 077
cd ~/workspace/storyforge
VIRTUAL_ENV="/Users/keedle/.local/share/storyforge/venvs/r60-owner"
export VIRTUAL_ENV PATH="$VIRTUAL_ENV/bin:$PATH"
export PYTHONPATH="$PWD/src"
OWNER_ROOT="/Users/keedle/.local/share/storyforge/r60/private"
BINDINGS="$OWNER_ROOT/GOLD48_ADAPTER_BINDINGS_CANDIDATE_PRIVATE.json"
R60_EVIDENCE="$OWNER_ROOT/r60-cpu-job-json-log-line.private.json"
FROZEN="$OWNER_ROOT/r60-gold48-generation-profile-20261121/gold48_four_arm_generation_profile_frozen_v1.json"
R54_EVIDENCE="$OWNER_ROOT/R54_ADAPTER_RELOAD_VERIFIED_PRIVATE.json"
R46_EVIDENCE="$OWNER_ROOT/r46_training_report.json"
OUT="$OWNER_ROOT/gold48-frozen-worker-input-v1"
INPUT_JSONL="$OUT/GOLD48_GENERATION_INPUTS_PRIVATE.jsonl"
INPUT_MANIFEST="$OUT/GOLD48_GENERATION_INPUT_MANIFEST_PRIVATE.json"
# Owner 未提供以下路径，不猜测：
OWNER_FREEZE="<owner-local>/GOLD48_SCOPED_FROZEN_MANIFEST_PRIVATE.json"
DRAFT="<owner-local>/GOLD48_RECONSTRUCTED_INPUTS_DRAFT_PRIVATE.json"
ACCEPTED="<owner-local>/GOLD48_ADAPTER_BINDINGS_OWNER_ACCEPTED_PRIVATE.json"
```

R46/R54 原报告必须是**原始文件字节**，不能重新格式化。R60 evidence 必须是此前 Job `6b00a44aefaf5e14f4b3c6b5` 的 JSON 回执**原始日志单行字节（末尾不附加换行）**；三份文件必须在私有目录且 mode `0600`。此步骤不读取 Adapter 权重。

## 2. 物化冻结 JSONL 和 Manifest

```sh
# 历史命令，仅在新的 Owner 授权范围内使用；当前已完成，不应重跑。
python3 scripts/r60_gold48_generation_input_materialize_cpu.py \
  --frozen-profile "$FROZEN" \
  --owner-freeze "$OWNER_FREEZE" \
  --reconstructed-draft "$DRAFT" \
  --private-root "$OWNER_ROOT" \
  --output-dir "$OUT"
INPUT_JSONL="$OUT/GOLD48_GENERATION_INPUTS_PRIVATE.jsonl"
INPUT_MANIFEST="$OUT/GOLD48_GENERATION_INPUT_MANIFEST_PRIVATE.json"
shasum -a 256 "$INPUT_JSONL" "$INPUT_MANIFEST"
```

该入口使用 Git Blob 锁验证 Frozen Profile，读取 Owner 冻结里的 Draft SHA 和 48 条逐案 canonical SHA，逐条严格对应，不重新生成任何 Prompt。create-only，第二次执行会 HOLD。核对输出文件均为 mode `0600`、目录 `0700`；只在 Owner 本地保存打印的 SHA。

## 3. Owner 对现有 Adapter 候选签收

```sh
# 历史命令，2026-11-21 已签收；不要重复执行 create-only。
python3 scripts/r60_gold48_owner_generation_authority_cpu.py \
  --mode accept-bindings \
  --frozen-profile "$FROZEN" \
  --owner-freeze "$OWNER_FREEZE" \
  --adapter-bindings "$BINDINGS" \
  --input-manifest "$INPUT_MANIFEST" --input-jsonl "$INPUT_JSONL" \
  --r46-evidence "$R46_EVIDENCE" \
  --r54-evidence "$R54_EVIDENCE" \
  --r60-evidence "$R60_EVIDENCE" \
  --explicit-owner-accept --accepted-output "$ACCEPTED"
shasum -a 256 "$ACCEPTED"
```

只有在 Owner 看过三个来源文件且同意**历史 SHA 来源与 R60 CPU Job 日志的有限证据范围**后才执行。验收状态是 `OWNER_GOLD48_ADAPTER_BINDINGS_ACCEPTED__MOUNT_PENDING`；仍然 **不声称** Provider 挂载或三份当前远端权重字节已独立签收。不重跑 R60 1.87 GB SHA。

## 4. 尚未授权：Owner 单独签发每臂的生产回执

这一段是**未来独立批准正式推理后**的执行说明；目前冻结 Profile 的 `inference_authorized=false`、Owner Trust 公钥指纹未登记，**不要执行签发或 GPU**。Owner 私钥只留 Mac、chmod `0600`；运行端只得到签名回执和公钥。由 Owner 单独审批 Run ID、角色、输出目录、资源与有效期，再执行脚本的 `--mode sign-one-arm --explicit-owner-generation-authorization`，其余参数用 `--help` 查看。脚本检验已签收 Adapter、源文件、48 输入、SHA 锁与镜像 Digest，回执原子 create-only 0600，输出不覆盖。

运行端的可信公钥 SHA256 需要由 Owner 独立核对后，经审查改为 `gold48_owner_receipt.py::OWNER_TRUSTED_PUBLIC_PEM_SHA256` 的固定值；现保持空值，强制 HOLD，不能把命令行传入的新公钥直接视为信任锚。

## 5. 验收口径

Owner 本地物化/签收 SAFE、GitHub 合成 CI、CPU 依赖 Hash Install、真实 GPU/PEFT 加载分别独立签收。GPU Smoke 必须另行授权；本 runbook 不发起任何 HF Job 或正式 192 条推理。

## 6. 选定 CPU 基础镜像中的 Hash-pinned 安装实证

CPU Job `6b00b0894fdc5ab3c55be7f0` 在固定基础镜像 `pytorch/pytorch@sha256:77f17f843507062875ce8be2a6f76aa6aa3df7f9ef1e31d9d7432f4b0f563dee` 中读取 Git 固定 Commit `c4dd8c8ceecf60a26ec476ebf46f07294c9d8f65` 的锁文件，先校验 77,715 字节、SHA256 `dc3425f4895e091c4f5981a4933a6ba2e8fdd8426d8e074069c8cfa2ff4f8d5e`，再执行 `pip install --require-hashes -r <lock>`，返回 0；`pip check` 通过。预装 Torch `2.6.0+cu124` 未改动，签名依赖 cryptography `46.0.4` 安装成功。此前 uv strict hash 安装因 torch 上游无版本约束而 HOLD，换用 pip 后闭环。**仅 CPU 基础镜像 + 哈希覆盖安装 PASS，不等于实际 GPU/PEFT 权重加载 PASS**。

## 7. 加载前授权与运行环境身份（后续真实 GPU 前必须满足）

本仓库新增 `gold48_runtime_gate.py::run_authorized_gold48_production` 作为正式调度入口；执行顺序固定为：冻结输入 / 三份来源证据核对 → **Owner Ed25519 验签** → **Provider 独立签名的实际镜像 Digest 验证** → 当前容器依赖版本与 SHA 锁核对、`pip check` → **共享持久目录 create-only 消耗本次 Owner 授权** → `load_pinned_gold48_backend(launch_permit=...)` → 既有 Worker。

Loader 不再接受 `runtime_authorized=True`。单纯给它一个布尔值或任意字典，必须在 GPU 初始化前 HOLD。Provider 公钥指纹 `PROVIDER_TRUSTED_PUBLIC_PEM_SHA256` 和 Owner 公钥指纹 `OWNER_TRUSTED_PUBLIC_PEM_SHA256` 需要分别由可信方审查并固定；当前均**未设置**。Provider 证明包含可追溯的 Job Inspect SHA、Job ID、运行范围及镜像 Digest，并必须由可信独立方使用预登记公钥签名；不能用用户输入的 `runtime_image_digest` 参数当实测值。

生产消耗账本路径固定为 `/mnt/storyforge-private/gold48-authorizations-spent`，须由生产平台提供跨运行共享、持久、0700、独立挂载目录；每份授权回执 SHA 映射一份 create-only 0600 消耗记录。**失败或崩溃后不允许自动重跑 GPU/模型调用**，必须另发 Owner 签名的新 Run ID 和输出命名空间。未经确认跨运行持久挂载的本地临时目录不可以代替此账本。

本轮的 CPU 模拟测试验证了这些门禁的拒绝路径和执行先后，并**没有**取得真实 Provider 镜像签名证明，也没有执行真实 GPU。当前 Loader 和正式生成应保持 HOLD。

## 8. Sidecar 失败的只读恢复（不重新生成 48 条）

生成开始前会写入 `<output>.launch.private.json` 作为 0600、create-only 运行意图证据。若 48 条输出已完整发布，但 `<output>.identity.private.json` 写入失败，可以调用 `gold48_contract_bridge.recover_gold48_identity_sidecar(...)`：重新检查冻结 Profile、Owner 签名、来源回执、运行意图和**已有**输出的 48 条顺序 / Seed / token 预算 / Schema / 文件 SHA，再 create-only 补写 Sidecar。

恢复函数**不要求 Backend、不载入任何模型、不调用 GPU 或 generate()**。对于真实 Provider 已测量的运行，还需传入 Provider 原始签名证明、公钥及依赖合同以复核身份；无法取得这些证据就 HOLD。已有 Sidecar、缺失 launch marker、缺失或不完整输出全部拒绝，不删除、更改或覆盖输出。授权有效期已经过期时不能绕过验签重写身份；应由 Owner 单独批准处理，而不是自动重复模型生成。

**2026-11-21 后续代码门禁收口：**签名回执现在新增不可省略的 `execution_environment`。生产 Owner CLI 只签出 `PRODUCTION_GPU_48_GENERATIONS`（`inference_authorized=true`、`gpu_authorized=true`）；合成测试密钥使用 `SYNTHETIC_CPU_ONLY_CONTRACT_TEST`（两个授权位均为 false），并且必须显示 `gpu_started=false`、`inference_started=false`。生产签名绝不能用于合成 Backend 的直接四臂入口；合成签名绝不能用于 GPU 前置门禁。真实 Backend 必须能够在共享持久账本中核对已消耗回执、输出范围、Adapter SHA、镜像测量与依赖锁。依赖合同的锁 SHA、镜像 Digest、包版本和已验收 CPU Job 身份在代码内有独立硬钉，不能通过修改传入 JSON 放宽。上述均为 CPU 合成防回归验证，**不代表真实 Provider 挂载、GPU 或正式生成已验收**。

## 9. 已签收 Adapter 的准确边界

Owner 回执为 `OWNER_GOLD48_ADAPTER_BINDING_ACCEPTED__MOUNT_UNVERIFIED`，它只签收 **R46/R54 历史报告 SHA、R60 原 CPU Job SHA 日志、三份来源证据、映射候选与48条冻结输入**。生产前置门禁要求明确保持 `provider_volume_attestation_verified=false`、`current_remote_weight_bytes_verified_all_three=false`；只有真正 Loader 加载精确文件时通过 Adapter 字节哈希，才能确认那次运行的实际本地 Adapter 文件。**`owner_receipt_verified=true` 不代表 Provider 已验明挂载或三份当前远端权重全部 PASS。**

## 10. 首次真实 HF Provider 三路只读挂载验收（CPU，不读权重）

已在 **HF CPU Job [`6b00c1024fdc5ab3c55bfcf3`](https://huggingface.co/jobs/adradar/6b00c1024fdc5ab3c55bfcf3)** 使用固定镜像 `pytorch/pytorch@sha256:77f17f843507062875ce8be2a6f76aa6aa3df7f9ef1e31d9d7432f4b0f563dee`，将现存三个冻结 checkpoint 子目录分别以 HF Jobs 原生 `:ro` 卷挂载到 `/ro_adapters/r46_v02`、`/ro_adapters/r54_v03a`、`/ro_adapters/r60_base336`。

探针读取容器 `/proc/self/mountinfo` 确认**三处精确挂载点均存在且 ro**；三个 `adapter_model.safetensors` 的文件大小均为 `1,867,797,544` 字节；三份 `adapter_config.json` 依次为 `1,282 / 1,282 / 1,288` 字节，读取配置并验证 LoRA 类型、r=64、alpha=128、12 个目标模块集合、基础模型固定 Revision。Job `COMPLETED`，且 `gpu_started=false`、`model_calls=0`、`weights_read=false`、`weights_hashed=false`。

SAFE 结构化实证：`experiments/r60_quality/gold48_provider_ro_mount_cpu_safe_receipt_20261121.json`。**仅本次 CPU Job 的挂载及元数据 PASS**，不等于后续 GPU Job 挂载 PASS、不等于当前三份权重 SHA PASS、也不等于 Owner 或 Provider 正式 GPU 授权。保留 Owner 原始 Adapter 签收及 `provider_volume_attestation_verified=false`、`current_remote_weight_bytes_verified_all_three=false`；**不修改任何冻结 Profile 和私有回执**。未来正式 HF Job 应复用已验证的相同三个 checkpoint 只读挂载配置，并由真实 Loader 在每一臂开始生成前核对相应 Adapter 精确字节 SHA，不重跑此前已完成的历史 CPU SHA 任务。

## 11. 正式运行进程的只读挂载实时校验（不重复 HF 探针）

在 `gold48_runtime_gate.authorize_and_consume_before_gpu` 中，三臂（非 base）必须于**消耗一次性 Owner 授权之前**，通过当前容器的 `/proc/self/mountinfo` 验证 `/ro_adapters/<role>` 是精确独立且 `ro` 的挂载点，同时检查非符号链接目录、权重文件大小 1,867,797,544 字节与三个 Adapter 原始配置文件固定大小。检查只用 `lstat` 和 mountinfo，不读取或 SHA 计算权重。正式 Loader 消费授权时及生成前继续复核该挂载观察，并由原 Loader 完成权重字节流 SHA。过去 CPU Job 的挂载 PASS 不会被当成新进程的挂载实证。若缺失、可写、路径错误、被替换为 symlink 或文件尺寸不同，必须在 GPU 及模型调用之前 HOLD；未签发的 Owner/Provider 许可仍不能被绕过。

## 12. 旧问题已定位：ChatGPT HF Connector 私有 Bucket RW 挂载 403（禁止重复排查）

**沿用 2026-11-03 与 2026-11-10 已核验结论，不再把 Connector 403 描述为未知的组织/Bucket 总体写入权限问题。** 同一组织 `adradar` 的 HF Jobs 在 ChatGPT Connector：无挂载 PASS、私有 Bucket `:ro` PASS、私有 Bucket `:rw` 在提交阶段 403（Job 不创建）。Mac 本地 HF CLI 使用相同组织与 Bucket 的默认 RW 挂载已经完成写入、读回、删除；实际成功 Job [`6af2ee90ab34849891ab2f6e`](https://huggingface.co/jobs/adradar/6af2ee90ab34849891ab2f6e) 于 2026-11-10 `COMPLETED`。这排除了 Bucket 整体不可写、组织总体缺乏 Jobs 资格及简单的卷语法错误。ChatGPT 侧失败点曾定位在 `/api/buckets/adradar/storyforge-training/xet-write-token`；OAuth scopes 未含 `write-repos` 是一个观察点，**尚不足以独立证明具体后端根因**。

2026-11-21 的 Gold48 可写账本探针在 ChatGPT Connector 上重复收到相同 403，未创建 Job、未写入任何 Bucket 文件；**这是已知连接器限制的再次出现，不是新的主线验收结果**。不得因它再提交一轮 ChatGPT RW 探针、重复更换 CPU flavor、切换个人 namespace、反复重新 OAuth 或重跑成功的 RO Adapter Job。后续需要 RW 时，优先复用**已经成功的 Owner Mac CLI 提交通道**，输入继续 `:ro`，输出/账本使用独立的私有 RW 卷；任何实际创建和 GPU Job 仍须按项目单独审批。

正式推理前剩余的**不同**技术门禁是：在 Owner Mac CLI 可以写入的**隔离私有目标目录**上，用原有 `OutputManager.write_safe` 核验 0700/0600、原子 create-only、拒绝覆盖、目录 `fsync` 以及**跨 Job 持久性**。过去 CLI 的简单写入成功并不等于该原子账本合同通过。生产代码 `gold48_runtime_gate.verify_atomic_private_publication_before_spend` 已加入对真实输出目录和持久账本目录的检查，并在消耗 Owner 签名、GPU/模型初始化前失败关闭。该测试不会授予任何推理权限；不得用无法保证原子性的 FUSE 挂载冒充已验证共享账本。


## 13. Gold48 授权账本的 HF Bucket 挂载实证与安全结论（2026-11-21）

**最新真实状态：此节原有双 Job 实验因关键前置门禁 HOLD 而暂停，下面历史命令仅供追溯，禁止直接执行第二份 Job 或通过 chmod/放宽 0700/省略门禁反复探测来取得表面 PASS。**

- **CLI 参数故障已单独关闭**：HF Job `6b00c8544fdc5ab3c55c02dd` 的 image 曾被错误解析为 `--attempts`，已于上一提交修正；它没有执行探针。
- **真正执行的第一份 CPU Job**：[`6b00ca46efaf5e14f4b3f8ca`](https://huggingface.co/jobs/adradar/6b00ca46efaf5e14f4b3f8ca) 使用 `python:3.11`、`cpu-basic` 和 Mac CLI `:ro` 输入、`:rw` 隔离输出，HF Inspect 为 `ERROR`（exit 2），SAFE 日志 `MOUNT_DIRECTORY_MODE_0700_HOLD`，`gpu_started=false`、`model_calls=0`、`weights_read=false`、`training_started=false`。检查在目录模式校验阶段停止，**没有执行**原子发布、拒绝覆盖或跨 Job 持久性验证。SAFE 没有记录挂载根的实际八进制权限，不能声称观察到了特定 mode。
- **官方挂载语义限制**：HF `hf-mount` 项目 [Best for / Not for](https://github.com/huggingface/hf-mount#best-for--not-for) 明确不支持跨节点文件锁和强一致性多写入用例；其 [mount options](https://github.com/huggingface/hf-mount#options) 说明远端对象不保存 POSIX 元数据，远端目录默认报告 `0755`、文件 `0644`，权限显示可能是挂载映射，不能当成安全持久账本的真实私有模式认证。**这解释了为什么 mode 需要核对，但不是对本 Job 实际 mode 的直接测量。** HF Jobs 的具体托管挂载实现仍未独立鉴定，故不据此推断更细的文件系统行为。
- **决策**：`HF_BUCKET_AS_PRODUCTION_ONE_SHOT_AUTHORIZATION_LEDGER=HOLD_UNPROVEN_CROSS_JOB_ATOMICITY`。即使未来某个 Bucket 单 Job 支持 `OutputManager.write_safe`，也不等于跨多个隔离 Job 的原子 compare-and-create、共享唯一性或崩溃恢复语义。**不要**尝试 `chmod 0700` 临时改变远端目录来绕过门禁，不修改 `DURABLE_CONSUMPTION_ROOT` 条件，不把 HF Bucket 的普通持久对象写入冒充一次性授权消耗。
- **主线下一依赖**：Owner/Provider 需选定能独立证明**全局原子唯一约束**、私有访问控制和跨 Job 崩溃持久性的授权账本承载（例如已审查、隔离的新 PostgreSQL 原子唯一键事务，或真实跨节点支持该语义的持久 POSIX 卷）；先对已有平台可复用能力做只读核对，禁止改写故事业务数据库或新建竞争的通用账本框架。原 `OutputManager` 继续用于与其能力相符的私有输出，当前 Gold48 正式推理保持 HOLD；需 Owner 对选定存储、密钥与 GPU 范围分别审批。

### PostgreSQL 现成能力只读复核（2026-11-21；不改生产库）

对既有 StoryForge Supabase 只查询 `pg_catalog` 的**表名/字段/唯一索引/约束/函数签名和权限**，未读取任何业务行或私有故事，未执行 DDL/DML。独立结果：

- 生产 PostgreSQL 已有基于 `UNIQUE` / 部分唯一索引的任务领取及防重复机制；部分 RPC 使用 `SECURITY DEFINER` 并向非授权角色禁用 `EXECUTE`，因此可以**复用数据库原子事务技术和已有权限审查模式**，不需开发新的通用分布式锁。
- 现有 `v2_generation_evidence_grants` 的 `purpose` CHECK **仅允许** `training-evidence`；`v2_generation_evidence_grant_operations` 的 `action` CHECK **仅允许** `issue/revoke`。**不能直接把 Gold48 GPU 推理消耗塞到这两张生产业务表、改约束或借训练证据授权**。目前未发现现成 Gold48 专用的持久消费关系/RPC。
- 当前只读 Connector **不可执行**所需的独立消费写入入口，也不能签发 Owner/Provider Ed25519；查到现有模式不等于实际 Gold48 执行能力已存在。连接账号曾被确认具有 BYPASSRLS，不得把它用于写入或读取受保护业务正文。
- **唯一下一步技术门槛**：由 Owner/平台维护者在**独立隔离权限域**审查一个每份签名回执 SHA 只能原子消耗一次的 PostgreSQL 唯一键事务入口（或另一个具有同等强保证的现成持久系统）；必须证明两个并发 Job 最多一个成功、故障后不能无授权重试、远端 Job 只能调用最小权限签收接口而不能重置或删除。尚无 Owner 储存/密钥批准时**不提交新 DDL、RPC 或 Python 后端**。既有 `gold48_runtime_gate.py` 目前使用**文件型** `DURABLE_CONSUMPTION_ROOT` 和 `OutputManager`；不得仅改文件路径或把数据库 INSERT 的配置字符串当成已接线，未来经批准再做最小原子消费适配，保留 Owner 签名、Provider 实测身份及现有 Worker。
- HF Bucket 原子账本探针已正式停止，不再重复前述 `0700`/RW 试错。**冻结输入/Adapter/Profile 不动；GPU、生成、训练及 Quality-v1 晋升仍 HOLD。**

### 历史双 Job 命令（当前暂停；不得直接继续执行）



**2026-11-21 Owner 首次提交的 CLI 兼容性纠正（优先遵循）：** Job [`6b00c8544fdc5ab3c55c02dd`](https://huggingface.co/jobs/adradar/6b00c8544fdc5ab3c55c02dd) 已在 HF Provider Inspect 中确认为 `ERROR`，`docker_image=--attempts`、`command` 以 `1 python:3.11` 开头，错误为 `docker.io/--attempts` 不是合法镜像。原 CLI 配置中的 `--attempts 1` 被当前 Mac 版 `hf jobs run` 误解析为镜像和命令。**探针尚未运行**，只读核对远端目标 `.gold48-atomic-20261121-v1.private.json` 不存在；此失败不是 Bucket RW、不支持原子写、权限不足或 OutputManager 的证据。下面两条命令均已删除当前 CLI 不兼容的 `--attempts 1`，保持 `--detach`、镜像 `python:3.11`、输入 RO、输出 RW、原 Probe ID 不变。再提交前应先确认 `hf jobs run --help` 中实际支持哪些选项；**不得为了单次尝试属性擅加未受支持的 flag**。没有确认服务端重试语义时，不将 CPU 探针的成功外推为正式 GPU 单次授权保证；正式 GPU 的一次性授权仍由独立 Owner 签名和持久消耗账本控制。不需要重传原有 Stage 或更换 Probe ID/路径。



**只验证前述未完成的原子发布及跨 Job 持久性，不再重复 HF Bucket 的普通 RW 通断测试。** 采用已经成功的 Owner Mac HF CLI `hf jobs run --namespace adradar` 路径，**不使用 ChatGPT Connector 提交 RW Job**。新增最薄入口 `scripts/r60_gold48_ledger_atomic_cpu_probe.py` 直接加载并验证仓库现有 `hf_runtime/outputs.py` Git Blob `69838b603b43663eaa12b1b1947ce14abad524bc`，调用原生 `OutputManager.write_safe`，不重新实现原子写算法。隔离 Probe 目录内只有公开合成标记；不读取或改动 Owner 私有签名账本、48 条文本、Adapter、模型或训练任务。

下方命令**须在 Owner Mac** 执行；每条真实 CPU Job 均独立提交一次，失败只报 HOLD、不改 image/flavor 重试。运行前检查当前分支的 Git 提交已含上述脚本，以及 HF CLI 已登录 `adradar`。务必使用**新的独立探针路径**，不要覆盖原有 `preflight` 其他文件。先用已确认可用的 `hf buckets cp` 上传两份公开源码及一份纯合成初始化文件，令 RO/RW 子目录实际存在：

```sh
umask 077
cd ~/workspace/storyforge
PROBE="hf://buckets/adradar/storyforge-training/preflight/r60/gold48-ledger-atomic-cpu-20261121-v1"
hf buckets cp scripts/r60_gold48_ledger_atomic_cpu_probe.py "$PROBE/input/probe.py"
hf buckets cp src/storyforge_dataset/hf_runtime/outputs.py "$PROBE/input/outputs.py"
printf '%s\n' 'SYNTHETIC_NO_OWNER_DATA' | hf buckets cp - "$PROBE/output/PROBE_ONLY.txt"
```

只把 `$PROBE/input` 以 `:ro` 挂到 `/input`；只把新建的 `$PROBE/output` 以 `:rw` 挂到**正式账本预计使用的容器路径**。第一份 Job：

```sh
ROOT="/mnt/storyforge-private/gold48-authorizations-spent"
hf jobs run --namespace adradar --name gold48-atomic-ledger-write-cpu \
  --flavor cpu-basic --timeout 10m --detach \
  -v "$PROBE/input:/input:ro" -v "$PROBE/output:$ROOT:rw" \
  python:3.11 -- python /input/probe.py --phase write \
  --root "$ROOT" --source /input/outputs.py \
  --probe-id gold48-atomic-20261121-v1
```

第一份 Job 日志须报告 `ATOMIC_CREATE_ONLY_CPU_PASS__SECOND_JOB_PENDING`，并证明 `direct_rw_mount_present=true`、`root_mode_0700=true`、`marker_mode_0600=true`、`atomic_create_only_verified=true`；如 Bucket FUSE 不能保持 0700、硬链接/原子无替换发布或目录 fsync，请保留精确 HOLD，**不得使用简单普通写文件的 PASS 替代**。第一份成功后，再执行与其**不同 Job ID** 的第二份：

```sh
hf jobs run --namespace adradar --name gold48-atomic-ledger-verify-cpu \
  --flavor cpu-basic --timeout 10m --detach \
  -v "$PROBE/input:/input:ro" -v "$PROBE/output:$ROOT:rw" \
  python:3.11 -- python /input/probe.py --phase verify \
  --root "$ROOT" --source /input/outputs.py \
  --probe-id gold48-atomic-20261121-v1
```

第二份日志须为 `ATOMIC_CREATE_ONLY_AND_CROSS_JOB_PERSISTENCE_CPU_PASS`，且 `marker_sha256` 与第一份一致、`cross_job_persistence_verified=true`。这是**独立合成存储验收**，与真实 Owner 账本的运行部署、独立签名信任锚、GPU Smoke / 192 条生成批准完全分离。不自动发第二份 Job、不自动重试；仅在第一份明确 PASS 后手动提交第二份。任何输出都不得包含私有数据。实际完成后回收两个 Job ID 和仅 SAFE 状态写入本手册，不修改已冻结 Profile。


### 2026-11-21 结果交付路径进一步简化（覆盖上方旧 CLI 说明）

按 [HF Jobs volumes 官方说明](https://huggingface.co/docs/hub/jobs-configuration#volumes)，Job 已原生支持独立 `:rw` Bucket 输出挂载，因此 **正式 Job 内不再调用 `hf buckets cp`、不需要注入 `HF_TOKEN`**。原 `deliver_gold48_private_result` 现在直接向准确挂载的 `/output` 写入 3 份私有对象，最后写 SHA256 manifest，并在同一挂载内回读 SHA。它要求 `/output` 在内核 mountinfo 中是**直接可写 FUSE 挂载**，拒绝用容器本地目录假冒远端交付；`/output` 的 POSIX mode **不是**授权锁条件。真正需要 `0700/0600 + fsync` 的只是 Job 内本地生成原件。

Mac 端在提交前必须核对结果前缀 `experiments/r60-gold48/outputs/<run_id>/` 为空，确认输入只读、唯一 Owner Mac、无自动重试；正式 Job 成功后，**由 Owner Mac 独立 `hf buckets cp` 下载四份结果并重算 SHA 与 48 条内容结构**，不能把 Job 内本地 FUSE 回读作为最终验收。此前手册关于“Job 内 `hf buckets cp` 上传并下载校验”的说法是历史方案，以本段为准。未签名/未批准 GPU 时仍保持 HOLD。


### 2026-11-21 Owner Mac 独立下载核验入口（代码/合成测试；未执行真实下载）

已有 `scripts/r60_gold48_gpu_result_audit.py` 复用原 `r60_common2_wrapped_hf_cli.remote_set` 的 HF Bucket 全量文件集检查、原 `InputManager` 的 O_NOFOLLOW/SHA 读取，以及 `gold48_contract_bridge._read_existing_gold48_output` 的 48 条逐条数据结构/Seed/token 上限检查；它**不新建生成器、不提交 HF Job、不调用模型**。

Owner Mac 只有在真实 Job 完成且拿到四份输出后执行（`--owner-download-root` 是已存在的本地 mode 0700 私有目录，`--frozen-input-manifest` 是已有 Owner 私有 0600 输入清单）：

```sh
PYTHONPATH="$PWD/src:$PWD/scripts" python scripts/r60_gold48_gpu_result_audit.py \
  --run-id "<Owner 本次单臂已批准的 Run ID>" \
  --model-role base \
  --owner-download-root "$HOME/.local/share/storyforge/r60/private/gold48-owner-results" \
  --frozen-input-manifest "<已有 Owner 0600 输入 Manifest 路径>"
```

该入口先只读查验远端前缀**恰好**有 4 份既定文件，随后一次性创建本地 `0700` 下载子目录，逐个下载、转为 `0600`，核对 manifest 的全部文件 SHA、文件大小与次序，再比对 48 条生成内容、输入 SHA、Provider image SHA、Owner receipt 摘要等私有 Sidecar/launch 字段。SAFE 结果 `OWNER_GOLD48_RESULT_BYTES_AUDITED__SIGNATURE_REVIEW_PENDING` **不是**独立核验 Ed25519 签名，不表示 Quality-v1 已准入。下载目录已存在、远端不完整、回执不一致或下载失败均 HOLD；没有自动重试或任何远端写操作。此入口待正式 GPU 运行后由 Owner Mac 使用真实私有数据验收，不得预先操作未来 Run ID。


### 2026-11-21 现有生产 Dispatcher 的极薄 HF Job 入口（CPU 合成检查完成前不得声称可执行）

新增 `scripts/r60_gold48_gpu_worker_entry.py` **不是新 Runner**：它不重复生成循环、Sampler、签名校验、Adapter Loader、HF Job 提交和 Result Audit，只将 **15 份固定文件**从 `/input/gold48:ro` 安全核验并本地化为 `0600`，准备 `/tmp/storyforge-gold48-private/inputs`、`outputs/<run_id>` 和 `spent` 三处 mode `0700` POSIX 目录，然后传入现有 `run_authorized_gold48_production`。运行前检查准确的 RO 挂载、manifest 输入 SHA、冻结 Profile 原 Git Blob、Tokenizer CPU 私有模板 SHA 和锁 SHA；**任何历史原始回答不得上传到这个 Stage**。

固定文件名清单在 `scripts/r60_gold48_gpu_worker_entry.py::STAGED`，Owner 必须在 Mac 本地完成完整 SHA 与源证据签收后，才可按照已存在的 HF Stage 清单上传策略建立隔离、唯一 Run ID 的 RO 输入。入口有两种模式：`check` 只读且不调用 GPU；`execute --explicit-owner-gpu-execution` 才可能进入正式运行，但仍会在本地化前验证 **Owner/Provider 独立 pin 都已登记**，之后再由现有 Runtime Gate 逐项验签和消费。**目前两项 pin 未登记，因此 execute 必然 HOLD；不启动或提交 GPU Job，也不以 CLI dry-run 代替 Provider Job ID 实测身份证明。**

运行阶段的 Template SHA 从已审查 CPU Tokenizer 私有回执 `chat_template_sha256_PRIVATE` 取得，不打印私有值；非当前 Job 的 Provider Attestation 无法代替当前 Job 的真实测量签名。正式 Job 的 Code 版本/Stage 私有文件集、目标 `:rw` Bucket 结果目录与 Owner Mac 逐 SHA 回收仍须受控签收。请勿更换已冻结模型、Adapter、48 条问题或生成参数。


### 2026-11-21 当前 HF Job 身份签名门禁（修复已提交，时序仍待解决）

`gold48_runtime_gate.verify_provider_image_measurement` 现在必须验证：独立签名的 Provider Inspect `measurement.provider_job_id` 与**执行中的** HF Jobs 官方 `JOB_ID` 环境变量精确一致（24 位小写十六进制）；当前 Job ID 缺失、格式不符、或签名属于别的 Job 均在 GPU 加载前 HOLD。保留签名与镜像摘要、Run ID/role 检验。参考 [HF Jobs 官方环境变量](https://huggingface.co/docs/hub/jobs-configuration)。

**尚存真正的提交时序阻塞**：目前 15 文件 RO Stage 要求在提交前包含 Provider Attestation；然而新 Job ID 要在提交后才生成。不能使用上次 CPU Job 的证明，也不能忽略本次一致性校验。只有经 Owner 和独立 Provider 许可的**当前 Job 启动后真实证据交接**完成并验收，才有可能启动 GPU。此轮不新增数据库或签名服务，不启动 HF Job，不签发授权。


### 当前 Job ID 证明的最小交接：独立只读挂载（2026-11-21）

**已修正“提交前必须知道 JOB_ID”的循环依赖**。Gold48 固定输入 Stage 由 15 份减为 **14 份**：`provider_attestation.private.json` 不再允许预置其中，其余冻结输入、原 SHA、Adapter 只读挂载均不变化。**仅多增加一个运行时数据交接挂载**，不是新提交器或独立授权服务：

- Owner 在**实际 GPU 提交授权之前**，为单臂唯一 `run_id` 在已存在的私有 Bucket 下准备独立前缀 `preflight/r60/gold48/provider-handoff/<run_id>/`，首先放置一份不含私有内容的 `handoff-pending.json`，结构为 `{"schema":"storyforge_r60_gold48_provider_handoff_pending_v1","run_id":"<run_id>","model_role":"<role>"}`。HF Job **精确 RO 挂载**该前缀到 `/input/provider`，冻结输入前缀仍精确 RO 挂载到 `/input/gold48`，最终结果独立 RW 挂载到 `/output`。不得把整个 Bucket 挂载为 RW。
- HF Job 在启动后拿到真实 `JOB_ID`，运行现有预检并停在**GPU 加载之前**。可信 Provider **在单独的受控 Owner/Provider 流程中**查看这个真实 Job 的 image Inspect 证据，再用其事先登记的独立 Ed25519 密钥签发包含 `provider_job_id=JOB_ID` 的已有 schema 证明，上传为该前缀中的**唯一新增** `provider_attestation.private.json`。不向 GPU Job 注入 Provider 私钥或 HF 上传令牌。
- 新增的 **一个** `receive_current_provider_attestation` 函数仅在 `execute` 中启用：复用严格 RO/FUSE mountinfo 检查，核对 pending 的 run/role，最多等待 **600 秒**（每两秒检查，远程最终一致性只作为可见性机制，不是原子锁）；一旦证明出现，将其 SHA 核验并物化为本地 0600，再直接调用现成 `verify_provider_image_measurement` **验证签名、公钥 Pin、当前 JOB_ID、运行范围和镜像摘要**。不存在、超时、异 Job、签名无效或目录存在非预期文件均 HOLD，绝不自动重提生成。这里每秒的 GPU 资源等待可能计费，必须先有明确成本/时长授权。
- **尚未真实验收**：HF 托管的 RO 挂载在运行中对外部新增文件的可见性需要一次受控 CPU 合成验收，且须核对实际 HF Job 是否使用该更新机制；单独的 GPU Smoke/生成与 Owner/Provider 信任锚仍待签收。不能把代码 CI 当作动态挂载 PASS 或真实推理授权。

下一步仅复用既有 `r60_common2_wrapped_hf_cli` 的单 Owner 提交防重复和 `r60_base336_gpu_cli` 的 GPU 参数/dry-run 生成，给定上述 **RO Stage + RO Provider Handoff + 3 个 Adapter RO + 单 Run RW 输出**，在 Mac 上完成受控**只读参数检查和远端空目录核验**，不开发通用 Runner。HF 官方 hf-mount 支持 Bucket 的 live-follow/eventual consistency，但不能保证每次容器托管挂载都立即看见新增文件，故先作 CPU 合成验收。

### Owner Mac 受控 GPU CLI 参数验证（2026-11-21；完全不提交）

新增最薄 `scripts/r60_gold48_gpu_cli.py`，它**只有 `shape` 和 `dry-run`，没有 submit / execute**；直接复用 `hf_job_guard.build_hf_argv`、`r60_base336_gpu_cli` 的固定镜像/Flavor/Timeout、`r60_common2_wrapped_hf_cli` 的 HF CLI 兼容判断。它确认一次 Gold48 单臂 Job 必须配置 **6 个精确 RO 挂载（14 份冻结输入、Provider 延后交接、不可变代码 Bundle、3 个 Adapter）和一个独立 RW 输出**；完全拒绝 Bundle/Adapter 缺失、根 Bucket、跨源重复及不合法 Code SHA。生成的实际 Worker 命令固定为 `python /input/code/scripts/r60_gold48_gpu_worker_entry.py check --run-id ... --model-role ...`，因此即便用户调用 `dry-run`，也不能启动真实模型推理。**代码 Bundle 尚未安全物化/上传，三个 Adapter 的私有原始 Bucket URI 在 SAFE 证据里没有公开：不猜路径，不自动建立 Stage，不执行 GPU。**

Owner Mac 在已有 3 个 Adapter 的原始私有 `hf://buckets/...` 路径已由 Owner 核对，并且每个 Run ID 对应**不可变代码 Bundle 前缀的末尾 40 位等于已批准的 Git commit**后，可运行命令形状检查：

```sh
# 先把 run_id、code_uri、adapter_r46/adapter_r54/adapter_r60 绑定到真实已签收值
PYTHONPATH="$PWD/src:$PWD/scripts" python scripts/r60_gold48_gpu_cli.py shape \
  --run-id "$run_id" --role base --code-prefix "$code_uri" \
  --adapter-r46-v02 "$adapter_r46" \
  --adapter-r54-v03a "$adapter_r54" \
  --adapter-r60-base336 "$adapter_r60"
```

若 CLI 支持且 Owner 准备继续只读核验，将 `shape` 替换为 `dry-run`；状态 `GOLD48_GPU_CLI_DRY_RUN_PASS__NO_JOB` **仅**说明原 HF CLI 接受参数，不是远端 Code/Adapter SHA、不代表 Bucket 中已存在这些对象、也不是 GPU 授权。**这一步尚未在 Owner Mac 上实际执行。** `hf_job_guard.validate_spec` 仍是 CPU-only，不改动其政策。

**真正下一依赖**：优先用现有代码 Stage/依赖闭包方法给已批准的 Git HEAD 制作独立只读 Bundle（不可在未来 HF Job 中从 `main` 或浮动 URL 拉取代码）；Owner 独立确认 Adapter 私有 RO 来源；对 Provider 独立 RO 挂载的“Job 运行期间外部新增文件可见”做一次隔离 CPU 合成验收。没有这些实际证据，不能把参数检查提升为正式 GPU 任务 READY。


### 动态 RO 挂载真实 CPU 验收：仅用既有 HF CLI 与独立纯合成 Bucket（待 Owner Mac 执行）

**不要提交 Gold48 GPU Job。** 当前专用私有测试 Bucket `hf://buckets/adradar/storyforge-r60-volume-smoke-input-20261104` 已存在，原有 `synthetic.jsonl` 不修改；选定一个全新唯一子前缀只放两份纯合成 JSON。**这测试的是运行中已挂载 RO 目录能否观察到外部新增文件，不是旧 `0700` 共享账本，也不验证 Provider 正式签名/镜像/Adapter**。不使用带实际 Owner/Provider 签名或 Gold48 文本的生产 Bucket。

Owner Mac 先在本机一个终端执行以下全部步骤直到 HF Job ID 输出（不要使用 `--attempts 1`，之前在 Mac 上被 CLI 错误解析为镜像）：

```bash
set -euo pipefail
umask 077
SLOT="gold48-ro-live-20261121-$(openssl rand -hex 5)"
BASE="hf://buckets/adradar/storyforge-r60-volume-smoke-input-20261104/$SLOT"
LOCAL="$(mktemp -d)"
printf '%s\n' '{"schema":"storyforge_gold48_ro_live_pending_synthetic_v1"}' > "$LOCAL/handoff-pending.json"
hf buckets cp "$LOCAL/handoff-pending.json" "$BASE/handoff-pending.json"

hf jobs run --namespace adradar --name "$SLOT" \
  --flavor cpu-basic --timeout 5m --detach \
  -v "$BASE:/input/provider:ro" python:3.11 -- python -u -c '
import json, os, pathlib, time
root = pathlib.Path("/input/provider")
jid = os.environ.get("JOB_ID", "")
mounted = root.is_mount()
before = {p.name for p in root.iterdir()} if mounted else set()
rows = [line.split() for line in pathlib.Path("/proc/self/mountinfo").read_text().splitlines()]
rows = [r for r in rows if "-" in r and len(r) > r.index("-") + 1 and r[4] == str(root)]
fstype = rows[0][rows[0].index("-") + 1] if len(rows) == 1 else "UNKNOWN"
read_only = len(rows) == 1 and "ro" in rows[0][5].split(",")
if not (mounted and read_only and before == {"handoff-pending.json"} and len(jid) == 24):
    print(json.dumps({"schema":"storyforge_gold48_ro_live_cpu_probe_safe_v1","status":"HOLD","reason":"BASELINE_RO_MOUNT_HOLD","fstype":fstype,"gpu_started":False,"model_calls":0}), flush=True)
    raise SystemExit(2)
end = time.monotonic() + 120
while time.monotonic() < end:
    names = {p.name for p in root.iterdir()}
    if names == {"handoff-pending.json", "arrived.json"}:
        try:
            data = json.loads((root/"arrived.json").read_text())
            ok = data == {"schema":"storyforge_gold48_ro_live_arrived_synthetic_v1"}
        except (OSError, ValueError):
            ok = False
        print(json.dumps({"schema":"storyforge_gold48_ro_live_cpu_probe_safe_v1","status":"RO_NEW_FILE_VISIBLE_PASS" if ok else "HOLD","reason":"DYNAMIC_RO_READBACK" if ok else "ARRIVED_FILE_INVALID","fstype":fstype,"gpu_started":False,"model_calls":0}), flush=True)
        raise SystemExit(0 if ok else 2)
    if names != {"handoff-pending.json"}:
        print(json.dumps({"schema":"storyforge_gold48_ro_live_cpu_probe_safe_v1","status":"HOLD","reason":"UNEXPECTED_REMOTE_FILESET","fstype":fstype,"gpu_started":False,"model_calls":0}), flush=True)
        raise SystemExit(2)
    time.sleep(2)
print(json.dumps({"schema":"storyforge_gold48_ro_live_cpu_probe_safe_v1","status":"HOLD","reason":"REMOTE_CHANGE_NOT_VISIBLE","fstype":fstype,"gpu_started":False,"model_calls":0}), flush=True)
raise SystemExit(2)
'
```

**只在该 Job 已进入 RUNNING 且初始挂载存在后**，Owner Mac 使用保留的同一组 shell 变量立即上传第二份**纯合成**文件（不上传私有签名），不得覆盖原 pending：

```bash
printf '%s\n' '{"schema":"storyforge_gold48_ro_live_arrived_synthetic_v1"}' > "$LOCAL/arrived.json"
hf buckets cp "$LOCAL/arrived.json" "$BASE/arrived.json"
```

用 `hf jobs inspect <JOB_ID>` / `hf jobs logs <JOB_ID>` 读取 SAFE 结果，记录 `JOB_ID`、`status` 和 `fstype`。**验收条件**：Job `COMPLETED` 且 SAFE `RO_NEW_FILE_VISIBLE_PASS`、直接 RO mount、实际文件集精确；任一不满足则仅记录 HOLD，不提交第二个重复探针、不延长 GPU 等待时间。若 mount fstype 非 `fuse*`，即使内容变更可见，当前 Gold48 Worker 仍会拒绝，必须先审查这个真实差异，不要悄悄放宽文件系统检查。该 CPU 实测只签收挂载语义，不意味着任何 GPU/生成/Quality-v1 授权。

**Agent 不得自行发起这个跨 Actor CPU 测试**：聊天端没有 Owner Mac 的 `hf buckets cp` 上传通道；需要 Owner 在同一机器负责“Job 运行中外部上传”动作。完成前保持 `provider_handoff_live_mount_verified=false`。
