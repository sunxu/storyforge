# StoryForge R60 — Common2 冻结通用System包装后的HF CPU质量流水线门禁

2026-11-12。**代码已准备；尚无新HF Job、无包装后真实Collator PASS、无数据入训/GPU许可。**
仅作用于 Common2 已质量审核PASS的**两条实验候选**，不扩样、不接触R50正文，不用生产数据库。Owner真实SAFE此前证实原始无System输入与冻结R27/R52通用System的内存包装PASS2/2、源目标未改变；这仍不是新增System后的实际Qwen/Swift Tokenizer/Collator验收。

## 与Quality Pipeline / Skill的关系

- `skills/storyforge-roleplay-sft/SKILL.md` 负责 SOURCE / ISOLATION / STRUCTURE / QUALITY / FREEZE / TRAINING 独立门禁。已PASS的独立质量审查不等于新包装输入已正式训练准入。
- `skills/storyforge-hf-jobs/SKILL.md` 负责HF Job doctor→合成测试→只读/写隔离→远端单次CPU→SAFE回收。优先复用`src/storyforge_dataset/hf_runtime/`公共`InputManager`/`OutputManager`/`ResourceGuard`、`scripts/hf_job_guard.py`、已有严格R18 `hf_label_mask_audit.py` 和真实Swift业务Collator适配器。
- Gold Quality Pipeline只登记技术预检作为`TRAINING`工程证据，不自动追加文学`QUALITY_PASS`或把`quality_v1_admitted`提高；不写入逐案Review或Owner私有crosswalk。与 `docs/standards/GOLD_QUALITY_PIPELINE_CN.md` 独立。
- 已成功的Common2无System CPU2 Job `6af570089737d9a9e093d501` 作为参考**不重跑**；本次改了System，原Token计数不能复用。

## 工程输入输出合同

- 源：Owner 现有`$HOME/.local/share/storyforge/r60/private/r60-real1000-common2-sft-experimental11-v1/`，其中冻结JSONL与manifest不改。
- 通用System：原R27/R52明示合成训练指令，449 UTF-8 bytes，SHA256 `5e1b28cd9181f5d334f1f10a54a251f9255e655a3e597519c7cfcc530d8c5e83`；不是历史真实sent请求。
- Model：`Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`，只下载所需JSON/Jinja/Tokenizer/Processor文件，禁止`*.safetensors`、`*.bin`和GPU。
- 真正运行的配置：`ms-swift==4.5.3`、`transformers==5.16.1`、`tokenizers==0.23.3`，`qwen3_8`、`last_round`、`max_length=16384`、`add_non_thinking_prefix=false`。基础PyTorch镜像、decord CPU警告等沿用成功CPU2实践，固定镜像 manifest SHA，版本与上一轮实测相同；**不宣称传递依赖已经hash-lock**。
- Mac创建唯一私有0700 Stage，文件0600；`SHA256_MANIFEST_PRIVATE.json`包含本批代码与源输入字节指纹，不提交GitHub、不打印SHA。远端挂载Stage**RO**到`/input/common2`，独立结果前缀**RW**到`/output`，`hf_job_guard`保证组织`adradar`、单次尝试、CPU flavor、120min上限、无自动个人namespace回退。
- 远端工作器通过`ResourceGuard.check_cpu_only`拒绝GPU，`InputManager.open_verified`验收Stage字节，临时scratch内构造System包装，复用R18严格最后Assistant监督审核与Swift真实Collator。输出唯一`/output/R60_COMMON2_WRAPPED_CPU_SAFE_RECEIPT.json`由`OutputManager.write_safe` create-only发布；不写训练JSONL，不调用模型推理。
- 成功业务状态`R60_COMMON2_WRAPPED_HF_CPU_COLLATOR_PASS__TRAIN_HOLD`，其独立Owner验收状态`WRAPPED_CPU_RECEIPT_ACCEPTED__TRAIN_HOLD`。任一步失败HOLD，Job显示COMPLETED不等于PASS。
- 所有技术SAFE仍要求`r60_input_design_approved=false`、`deployment_template_compatibility_verified=false`、`semantic_world_isolation_verified=false`、`quality_v1_admitted=0`、`train_admitted=0`、`gpu_started=false`。

