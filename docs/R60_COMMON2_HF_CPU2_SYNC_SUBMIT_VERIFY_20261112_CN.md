# StoryForge R60 — Common2 两条实验性SFT：复用R53 HF CPU真实Collator验收

> **2026-11-12 最新权威覆盖声明：Common2 CPU技术验收已PASS（优先于以下全部旧“IMAGE_FIX_HOLD/Collator未知”段落）。** 第五轮真实HF Job `6af570089737d9a9e093d501` 已 `COMPLETED`，Worker输出 `R60_CPU2_V2_REAL_COLLATOR_PASS__R50_TRAIN_HOLD`；已验证两条实验输入的Tokenizer、严格R18 Label Mask、实际ms-swift Collator。**不再执行下文任何旧Submit、重试、Stage重建命令**。当下只读验签既有SAFE回执、分析原生/Swift模板不等价、核验完整R50排除、形成Owner训练准入决策；`SOURCE_BOUND_DERIVED_CONTEXT_NOT_ACTUAL_SENT`、`native_template_token_parity_verified=false`、`r50_complete_exclusion_verified=false`、`train_admitted=0`、GPU/SFT HOLD。环境和可复用命令详见 [HF Jobs Mac CLI CPU2实战手册](standards/HF_JOBS_MAC_CLI_CPU2_PLAYBOOK_20261112_CN.md)。本覆盖声明只更新Common2，不替代其他Agent并行状态。\n\n
## 2026-11-12 权威交接状态（优先于本文所有较旧操作建议）

**最新Owner实际回执是 `R60_COMMON2_CPU2_IMAGE_FIX_HOLD` / `SAFE_REMOTE_OR_RUNTIME_HOLD`，不是“新Job成功提交”。** 已知首次HF CLI Job `6af53990ab34849891aecb44` 因镜像参数 `docker.io/--name` ERROR；随后SDK镜像修复仍HOLD，不能确认是否另建Job。**禁止直接执行本文件下文的旧 `submit` 或SDK重试命令、删除重试标记或重传原stage。** 接手者必须先只读运行`scripts/r60_common2_hf_cpu_image_probe.py`、核对HF Job真实列表和标记。权威任务书：[R60下一Agent接手任务书](R60_COMMON2_NEXT_AGENT_HANDOFF_20261112_CN.md)；[可复制启动提示词](R60_COMMON2_NEXT_AGENT_START_PROMPT_20261112_CN.md)。Common2质量PASS2、实验输入2、Tokenizer2552/4048 PASS；**Collator真实验收未知/未通过、R50全量隔离HOLD、train_admitted=0、GPU禁止。** Wave40已选40条位置，但盲审暂停，生产留证因无权限DEFERRED。


## 2026-11-12 镜像修复脚本SAFE_REMOTE_OR_RUNTIME_HOLD：先只读定位，禁止二次提交

Owner执行 `scripts/r60_common2_hf_cpu_image_retry.py` 返回 `R60_COMMON2_CPU2_IMAGE_FIX_HOLD`、`reason_code=SAFE_REMOTE_OR_RUNTIME_HOLD`。该统一代码可能对应API版本/权限/旧Job读取/状态字段/提交失败；**无法凭回执证明是否已发出新Job请求**。不允许直接重试、删除任何 `.cpu-submit-image-fix-attempted` 标记或重新同步冻结数据。

新增 `scripts/r60_common2_hf_cpu_image_probe.py`：只读确认本地27文件SHA256、已同步Bucket READY、旧Job是否实际为指定镜像解析ERROR、提交重试标记存在性，逐阶段仅发SAFE布尔状态及白名单原因；本脚本绝不调用run_job。

```bash
set -euo pipefail
cd "$HOME/workspace/storyforge-r60-4router-review"
HF_ENV="$HOME/.local/share/storyforge/venvs/hf-cli"
RUN_KEY="r60-common2-cpu2-20261112T032815Z-71c840b37254"
STAGE="$HOME/.local/share/storyforge/r60/hf-cpu2-stages/$RUN_KEY"
"$HF_ENV/bin/python" scripts/r60_common2_hf_cpu_image_probe.py \
  --run-key "$RUN_KEY" --stage "$STAGE" \
  --old-job 6af53990ab34849891aecb44
```

