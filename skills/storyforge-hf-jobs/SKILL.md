---
name: storyforge-hf-jobs
version: 1.0.0
language: zh-CN
description: 使用 StoryForge 公共 HF Jobs Runtime 准备、验证、执行和诊断 CPU Jobs；本地优先、合成测试优先、GPU 默认拒绝。
---

# StoryForge HF Jobs Runtime

## 目标

本 Skill 是后续 ChatGPT Agent、Codex 和本地开发者使用公共 Runtime 的操作入口。它不是 Job 提交器、模型加载器、训练器或数据审核器。完整 API 与稳定 Schema 以 `src/storyforge_dataset/hf_runtime/` 和 `docs/standards/HF_JOBS_ENGINEERING.md` 为准；本 Skill 不复制算法。

## 开始前必须做

1. 检查 `git worktree list`、目标 Worktree 的分支、HEAD、`git status --short`、远端和 PR 状态。不得覆盖其他 Worktree 或未提交文件。
2. 阅读 `AGENTS.md`、本 Skill、`docs/standards/HF_JOBS_ENGINEERING.md` 及对应业务 Runbook。
3. 识别本轮任务属于本地测试、合成 CPU Smoke、业务 CPU 预检、GPU 推理还是训练。CPU 授权绝不推导出 GPU 或训练授权。
4. 搜索现有公共 Runtime、`token_preflight.py`、SAFE 回执、输入指纹、现有 Runner 和历史成功 Job。优先复用；不得复制共享算法。
5. 明确输入/输出路径、挂载模式、文件名、SHA256、模型 Revision、Python/依赖/镜像版本和单次 Job 目的。缺失的事实必须标记 UNKNOWN，不得猜测。

## 固定执行顺序

1. **Doctor**：在目标 Python 3.11 环境运行 `python -m storyforge_dataset.hf_runtime doctor --profile cpu --json`。Doctor 只诊断，不提交 Job。
2. **本地门禁**：Ruff、compileall、Runtime 单测、Volume 边界测试、Runner 合成测试、token_preflight 回归测试全部通过。
3. **合成环境**：先在临时目录或 Linux CI 模拟 RO/RW Volume。覆盖 symlink、SHA 错误、create-only、原子发布、fsync、并发和清理失败。
4. **远端门禁**：只有本地测试和 GitHub CI 全部通过，且任务确实需要真实 HF 托管 Volume/Tokenizer 行为时，才提交一个有明确目的的 CPU Job。使用 `adradar` 命名空间、CPU Flavor、有限超时、单次尝试、固定输入和唯一输出前缀。
5. **回收验收**：Job COMPLETED 不是 PASS。必须下载 SAFE 回执，检查 Schema、业务状态、输入 SHA、输出字节数，并在本地重新计算 SHA256。
6. **记录证据**：提交安全聚合证据、精确 Commit、Job ID、镜像/依赖版本、测试命令和剩余限制。不得提交 PRIVATE 正文、逐案 ID、私有哈希或凭据。
7. **停止在授权边界**：CPU 预检结束后，不得自动推理、评审、准入或训练。GPU/训练须另行明确授权。

## R60 Common2 添加合成System后的CPU2复用入口（2026-11-12）

- 本轮属模型特定**业务CPU预检**，复用此前真实CPU2固定镜像、Qwen3.8/ms-swift环境和R18真实Collator；不使用Mac本地Token、没有27B权重下载/训练/GPU。新的R27/R52冻结System导致输入变化，旧无System CPU2不能作新输入PASS。
- 业务工程入口：`scripts/r60_common2_wrapped_hf_stage.py`（create-only SHA Stage）、`scripts/r60_common2_wrapped_hf_cli.py`（preflight/sync/ready/submit --execute；共享`hf_job_guard`）、`scripts/r60_common2_wrapped_hf_worker.py`（共用Runtime Input/Output/Resource），`scripts/r60_common2_wrapped_hf_receipt_verify.py`（Owner只读回执验证）。完整命令和Schema在`docs/R60_COMMON2_WRAPPED_HF_CPU_QUALITY_PIPELINE_20261112_CN.md`，Skill不复制代码或算法。
- 必须先Doctor、Ruff、Runtime/Volume、Token共享核心和业务合成测试，再新建私有Stage；真正远端只能`adradar`的CPU-upgrade/独立RO/RW，新的RUN_KEY/结果前缀，单次提交并保留提交marker。禁止向上游Quality Manifest自动导入这一技术回执。
- 仅当业务SAFE被Owner下载并独立验证，才写技术PASS；`job COMPLETED`、本地Stage PASS或dry-run PASS都不等于实际Swift Collator PASS。当前正式SFT admission与GPU许可仍为0。