## 可复用目录结构

- `scripts/r60_common2_wrapped_hf_stage.py`：Stage `prepare/verify`，自动收集本次业务适配器的本地import依赖与公共Runtime代码，所有文件版本冻结，Hash Manifest末尾创建；不复制通用Tokenizer算法。
- `scripts/r60_common2_wrapped_hf_cli.py`：Stage `preflight/sync/ready/submit --execute`，同步manifest最后上传；READY验证远端文件集合/结果EMPTY和全量Job历史、CLI dry-run；submit前O_EXCL创建尝试标记，失败也不覆盖和不重试。
- `scripts/r60_common2_wrapped_hf_worker.sh`：固定CPU镜像Python 3.11环境依赖安装，禁止推理/GPU；日志压制，仅公开SAFE结果。
- `scripts/r60_common2_wrapped_hf_worker.py`：共享Runtime与真正Wrapped Swift业务审计；
- `scripts/r60_common2_wrapped_hf_receipt_verify.py`：Owner只读SAFE业务回执校验，保守限定计数、schema、status、模型revision与未授权标记；
- `tests/test_r60_common2_wrapped_hf_pipeline.py`：Stage immutable/SHA tamper、CLI只用CPU与RO/RW、回执完整性和隐私。
- 真实Tokenization仍在HF CPU上执行，不在Owner Mac上执行。代码适用于两条Common2，但Stage/Job基础设施可复用到后续质量流水线的其他批次；新批次须单独适配源Schema、数目、审核准入及输出，不能绕过固定2条检查。

## Mac实际执行（Owner端，按顺序）

```bash
set -euo pipefail
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
git status --short

export PATH="/opt/homebrew/bin:$PATH"
export PYTHONPATH="$PWD/src"
PY="$HOME/.local/share/storyforge/venvs/r60-tests/bin/python"
SDKPY="$HOME/.local/share/storyforge/venvs/hf-cli/bin/python"
"$PY" -m storyforge_dataset.hf_runtime doctor --profile cpu --json
"$PY" -m pytest -q tests/test_r60_common2_wrapped_hf_pipeline.py \
  tests/test_r60_common2_wrapped_system_cpu_audit.py
"$PY" -m compileall -q scripts/r60_common2_wrapped_hf_*.py
# 测试仍应先跑Ruff、Runtime/Volume与token_preflight回归；详见两个Skill
```

**仅在本地所有测试和相应CI均绿后**新建私有Stage；请勿重新建立旧的CPU2 Stage：

```bash
BASE="$HOME/.local/share/storyforge/r60/private"
RUN_KEY="r60-common2-wrapcpu-$(date -u +%Y%m%dT%H%M%SZ)-$(openssl rand -hex 6)"
STAGE_ROOT="$BASE/hf-wrapped-cpu-stages"
mkdir -p "$STAGE_ROOT"
chmod 700 "$STAGE_ROOT"
STAGE="$STAGE_ROOT/$RUN_KEY"
INPUT="$BASE/r60-real1000-common2-sft-experimental11-v1"
"$PY" scripts/r60_common2_wrapped_hf_stage.py prepare \
 --input-dir "$INPUT" --run-key "$RUN_KEY" --stage "$STAGE"
"$PY" scripts/r60_common2_wrapped_hf_stage.py verify \
 --run-key "$RUN_KEY" --stage "$STAGE"
"$PY" scripts/r60_common2_wrapped_hf_cli.py preflight \
 --run-key "$RUN_KEY" --stage "$STAGE"
```

同步和远端准备检查（以下命令**仅准备，不提交CPU Job**）：

```bash
# 使用已接入组织Bucket的HF CLI2.4.0和隔离HF SDK venv；如有外部依赖故障先HOLD
"$SDKPY" scripts/r60_common2_wrapped_hf_cli.py sync \
 --run-key "$RUN_KEY" --stage "$STAGE"
"$SDKPY" scripts/r60_common2_wrapped_hf_cli.py ready \
 --run-key "$RUN_KEY" --stage "$STAGE"
```

