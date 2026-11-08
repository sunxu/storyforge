# R60 HF Quality：1000 条 A/B Stage 实测 PASS → HF CPU Tokenizer 预检（2026-11-08）

> **防止重复付费排障（2026-11-08）**：R58 于 2026-11-01 已真实验证 `transformers==4.57.1`、`sentencepiece==0.2.1`、`jinja2==3.1.6`。本轮 R60 最初遗漏 Jinja2，导致 A v3 CPU Job `6af042680e0338d1bb84a276` 的 Chat Template `ImportError`。实际根因仍需新容器验证，但以后不能跳过现有 [HF Tokenizer 共享规范](standards/HF_TOKEN_PREFLIGHT_REUSE_CN.md) 的依赖基线。正式 HF Job 提交前先核验本地 CLI `--check-hf-cli`、原生 `--dry-run`；容器内先 `pip check`、再做 Jinja2/sentencepiece import probe，随后才可读取冻结 input 和启动 CPU Tokenizer。原 Jinja2-fix 任务名/输出目录和命令见 [A 故障修复](R60_HF_CPU_JOB_A_FAILURE_DIAGNOSTIC_20261108_CN.md)，不可重用旧失败的输出前缀。

## 已由 Owner Mac 实际确认

- 原冻结池：1000/1000，原 6 条 Seed + 新增 994，20 私有扩样页，400 Story；未修改原数据
- `r60_hf_quality_adapter.py prepare` → `HF_QUALITY_BLIND_STAGE_READY__NOT_SUBMITTED`，`cases_staged=1000`，A/B 两槽
- `r60_hf_quality_adapter.py audit` → `HF_QUALITY_DUAL_PARTIAL__NO_ADMISSION`，`complete_pairs=0`，`model_a_reviewed=0`，`model_b_reviewed=0`，`HOLD=1000`、`PASS=0`、`REJECT=0`
- Owner crosswalk **未上传**；GPU 未提交；没有实际评分或训练准入；R50 / world 仍 HOLD
- 模型 A `Qwen/Qwen3-32B@9216db5781bf21249d130ec9da846c4624c16137`
- 模型 B `zai-org/GLM-4-32B-0414@077b5c2f5c43bd3239fd605a0600229e8facbd4a`

**1000 HOLD 表示未收到审核结果，不代表模型判定 1000 条质量不合格。**

## 为什么要使用有守卫的项目 Bucket，而不是直接 -v 本地目录

HF 现行 CLI 的 `-v "$STAGE/input_A:/input:ro"` 会先隐式同步该本机目录到私有 `jobs-artifacts` Bucket。它虽然可用，但不符合仓库 `AGENTS.md`、`docs/HF_JOBS.md` 及 `scripts/hf_job_guard.py` 强制的项目存储策略。统一使用 `hf://buckets/adradar/storyforge-training` 下全新精确子目录，明确 RO 输入与不同 RW 输出，不切换个人 Namespace。

**隐私告知**：接下来的 `hf buckets sync` 会将 A/B 盲审包中的三条历史消息和目标真实正文发送到 HF 私有存储；盲 ID 不意味着正文匿名。必须只同步 `input_A`、`input_B`，**绝不能同步整个 `STAGE` 或 `STAGE/owner`**。本次工具或仓库提交没有执行任何上传。

## Owner Mac 第 1 步：本地核验并明确上传范围

在 StoryForge 仓库根目录，使用以前成功的 Owner Mac HF CLI 账号：

~~~bash
set -euo pipefail
set +x
umask 077
BASE="$HOME/.local/share/storyforge/r60/private"
EXPAND="$BASE/r60-expand-first-600"
STAGE="$BASE/r60-hf-quality-first-1000"

python3 - <<'PY'
from pathlib import Path
pins = {
    "transformers==4.57.1",
    "sentencepiece==0.2.1",
    "jinja2==3.1.6",
    "huggingface_hub>=0.35,<3",
}
declared = {
    line.strip() for line in Path("requirements/hf-quality-reviewer.in").read_text().splitlines()
    if line.strip() and not line.lstrip().startswith("#")
}
if not pins.issubset(declared):
    raise SystemExit("R60_REVIEWER_DEPENDENCY_PROFILE_HOLD")
print("R60 reviewer dependency source profile: PASS")
PY

hf auth whoami
python3 -m storyforge_dataset.hf_runtime doctor --profile cpu --json
python3 experiments/r58_quality/r60_hf_quality_adapter.py audit \
  --expand-dir "$EXPAND" --stage-dir "$STAGE"

for SLOT in A B; do
  test -f "$STAGE/input_$SLOT/source.private.jsonl"
  test -f "$STAGE/input_$SLOT/runner.py"
  test -f "$STAGE/input_$SLOT/token_core.py"
  test -f "$STAGE/input_$SLOT/runtime_inputs.py"
  test -f "$STAGE/input_$SLOT/runtime_resources.py"
  test -d "$STAGE/output_$SLOT"
done
test -f "$STAGE/owner/owner_crosswalk.private.json"
test -f requirements/hf-quality-reviewer.lock
LOCK_SHA="$(shasum -a 256 requirements/hf-quality-reviewer.lock | awk '{print $1}')"
for SLOT in A B; do
  install -m 600 requirements/hf-quality-reviewer.lock \
    "$STAGE/input_$SLOT/hf-quality-reviewer.lock"
done
echo "R60_REVIEWER_LOCK_SHA256=$LOCK_SHA"
~~~

这里仅向 A/B 输入目录增加公开、hash-pinned 的依赖锁文件；不改写 `source.private.jsonl`、Runner、Token Core、Runtime 文件或 Owner crosswalk。后续同步会一并上传该锁文件。