### 2026-11-12 Mac统一Owner venv与只读Stage核验

Mac端统一使用独立`venvs/r60-owner`（Python3.11、仓库dev测试依赖、`huggingface_hub==1.33.0`）运行pytest/Ruff/HF CLI/私有Stage预检；旧`r60-tests`和`hf-cli`原环境不删除也不修改，HF CPU Job Linux 运行环境仍分开冻结。现有R60 Common2 wrapped Stage已出现`STAGE_FILES_HOLD`，优先`scripts/r60_common2_wrapped_hf_stage.py inventory`只读聚合SAFE；不删除`__pycache__`、不忽略未登记文件、不修改Stage Manifest、不在旧run key下重sync/submit。完整命令见`docs/R60_COMMON2_WRAPPED_HF_CPU_QUALITY_PIPELINE_20261112_CN.md`。

### 2026-11-12 CLI无 --attempts 的精确兼容门禁

HF Jobs官方文档确认默认Job执行1次。`r60_common2_wrapped_hf_cli.py`的本项目薄适配器仅在CLI help缺失项**恰好**为`--attempts`且Owner Python所用`huggingface_hub==1.33.0`时，以官方默认单次执行替代显示`--attempts 1`；保留所有其他安全选项与共享`hf_job_guard.py`不变。任何其他参数缺失、未固定SDK版本或CLI dry-run未确认必须HOLD。先运行`cli-flags`确认`attempts_mode=PINNED_CLI_DEFAULT_ONE`，然后`ready`，不得跳过提交前marker/组织历史检查。完整回归、Owner命令和当前状态见`docs/R60_COMMON2_WRAPPED_HF_CPU_QUALITY_PIPELINE_20261112_CN.md`。

## Runtime 使用约定

- 只从 `storyforge_dataset.hf_runtime` 导入公共 API。
- 使用 `RuntimeContext.detect()` 识别环境；Host Path 和 Container Path 必须显式区分。
- 输入通过 `InputManager.open_verified` 进行 no-follow 打开、大小限制和 SHA256 校验；不要把 mode bits 或硬链接数当成内容完整性证明。
- 输出通过 `OutputManager.probe` 和 `OutputManager.write_safe`；目标必须 create-only，禁止覆盖和静默降级。
- 用 `DiagnosticReporter` 记录阶段和 allowlisted 错误码；禁止打印异常正文、堆栈、Prompt、环境转储或任意私有路径。
- 用 `ResourceGuard.check_cpu_only` 检查 CPU profile；未知 GPU 状态必须 fail closed。
- 用 `ReceiptValidator` 验证 Runtime 诊断回执。业务回执仍由对应业务适配器按业务 Schema 验证。
- `token_preflight.py` 是唯一 Tokenization 共享核心。业务差异只能放在薄适配器中，禁止复制 token 算法。

## HF Job 提交安全

- 使用组织命名空间 `adradar`；禁止因 403/402 自动切换个人 Namespace。
- 输入挂载必须显式 RO；输出使用独立、唯一前缀并显式 RW。不得把训练 Bucket 整体 RW 挂载。
- 新 Smoke 必须使用专用私有测试 Bucket 和纯合成输入；不能复用 `storyforge-training`。
- 不自动重试、不自动 fallback、不扩大权限、不删除 Bucket。
- 不把仓库 Public 理解为私有数据可公开。仓库禁止包含私有训练文本、Gold/R50/R59 逐案数据、凭据和 Token。
- 任何 CPU Job 不得加载模型权重，除非业务任务明确要求 Tokenizer；Tokenizer 任务必须固定模型 Revision，并禁用 GPU。
- 本 Skill 不授予 GPU、推理或训练权限。

## 命令入口

```bash
python -m storyforge_dataset.hf_runtime doctor --profile cpu --json
ruff check src/storyforge_dataset/hf_runtime tests
python -m compileall -q src/storyforge_dataset/hf_runtime
pytest -q tests/test_hf_runtime.py tests/test_hf_runtime_volume_edges.py
python -m unittest discover -s tests -p 'test_token_preflight_core.py' -q
```

真实 HF Smoke 的参数与证据流程见 [CPU_SMOKE.md](references/CPU_SMOKE.md)。遇到错误码先查 [TROUBLESHOOTING.md](references/TROUBLESHOOTING.md)，不得通过降低安全门槛绕过。

## 明确非目标

本 Skill 不修改 Gold87/108/192/195、R50、R59 冻结 Prompt/来源/私有输入，不做 Quality-v1 admission，不自动提交 Job，不自动启动 GPU、模型推理或训练。