如果 `retry_marker=PRESENT`，必须先核实Owner HF Job列表是否新Job已创建；存在标记不是Job成功证据，但不能直接删除重试。若 `old_job=NOT_CHECKED`，先判断API/权限异常；若 `LOCAL_STAGE_HOLD` 或 `REMOTE_RUN_FILESET_HOLD`，核对源哈希和Bucket集合，不更改原始冻结数据。所有结果仍正式训练准入0、CPU-only、无GPU/训练。


## 2026-11-12：Job镜像解析失败，改用类型化SDK进行受控单次修复

Owner Mac真实 Job `6af53990ab34849891aecb44` 终态 **Error**：`Job image specification error: Invalid image name ... docker.io/--name`。CLI将原 `--name` 误识别为IMAGE，此次Worker尚未运行，无法把它记作Collator失败，也不得重跑同一CLI命令。

新脚本 `scripts/r60_common2_hf_cpu_image_retry.py` 不再从shell拼接 `hf jobs run` 位置参数，改用有名称的 `HfApi.run_job(image=..., command=..., volumes=..., namespace=..., flavor='cpu-upgrade')`，只允许固定原RUN_KEY和Job ID；先从Owner认证的HF API查明旧Job已经ERROR且消息确实包含镜像解析错误，再核对当前远端READY、27个Stage字节SHA256一致，使用 `cpu-submit-image-fix-attempted` 原子防重复标记，最多执行一次SDK调用，不改/重新上传数据、不中断其他Agent。

执行前确保已切换到含修复的GitHub固定HEAD，且CI通过；用独立HF CLI Python环境执行（既有项目Transformer环境不用升级），不要使用已经创建旧Job的 `submit` 模式：

```bash
set -euo pipefail
cd "$HOME/workspace/storyforge-r60-4router-review"
HF_ENV="$HOME/.local/share/storyforge/venvs/hf-cli"
RUN_KEY="r60-common2-cpu2-20261112T032815Z-71c840b37254"
STAGE="$HOME/.local/share/storyforge/r60/hf-cpu2-stages/$RUN_KEY"
"$HF_ENV/bin/python" scripts/r60_common2_hf_cpu_image_retry.py \
  --run-key "$RUN_KEY" --stage "$STAGE" \
  --old-job 6af53990ab34849891aecb44
```

成功返回 `R60_COMMON2_CPU2_IMAGE_FIX_JOB_SUBMITTED`及**新Job ID**，不是正式Collator PASS。若状态核实失败或重复提交标记已存在，安全HOLD，不能删除标记盲重试；请先只读核查旧Job及新Job状态。`HfApi.run_job`不需要Mac安装ms-swift/PyTorch，工作负载限定CPU-only，GPU/训练禁止。


## 2026-11-12 HF连接器403与Owner Mac执行路径

用户已明确授权当前已同步RUN_KEY的CPU-only Collator审核。ChatGPT HF连接器使用 `namespace=adradar`、`flavor=cpu-upgrade`、同一Worker与私有Bucket挂载提交时，HF API返回 **403 Forbidden**，未取得Job ID和成功回执，不能声称已启动；不自动重试连接器。Mac端已有可用的HF CLI及Bucket READY PASS，因此由Owner Mac提交。

当前项目的 `AGENTS.md §2.1` 已声明用户明确要求的CPU预检不需逐Job成本再授权。已从本轮R60 `submit.sh` 删除额外的付费授权变量，并保留远程READY、本地SHA256和一次性submit本地锁。

```bash
set -euo pipefail
cd "$HOME/workspace/storyforge-r60-4router-review"
HF_ENV="$HOME/.local/share/storyforge/venvs/hf-cli"
RUN_KEY="r60-common2-cpu2-20261112T032815Z-71c840b37254"
STAGE="$HOME/.local/share/storyforge/r60/hf-cpu2-stages/$RUN_KEY"
PATH="$HF_ENV/bin:$PATH" bash scripts/r60_common2_hf_cpu_submit.sh submit "$RUN_KEY" "$STAGE"
```

