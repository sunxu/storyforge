# R60 Implementation Report

日期：2026-11-04  
Architecture：R60 Architecture Baseline v1.0  
Repository：`sunxu/storyforge`  
Branch：`r60/hf-jobs-runtime`  
Current implementation HEAD at report creation：`e75d358e8bfedd3d58b3839a864b3b8164fc2608`  
PR：[#12](https://github.com/sunxu/storyforge/pull/12)，Draft

## 1. 已交付

### 公共 Runtime

七个批准模块已实现并纳入 CI：

- `context.py`
- `paths.py`
- `inputs.py`
- `outputs.py`
- `diagnostics.py`
- `resources.py`
- `receipts.py`

P0 Doctor：
`python -m storyforge_dataset.hf_runtime doctor --profile cpu --json`

Runtime 使用 Python 3.11 标准库；不导入 Transformers、PyTorch、ms-swift 或 HF Hub；不提交 Job、不访问网络、不执行模型推理或训练。

### 真实 HF CPU Volume Smoke

Job：`6aeaf0c3c78863f9c6323e15`  
Flavor：`cpu-basic`  
Python：3.11.18  
运行时：Linux x86_64 / HF_JOB

真实验证：
- RO mount flag + 实际 create denied
- 输入 SHA256、JSONL schema、合成数据范围
- RW probe
- create-only SAFE 原子发布及 readback
- GPU 未启动、训练未执行

SAFE：
- `R60_CPU_VOLUME_SMOKE_SAFE.json`
- 907 bytes
- SHA256：`d66e2685c5420ea9e2cf0ded7aa5768e67b371df906aae865eb93adc3213d6f1`

Owner 已确认 Mac 下载文件 907 bytes，SHA256 与远端完全一致；R60-05 回收验收 PASS。

### 可复用 Skill

新增 `skills/storyforge-hf-jobs/`：
- SKILL.md / README.md
- Runtime、CPU Smoke、Diagnostics、Security、Troubleshooting references
- CPU Job、SAFE Receipt、Local Test 示例
- Skill contract tests

新增 `docs/standards/HF_JOBS_ENGINEERING.md`，并在 `AGENTS.md` 中加入必须先阅读 Skill 的跨 Agent 规则。

### R59 Pilot8 Tokenizer Runner 迁移

文件：`experiments/r58_quality/r59_semantic_prompt_token_cpu.py`

迁移到公共 Runtime：
- RuntimeContext：要求真实 HF_JOB 环境
- PathResolver：Host/Container 路径显式解析
- InputManager：no-follow、regular file、限长读取
- OutputManager：真实 RW probe、SAFE create-only 原子写入
- ResourceGuard：Tokenizer 导入前后检查 CPU profile
- DiagnosticReporter + ReceiptValidator：独立 Runtime diagnostic SAFE 回执

保留原有 R59 业务 SAFE Schema 和 Tokenization 业务合同。唯一 Tokenization 算法继续使用 `src/storyforge_dataset/token_preflight.py`；未复制算法、未修改 Prompt、Pilot8 选择、模型 Revision 或预算。

私有输入 SHA 与 Prompt fingerprint 可通过 HF protected secrets 注入，避免进入 Job command arguments。

## 2. 最新 GitHub 验证

最新 R60 CI：
- Run：`41805593941`
- Commit：`e75d358e8bfedd3d58b3839a864b3b8164fc2608`
- Ruff：PASS
- Compile：PASS
- Runtime + Volume：37 passed
- CPU Volume Smoke adapter：10 passed
- Skill contract：3 passed
- R59 Tokenizer adapter：7 tests OK
- token_preflight regression：8 tests OK
- Runtime dependency boundary：PASS

全仓 CI：
- Run：`41805593772`
- 670 passed，5 skipped，24 subtests passed
- Ruff / Tests / Evidence Integrity：PASS

### 独立 R58 scoped workflow 的未解决失败

Run：`41805593815`  
Job：`r58-synthetic`  
失败项：`test_secure_output_private_only`  
错误：`STAGING_RECEIPT_MISMATCH`，发生于 `gold_quality_review_bind.py`。

该失败不在本轮修改的 R60 Runtime、R59 Tokenizer adapter 或 Skill 测试中；同一工作流的 `r58-source-json-structure` Job 通过。此失败未被忽略或改写为 PASS；暂列为独立 R58 pipeline HOLD，需单独审查，R60 未擅自修改其审核/来源实现。

## 3. Tokenization 核心身份

`src/storyforge_dataset/token_preflight.py` 在 Architecture baseline commit `adc3876d6d0350c270e2b5fa5ccc832438fdf7ee` 的 Blob SHA 与当前 R60 分支一致：

`9ea7596c2151ee10aa1394beedc36ffeb9a7fca8`

因此共享 Tokenization 核心保持字节不变。

## 4. 尚未完成

| 项目 | 状态 | 说明 |
|---|---|---|
| Owner Mac 最新 R60/R59 回归 | PENDING | 需在最新 HEAD 上复跑本地命令 |
| R59 真实 Pilot8 CPU Tokenizer Job | NOT RUN | 尚未读取/挂载 R59 私有输入 |
| R59 双 SAFE 回执回收 | NOT TESTED | 依赖真实 R59 CPU Job |
| Docker 镜像 Digest | PENDING | HF Job 元数据只暴露 `python:3.11` Tag |
| R58 scoped synthetic | HOLD | `STAGING_RECEIPT_MISMATCH` |
| PR 最终合并 | PENDING | PR #12 仍为 Draft |

R59 真实 Tokenizer Job 不得在 Owner 本地合成回归通过前执行；执行时必须使用冻结 Prompt、固定模型 Revision、私有输入、protected secrets 和独立 RW 输出路径。CPU 授权不包含 GPU 或训练。

## 5. 安全与授权核对

- GPU authorization：NONE；未启动 GPU。
- 未执行推理或训练。
- 未访问 Gold、R50、R59 私有输入或原始审核数据。
- 未修改 Gold87/108/192/195、R50 或 R59 冻结 Prompt/来源。
- 未进行 Quality-v1 自动准入。
- 两个 R60 专用测试 Bucket 与 `storyforge-training` 隔离。
- Public GitHub 只包含代码、合成测试、工程文档和聚合证据。

## 6. 建议下一步

1. Owner 在 Mac 拉取当前分支，运行最新 Runtime、Skill、R59 adapter 和 token_preflight 合成回归。
2. 如果全部通过，按 R59 Runbook 在独立受控 Bucket 中准备冻结 Pilot8 私有输入；私有 SHA/fingerprint 仅通过 HF protected secrets 传入。
3. 运行一次 R59 CPU Tokenizer Job，回收业务 SAFE 与 Runtime diagnostic SAFE 并分别验证。
4. 记录镜像 Digest 或明确其无法固定的限制。
5. 单独定位 R58 `STAGING_RECEIPT_MISMATCH`，不得通过降低数据质量门槛处理。
6. 完成最终安全审查后再请求 Owner 审批 PR；不自动合并。
