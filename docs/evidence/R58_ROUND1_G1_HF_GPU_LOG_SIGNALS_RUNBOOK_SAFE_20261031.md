# R58 G1 — 已有 HF 未分类 GPU Job 日志信号本机审阅（可选、须显式授权）

2026-10-31。Owner SAFE 回执已经验证：`adradar` 下 69 个可见 HF Job，已知参数更新 5 个，文档描述的非训练用途 4 个；余下 60 个待分类，其中 GPU 18（COMPLETED 7、ERROR 9、CANCELED 2），CPU 42。该枚举不能证明其他命名空间、被删除任务或日志保留完整性。六份已知 Train/Validation 冻结来源 184 placements、27 UUID 的对账及 R04 非 Gold 故事 07/11 的零交集不变；G1 仍 HOLD。

## 风险与硬边界

- **这一步会读取历史 Job 的运行日志，和之前的元数据枚举不同。日志可能包含私有参数、训练来源、故事片段，甚至潜在的受保护 R50 内容。** 只有 Owner 明确允许审阅这些历史日志时才能运行；此前只批准元数据查看并不等于批准日志查看。
- `probe_hf_gpu_job_logs.py` **默认不允许读取日志**，只有显式传入 `--allow-private-historical-job-logs` 才调用官方 `HfApi.fetch_job_logs(job_id=..., namespace='adradar', follow=False)`。从先前创建的 `0600` 私有 60 Job 台账取 18 GPU ID，不输出 Job ID。
- 不读 `JobInfo.command`、arguments、environment、secrets、labels，也不下载 Bucket / checkpoint / R50 测试源、不发起新的 HF Job。日志只在 Mac 本地内存中逐行扫描，不写原始日志和匹配行；最多处理每个 Job 8 MB 或 200,000 行（超过直接 PENDING），日志 SHA256 仅写新的 `0600` 私有台账。异常只返回聚合 `LOG_UNAVAILABLE_PENDING`。
- 输出中的 `POTENTIAL_OPTIMIZER_LOG_INDICATOR` 只是待审训练迹象；`NO_INDICATOR_OBSERVED__NOT_EXCLUDED` **不能证明**不存在参数更新。错误/取消任务不能排除。18 GPU 全数仍是 PENDING，42 CPU 也全部 PENDING；不能因为日志没匹配就升格成完整训练来源注册表。
- 不对可能存在于历史日志中的 R50 内容做已排除保证（SAFE `r50_protected_content_absence_from_historical_logs_verified=false`）。如严格禁止接触任何可能含有 R50 的历史日志，请**不要运行本步骤**；保留 G1 HOLD 并先做来源范围人工限定。

## Mac 操作（可选，只读 HF，不启动计算）

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only
python3 -m unittest discover -s experiments/r58_round1 -p 'test_*.py' -q

ROOT="$HOME/.storyforge-r58-private/round1_pilot_20261030"
INPUT="$ROOT/g1_hf_unknown_jobs_private.json"
OUT="$ROOT/g1_hf_gpu_log_signal_review_private.json"

# 只有 Owner 明确批准读取现有历史 Job 日志时，才执行以下命令。
# 不导出原始日志、Job ID、训练正文；不覆盖已有 PRIVATE 台账。
umask 077
if [ -e "$OUT" ] || [ -L "$OUT" ]; then
  echo 'HOLD: private GPU log receipt exists; no overwrite'
else
  python3 experiments/r58_round1/probe_hf_gpu_job_logs.py \
    --namespace adradar \
    --private-unknown-ledger "$INPUT" \
    --private-output "$OUT" \
    --allow-private-historical-job-logs
fi
```

新增 20 项离线合成测试在本地 PASS。原有 R58 测试基线以 Owner 实际输出为准，不预设完整数量。

## 仅回传 SAFE 汇总

只返回 `gpu_log_scan_state_counts`、`gpu_logs_requested`、`cpu_jobs_still_unclassified` 和 G1 等 SAFE 状态，不要粘贴完整 `hf jobs logs` 输出、私有台账、token、shell 环境或 HF 命令参数。

**后续真正所需：** 对所有疑似参数更新 Job 取 primary Trainer 输入/运行时哈希与代码版本，并有可信完整 Job 清单（含失败/取消、其他命名空间与历史保留限制）；不能凭本工具核准训练。`G1=HOLD`，Train/Validation/Teacher=0，`expansion_allowed=false`，PR #7 Draft。