如HF CLI发生含糊错误，不得删除 `$STAGE.cpu-submit-attempted` 标记盲目重试，先用Mac `hf jobs ps --namespace adradar` 及远程日志确认是否已创建Job。此次仍只允许CPU真实Collator验证、禁止模型训练/GPU，训练准入为0。


## 2026-11-12 最新Owner决策：取消额外付费授权门禁，Common2 CPU2 已授权

Owner明确授权本次 `r60-common2-cpu2-20261112T032815Z-71c840b37254` 的HF CPU-only真实Collator验证，同时要求移除StoryForge额外“付费CPU需逐次再确认并通过环境变量批准”的工程约定。**本次授权已满足，正常执行 `submit` 无需 `STORYFORGE_ALLOW_PAID_CPU` / `STORYFORGE_R60_COMMON2_NO_TRAIN_ONLY`。** 保留`sync`与`submit`独立操作、仅CPU、无GPU、无训练、源文件SHA256绑定、远端文件集合严格验收及防重复提交标记；不扩大为任何模型训练、推理、未来收费工作或其他RUN_KEY的自动发起授权。

Owner刚确认 `R60_COMMON2_HF_CPU2_REMOTE_READY_PASS`、`R60_COMMON2_SYNC_READY__NO_JOB`：27个暂存文件已同步并完成集合校验，**无需重复sync或重建数据**。本轮使用同步时冻结的Worker源码；更新Mac本地 `submit.sh` 即可，不需要重新上传已有stage的内容。

Mac执行（确保本工作树已切换到含新`submit`代码的最新固定提交；使用原有的独立HF CLI venv）：

```bash
set -euo pipefail
cd "$HOME/workspace/storyforge-r60-4router-review"
HF_ENV="$HOME/.local/share/storyforge/venvs/hf-cli"
RUN_KEY="r60-common2-cpu2-20261112T032815Z-71c840b37254"
STAGE="$HOME/.local/share/storyforge/r60/hf-cpu2-stages/$RUN_KEY"
PATH="$HF_ENV/bin:$PATH" bash scripts/r60_common2_hf_cpu_submit.sh submit "$RUN_KEY" "$STAGE"
```

`submit`执行前会重复验证Bucket就绪和Stage SHA256，使用`$STAGE.cpu-submit-attempted`作为原子本地防重复提交标记。若CLI返回含糊的错误，**不要删除标记盲目重复计费**，先核查`hf jobs ps`和真实Job状态。不要在Mac装ms-swift/torch；不要上传R50保护集或启动GPU。


## 2026-11-12：Owner真实Stage 27文件PASS，远程前缀HOLD专项修复

Owner返回：`R60_COMMON2_HF_CPU2_STAGE_READY__NO_JOB`，`private_examples=2`、`files_staged=27`、`run_key=r60-common2-cpu2-20261112T032815Z-71c840b37254`，随后`R60_COMMON2_HF_CPU2_REMOTE_PREFIX_HOLD`。**这代表本地数据及源码已成功stage，但Bucket前缀检查没有通过；并不是Collator或数据的失败，未创建Job，也不能推断上传成功。** 通过HF Bucket只读列表检查，该RUN_KEY目录目前为空，仍须以Owner本地权限及接口核验为准。不能绕过fail-closed检查，不能重跑付费Job。

已修复`scripts/r60_common2_hf_cpu_bucket_guard.py`，保留严格HOLD的同时只输出 allowlist 的`R60_COMMON2_REASON_CODE`，区分`SDK_MODULE_MISSING`、`SDK_API_UNAVAILABLE`、`SDK_API_INCOMPATIBLE`、`REMOTE_AUTHORIZATION_HOLD`、`REMOTE_CONNECTION_HOLD`与其他验证问题。**所有异常原文/路径/私有IDs不输出。** 历史`hf` CLI可单独安装，Mac当前`python3`未必使用同一环境的`huggingface_hub`，故优先核实SDK兼容性，不能盲目修私有数据。

在最新版本代码上执行（**只检查，不上传、不创建Job**）：

