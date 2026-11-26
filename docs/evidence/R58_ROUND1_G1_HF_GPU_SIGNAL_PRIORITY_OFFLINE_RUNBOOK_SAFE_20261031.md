# R58 G1 — 1/18 GPU 日志信号回执离线交叉核验（SAFE）

日期：2026-10-31。Owner 上轮返回 69 Job（其中 5 已知参数更新、4 文档记载非训练用途、60 尚未分类），其中 18 个 GPU 的历史日志信号扫描结果为 **1 `POTENTIAL_OPTIMIZER_LOG_INDICATOR` + 17 `NO_INDICATOR_OBSERVED__NOT_EXCLUDED`**；另外 42 个 CPU 仍未知。所有任务都保持 G1 HOLD。17 个没有匹配信号，不等于没有参数更新；一个匹配信号，也不等于训练确证。

## 仅复核已有 PRIVATE 元数据，不增加日志读取

新增 `experiments/r58_round1/review_hf_gpu_signal_receipt.py` 仅从 Owner Mac 读取先前两份私有回执（不读取训练正文或原始日志）：

- `g1_hf_unknown_jobs_private.json`：既有 60 个未分类任务 ID、硬件类别和当时状态。
- `g1_hf_gpu_log_signal_review_private.json`：先前 18 个 GPU 日志信号回执和源台账 SHA256。

脚本先验证原 60 Job / GPU18 / CPU42 的固定范围、私有文件权限与模式 0600、回执与源的 SHA256 绑定、GPU 18 个 ID / stage 精确对应、正向信号类别只能为原工具允许的枚举值、未存在任何已批准训练或非训练分类。严格要求冻结回执恰好 1+17；异常即 HOLD（退出码 42），不能借程序绕过旧门禁。不会再次调用 HF API，不会读取 `fetch_job_logs`，不会写原始日志、Job 命令、配置、Token、story UUID 或 R50 内容。

SAFE 输出只包含优先任务的状态（COMPLETED/ERROR/CANCELED）和标准化迹象类别，**不会显示其 24 位 Job ID**。可选生成唯一一个新的 `0600` 私有优先队列文件，仅保存此 1 个需进一步核实的 Job ID 与已有回执哈希，并标记 `PENDING_PRIMARY_RUN_ARTIFACT`，不能覆盖任何旧账本。该文件不能发到聊天或 GitHub。

## Owner Mac 运行

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only
python3 -m unittest discover -s experiments/r58_round1 -p 'test_*.py' -q

ROOT="$HOME/.storyforge-r58-private/round1_pilot_20261030"
UNKNOWN="$ROOT/g1_hf_unknown_jobs_private.json"
GPU="$ROOT/g1_hf_gpu_log_signal_review_private.json"
OUT="$ROOT/g1_hf_gpu_signal_priority_one_private.json"

umask 077
if [ -e "$OUT" ] || [ -L "$OUT" ]; then
  echo 'HOLD: priority ledger exists, refuse overwrite'
else
  python3 experiments/r58_round1/review_hf_gpu_signal_receipt.py \
    --private-unknown-ledger "$UNKNOWN" \
    --private-gpu-signal-ledger "$GPU" \
    --private-priority-output "$OUT"
fi
```

新增 **17/17** 合成单测通过。全量 R58 测试精确数以 Owner Mac 输出为准。只返回测试摘要与 **SAFE JSON**，不要返回带 Job ID 的私人文件及日志原文。

## 完成后仍必须 HOLD

- 该回执只证明**原先两个私有台账内部自洽**，不能证明任何一次远端模型更新，或日志保留/历史任务枚举完整。
- 需要后续单独审阅该任务的真实运行证据（是否调用优化器、真实 `global_step` / checkpoint、运行时 train/validation 文件哈希、来源世界 UUID），并明确证据边界。不可把单条日志指标当成参数更新或用 `ERROR` / `CANCELED` 排除更新。
- 其余 17 GPU、42 CPU 都未被清除；已知五个参数更新 Job 的 primary 输入验证也仍不完备；历史已删除/其他命名空间任务仍有缺口。
- R50 仍为密封测试源；本轮不打开 R50，不启动 GPU/CPU Job、不训练、不扩样、不修改任何冻结队列。`G1=HOLD`、Train / Validation / Teacher 准入=0，PR #7 保持 Draft。
