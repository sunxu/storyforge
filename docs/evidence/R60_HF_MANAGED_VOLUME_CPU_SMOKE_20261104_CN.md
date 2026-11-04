# R60 HF Managed Volume CPU Smoke 证据

日期：2026-11-04  
分支：`r60/hf-jobs-runtime`  
最终 Smoke 代码基线：`09955a254f0a462553d93b7bdac7f6e66a54c716`

## 1. 范围与隔离

本次只验证 HF Jobs Runtime 基础设施，不运行模型、Tokenizer、推理或训练。

使用两个独立私有 Bucket：
- 输入 RO：`hf://buckets/adradar/storyforge-r60-volume-smoke-input-20261104`
- 输出 RW：`hf://buckets/adradar/storyforge-r60-volume-smoke-20261104`

没有挂载或访问 `storyforge-training`。没有访问 Gold、R50、R59 冻结私有数据。

输入为 3 条合成 JSONL：
- 文件名：`synthetic.jsonl`
- 字节数：198
- SHA256：`da852b7122cb67907b15dc918bae5264b02e6d1f1ccd01908f55ee0f30caf7bd`
- Schema：`storyforge-r60-smoke-input-v1`

## 2. 远端执行记录

### Job A — 首轮发现文件系统差异

- Job：`6aeaef67c78863f9c6323d62`
- Flavor：`cpu-basic`
- Python：3.11.18
- RO mount flag、实际写入拒绝、输入 SHA256、JSONL、RW 探针均 PASS。
- SAFE 发布返回 `OUTPUT_CREATE_FAILED`。
- 输出 Bucket 未产生 SAFE 文件。

根因方向：原子发布首先使用硬链接；HF 管理 Volume 不支持该操作。随后增加 Linux `renameat2(RENAME_NOREPLACE)` 兼容路径，保留原子与 create-only 语义。若两种原子 no-replace 机制均不可用，则返回明确错误 `OUTPUT_ATOMIC_PUBLISH_UNSUPPORTED`，不降级为普通覆盖式写入。

### Job B — CPU 元数据识别修复前验证

- Job：`6aeaf068c78863f9c6323dce`
- Flavor：`cpu-basic`
- Runtime 正确识别为 `HF_JOB`。
- ResourceGuard 将平台 CPU accelerator 元数据误判为 GPU 可见，返回 `CPU_PROFILE_GPU_VISIBLE`。
- 未进入输入读取和 SAFE 写入阶段。

随后按 HF Jobs 的 CPU Flavor 元数据增加明确 CPU allowlist，并保留对 GPU accelerator 的 fail-closed 检查。诊断回执合并 allowlisted ResourceGuard checks，不输出原始环境变量。

### Job C — 最终成功

- Job：`6aeaf0c3c78863f9c6323e15`
- URL：`https://huggingface.co/jobs/adradar/6aeaf0c3c78863f9c6323e15`
- Flavor：`cpu-basic`
- Docker image：`python:3.11`
- 实际 Python：`3.11.18`
- Runtime：`HF_JOB`
- Linux：`x86_64`
- Job 状态：`COMPLETED`
- SAFE status：`PASS`

所有 19 项检查 PASS：
- `accelerator_profile`
- `cpu_profile`
- `create_denied`
- `cuda_visibility`
- `gpu_not_started`
- `hf_job_runtime`
- `input_jsonl`
- `input_record_count`
- `input_root`
- `input_sha256`
- `input_synthetic_only`
- `mount_readonly_flag`
- `nvidia_device_nodes`
- `nvidia_visibility`
- `output_root`
- `output_rw_probe`
- `output_safe_receipt`
- `runtime_no_cuda_import`
- `training_not_performed`

最终声明：
- `private_values_emitted=false`
- `gpu_started=false`
- `training_performed=false`

## 3. SAFE 回执回收与摘要

Bucket 文件：
`hf://buckets/adradar/storyforge-r60-volume-smoke-20261104/R60_CPU_VOLUME_SMOKE_SAFE.json`

- 文件存在：PASS
- 文件大小：907 bytes
- SHA256：`d66e2685c5420ea9e2cf0ded7aa5768e67b371df906aae865eb93adc3213d6f1`
- 内容读取：PASS
- 在当前工作环境按远端读取的精确字节重建文件并复算 SHA256：PASS

注意：当前证据证明了 HF Bucket -> ChatGPT 工作环境的读取和字节校验。Owner Mac 本地 CLI 下载及本机 `shasum` 复核仍为 `PENDING`，不能将其写成已完成。可用 Hugging Face CLI 在 Mac 执行：

```bash
set -euo pipefail
DEST="$HOME/.local/share/storyforge/r60/smoke-recovery"
FILE="$DEST/R60_CPU_VOLUME_SMOKE_SAFE.json"
mkdir -p "$DEST"
test ! -e "$FILE"
hf buckets cp \
  hf://buckets/adradar/storyforge-r60-volume-smoke-20261104/R60_CPU_VOLUME_SMOKE_SAFE.json \
  "$FILE"
shasum -a 256 "$FILE"
wc -c < "$FILE"
```

预期 SHA256：
`d66e2685c5420ea9e2cf0ded7aa5768e67b371df906aae865eb93adc3213d6f1`

预期字节数：`907`。

## 4. CI 证据

最终代码 HEAD：`09955a254f0a462553d93b7bdac7f6e66a54c716`

R60 Runtime CI：
- Run：`41801949307`
- Job：`126479592021`
- Ruff：PASS
- Compile：PASS
- Runtime + Volume tests：`37 passed`
- CPU Smoke adapter tests：`10 passed`
- Token preflight regression：PASS
- Runtime dependency boundary：PASS

全仓 CI：
- Run：`41801949017`
- Job：`126479590978`
- `668 passed, 5 skipped, 24 subtests passed`
- Evidence integrity：PASS

## 5. 环境识别修复

Hugging Face Jobs 文档列出的内建环境变量为 `JOB_ID`、`ACCELERATOR`、`CPU_CORES`、`MEMORY`。Runtime 现已识别 `JOB_ID`，ResourceGuard 对 CPU Flavor 和 GPU Accelerator 进行区分。

参考：
- https://huggingface.co/docs/hub/jobs-configuration
- https://huggingface.co/docs/hub/storage-buckets-access

## 6. 限制与后续

- Docker image 使用 `python:3.11` 标签；Job metadata 未返回解析后的镜像 digest，镜像 digest 固定性仍为 `PENDING`。
- Owner Mac 本地下载和 SHA256 复核仍为 `PENDING`。
- 最新代码的 GitHub CI 已通过；Owner Mac 本地对本轮新增改动的复跑记录尚未取得。
- R59 Adapter 迁移未开始。
- PR 继续保持 Draft，等待本机回执复核及后续 R59 集成审查。

## 7. 最终状态

`R60_HF_CPU_VOLUME_SMOKE_PASS__SAFE_BUCKET_READBACK_HASH_VERIFIED__OWNER_MAC_SYNC_PENDING`