再次确认上述 `audit` 的 `cases_total=1000`、`complete_pairs=0`。测试通过后，根据实际 HF 账号组织权限，为本轮创建**唯一的新远端前缀**；不要复用旧 R59/R58 Jobs 或测试输出。

## Owner Mac 第 2 步：显式同步两个独立私有输入到 adradar 项目 Bucket

以下命令执行时，**确实上传私有故事正文到 HF**。只同步两个 `input_*` 目录；不传 Owner 身份映射、不传输出/其它项目文件。

~~~bash
RUN_ID="r60-quality-cpu-$(date -u +%Y%m%dT%H%M%SZ)"
BUCKET="hf://buckets/adradar/storyforge-training"
INROOT="$BUCKET/quality-review/r60/$RUN_ID"

hf buckets sync "$STAGE/input_A" "$INROOT/input_A"
hf buckets sync "$STAGE/input_B" "$INROOT/input_B"
~~~

`RUN_ID`、`BUCKET` 和 `INROOT` 保留在当前 Shell（断开终端后需重新设置相同 RUN_ID），这样后续所有 Job 证据绑定同一来源。同步失败立即 HOLD，不切换 Namespace、不扩大权限、不运行 GPU。

## Owner Mac 第 3 步：仅构造/验证 HF CPU Job 提交规格

按照仓库标准，所有 CPU Job 由已有 `scripts/hf_job_guard.py` 提交。这个 Guard 默认只检查参数，**不提交 Job**，而且要求同时指定私有 RO input 和独立 RW output。下列循环仅输出 `PREFLIGHT_PASS_NOT_SUBMITTED` 或 SAFE HOLD：

~~~bash
for SLOT in A B; do
  case "$SLOT" in
    A) MODEL="Qwen/Qwen3-32B"
       REV="9216db5781bf21249d130ec9da846c4624c16137" ;;
    B) MODEL="zai-org/GLM-4-32B-0414"
       REV="077b5c2f5c43bd3239fd605a0600229e8facbd4a" ;;
  esac

  CMD="set -eu
export CUDA_VISIBLE_DEVICES=''
export TOKENIZERS_PARALLELISM=false
test "$(sha256sum /input/hf-quality-reviewer.lock | awk '{print $1}')" = '$LOCK_SHA'
python3 -m pip install --quiet --no-cache-dir --require-hashes -r /input/hf-quality-reviewer.lock
python3 -m pip check
python3 -c 'import transformers, jinja2, sentencepiece; assert transformers.__version__ == "4.57.1"; assert jinja2.__version__ == "3.1.6"; assert sentencepiece.__version__ == "0.2.1"; print("R60 reviewer dependency baseline: PASS")'
echo HF_TOKEN_DEPS_PASS
test -f /input/source.private.jsonl
python3 /input/runner.py --input /input/source.private.jsonl \
  --output-dir /output --model '$MODEL' --revision '$REV' \
  --token-preflight-only --max-model-len 32768 --max-output-tokens 2400"

  python3 scripts/hf_job_guard.py \
    --namespace adradar \
    --name "r60-quality-cpu-$SLOT-$RUN_ID" \
    --flavor cpu-basic \
    --timeout-minutes 45 \
    --input-volume "$INROOT/input_$SLOT:/input:ro" \
    --output-volume "$INROOT/cpu-output-$SLOT:/output:rw" \
    --image python:3.11 \
    -- /bin/sh -lc "$CMD"
done
~~~

检查两条返回均为 `PREFLIGHT_PASS_NOT_SUBMITTED`，`gpu_allowed=false`，RO/RW 约束 PASS。

## 第 4 步：确认上传内容与权限后，只提交 CPU Tokenizer Job

如已确认私有数据上传范围与上述 Job 规格，并已满足组织 CPU 运算权限，可将第 3 步循环中的 `python3 scripts/hf_job_guard.py` 参数增加 **`--submit`** 再运行。它只允许 `cpu-basic` / `cpu-upgrade`，不可能升级为 GPU；不会提交训练。每个 Slot 独立新 Job，不自动重试。

**注意：** 它会实际使用付费 HF CPU 并执行 1000 行模型 Tokenizer / Chat Template 预检；没有模型推理。模型 Revision/Transformers 版本不兼容、CPU 内存不足、CPU Profile 违规或 45 分钟超时必须 HOLD，不要自动改为 GPU。

预期成功 SAFE 为：
- `schema=storyforge_hf_literary_safe_v1`
- `status=HF_REVIEW_CPU_TOKEN_PREFLIGHT_PASS__NO_GPU`
- `cases_checked=1000`
- `over_budget_count=0`，`gpu_started=false`，`training_authorized=false`

GPU 是否可用、两模型是否支持 vLLM JSON 结构化输出、镜像版本与依赖一致性，**不由 CPU Tokenizer PASS 证明**，仍须单独校准及明确预算授权。

## 后续：结果与 Quality-v1

依照 `docs/R60_HF_QUALITY_PIPELINE_REUSABLE_1000_CN.md`，之后是 A/B 各 5 条 GPU 校准（额外授权）→ 验证私有 checkpoints / 精确原文引文 → 批量审核 → Owner 私有 A/B 导出 → 既有 `storyforge-gold-quality append-review` 导入 → R50 全集元数据排除/world 隔离 → 训练数据冻结/CPU ms-swift Collator → GPU SFT 独立审批。

本文件只准备执行指导；**本次报告没有提交 HF CPU/GPU Job，没有同步任何 Owner 私有输入，也没有产生真实文学评分**。
