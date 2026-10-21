# StoryForge R54 V2 — HF GPU `sync → submit → verify` 工程说明（未授权 GPU）

版本：2026-10-21。**状态：脚本已实现并提交 GitHub；未启动任何 R54 GPU Job。**

## 0. 冻结输入与训练合同

- R53 已由 Owner 回执验收：私有 **31 Train / 9 Validation**，清单 SHA256 `00b8182812d8bbc33eaacede962506ec718c6b987ef82c429f75401c4c107261`。
- 正式 Train `d0425c54b534307047457d05e6890b50076ad2d23ce9ab3d52f94d1a3db585a7`，正式 Validation `b5ea4075419ce02a1340f6ece875068746918ce1d4c6d72ee2f799b3fe58754d`。
- R53 正式发布回执 SHA `3d8078ee3b4528521b7f67ba1dd7983f0d20bfeb4d7c79e92d9cabe2c6b2e836`。
- 真实 R53 CPU40 报告 SHA `8624c21b6d9fff5e74006bca000c69f0d39870f1fb030c2ff4fb96cc523f1f45`，原版 Owner 端 CPU intake SHA `b3bff2625c360aad10d985b42884263a26a72e85e7d1ddc7d0df916b6598381e`。
- V2 配置 `configs/v03_r54_qlora_31_9_16step_v2.yaml` SHA256 `55ac554a4fe4b4974b7f7f664dcf5a9163b5e37219150acc087309282ef4d861`，Qwen 固定 revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`。
- A100 80GiB，NF4 4-bit / BF16，LoRA 64/128/dropout 0.05，max_length 16384，last_round，**1 Epoch，batch1×accum2，预计 16 optimizer steps**。评估在 4/8/12/16；保存 8/16；实际完成由 Trainer state 验证。
- 该版本不同于 R46 的梯度累积 8 和周期 3：**不是仅数据不同的单变量对照试验**。

## 1. 只读测试（无 HF Job、无 GPU、无远程数据写入）

```bash
cd ~/workspace/storyforge
git switch main
git pull --ff-only origin main
python3 -m unittest discover -s tests -p 'test_v03_r54_gpu_pipeline.py' -v
python3 -m unittest discover -s tests -p 'test_v03_r54_last_step_checkpoint_gate.py' -v
```

- 原有 V2 数据预检、最终 checkpoint 本地测试此前合计 **27/27 PASS**。
- **新增的 GPU 工作流 25 项自动测试已提交代码，但截至本记录尚未在本次助手容器中执行**；请以上述 Mac 端实际结果为准，不要把未跑的测试写成 PASS。
- `hf jobs run` 仅在脚本的 `submit` 分支，且受两个付费授权开关控制。对本次 `继续` **没有** GPU 授权。

## 2. 私有源准备与 `sync`（无 GPU Job）

私有 R53 发布包应已经由 Owner 在 Mac 按 V4 校验并生成；**从本地正式发布目录取数据，不从 GitHub 的其它旧训练路径取样本**：

```bash
cd ~/workspace/storyforge
R53="$HOME/.local/share/storyforge/r53-authorized-release"
RELEASE="$R53/R53_FORMAL_DATA_ONLY_RELEASE_31_9"
CPU_REPORT="$R53/evidence/R53_HF_CPU40_AUDIT_REPORT_PRIVATE.json"
CPU_INTAKE="$R53/evidence/R53_CPU40_OWNER_INTAKE_VERIFIED.json"

# 必须先跑上述无 GPU 的测试；确保 HF CLI 和 Python huggingface_hub 已登录可用。
hf auth whoami
python3 -c 'from huggingface_hub import HfApi; print("R54_HF_BUCKET_API_READY")'

bash scripts/v03_r54_gpu_submit.sh sync \
  "$RELEASE" "$CPU_REPORT" "$CPU_INTAKE"
