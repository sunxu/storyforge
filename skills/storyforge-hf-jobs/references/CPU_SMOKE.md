# CPU Smoke 操作流程

## 本地门禁

先执行 Doctor、Ruff、compileall、Runtime/Volume/Runner 合成测试及 token_preflight 回归。Linux 文件系统行为必须由 Linux CI 覆盖；macOS PASS 不能替代 Linux Volume 语义。

## 输入准备

- 只用专用测试 Bucket 与合成 JSONL。
- 输入文件先在本地固定字节并计算 SHA256。
- 输入挂载为 RO；输出使用独立 Bucket/前缀并挂载 RW。
- 记录 Job 使用的 Git Commit、Python、镜像 Digest、依赖锁文件 SHA256。
- Bucket 前缀每次唯一；不覆盖历史输出。

## 提交前检查

- Namespace 必须是 `adradar`。
- Flavor 必须是明确 CPU Flavor，例如 `cpu-basic`。
- timeout 必须有限；attempt=1；禁止自动重试。
- 确认命令只调用目标 Runner，不下载模型权重、不初始化 CUDA、不训练。
- 检查挂载路径和模式；不得将私有训练 Bucket 整体 RW 挂载。

## 远端验收

按以下顺序核验：Job 创建 → Job 完成 → Runner 输出安全摘要 → 输出 Bucket 文件存在 → SAFE 文件 Schema/状态 → 文件字节数 → 本地下载 → 本地 SHA256 与远端摘要一致。

Job 页面显示 COMPLETED 仅表示进程结束，不等于业务 PASS。任何一项失败均标记 HOLD/FAIL，不自动重试。

## 费用与停止条件

仅当本地门禁全绿、真实托管 Volume/Tokenizer 行为确实无法本地证明时才使用付费 CPU Job。一次失败先分析日志和 SAFE 回执；不得连续盲目提交。CPU 授权不包括 GPU、推理和训练。

## 固定容器镜像

历史 Job 若只记录 image Tag，不能追溯证明 resolved digest。新 Linux/amd64 HF CPU Job 应使用 platform-specific digest pin：

```text
python:3.11@sha256:aa24d1f30c72a360c82754ec26aa72437ee72152123ec319415c9eb49ff16fff
```

该 manifest 对应 Python 3.11.18-trixie；Docker Hub 同时列出 index digest `sha256:390127d66a75154671aa02f62a49aa7f83c386f33cdc84a8e8f060650e2e19f8`。仅将其作为后续任务的 pinned image，不用于追认之前使用 Tag 的 Job。参见 [Docker Hub manifest](https://hub.docker.com/layers/library/python/3.11/images/sha256-aa24d1f30c72a360c82754ec26aa72437ee72152123ec319415c9eb49ff16fff)。