```bash
set -euo pipefail
cd "$HOME/workspace/storyforge-r60-4router-review"
RUN_KEY="r60-common2-cpu2-20261112T032815Z-71c840b37254"
STAGE="$HOME/.local/share/storyforge/r60/hf-cpu2-stages/$RUN_KEY"
test -s "$STAGE/SHA256SUMS.txt"
python3 -m pytest -q tests/test_r60_common2_hf_cpu_stage.py
python3 scripts/r60_common2_hf_cpu_bucket_guard.py empty "$RUN_KEY" --stage "$STAGE"
```

若返回`R60_COMMON2_REASON_CODE=SDK_MODULE_MISSING`或`SDK_API_UNAVAILABLE`，优先检查`python3`是否可以访问包含`HfApi.list_bucket_tree`的`huggingface_hub`（无需Mac安装ms-swift/torch）；若是`REMOTE_AUTHORIZATION_HOLD`，检查当前HF认证身份与私有Bucket只读权限；若是`REMOTE_CONNECTION_HOLD`，检查Mac代理及到HF的网络。**不要在无法确定原因时更改Bucket或重建冻结数据。**

只有旧RUN_KEY真实前缀仍空，且本地源SHA256和新版guard都PASS时，才能复用旧stage，不重新产生私有源文件：

```bash
bash scripts/r60_common2_hf_cpu_submit.sh sync-existing "$RUN_KEY" "$STAGE"
```

`sync-existing`先执行本地sha256校验、远端empty校验、上传源文件和最后的SHA256SUMS，再执行远端ready文件集检查。**这一步只sync，不提交收费Job**。如果部分同步中断，远端非空时会拒绝重用运行键，须分析恢复策略，不能覆盖或删除远端证据。直到`R60_COMMON2_SYNC_READY__NO_JOB`明确输出之前不得执行`submit`。


2026-11-12。Owner明确：**不在Mac安装ms-swift或完整训练栈**；使用曾在R53/R27/R18中验证的HF CPU no-training流程。此处只准备脚本与Owner Mac指令，**当前未同步私有数据、未创建付费CPU Job，也未启动GPU**。

## 当前真实事实与边界

- 独立质量PASS2、103/243条持久化源历史已恢复，采用最近11条历史构造2条实验性SFT输入；原始实际发送System/世界卡并未验证。
- Owner已在Mac使用固定Qwen tokenizer revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` 对两条真实实验样本得到 **2552、4048** tokens；上限16384。
- Mac直接运行现有`--stage both`得到`COMMON2_CPU_TEMPLATE_AUDIT_HOLD`；此通用状态无法证明是输入问题，且**历史项目从未要求Mac安装完整ms-swift**。
- Wave40先前选好的40位置仍私有冻结、暂停盲审；完整R50隔离仍HOLD，`train_admitted=0`。

## 可复用程序

- `scripts/r60_common2_hf_cpu_stage.py`：Mac纯标准库，检查私有输入源文件权限及sha、2/2数据合同、目标仅最后assistant、训练准入0；递归收集实际脚本所依赖的本仓库Python模块，并强制官方`hf_label_mask_audit.py` Git blob保持`15296f1d8438f40d727c84913ac658cf6de01cb4`。构造**不覆盖**的0700私有stage文件夹及SHA256SUMS；没有外部调用。
- `scripts/r60_common2_hf_cpu_bucket_guard.py`：复用R53 read-only `HfApi.list_bucket_tree`，**确认远程新运行键不存在、同步后文件集合与本地manifest完全一致**；鉴权错误即拒绝，不能把空`hf buckets ls`返回码当作成功证据。
- `scripts/r60_common2_hf_cpu_submit.sh`：`sync`仅上传数据/代码与最后的hash清单，不启动Job；`submit`无需付费授权环境变量；保留远程文件集合校验、本地SHA256验收及每个RUN_KEY仅一次提交的本地持久标记。
- `scripts/r60_common2_hf_cpu_worker.sh`：仅`cpu-upgrade` Flavor、`CUDA_VISIBLE_DEVICES=\"\"`，先验证所有stage SHA256，再按R53成功依赖安装`ms-swift==4.5.3`、`transformers==5.16.1`，仅下载冻结Qwen tokenizer/config/模板**不下载模型权重**；将只读私有源复制到HF Job专属0700/0600目录，调用已有`r60_common2_sft_cpu_template_audit.py --stage both`，继续使用R18/R53真实`hf_label_mask_audit.py`检查`last_round`、最终Assistant-only Loss、真实Collator后标签。**不执行`swift sft`或任何训练**。仅向Bucket保存SAFE JSON和运行状态，不公开私有正文。

