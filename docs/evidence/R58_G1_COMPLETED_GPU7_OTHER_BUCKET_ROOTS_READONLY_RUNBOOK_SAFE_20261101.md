# R58 G1 — 7 个已完成但未找到 Job-ID 专属目录的 GPU Job：其他五处 Bucket 根目录元数据核验

日期：2026-11-01。仅在 `r58/roleplay-sft-skill-v01` Draft PR #7 上追加。**不改变 G1/G2 HOLD。**

## 已有证据和本轮目标

Owner Mac 已回传 SAFE 回执：18 个原始未分类 GPU Job 中，4 个在 `runs` 与 `baseline-runs/capacity` 两处根目录出现 Job-ID 专属目录（2 CANCELED / 2 ERROR），另 14 个未出现（7 COMPLETED / 7 ERROR）。原有 60 个 Job **没有任何一个被排除**，GPU 18 / CPU 42 继续 PENDING。证据：

`docs/evidence/R58_G1_GPU18_BUCKET_PREFIX_COVERAGE_OWNER_RECEIPT_SAFE_20261101.json`。

新工具：`experiments/r58_round1/r58_g1_gpu7_completed_other_bucket_roots_metadata_safe_20261101.py`。

仅对原 60 项 PRIVATE 未分类清单里的 **7 个 COMPLETED、且原两根目录无专属目录的 GPU Job** 进行**路径名称是否包含精确 Job ID**的元数据核对，限定五处额外根目录：

- `experiments`
- `baseline-runs/baseline`
- `evaluation`
- `evaluation-runs`
- `preflight`

工具为有界只读目录遍历，单根目录最多 1000 次目录列举、5000 条元数据、深度最多 10，出现不支持结构或不完整状态立即 HOLD。不遍历 `cache`，不扫其他 HF Namespace、外部训练平台、已删除历史 Job。该搜索**不读取文件字节、日志、命令、Secrets、训练文本或 R50 密封题目正文**；仅处理文件或目录的名称，逐 Job 结果仅写 Owner 机器的 PRIVATE 回执。

「路径出现 Job ID」仅是**潜在工件关联线索**，不能证明来源可信、optimizer step 或训练输入；「路径未出现 Job ID」不能证明 Job 未训练。两种情形均继续 PENDING。

## 先 Pull，再在 Owner Mac 执行

依赖：此前已存在的两个 PRIVATE 原始账本及 GPU18 目录覆盖 PRIVATE 回执；不要修改或上传它们。对本机当前工作区有未提交改动时不要强制覆盖。

```bash
cd ~/workspace/storyforge-r58-run
git status --short
git switch r58/roleplay-sft-skill-v01
git pull --ff-only origin r58/roleplay-sft-skill-v01

python3 -m py_compile \
  experiments/r58_round1/r58_g1_gpu7_completed_other_bucket_roots_metadata_safe_20261101.py

python3 experiments/r58_round1/r58_g1_gpu7_completed_other_bucket_roots_metadata_safe_20261101.py \
  --repo-root "$PWD"
```

终端仅返回 SAFE JSON。成功时才独占生成本机 0600 PRIVATE 文件：

`~/.storyforge-r58-private/round1_pilot_20261030/g1_gpu7_completed_other_roots_PRIVATE_20261101.json`

若已有同名文件或远端元数据不完整，工具安全 HOLD，**不覆盖、不删除重跑、不跳过结构检查**。如果本机报告 HOLD，请只贴回 SAFE JSON 和返回码，勿共享异常堆栈、路径、个人账号或 PRIVATE 原文。

## 质量和门禁

归档前只完成源码边界静态核验；是否支持 Owner Mac 上的 Bucket API 目录元数据格式，由本次实测判定。**没有进行新 HF Job 或 GPU、完整项目测试，不得宣称 E2E PASS**。

G1=HOLD、G2=HOLD、G3=NOT_STARTED、Train/Validation/Teacher=0，禁止扩样、禁止 GPU 训练、不访问新的原始 Job 日志。
