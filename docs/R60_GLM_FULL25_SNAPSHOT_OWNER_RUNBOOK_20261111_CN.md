# R60 GLM 完整25条 Snapshot 生成：Owner Mac 执行手册

> **2026-11-11 新 Agent 交接权威入口：** [R60 GLM 全25下一 Agent 任务书](R60_GLM_FULL25_NEXT_AGENT_HANDOFF_20261111_CN.md)。本手册只负责 Owner Mac 命令与执行操作；当前方案是 **独立全25条一次生成**、`--full25` CPU 回放，**不允许**恢复1–2条试跑或失败12条重试。本手册的执行代码 PIN 固定为 `6f2a71f12f3a2408b4082d6f8b86e69e0b5cf384`；更新文档不意味着 GPU 已运行。最新 GitHub 状态由接手 Agent 重新核实。


本轮 Owner 明确要求取消1~2条限制，直接生成完整25条原始 GLM B25 输入。此次是独立25条全量重审，而非12条失败样本子集重试。旧的13 VERIFIED/12 TECHNICAL_FAILURE 历史回执不可覆盖；新运行独立保存完整原始文本 Snapshot 和新的 Checkpoint/技术回执。

代码固定提交：6f2a71f12f3a2408b4082d6f8b86e69e0b5cf384。模型：zai-org/GLM-4-32B-0414；revision 8dea913c41b543527c2860fb6f3c15c202f24aeb；输入25条 SHA 01639568cf21a7b98356f2b3b74f567943b4a6844edb9230b58759789ab67fc9。

## 2026-11-11 核验修复：全量模式与旧 probe 守卫冲突

旧提交 `77da8093c831a6cb3771385b1c673ffb82143529` 虽然四组 CI PASS，仍有参数冲突：`--snapshot-full25` 要求不传 `--snapshot-probe-cases`，但旧守卫只要有 Snapshot 目录且 probe=0 就拒绝，导致真实 H200 在加载前 `SNAPSHOT_PROBE_SCOPE_HOLD`。现已修改条件为 `and not args.snapshot_full25`，并增加 AST 执行式 CPU 回归验证全量/旧 probe 双路径。**旧 PIN 已废弃，不得拿它提交 H200。**

全量25条运行会在冻结 Runner 技术异常时继续保存签名技术失败回执；如果模型生成/快照写入出现非预期错误，可能提前停止，不能宣称25份 Snapshot 已保存。CPU Replay 的 `--full25` 可以读取完整或连续的部分前缀；只有 `replayed_cases=25` 且生成回执另行核验25/25，才算完整运行验收。

新 Agent 接手时请先读[权威全25交接任务书](R60_GLM_FULL25_NEXT_AGENT_HANDOFF_20261111_CN.md)，并使用[新 Agent 启动提示词](R60_GLM_FULL25_NEW_AGENT_PROMPT_20261111_CN.md)。


## 新 Agent 交接用：可复制的 Owner Mac 准备与运行命令（尚未执行）

**本节仅用于交接**：写出命令不等于执行过 Owner Mac CPU 预检或提交付费 H200。接手 Agent 必须核实 GitHub 实际状态、Owner Mac 私有路径和权限，再由 Owner 自行操作。运行代码以本手册的固定 PIN 为准，不能使用 GitHub 当前文档 HEAD 混装工具。

### A. Owner Mac：固定代码、私有输入与 FULL25 CPU 预检

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
BASE="$HOME/.local/share/storyforge/r60/private"
SOURCE="$BASE/r60-hf-quality-pilot25-vllm0100/input_B_quote_observer_v1"
PIN="6f2a71f12f3a2408b4082d6f8b86e69e0b5cf384"

# 每次建立全新私有 staging；命令本身不需要 GPU。
STAGE="$BASE/r60-glm-full25-owner-stage-$(date -u +%Y%m%dT%H%M%SZ)"
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
git -C "$ROOT" cat-file -e "$PIN^{commit}"
test ! -e "$STAGE"
for F in runner.py source.private.jsonl token_core.py runtime_inputs.py runtime_resources.py; do
  test -f "$SOURCE/$F" || { echo "FROZEN_INPUT_SUPPORT_MISSING_HOLD:$F"; exit 42; }