## Mac：先完成离线测试，再选择同步

使用已固定版本Owner工作树，不强制切换本地已被其他worktree占用的分支：

```bash
set -euo pipefail
cd "$HOME/workspace/storyforge-r60-4router-review"
git status -sb
python3 -m pytest -q tests/test_r60_common2_hf_cpu_stage.py

BASE="$HOME/.local/share/storyforge/r60/private"
INPUT_DIR="$BASE/r60-real1000-common2-sft-experimental11-v1"
test -f "$INPUT_DIR/R60_COMMON2_SFT_EXPERIMENTAL_MANIFEST_PRIVATE.json"
test -f "$INPUT_DIR/R60_COMMON2_SFT_EXPERIMENTAL_NOT_ADMITTED_PRIVATE.jsonl"
```

**这一步零远程调用；脚本本身不依赖Mac Transformers、Swift或Torch。**

### 1. `sync`：只同步私有Bucket，不创建任何Job

先通过Owner账户`hf auth whoami`确认权限。仅在Owner明确接受**将当前两条私有互动小说正文上传至现有受限Bucket**的情况下执行：

```bash
bash scripts/r60_common2_hf_cpu_submit.sh sync "$INPUT_DIR"
```

输出示例只包含新键与本地stage路径：

```text
R60_COMMON2_RUN_KEY=r60-common2-cpu2-...-...
R60_COMMON2_PRIVATE_STAGE_DIR=/Users/.../.local/share/storyforge/r60/hf-cpu2-stages/<RUN_KEY>
R60_COMMON2_SYNC_READY__NO_JOB
```

保存实际RUN_KEY和STAGE_DIR。**不要使用示例占位符作为真实运行键**。同步可能产生网络/存储费用，但不会启动计费计算。

### 2. `submit`：单独明确付费CPU批准后才执行

`cpu-upgrade`可能收费。只有Owner无需重复授权**这一次特定运行键**才使用下列命令：

```bash
RUN_KEY="前一步真实打印的键"
STAGE_DIR="前一步真实打印的本地stage目录"

bash scripts/r60_common2_hf_cpu_submit.sh submit "$RUN_KEY" "$STAGE_DIR"
```

此操作运行**单次**HF Job（`--flavor cpu-upgrade --timeout 120m`），属于计费资源；没有自动重试、没有GPU，超时是硬上限不是预计运行时长。

HF CLI会打印JOB_ID，保存后查看日志：`hf jobs logs -f adradar/JOB_ID`（必须以真实ID代替）。

### 3. 仅拉回SAFE验收回执

仅在Worker成功结束后：

```bash
RUN_KEY="真实运行键"
BASE="$HOME/.local/share/storyforge/r60/private"
D="$BASE/r60-common2-hf-cpu2-result-$RUN_KEY"
mkdir -m 700 "$D"
hf buckets cp \
 "hf://buckets/adradar/storyforge-training/preflight/r60/common2/cpu2/results/$RUN_KEY/R60_COMMON2_CPU2_SAFE_RECEIPT.json" \
 "$D/R60_COMMON2_CPU2_SAFE_RECEIPT.json"
chmod 600 "$D/R60_COMMON2_CPU2_SAFE_RECEIPT.json"
cat "$D/R60_COMMON2_CPU2_SAFE_RECEIPT.json"
```

目标严格为`COMMON2_CPU_TOKENIZER_COLLATOR_PASS__R50_TRAIN_HOLD`，须有`cases=2`、`collator_verified=true`、`r50_complete_exclusion_verified=false`、`train_admitted=0`。失败时不能改变窗口、覆盖冻结文件或自动重新计费；需先按SAFE阶段信息定位CPU-only错误。

## 后续真正门禁

远程Collator成功仅意味着**技术格式通过**，不是准许SFT。继续完成**完整R50受保护故事、会话、消息源隔离**（五个已知故事不足以替代全量）；确认世界/角色信息不足问题；之后再由Owner另行决定是否准入和是否启动GPU。**Wave40保留待审，但不是此次验收的一部分。**
