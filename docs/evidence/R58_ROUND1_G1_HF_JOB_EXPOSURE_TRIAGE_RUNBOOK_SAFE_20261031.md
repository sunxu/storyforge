# R58 G1 — Hugging Face 已有 Job 聚合分层与未知任务本机私有台账（SAFE）

日期：2026-10-31。此前 Owner Mac 188/188 合成测试 PASS；只读 `HfApi.list_jobs(namespace="adradar")` 返回 69 个任务：36 COMPLETED / 31 ERROR / 2 CANCELED。五个已知模型参数更新任务（v0.1 smoke、capacity、baseline，R46，R54）全部返回 COMPLETED；其余 64 个未知。**ERROR、CANCELED 和 CPU flavor 均不能证明任务没有模型参数更新**，不能据此放开 G1。

## 本轮比对范围

追加使用现有 SAFE 文档中已列明用途的四个 Job ID（不是从训练命令或输出推断）：

- v0.1 validation paired evaluation — `docs/HF_RUN_REGISTRY.md`。
- v0.1 old held-out paired evaluation — `docs/HF_RUN_REGISTRY.md`。
- v0.1 checkpoint SHA256 CPU verification — `docs/HF_RUN_REGISTRY.md`。
- R53 CPU40 tokenizer/collator/no-train preflight — `docs/evidence/V03_R53_HF_CPU40_OWNER_INTAKE_SOURCE_LOG_RECEIPT_ACCEPTED_20261021.md`。

这四个任务仅标为 **`KNOWN_DOCUMENTED_NO_OPTIMIZER_PURPOSE`**，其目的来自已冻结的报告，不表示每个远端 Job 的完整命令/实际训练过程已被独立复审。新增工具 `triage_hf_job_exposure.py` 将 5 个已知参数更新 + 4 个文档用途任务与当前可见任务 ID 比对，并把余下任务按 `status.stage` 与 `flavor` 聚合分层。只访问 `JobInfo.id`、`JobInfo.status.stage`、`JobInfo.flavor` 三个字段；不会访问 command、arguments、environment、secrets、labels、日志、指标、Bucket 或 R50。

CPU/GPU 只是 **硬件优先级标签**，不是是否训练的判定。未知 flavor 保留 `UNRECOGNIZED`。不可因某 Job 失败、取消、用 CPU、已知标签或不在当前列表而认定无训练数据曝光。

## Mac 运行（不启动 HF Job、不下载训练数据）

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only
python3 -m unittest discover -s experiments/r58_round1 -p 'test_*.py' -q

ROOT="$HOME/.storyforge-r58-private/round1_pilot_20261030"
OUT="$ROOT/g1_hf_unknown_jobs_private.json"
umask 077
if [ -e "$OUT" ] || [ -L "$OUT" ]; then
  echo 'HOLD: UNKNOWN_JOB_PRIVATE_LEDGER_EXISTS_NO_OVERWRITE'
else
  python3 experiments/r58_round1/triage_hf_job_exposure.py \
    --namespace adradar \
    --private-unknown-output "$OUT"
fi
```

此前 188 项 + 新增 21 项合成测试，预计 **209 项**；实际数量以 Mac 为准。私有账本为 `0600`、仅包含仍未知的 Job ID / stage / 粗粒度硬件类别 / PENDING 标记，拒绝覆盖与普通符号链接。只向聊天返回测试摘要与 **stdout 的 SAFE JSON**，**不要上传私有账本、HF 列表原文、Job 命令/参数/密钥/训练来源**。

## 完成的边界和后续

此轮可以判断有多少未知任务属于 GPU/CPU/不认识的硬件，优先审查可能涉及参数更新的历史运行。**不会**自动证明远端训练输入字节与冻结数据一致，也不会覆盖 HF 其他账号、命名空间、已删除或保留策略之外的任务。

需要对每个疑似涉及参数更新的任务独立核验 source revision、真实输入 SHA256、训练/验证用途及是否在出错前产生更新；训练 smoke 和 capacity 也必须包含。不能仅凭 `list_jobs` 状态完成来源全集证明。

`G1=HOLD`、Train/Validation/Teacher 准入=0、`expansion_allowed=false`、R50 sealed、PR #7 Draft，G2/G3 不启动。不生成、修改或覆盖之前的 G1 PRIVATE 账本；不提交付费 HF CPU/GPU 或新的训练任务。
