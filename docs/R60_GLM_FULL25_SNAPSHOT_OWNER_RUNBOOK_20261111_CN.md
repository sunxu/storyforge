# R60 GLM 完整25条 Snapshot 生成：Owner Mac 执行手册

本轮 Owner 明确要求取消1~2条限制，直接生成完整25条原始 GLM B25 输入。此次是独立25条全量重审，而非12条失败样本子集重试。旧的13 VERIFIED/12 TECHNICAL_FAILURE 历史回执不可覆盖；新运行独立保存完整原始文本 Snapshot 和新的 Checkpoint/技术回执。

代码固定提交：40b1389818e5368b1e110a57a31cbe5d338c1870。模型：zai-org/GLM-4-32B-0414；revision 8dea913c41b543527c2860fb6f3c15c202f24aeb；输入25条 SHA 01639568cf21a7b98356f2b3b74f567943b4a6844edb9230b58759789ab67fc9。

## 2026-11-11 核验修复：全量模式与旧 probe 守卫冲突

旧提交 `77da8093c831a6cb3771385b1c673ffb82143529` 虽然四组 CI PASS，仍有参数冲突：`--snapshot-full25` 要求不传 `--snapshot-probe-cases`，但旧守卫只要有 Snapshot 目录且 probe=0 就拒绝，导致真实 H200 在加载前 `SNAPSHOT_PROBE_SCOPE_HOLD`。现已修改条件为 `and not args.snapshot_full25`，并增加 AST 执行式 CPU 回归验证全量/旧 probe 双路径。**旧 PIN 已废弃，不得拿它提交 H200。**

全量25条运行会在冻结 Runner 技术异常时继续保存签名技术失败回执；如果模型生成/快照写入出现非预期错误，可能提前停止，不能宣称25份 Snapshot 已保存。CPU Replay 的 `--full25` 可以读取完整或连续的部分前缀；只有 `replayed_cases=25` 且生成回执另行核验25/25，才算完整运行验收。

## 准备

从固定提交读取 r60_glm4_b25_continuous_review.py、r60_glm4_full25_snapshot_entrypoint.sh、r60_glm4_servercopy_localize.py、r60_generation_snapshot.py、r60_review_isolation_core.py、r60_glm4_snapshot_replay.py、r60_glm4_snapshot_cpu_preflight.py、r60_glm4_literal_repair_cpu_probe.py、r60_glm4_exact_quote_repair.py、r60_glm4_b25_retry_contract.py。把上述文件与冻结 runner.py、source.private.jsonl 复制到仅 Owner 可读的新独立输入目录；不可直接修改冻结原件。

在 Owner Mac 执行 --full25 CPU 集成 preflight，SAFE status 必须为 GLM_FROZEN_SNAPSHOT_CPU_REPLAY_PREFLIGHT_PASS。全量模式 --snapshot-full25 需要 --case-limit 25、--isolate-technical-failures 和独立 --generation-snapshot-dir；禁止 --retry-baseline-dir、--resume、--snapshot-probe-cases、--literal-probe-cases、--snapshot-primary-only、--quote-literal-repair。本轮主目标是捕获真实生成，而不是自动修复引用。

## GPU Job

在 HF Mac CLI 以 --namespace adradar --flavor h200 --attempts 1 --timeout 2h --detach 运行，镜像 docker.io/vllm/vllm-openai@sha256:05a31dc4185b042e91f4d2183689ac8a87bd845713d5c3f987563c5899878271，命令为 bash /input/r60_glm4_full25_snapshot_entrypoint.sh RUN_ID。只读挂载 Owner Mac staging 到 /input:ro，权重 Bucket model-cache/glm4-32b-8dea913-servercopy 到 /model-source:ro，输出 Bucket adradar/storyforge-training 到 /bucket。

入口脚本负责创建两个新的 0700 目录并拒绝已有路径：/bucket/evaluation-runs/RUN_ID 为新审核回执；/bucket/private-generation-snapshots/RUN_ID 为只包含原始模型文本的不可覆盖私有 Snapshot。每条 Snapshot 在冻结校验前写入；slot01 主生成，slot02 如有冻结 Runner 二次修复生成。最大25条，每条技术失败仍继续；非预期异常或预算用尽时 fail closed。出现技术失败时即使25条已尝试，exit42 也可能出现；需以 ALL_CASES_ATTEMPTED 及 SNAPSHOT_FULL25_SUMMARY 统计为准。

## 结果 CPU Replay

取回该 RUN_ID 的真实私有 Snapshot 到 Owner Mac 私有目录，运行 r60_glm4_snapshot_replay.py --runner runner.py --input source.private.jsonl --snapshots 私有快照目录 --output 新SAFE报告路径 --full25。报告 scope=FULL25；若全25已持久化，replayed_cases=25。报告仅是 Replay 对比，不会自动转成 Quality-v1 训练准入。

操作边界：这不是训练；所有HF Job由Owner Mac手动提交；ChatGPT不代提交HF Job。脚本运行开始前要核对同一PIN下各模块和冻结Runner。GPU生成正常返回后保存快照；异常前尚未返回的模型中间输出不能保证持久化。
