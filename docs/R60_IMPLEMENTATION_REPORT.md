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
| Owner Mac R60/R59 regression | PASS (reported) | Runtime, volume, Skill, adapter, shared token_preflight and doctor checks passed before the real CPU Job |
| R59 真实 Pilot8 CPU Tokenizer Job | COMPLETED / BUSINESS HOLD | 8 cases tokenized; 2 over budget; see 2026-11-04 integration addendum |
| R59 双 SAFE 回执回收 | PASS | Both SAFE files recovered locally and SHA256 recorded |
| Docker 镜像 Digest | PENDING | HF Job 元数据只暴露 `python:3.11` Tag |
| R58 scoped synthetic | HOLD | `STAGING_RECEIPT_MISMATCH` |
| PR 最终合并 | PENDING | PR #12 仍为 Draft |

R59 真实 Tokenizer Job 已按 Owner 授权执行；后续重复执行仍须先通过 Owner 本地合成回归；执行时必须使用冻结 Prompt、固定模型 Revision、私有输入、protected secrets 和独立 RW 输出路径。CPU 授权不包含 GPU 或训练。

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


## 7. 2026-11-04 追加：CPU 依赖锁与镜像策略

CPU Tokenizer 依赖配置已新增：
- `requirements/hf-cpu-tokenizer.in`
- `requirements/hf-cpu-tokenizer.lock`（30 个直接/传递依赖固定版本，包含 SHA256 hashes）
- `requirements/README.md`
- `.github/workflows/r60-hf-cpu-lock-resolve.yml`

Lock SHA256：`a48957b2337d703f4629206663e74d9986482c6905e63013a46dc8662204cfba`。

锁文件工作流 Run `41807222164` PASS：重新解析与提交锁内容一致；在无 pip cache 条件下执行 `pip install --require-hashes`；`pip check` PASS；实际导入 Transformers 5.16.1、Tokenizers 0.23.3、huggingface-hub 1.33.0、Jinja2 3.1.6；确认 PyTorch 未安装。该 profile 不安装 ms-swift、vLLM、torchvision、decord 或 CUDA。

