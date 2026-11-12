# StoryForge：ChatGPT 直接调用 Hugging Face Jobs 的经验与当前可用路径

日期：2026-11-10
仓库：sunxu/storyforge
强制 namespace：adradar
项目 Bucket：hf://buckets/adradar/storyforge-training

## 1. 必须使用 adradar

StoryForge 的 Jobs、Bucket 和运行产物统一使用 adradar。ChatGPT 创建 Job 时必须显式传 namespace=adradar；inspect/logs 也必须显式传 namespace 与原始 Job ID。不得因为默认 namespace 不同而切换到个人账户。

## 2. ChatGPT → HF Jobs 已实测可用

2026-11-10，ChatGPT 通过 HF Jobs 接口创建并完成：
- CPU Job：6af2da25ab34849891aae99c，输出 ChatGPT to adradar HF Jobs probe。
- A100 Runtime Smoke：6af2dbbdab34849891aaef1e，状态 COMPLETED，三模型 3/3 PASS。
HF Job 元数据显示 owner=adradar、created_by=greenkeedle。A100 Smoke 证明当前组织的 GPU Jobs 创建和计费链路确实可用。

## 3. Bucket 挂载与写入必须分开判断

| 路径 | 实测 |
|---|---|
| Job 不挂载 Bucket | CPU/A100 均成功 |
| hf://buckets/adradar/storyforge-training:/workspace:ro | 成功，能读取目录 |
| Bucket RW mount / 写入 | ChatGPT 上下文 403 |
| hf buckets cp 上传 | 403，接口为 /api/buckets/adradar/storyforge-training/xet-write-token |
| Mac CLI 使用 RW / Sync Back | 历史已成功 |

结论：不能把 ChatGPT Bucket RW 失败等同于 HF Jobs 不可用，也不能据此判断组织无 Compute Credit。当前问题限定在 ChatGPT 调用上下文的 Bucket 写入凭证、Xet write token 或 RW 挂载授权；尚未证明究竟是哪一层。

曾尝试在 Job 中使用 secrets 注入 HF_TOKEN 并通过 hf buckets cp 写入，但实际仍收到 Xet write-token 403。不得记录或打印 Token 内容；在没有独立成功回执前，不把 Secret forwarding 当成已解决。

## 4. 当前 ChatGPT 直接执行的可复用办法

在不需要 Bucket RW 的 Smoke 场景：
1. ChatGPT 直接创建 adradar Job。
2. 使用固定镜像和 GitHub 固定 Commit；运行容器缺少 git 时，从 GitHub codeload 下载固定 Commit 的源码归档。
3. 模型和 Tokenizer 从固定 HF Revision 下载。
4. SAFE 写到 Job 本地临时目录，命令结束前将 SAFE JSON 输出到 Job logs。
5. ChatGPT 用 hf_jobs logs 读取回执，再提交到 GitHub 保存长期证据。

此路径已用于 P4 三模型 Runtime Smoke，真实结果为 3/3 PASS。它不依赖 Bucket RW，也不依赖 Mac CLI 代为创建 Job。

## 5. 需要继续修复的能力

- 找出 ChatGPT HF connector 的 Bucket 写入授权 / Xet write-token 403 原因。
- 单独验证 Secret forwarding 是否能为 Job 注入具有 adradar Bucket 写权限的 Token；禁止回显 Token。
- 如无法修复，继续使用 HF Job logs 回收 SAFE，再写入 GitHub；不得将 RW Bucket 标记为可用。
- 所有任务固定使用 adradar，禁止自动 fallback 到个人 namespace。

## 6. 已验证的历史挂载模式

Mac CLI 历史可用模式：两个输入卷只读、独立输出卷可写（/input:ro、/scripts:ro、/output:rw），并通过 CLI 的同步流程持久化输出。此结果不能直接外推到 ChatGPT connector 的 API 挂载路径。