以上均SAFE/CI PASS之后，Owner执行**仅一次付费HF CPU**（本项目Skill已允许最小必要CPU，不授权GPU）。用户可选择在准备完成后立即运行；本Agent不在没有Mac私有源和本地HF CLI会话时替用户提交：

```bash
"$SDKPY" scripts/r60_common2_wrapped_hf_cli.py submit \
 --run-key "$RUN_KEY" --stage "$STAGE" --execute
```

记录返回`job_id`，再用`hf jobs inspect <job_id>`（以安装版本`hf jobs --help`为准）查看**COMPLETED**；即使显示COMPLETED，也必须回收最新SAFE私有文件并验证：

```bash
RECEIPT_DIR="$BASE/hf-wrapped-cpu-receipts/$RUN_KEY"
mkdir -p "$RECEIPT_DIR"
chmod 700 "$RECEIPT_DIR"
REMOTE="hf://buckets/adradar/storyforge-training/preflight/r60/common2/wrapped-cpu/results/$RUN_KEY/R60_COMMON2_WRAPPED_CPU_SAFE_RECEIPT.json"
RECEIPT="$RECEIPT_DIR/R60_COMMON2_WRAPPED_CPU_SAFE_RECEIPT.json"
test ! -e "$RECEIPT"
hf buckets cp "$REMOTE" "$RECEIPT"
chmod 600 "$RECEIPT"
"$PY" scripts/r60_common2_wrapped_hf_receipt_verify.py \
 --run-key "$RUN_KEY" --receipt "$RECEIPT"
```

如需确认回收回执字节未在传输中变化，必须独立从远端读取元数据/下载重验并在Owner私有台账做SHA绑定，不能靠业务回执自证HF Job与输入字节逐字节绑定。禁止将私有清单SHA、私人回执JSON或正文上传Git。

## 停机与主线衔接

这一步只是 Quality Pipeline 的**TRAINING阶段CPU工程门禁**，不是文学审核，也不重新开展R50源隔离/全文语义判断。包装后PASS仍不证明历史R46 System原文字节与新通用System完全一致或实际部署模板一致。下一阶段Owner单独决策D1衍生输入资格、D2统一训练包装政策、D3部署输入合同、D4相关世界语义隔离、D5正式Train/Val发布与GPU训练许可。任何失效保持HOLD，旧Stage/Job/回执保留原样，不重试同RUN_KEY。

## 2026-11-12 Ruff静态检查修正（Owner贴回日志30项）

Owner Mac运行`ruff check scripts/r60_common2_wrapped_hf_*.py tests/test_r60_common2_wrapped_hf_pipeline.py`曾返回**30个静态检查问题**：`I001` import块排序、`RUF100` 未启用E402时多余`noqa`、`PLW1510` subprocess调用未明确`check=False`、`BLE001` SAFE保护所需异常兜底缺少逐处说明。已对所列4个业务Python和1个合成测试文件做最小修复：显式`check=False`依然根据returncode判断失败；保留隐私异常边界并在具体`except Exception`加`# noqa: BLE001`及原因；删多余E402 directive和排序import。**未关闭Ruff规则、未改CPU提交/RO-RW/模型模板/入训策略。** 最新代码尚待Owner复跑lint和pytest，不可宣称已全PASS。遇到剩余错误按实际日志修正，不提交新HF CPU Job直到测试及CI均绿。

复测：
```bash
set -euo pipefail
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
ruff check scripts/r60_common2_wrapped_hf_*.py tests/test_r60_common2_wrapped_hf_pipeline.py
PY="$HOME/.local/share/storyforge/venvs/r60-tests/bin/python"
"$PY" -m pytest -q tests/test_r60_common2_wrapped_hf_pipeline.py tests/test_r60_common2_wrapped_system_cpu_audit.py
bash -n scripts/r60_common2_wrapped_hf_worker.sh
```

