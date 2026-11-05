# R58 G1 — Hugging Face 已有训练 Job 只读清点（SAFE）

2026-10-31。目标是填补 G1 的 `all_actual_sft_runs_and_input_sources_proven_complete=false`，不是重新训练、推理、下载权重或批准 G1。本工具**只读取 HF API 的 Job 列表**；它本身**无法**证明所有训练 Job 的真正输入文件哈希和训练时数据流，也无法认证已删除的历史 Job、其他账号/命名空间的任务或另一个外部训练平台。输出永久保持 G1 HOLD。

## 已核验的本地背景

- Owner Mac 报告 R57 29 世界来源名录与六份冻结 SFT Train/Validation 来源完全对账：v0.1 65/15、R46 49/15、R54 31/9，**184 个 split placements / 27 个去重世界 UUID**。这 184 个不是去重样本数，也不是所有实际 GPU Job 的证据。
- Owner Mac 报告 R04 150 − Gold108 108 的两个世界与当前四个候选无 UUID 交集，原 R04 非 Gold 世界编号与故事 **07/11** 的映射已用冻结 inventory / 原始 ZIP SHA256 元数据证明；未读取原始档案和 R50 正文。
- 历史五个有模型参数更新的已知 HF Job：v0.1 rank32 smoke (3 steps)、v0.1 rank64 capacity (1 step)、v0.1 baseline (9 steps)、R46 exploratory SFT (7 steps)、R54 V2 SFT (16 steps)。前两个**不是**正式训练版本，但都实际运行了参数更新，不能被“所有实际训练数据曝光”错误忽略。这里只检验它们是否出现在当前命名空间的已有 Job 列表中，不判断具体输入。
- R46 已有 Owner Mac 原始远端七文件回执及 R45 原始 49/15 SHA 复现；R54 已有 31/9 正式冻结 release 和 Trainer state 的既有回执；v0.1 baseline 报告并列示 smoke/capacity。但这些历史文件的证据级别**不能**由 Job 枚举升级为“所有远端训练输入被直接重哈希”，也不能将验证集视为梯度训练。

## Mac 命令（只读，不收费，不下载模型）

前提：本机已登录有权限枚举历史 HF Job 的 Hugging Face 账号；`huggingface_hub` 使用本机已有认证，不在命令中明文放 token。若未安装所需 Python 包，用已有 Python 环境安装 `huggingface_hub`（安装本身可能访问软件包索引，不会启动 HF 计算任务）。

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only
python3 -m unittest discover -s experiments/r58_round1 -p 'test_*.py' -q

python3 experiments/r58_round1/check_hf_training_job_inventory.py \
  --namespace adradar
```

新增 16 项**纯合成测试**；上一轮 R58 预期 172，加本轮预计 **188 项**，以 Mac 实际结果为准。**不会**调用 `run_job`、`cancel_job`、`rerun_job`，不会打开 HF 训练日志、训练命令、环境变量或 secrets。程序使用官方 `HfApi.list_jobs(namespace='adradar')`，消费返回 Job 的 `id` 和 `status.stage` **仅用于聚合**。

可只分享工具打印的 SAFE JSON：`hf_jobs_returned`、各 status 数量、五个已知任务识别计数、其角色状态、未知任务计数。没有未知任务编号、命令、环境、Token、私有 story UUID 或原文。**不要**粘贴 `hf jobs list -a` 原始表格，表格可能包含内部脚本命令和敏感参数。

## 必须保持的限制

- `known_sft_or_training_smoke_job_ids_found=5` **不等于**输入全集通过。其他任务仍未分类，历史删除/保留策略未知，当前登录的 org/user 范围未必覆盖过去所有任务。
- 即使 `other_job_ids_unclassified=0`，也不能证明没有过去删除的训练任务。
- 对每个确实涉及参数更新的实际 Job，还需只读检验**原始训练输入哈希、Train/Validation 分离、作业时刻的命令/日志及 source revision**。v0.1 smoke/capacity 必须纳入，不能直接沿用 baseline 的 65/15 数据声明。
- 工具绝不触及 R50 测试内容、Owner 私有账本、付费 CPU/GPU，不覆盖任何文件；G1 仍 HOLD，Train/Validation/Teacher 为零，禁止扩样，PR #7 Draft。