Docker 官方镜像当前 `python:3.11` 标签对应 Python 3.11.18-trixie。当前 Linux/amd64 manifest digest 为 `sha256:aa24d1f30c72a360c82754ec26aa72437ee72152123ec319415c9eb49ff16fff`，index digest 为 `sha256:390127d66a75154671aa02f62a49aa7f83c386f33cdc84a8e8f060650e2e19f8`。来源：[Docker Hub python:3.11 manifest](https://hub.docker.com/layers/library/python/3.11/images/sha256-aa24d1f30c72a360c82754ec26aa72437ee72152123ec319415c9eb49ff16fff)。

R60 初始 Volume Smoke 的历史 Job 元数据没有提供 resolved digest；本次 R59 Pilot8 Job 使用了 platform-specific digest pin：`python:3.11@sha256:aa24d1f30c72a360c82754ec26aa72437ee72152123ec319415c9eb49ff16fff`。


## 2026-11-04 macOS host-path compatibility fix

Owner's first local run passed Ruff, 48 Runtime/Volume/Skill tests, shared token_preflight 8/8, CPU doctor, and immutable-core comparison. Two R59 adapter tests failed because macOS temporary paths traverse an OS-managed symlink ancestor (commonly `/var -> /private/var`), which the HF managed-mount root validator correctly rejects.

Fix commit: `ddf2ea3419fb2f0a1b772e0ff0c54aed065fe5c0`.
- R59 helper defaults now use strict `path_kind="container"`.
- Managed mount root validation remains mandatory for container input/output paths.
- Local synthetic tests explicitly pass `path_kind="host"`; this skips only the managed-mount root check. Final input still uses InputManager no-follow/descriptor/size verification, and final SAFE publication still uses OutputManager create-only atomic writing.
- Symlinked final input files remain rejected.

Latest GitHub validation at this commit:
- R60 HF Runtime CI Run `41808603414`: SUCCESS; Ruff, Compile, Runtime, Volume, Skill and R59 adapter tests all passed.
- Repository CI Run `41808603086`: SUCCESS; tests and Evidence Integrity passed.
- CPU tokenizer dependency lock Run `41808603081`: SUCCESS.
- R58 scoped synthetic Run `41808603506`: FAILURE at its existing Environment and scoped test baselines step; remains separately held and must not be treated as an R60 regression without inspecting that job's log.

Owner pulled the fix, reran the local regression, and completed the real R59 Pilot8 CPU Tokenizer Job. Its Runtime diagnostic passed; the business token-budget result is HOLD (2 of 8 over budget).


## 2026-11-04 R59 Pilot8 CPU Tokenizer integration — superseding status

This section supersedes earlier statements in this report that the real R59 Pilot8 CPU Job had not run.

### Executed Job

- Job ID: `6aeb0f8f0e0338d1bb7fb6c1`
- Flavor: `cpu-basic`
- Runtime: Python 3.11.18, Linux x86_64, `HF_JOB`
- Image: `python:3.11@sha256:aa24d1f30c72a360c82754ec26aa72437ee72123ec319415c9eb49ff16fff`
- Executed commit: `96cdb76d4b7e61d2a34216d70d45396e66163e2a`
- R60 branch HEAD at Job execution: same full commit; subsequent branch commits in this update are documentation/evidence-only
- Commit parity evidence: [R60_R59_COMMIT_PARITY_20261104.md](evidence/R60_R59_COMMIT_PARITY_20261104.md)

### Runtime result

Runtime diagnostic status: `PASS`, phase `COMPLETION`.

Checks passed: CPU accelerator profile, input open verification, prompt contract, RuntimeContext, CPU-only resource checks, tokenizer dependency import, tokenizer load, tokenization completion, and business SAFE write.

- `gpu_started=false`
- `training_performed=false`
- `private_values_emitted=false`
- `r50_accessed=false`
- `quality_v1_admitted=0`

### Business Tokenizer result — HOLD

The tokenizer completed all 8 frozen Pilot8 cases using `Qwen/Qwen3-32B`, pinned revision `9216db5781bf21249d130ec9da846c4624c16137`, Transformers `5.16.1`, max model length 32,768, and reserved output 2,400 tokens.

- Prompt token min: 3,460
- Median: 7,139
- P95: 106,839
- Maximum: 106,839
- Over-budget cases: 2 of 8
- Maximum total tokens including reserved output: 109,239
- Business status: `R59_PILOT8_HF_CPU_TOKEN_OVER_BUDGET__HOLD`

This is a successful Runtime execution and a HOLD business result. It is not a Runtime failure and does not authorize prompt truncation, candidate admission, or training.

### Recovered SAFE receipts

Both output files were synchronized back to the Owner's Mac and their SHA256 values were recorded:

| Receipt | SHA256 |
|---|---|
| `R59_PILOT8_R60_CPU_TOKEN_SAFE.json` | `72909e5d33fe08724ec857d2e9ccd08d855d2070662c6d40e25d1eb412778e55` |
| `R59_PILOT8_R60_RUNTIME_DIAGNOSTIC_SAFE.json` | `5763eefcdaeaf21c59b5bf83d5736d4bf4e683d945cac08677ba1207474ea0f8` |

Private prompt contents, private input SHA256, prompt fingerprint, and per-case text are intentionally omitted from this public report.

### Updated status

- R59 real CPU Tokenizer Job: `COMPLETED`
- Runtime diagnostic: `PASS`
- Business token budget: `HOLD` (2/8 over budget)
- Dual SAFE recovery: `PASS`
- Commit parity: `PASS`
- GPU / inference / training: `NOT PERFORMED`
- Quality-v1 admission: `0`

Earlier statements that the R59 CPU Job and dual SAFE recovery were NOT RUN / NOT TESTED are superseded by this section.


## 2026-11-04 R60-A convergence CI refresh

At the documentation/evidence-only branch head after the R59 integration record, GitHub reports:

- Repository CI Run `41833120383`: SUCCESS.
- R60 HF Runtime CI Run `41833120491`: SUCCESS.
- R60 HF CPU tokenizer dependency lock Run `41833120402`: SUCCESS.
- R58 scoped synthetic Run `41833120375`: FAILURE; remains a separately scoped R58 HOLD and is not relabeled as an R60 pass.

All commits added after the R59 Job commit are documentation/evidence-only changes to the R60 report, handoff, and commit-parity evidence. No Runtime module, R59 adapter, tokenization core, frozen prompt, or private data changed after the R59 Job.

R60-A scope decision: the four proposed peripheral tools are not being implemented in this PR. They remain future additive work after API overlap review; only a concrete defect blocking the approved Runtime contract can justify expanding R60 scope.
