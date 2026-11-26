# R58 G1 — v0.1 三个实际参数更新 Job 的原始输入字节核对（SAFE）

日期：2026-10-31。目的：将 GitHub 已核实的 v0.1 65 Train / 15 Validation 原始来源，与 Smoke（3 步）、Rank64 Capacity（1 步）、Baseline（9 步）**各自运行目录的编译输入**进行逐字节 SHA256 对账；不重新训练，不调查全部 HF Job，不访问 R50 密封原文。

## 可核实的历史来源

- `scripts/hf_submit_smoke.sh` 和 `scripts/hf_submit_baseline.sh` 都将 v0.3 原始 JSONL 上传至共享 `datasets/v0.3/{train,validation}.jsonl`。
- `scripts/hf_job_runner.py` 读取该共享源，经 `scripts/prepare_sft.py` 转换为 `runs/<smoke_job_id>/{train,validation}.jsonl`，随后 `swift sft` 读取这两个编译文件。
- `scripts/hf_baseline_runner.py` 对 Capacity / Baseline 在 `baseline-runs/<capacity|baseline>/<job_id>/{train,validation}.jsonl` 运行同样的编译；Capacity / Baseline 都将各自编译文件交给 `swift sft`。
- 在 Smoke 原始 Git 基线 `b5915cbb434db64744a7343d6b4539670df70b79`、Baseline 原始 Git 基线 `35cb49e82f53a8931f765eb93aa9b8fcca3df9a6`、当前 R58 分支上，`scripts/prepare_sft.py` 都是同一个固定 Git blob：`2c60e69b0d288a3decfafdf2b07095c6dfed48a7`。
- 原始 v0.1 Git blob：Train `3e64c9932ca43fefa8ecfb200085fe718581b6f9`（SHA256 `9a24f07befee9e701c587f4b154b0e780c29534abe3a0fa8b0c310511172a60f`）；Validation `db0ae8b86038be1b372d547fdb2d6b0b7e33b54e`（SHA256 `083a6f124abc414a0edf268d1a95788f738d55e7ecd229a78c67087991f46c36`）。

## 核对的八个文件

共享源 `2` 个，加上三个已知参数更新 Job 各自的 Train / Validation 编译文件 `3×2=6` 个，共 **8 个**。公开 SAFE 返回中只计数，不输出 HF URI、Job ID、私有正文或故事 UUID。

### 限制

- 默认不访问 HF，须由 Owner 明确提供 `--allow-read-only-private-v01-input-bytes`。
- 工具通过固定 Git blob 读取**已公开在仓库内的**原始 v0.1 JSONL，按照同版本 `prepare_sft.py` 的转换语义在内存中重放。只在这一阶段解析 Git 公开源内容；**不会解析、打印或保存任何 HF 远端文件正文**。
- 远端文件通过 `HfFileSystem.open(..., 'rb')` 流式哈希，最大 6 MB/文件；仅允许上文固定八个路径。不写 Bucket、无训练/推理调用、无新 GPU 或 CPU Job；SDK 异常细节不得输出。
- 检验通过说明**当前**共享源和三个 Job 目录中的编译文件与 Git 固定重放一致；不证明历史每次任务启动时对象不可变、不证明每条数据参与梯度、不证明其它 60 个未分类 Job 无训练、不证明文件内容绝无 R50 数据。
- 最终 G1 保持 `HOLD`，Train / Validation / Teacher 均为 0，`expansion_allowed=false`。PR #7 继续 Draft。

## Owner Mac 操作

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only
python3 -m unittest discover -s experiments/r58_round1 -p 'test_*.py' -q

# 仅在明确允许读取既有私有 HF 输入字节时执行；不创建任何新 Job。
python3 experiments/r58_round1/check_v01_hf_primary_inputs.py \
  --repo-root "$PWD" \
  --allow-read-only-private-v01-input-bytes
```

返回 **SAFE stdout JSON** 与测试摘要即可，不上传 HF 原始 JSONL、命令日志、密钥、私有 UUID 或 R50。若任何源文件缺失、哈希不匹配、权限不足或编译语义不吻合，应报告通用 `HOLD`，**不得修改远端文件来迎合校验**。

编译输出的 SHA256 是对 Git 公开来源的确定性计算，可安全写进未来 GitHub 回执；该哈希仍不是历史远端不可变性签名。
