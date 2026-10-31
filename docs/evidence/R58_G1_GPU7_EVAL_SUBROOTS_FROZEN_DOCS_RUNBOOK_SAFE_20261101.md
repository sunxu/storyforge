# R58 G1 — 已完成 GPU7 的 evaluation-runs 子目录精确对账（SAFE）

日期：2026-11-01。仅适用于 `r58/roleplay-sft-skill-v01` Draft PR #7。

## 为什么需要修正

Owner Mac 的限域诊断发现：原 7 个 COMPLETED GPU Job 中，在 `evaluation-runs` 有路径名关联的 4 个，只在 `evaluation-runs/v03-r57` 精确命中其中 2 个。此前要求“R57 子目录 4/4 命中”的断言没有来源依据，导致安全 HOLD。该诊断 SAFE 证据：`docs/evidence/R58_G1_GPU7_R57_STAGE_DIAGNOSTIC_OWNER_RECEIPT_SAFE_20261101.json`。

本轮脚本不改写之前 4/3 的 Owner PRIVATE 台账；它只校验原有四个 Job 在已知五个 evaluation-runs 子目录的实际分布，不因路径有 `evaluation` 字样而判定没有训练。

## 限定范围

脚本：`experiments/r58_round1/r58_g1_gpu7_eval_subroots_and_frozen_docs_readonly_20261101.py`。

固定子目录：`test`、`v02-r47`、`v03-r55`、`v03-r57`、`validation`。目录元数据递归总上限 200 次列表调用、1200 个文件/目录对象、深度 10。根目录新增、缺失或格式异常时立即 HOLD。

只读四份既存 PRIVATE 元数据账本、HF Bucket 文件名/目录名，以及 Git HEAD 中的受控冻结 `.md/.json` 文档引用。逐 Job ID 不输出，不新建 PRIVATE 文件，不读取 HF 文件字节、命令/日志、模型权重、训练正文或 R50 密封内容，不启动 HF CPU/GPU。

输出包括五个子目录各自的精确匹配计数、四个 Job 的去重覆盖数、R57 子目录匹配数和四个／其余三个 Job 的冻结文档引用计数。子目录内找不到命名 Trainer/optimizer 文件，也不等于从未发生过参数更新。

## Owner Mac：先 Pull，再运行

```bash
cd ~/workspace/storyforge-r58-run
git status --short
git switch r58/roleplay-sft-skill-v01
git pull --ff-only origin r58/roleplay-sft-skill-v01
git rev-parse --short HEAD

python3 -m py_compile \
  experiments/r58_round1/r58_g1_gpu7_eval_subroots_and_frozen_docs_readonly_20261101.py

python3 experiments/r58_round1/r58_g1_gpu7_eval_subroots_and_frozen_docs_readonly_20261101.py \
  --repo-root "$PWD"
```

仅返回终端 stdout SAFE JSON；如失败，报告 `failed_stage` 与退出码 42，不分享 PRIVATE 账本或原始 traceback。脚本完成 GitHub 静态范围检查，但 Owner Mac 端到端与完整项目测试尚未执行。

## 停止规则

本轮结束后停止重复名称扫描。下一步只有可信原始 Trainer 优化器更新、历史输入消费、当时运行版本或权威 Job/Protected 来源全集才能实质推动 G1。任何目录名/文档引用的阳性或阴性发现都不解除 PENDING。

保持 `G1=HOLD`、`G2=HOLD`、`G3=NOT_STARTED`、Train/Validation/Teacher=0、`expansion_allowed=false`。
