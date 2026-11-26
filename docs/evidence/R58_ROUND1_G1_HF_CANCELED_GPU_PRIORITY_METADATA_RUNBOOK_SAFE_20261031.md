# R58 G1 — 单个 CANCELED GPU Job 提供商元数据核验（SAFE）

日期：2026-10-31。Owner 既有 60 任务私有清单 → 18 GPU Job 日志信号私有回执 → 1 个潜在信号任务私有优先账本均已通过来源关联校验。唯一信号为 `TRAINING_LOSS_GRAD_TELEMETRY`，Job stage `CANCELED`。这**不能**证明 `optimizer.step()`，也不能证明没有参数更新。17 个无信号 GPU、42 个 CPU 仍为 PENDING。

新增 `inspect_hf_priority_job_metadata.py` **仅对这一个已有私有优先 Job** 调用官方 `HfApi.inspect_job(job_id=...,namespace='adradar')`，通过本地 0600 优先台账读取私有 ID，不在 stdout / GitHub 输出 ID。默认只访问返回 `JobInfo` 的 `id`、`status.stage`、`started_at`、`finished_at`、`flavor`；不读命令、参数、密钥、环境变量、日志。SDK 返回对象可能内含敏感元数据，程序不展开、序列化、打印对象。

命令/参数分析为**额外权限**：只有 Owner 自主添加 `--allow-sensitive-command-intent` 才在 Mac 内存里访问命令和参数字符串，归类训练意图。命令字符串本身可能包含私有位置、Token 或封存 R50 的间接信息，不输出、不保存、不发送到聊天。即使识别训练命令，也**不是训练运行或梯度更新证明**。输出永久 `G1 HOLD`、准入 0、禁止扩样。

## Mac（默认仅元数据，不读命令）

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only
python3 -m unittest discover -s experiments/r58_round1 -p 'test_*.py' -q
ROOT="$HOME/.storyforge-r58-private/round1_pilot_20261030"
INPUT="$ROOT/g1_hf_gpu_signal_priority_one_private.json"
OUT="$ROOT/g1_hf_priority_provider_metadata_private.json"
umask 077
if [ -e "$OUT" ] || [ -L "$OUT" ]; then echo 'HOLD: private receipt exists'; else
python3 experiments/r58_round1/inspect_hf_priority_job_metadata.py \
  --private-priority-ledger "$INPUT" --private-output "$OUT"
fi
```

需要特别核验命令意图时，可以改用一个**全新的**不同输出路径并加 `--allow-sensitive-command-intent`；禁止对前次生成的私有回执覆盖或手动编辑。

只向聊天粘贴 SAFE JSON。不要粘贴 `inspect_job` 对象或 `hf jobs inspect` 原始输出（可能包含 environment/secrets）。严禁下载、查看 R50、提交新训练 / 付费任务。本核验不做 HF provider 日志完整性、历史所有 namespace 或真实输入 SHA256 证明。**没有培训／非训练排除权，G1 不放开。**