```

脚本先核对真实 R53 冻结输出与审核证据，再产生**唯一** `R54_RUN_KEY`，验证私有 Bucket 目标路径无任何既有对象，分文件上传私有输入+固定代码+配置，最后上传 `SHA256SUMS.txt`。同步后远端必须有精确 14 个预期对象，且没有历史结果或 submit 占位记录。

预期末尾：

```text
R54_REMOTE_STAGE_COMPLETE__NO_GPU_JOB
R54_RUN_KEY=r54-v2-...
R54_SYNC_READY_NO_GPU_JOB=hf://buckets/adradar/storyforge-training/preflight/v03-r54/gpu/runs/r54-v2-.../
R54_PAID_GPU_SUBMIT_NOT_EXECUTED
```

Bucket 上传本身可能有存储或网络费用，但**没有**启动 GPU Job。不要公开 Bucket 内容，所有正式故事文本/日志/Adapter 保留私有。

## 3. 将来单次付费 `submit` — 本轮未授权，不得执行

新的 R54 GPU 运行需要 Owner **另行明确批准**，不能沿用 R53 的私有数据发布授权或此前的 HF CPU 付费批准。脚本同时要求：
- `STORYFORGE_ALLOW_PAID_GPU=YES`
- `STORYFORGE_R54_OWNER_GPU_SCOPE=R54_31_9_V2_16STEP_ONE_EPOCH`
- 精确合法 `R54_RUN_KEY`，远端完整 14 个对象，且无历史结果或 submit 占位。

实际授权后执行单次 `submit` 才会创建 A100 Large、120 分钟上限的 Hugging Face Job；在提交前先写入本地防重复目录和远端 submission marker。同步脚本还会拒绝使用非 R53 原版 SHA1 `15296f1d8438f40d727c84913ac658cf6de01cb4` 的 Label Mask 审核器。上传失败、计费 API 未确定状态或 Job 失败，都**不自动重试**：先核查 HF 平台状态，取得新的授权与新 RUN_KEY 再决定。远端标记不是跨多客户端完全原子的分布式锁，运营上应确保只从一个已授权终端提交。

## 4. GPU Worker 的真实检查顺序

1. 确认运行范围权限和 RUN_KEY；校验整套远端代码、数据、配置 SHA256。
2. 复核 R53 私有发布回执、31/9 文件 SHA256、40/40 真实 CPU 报告及旧 intake。
3. 单 CUDA A100 80GB 显存门禁；安装固定 ms-swift 4.5.3 / transformers 5.16.1 / bitsandbytes 0.50.2。
4. 在将执行的固定配置下**再次运行真实 ms-swift 40/40 Label Mask audit**。
5. 锁定 Qwen 基座 revision；仅在全部前置门禁通过后启动一次 `swift sft`。
6. 检查 **checkpoint-8、checkpoint-16、global_step==16、验证 4/8/12/16、LoRA Adapter 权重+配置哈希**。
7. 从 Validation 的模型可见历史生成无 Gold target 的单条输入，真正运行 `swift infer` 重载 checkpoint-16；验证生成非空，并比对相同 Adapter 哈希。
8. 只在这些全部通过后写入 `R54_GPU_16STEP_ENGINEERING_PASS__NOT_PROMOTED` 报告与私有日志；失败记录 `FAILED_OR_INCOMPLETE__NO_PROMOTION`，保留证据且不晋升模型。

所有 HF 输出位于私有 `hf://buckets/adradar/storyforge-training/experiments/v03-r54/<RUN_KEY>/`。**不读取 R50，任何训练 LOSS、Adapter Reload PASS 都不是盲测质量结论。**

## 5. 完成实际 Job 后 `verify`（将来才用）

将下列现有文件从该 `RUN_KEY` 的私有结果前缀下载到 Mac：
- `R54_GPU_RUN_REPORT_PRIVATE.json`
- `R54_GPU_RUNTIME_PRIVATE.log`
- `R54_ADAPTER_RELOAD_VERIFIED_PRIVATE.json`

随后只读执行：

```bash
cd ~/workspace/storyforge
R53="$HOME/.local/share/storyforge/r53-authorized-release"
RESULT="$HOME/.local/share/storyforge/r54-results/REPLACE_WITH_RUN_KEY"
python3 scripts/v03_r54_gpu_verify.py \
  --report "$RESULT/R54_GPU_RUN_REPORT_PRIVATE.json" \
  --runtime-log "$RESULT/R54_GPU_RUNTIME_PRIVATE.log" \
  --reload-report "$RESULT/R54_ADAPTER_RELOAD_VERIFIED_PRIVATE.json" \
  --release-dir "$R53/R53_FORMAL_DATA_ONLY_RELEASE_31_9" \
  --config configs/v03_r54_qlora_31_9_16step_v2.yaml \
  --out "$RESULT/R54_GPU_OWNER_INTAKE_VERIFIED.json"
```

验收器会交叉校验 run key、输入、终态和日志。它验证 Owner 返回的**报告/日志/重载回执**；**如果未下载最终 Adapter 权重，不能声称在 Mac 上独立计算了远端权重 SHA256**。

**当前最终状态：** `R54_GPU_PIPELINE_CODE_STAGED_GIT__NO_HF_SYNC_IN_THIS_CHAT__GPU_NOT_AUTHORIZED__NO_R50`。
