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