## 2026-11-12 Owner真实Stage已PASS、远端编排HOLD定位修复

Owner SAFE：`run_key=r60-common2-wrapcpu-20261112T122746Z-5a612325db98`；现有Stage `$HOME/.local/share/storyforge/r60/private/hf-wrapped-cpu-stages/$RUN_KEY`已独立哈希检验44文件（包括2个私有源），`WRAPPED_CPU_STAGE_VERIFIED__NO_JOB`、`hf_jobs_submitted=0`、`train_admitted=0`。随后Owner的`sync`和`ready`均返回`WRAPPED_CPU_ORCHESTRATION_HOLD / SDK_OR_RUNTIME_HOLD`；这**不能证明**哪一步SDK/认证/远端状态发生故障，也**不能据此证明远端为空**。不得为排错新建Stage、重试上传、改写旧Stage或提交CPU。

修正业务CLI错误码：原`main()`遗漏了`REMOTE_PATH_HOLD`/`REMOTE_LIST_HOLD`分类，并将来自HF SDK的AttributeError/TypeError/HTTP/连接错误概括为`SDK_OR_RUNTIME_HOLD`；新`classify_safe_failure`复用原已成功的`r60_common2_hf_cpu_bucket_guard.classify_failure`，保持异常内容不泄露。新增显式`diagnose`（纯只读）分别检查已验签本地Stage、SDK初始化、远端input目录条目集合、output目录是否为空和本地尝试marker；不复制/上传/删除任何文件，不调用Job提交API；遇到故障只返回固定阶段`phase`和allowlisted安全分类。新合成测试覆盖远端部分Stage、SDK异常、非法返回路径。**新代码仍待Owner本机实测，不声称远端恢复**。

Owner Mac只读下一步（沿用原RUN_KEY；先别执行`sync/ready/submit`）：
```bash
set -euo pipefail
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-tests/bin/python"
SDKPY="$HOME/.local/share/storyforge/venvs/hf-cli/bin/python"
"$PY" -m pytest -q tests/test_r60_common2_wrapped_hf_pipeline.py
ruff check scripts/r60_common2_wrapped_hf_*.py tests/test_r60_common2_wrapped_hf_pipeline.py
KEY="r60-common2-wrapcpu-20261112T122746Z-5a612325db98"
STAGE="$HOME/.local/share/storyforge/r60/private/hf-wrapped-cpu-stages/$KEY"
"$SDKPY" scripts/r60_common2_wrapped_hf_cli.py diagnose --stage "$STAGE" --run-key "$KEY"
```
成功时可只读报告 `remote_input=EMPTY|PARTIAL_OR_MISMATCH|READY_FILESET`、`remote_output=EMPTY|NONEMPTY`、`submit_marker=ABSENT|PRESENT`；如果在某个阶段HOLD，将`phase`和`reason_code`用于后续针对性修复。**如果出现PARTIAL或READY，绝不继续执行只能同步EMPTY前缀的sync命令，优先核对远端来源完整性。** 原Stage不可覆盖。只有远端精确READY+输出EMPTY+marker ABSENT，CI与业务预检全部PASS后才能继续正式dry-run和CPU提交。

## 2026-11-12 Owner Mac本地旧CLI与剩余Ruff I001

Owner返回：Ruff仅剩 `scripts/r60_common2_wrapped_hf_worker.py` 和 `tests/test_r60_common2_wrapped_hf_pipeline.py` 两条 `I001`（前者需要两组import之间一个空行，后者需要移除多余空行）。已最小修正，不改HF逻辑。Owner调用`diagnose`时报 `invalid choice: 'diagnose'`，而远端Owner分支当前源码已明示`choices=["preflight", "sync", "ready", "submit", "diagnose"]`，证明调用的本地源码不是最新已提交版本，**不是HF SDK失败证据**。需要核对目标worktree/branch/HEAD、合并是否成功、本地脚本实际路径与GitHub一致；不覆盖本地私有Stage，且不继续`sync/ready/submit`。