done
echo "01639568cf21a7b98356f2b3b74f567943b4a6844edb9230b58759789ab67fc9  $SOURCE/source.private.jsonl" | shasum -a 256 -c -

umask 077
mkdir -m 700 "$STAGE"
for F in runner.py source.private.jsonl token_core.py runtime_inputs.py runtime_resources.py; do
  cp -p "$SOURCE/$F" "$STAGE/$F"
done
for F in \
  r60_glm4_b25_continuous_review.py \
  r60_glm4_full25_snapshot_entrypoint.sh \
  r60_glm4_servercopy_localize.py \
  r60_generation_snapshot.py \
  r60_review_isolation_core.py \
  r60_glm4_snapshot_replay.py \
  r60_glm4_snapshot_cpu_preflight.py \
  r60_glm4_literal_repair_cpu_probe.py \
  r60_glm4_exact_quote_repair.py \
  r60_glm4_b25_retry_contract.py
do
  git -C "$ROOT" show "$PIN:experiments/r58_quality/$F" > "$STAGE/$F"
done
chmod 600 "$STAGE"/*
python3 -m py_compile "$STAGE"/*.py
python3 "$STAGE/r60_glm4_snapshot_cpu_preflight.py" \
  --runner "$STAGE/runner.py" \
  --input "$STAGE/source.private.jsonl" \
  --full25
echo "OWNER_STAGE=$STAGE"
```

只有上述输出 `GLM_FROZEN_SNAPSHOT_CPU_REPLAY_PREFLIGHT_PASS` 且 SAFE 字段确认 `gpu_started=false`、`model_inference_calls=0`、`pinned_source_sha_verified=true`，才允许进入 B。**请保留 `OWNER_STAGE` 实际绝对路径**；不要在第二个终端猜测或重建该目录。上述五个冻结输入支持文件是历史已知输入包布局；如果目录实际结构不同，应先检查冻结 Runner 的导入依赖，不能补造文件或改写原 Runner。

### B. Owner Mac：独立全25 H200 命令（由 Owner 手动提交）

先在同一个终端设置 `STAGE` 为上一步输出的绝对路径，确认仍存在后再执行。**本交接阶段不执行本节命令。**

```bash
set -euo pipefail
test -f "$STAGE/runner.py"
test -f "$STAGE/r60_glm4_full25_snapshot_entrypoint.sh"
RUN_ID="$(date -u +r60-glm-full25-snapshot-%Y%m%dT%H%M%SZ)"
IMG="docker.io/vllm/vllm-openai@sha256:05a31dc4185b042e91f4d2183689ac8a87bd845713d5c3f987563c5899878271"
hf jobs run \
  --namespace adradar \
  --name "$RUN_ID" \
  --flavor h200 \
  --timeout 2h \
  --attempts 1 \
  --detach \
  -v "$STAGE:/input:ro" \
  -v "hf://buckets/adradar/storyforge-training/model-cache/glm4-32b-8dea913-servercopy:/model-source:ro" \
  -v "hf://buckets/adradar/storyforge-training:/bucket:rw" \
  "$IMG" \
  bash /input/r60_glm4_full25_snapshot_entrypoint.sh "$RUN_ID"
```

请先由 Owner 核查 HF CLI 组织权限与输出目录是否已存在；服务器端入口对两个新目录执行 `O_EXCL` 风格的不可覆盖门槛。若在本地或服务端发现同名路径，停止并新建 RUN_ID，不删除既有结果。不要加入任何 `--snapshot-probe-cases`、`--retry-baseline-dir`、`--resume` 或 GPU 修复开关。

### C. Owner Mac：真实快照的 CPU Replay（生成后执行）

先将 `hf://buckets/adradar/storyforge-training/private-generation-snapshots/RUN_ID` 中的**整个快照目录**受控复制到 Owner Mac 的新私有目录，检查来源及文件完整性。然后：

```bash
set -euo pipefail
# SNAP_DIR 必须是 Owner 实际获取并核验的私有快照目录。
# REPORT 必须是尚不存在的新 SAFE 报告文件。
test -d "$SNAP_DIR"
test ! -e "$REPORT"
python3 "$STAGE/r60_glm4_snapshot_replay.py" \
  --runner "$STAGE/runner.py" \
  --input "$STAGE/source.private.jsonl" \
  --snapshots "$SNAP_DIR" \
  --output "$REPORT" \
  --full25
```

必须看到 `scope=FULL25`、`replayed_cases=25`，且单独确认25份 slot01 快照验证及25份签名审核回执。Replay 的结果不能直接当作25条质量 PASS或训练准入。


## 准备

从固定提交读取 r60_glm4_b25_continuous_review.py、r60_glm4_full25_snapshot_entrypoint.sh、r60_glm4_servercopy_localize.py、r60_generation_snapshot.py、r60_review_isolation_core.py、r60_glm4_snapshot_replay.py、r60_glm4_snapshot_cpu_preflight.py、r60_glm4_literal_repair_cpu_probe.py、r60_glm4_exact_quote_repair.py、r60_glm4_b25_retry_contract.py。把上述文件与冻结 runner.py、source.private.jsonl 复制到仅 Owner 可读的新独立输入目录；不可直接修改冻结原件。

在 Owner Mac 执行 --full25 CPU 集成 preflight，SAFE status 必须为 GLM_FROZEN_SNAPSHOT_CPU_REPLAY_PREFLIGHT_PASS。全量模式 --snapshot-full25 需要 --case-limit 25、--isolate-technical-failures 和独立 --generation-snapshot-dir；禁止 --retry-baseline-dir、--resume、--snapshot-probe-cases、--literal-probe-cases、--snapshot-primary-only、--quote-literal-repair。本轮主目标是捕获真实生成，而不是自动修复引用。

## GPU Job

在 HF Mac CLI 以 --namespace adradar --flavor h200 --attempts 1 --timeout 2h --detach 运行，镜像 docker.io/vllm/vllm-openai@sha256:05a31dc4185b042e91f4d2183689ac8a87bd845713d5c3f987563c5899878271，命令为 bash /input/r60_glm4_full25_snapshot_entrypoint.sh RUN_ID。只读挂载 Owner Mac staging 到 /input:ro，权重 Bucket model-cache/glm4-32b-8dea913-servercopy 到 /model-source:ro，输出 Bucket adradar/storyforge-training 到 /bucket。

入口脚本负责创建两个新的 0700 目录并拒绝已有路径：/bucket/evaluation-runs/RUN_ID 为新审核回执；/bucket/private-generation-snapshots/RUN_ID 为只包含原始模型文本的不可覆盖私有 Snapshot。每条 Snapshot 在冻结校验前写入；slot01 主生成，slot02 如有冻结 Runner 二次修复生成。最大25条，每条技术失败仍继续；非预期异常或预算用尽时 fail closed。出现技术失败时即使25条已尝试，exit42 也可能出现；需以 ALL_CASES_ATTEMPTED 及 SNAPSHOT_FULL25_SUMMARY 统计为准。

## 结果 CPU Replay

取回该 RUN_ID 的真实私有 Snapshot 到 Owner Mac 私有目录，运行 r60_glm4_snapshot_replay.py --runner runner.py --input source.private.jsonl --snapshots 私有快照目录 --output 新SAFE报告路径 --full25。报告 scope=FULL25；若全25已持久化，replayed_cases=25。报告仅是 Replay 对比，不会自动转成 Quality-v1 训练准入。

操作边界：这不是训练；所有HF Job由Owner Mac手动提交；ChatGPT不代提交HF Job。脚本运行开始前要核对同一PIN下各模块和冻结Runner。GPU生成正常返回后保存快照；异常前尚未返回的模型中间输出不能保证持久化。