```bash
set -euo pipefail
cd ~/workspace/storyforge-r60-4router-review
pwd
git status --short
git branch --show-current
git rev-parse --short HEAD
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
grep -n 'choices=.*diagnose' scripts/r60_common2_wrapped_hf_cli.py
ruff check scripts/r60_common2_wrapped_hf_*.py tests/test_r60_common2_wrapped_hf_pipeline.py
PY="$HOME/.local/share/storyforge/venvs/r60-tests/bin/python"
"$PY" -m pytest -q tests/test_r60_common2_wrapped_hf_pipeline.py
SDKPY="$HOME/.local/share/storyforge/venvs/hf-cli/bin/python"
KEY="r60-common2-wrapcpu-20261112T122746Z-5a612325db98"
STAGE="$HOME/.local/share/storyforge/r60/private/hf-wrapped-cpu-stages/$KEY"
"$SDKPY" scripts/r60_common2_wrapped_hf_cli.py diagnose --stage "$STAGE" --run-key "$KEY"
```

如 `git merge --ff-only` 报错（分叉或未提交工作），**停止**，先检查差异/工作树状态，不执行`git reset --hard`、不`stash`掉其他Agent工作。若 `grep`匹配失败，不要运行后续诊断命令。该只读诊断不提交HF Job，实际远端状态须由新SAFE回执决定。

## 2026-11-12 STAGE_VERIFY先于SDK：本地解释器差异与固定失败码修正

Owner最新真实只读诊断返回`phase=STAGE_VERIFY`、`reason_code=SDK_OR_RUNTIME_HOLD`、`remote_input=UNKNOWN`、`remote_output=UNKNOWN`；**此处尚未初始化HfApi，也没查询远端**。此前Stage的44个文件使用`r60-tests`环境验证PASS，此诊断使用`hf-cli`环境。原因尚未确认：可能是两套Python环境使用不同包/SDK、Stage源字节发生变化、文件打开错误或诊断分类遗漏，不应把它推断为HF授权问题。

本次把Stage/共享InputManager的固定异常码（例如`INPUT_SHA256_MISMATCH`、`INPUT_OPEN_FAILED`、`STAGE_FILES_HOLD`、`INPUT_JSON_INVALID`）纳入诊断SAFE分类，仍不输出原始异常、私有路径或私有SHA；单测覆盖Stage失败和未知异常不泄露。**现有Stage不改、不复制、不重建，不重新sync、ready或submit。**

Owner使用相同代码、相同Stage，在两个Python解释器分别运行纯本地Stage验证，并核对`diagnose`是否继续停在同一阶段：

```bash
set -euo pipefail
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
KEY="r60-common2-wrapcpu-20261112T122746Z-5a612325db98"
STAGE="$HOME/.local/share/storyforge/r60/private/hf-wrapped-cpu-stages/$KEY"
PY="$HOME/.local/share/storyforge/venvs/r60-tests/bin/python"
SDKPY="$HOME/.local/share/storyforge/venvs/hf-cli/bin/python"
ruff check scripts/r60_common2_wrapped_hf_*.py tests/test_r60_common2_wrapped_hf_pipeline.py
"$PY" -m pytest -q tests/test_r60_common2_wrapped_hf_pipeline.py
"$PY" scripts/r60_common2_wrapped_hf_stage.py verify --stage "$STAGE" --run-key "$KEY"
"$SDKPY" scripts/r60_common2_wrapped_hf_stage.py verify --stage "$STAGE" --run-key "$KEY"
"$SDKPY" scripts/r60_common2_wrapped_hf_cli.py diagnose --stage "$STAGE" --run-key "$KEY"
```

**解释顺序：** 若仅SDKPY的Stage验证失败，先诊断本地Python版本、加载路径及共享Runtime兼容，不执行远端操作；若两者都失败，优先对比原Stage未动源字节和清单（私有哈希不外发）；若两者均PASS才查看新`diagnose`远端SAFE。如新版仍笼统HOLD，保留phase并进一步添加允许字段的边界测试，禁止打印异常正文。成功`Stage VERIFY`只是文件字节合同一致，不批准训练。
