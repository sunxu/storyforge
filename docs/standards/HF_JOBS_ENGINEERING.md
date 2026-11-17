# StoryForge HF Jobs 工程规范

状态：R60 v1.0；Python 3.11。公共实现以 `src/storyforge_dataset/hf_runtime/` 为唯一来源，操作入口见 `skills/storyforge-hf-jobs/SKILL.md`。

> **R60 Common2 已验证操作实践（2026-11-12）**：Mac Homebrew HF CLI 2.4.0 / 独立HF SDK Python 1.6.0、组织私有Bucket精确RO/RW挂载、CPU-upgrade固定镜像、版本锁、单次提交/故障恢复、Qwen3.8 Processor/Template/无权重RoPE及实际2条严格Collator验收，统一见 [HF Jobs Mac CLI CPU2实战手册](HF_JOBS_MAC_CLI_CPU2_PLAYBOOK_20261112_CN.md)。技术PASS不代表训练许可或R50排除完成。

## 原则

1. 本地优先：能在本地或 CI 证明的基础设施行为，不消耗付费 HF Job。
2. 证据优先：Job COMPLETED 不是 PASS；必须验证输入、SAFE 输出、回收字节和 SHA256。
3. CPU/GPU 隔离：CPU Job 不推导 GPU、推理或训练授权。
4. 一次修复长期复用：业务差异放薄适配器，公共文件/资源/诊断算法只维护在 Runtime。
5. 私有数据最小暴露：公共 GitHub 只放代码、合成测试和经审查聚合证据。
6. 不静默降级：不自动重试、覆盖、Namespace fallback、权限扩张或非原子写入。

## 使用流程

- 检查 Worktree、分支、HEAD、未提交文件与 PR。
- 阅读对应业务 Runbook；检查现有实现、共享核心、缓存与 SAFE 证据。
- 运行 Doctor：`python -m storyforge_dataset.hf_runtime doctor --profile cpu --json`。
- 运行 Ruff、compileall、Runtime/Volume/业务合成测试、token_preflight 回归。
- 真实 HF CPU Job 仅用于不可本地模拟的托管 Volume 或真实 Tokenizer 行为；使用专用测试存储、CPU Flavor、唯一输出目录和单次执行。
- 下载 SAFE 文件，严格验证 Schema/状态/大小/SHA256；将结果与 Job ID、Commit、依赖和镜像版本一起记录。
- 所有 GPU 推理和训练另行审批。

## Chat Template 依赖基线：Jinja2 故障不得复发

R58 于 2026-11-01 已验证 `transformers==4.57.1`、`sentencepiece==0.2.1`、`jinja2==3.1.6`；当时缺少 Jinja2 会触发 Transformers Chat Template `ImportError`，安装后 A/B 两组真实 HF CPU Tokenizer 预检通过。R60 发生同类故障属于重复发生，后续修复必须沉淀为共享依赖基线与提交前门禁。

强制要求：\n- R60 literary reviewer 使用独立依赖输入 `requirements/hf-quality-reviewer.in`（Transformers 4.57.1、SentencePiece 0.2.1、Jinja2 3.1.6）；不得误用 R59 Qwen3.8 的 `hf-cpu-tokenizer` profile（Transformers 5.16.1）。当前 reviewer `.in` 是直接依赖定义；付费 HF Job 前必须完成 hash-pinned lock 生成与验证。
- Jinja2 显式依赖 `jinja2==3.1.6`，不得依赖镜像预装；当前已验证的 Transformers/SentencePiece 组合为 `transformers==4.57.1`、`sentencepiece==0.2.1`。
- 每个 HF Runner/Job 的依赖定义必须可复用、可审查；禁止只在单次命令临时补装。
- Job 提交前，在相同镜像/依赖安装步骤执行 `pip check`、版本/import probe，并调用目标 Tokenizer `apply_chat_template`。失败即 fail closed。
- CI 覆盖依赖 pin 和 Chat Template 冒烟测试；不得为已知缺包问题重复提交付费 Job、换 flavor 或 namespace。
- 具体 R60 故障记录与命令见 `docs/R60_HF_QUALITY_CPU_PREFLIGHT_AFTER_STAGE_20261108_CN.md`。

## Runtime 模块

`context.py`、`paths.py`、`inputs.py`、`outputs.py`、`diagnostics.py`、`resources.py`、`receipts.py` 七模块职责和 API 见 `docs/standards/R60_HF_JOBS_RUNTIME_ARCHITECTURE_V1_CN.md`。Runtime 只依赖 Python 标准库。

## Tokenizer 复用

`src/storyforge_dataset/token_preflight.py` 是唯一 Tokenization 核心，保持不变。业务 Runner 只能调用它，不能复制 `encode_chat`、token ID 提取、预算汇总或 fingerprint 算法。业务适配器负责业务输入合同、模型 Revision 和业务 SAFE 状态。

## 诊断与隐私

Runtime diagnostic schema 为 `storyforge-hf-runtime-diagnostic-v1`。业务 SAFE 回执保留业务 Schema。禁止输出 Prompt、对话、逐案标识、凭据、DSN、HF Token、异常消息、堆栈或任意私有路径。未知错误映射为稳定 allowlisted code。

## Volume 安全

输入必须 no-follow、regular file、限长读取、SHA256 校验。HF 管理 Volume 可能规范化 mode bits/link count，不能把这些元数据作为内容完整性证明。输出目标必须 create-only；优先使用 Runtime 已测试的原子 no-replace 发布，能力不足时 fail closed。不得递归修改 Volume 权限。

## 依赖与镜像

Runtime 核心 Python 3.11 标准库，无第三方运行时依赖。Tokenizer 适配器必须由业务规范单独固定 Transformers、Tokenizer 及必要模板依赖。每个 HF Job 应记录实际镜像 Digest；只有 Tag 而没有 Digest 时，标记镜像不可变性未验证。依赖锁文件必须记录版本和 SHA256。

## 状态边界

Runtime PASS 只表示基础设施检查通过。Token PASS 不等于语义审核 PASS；语义 PASS 不等于 Quality-v1 admission；Quality-v1 admission 不等于 GPU 训练授权。

## R60 Base336 GPU实验：复用与专用边界（2026-11-16）

- CPU336真实Tokenizer/Collator/R18 Label Mask证明已通过293/43原始行字节多重集合一致性转移；不重复提交CPU Job或重跑Tokenizer/Collator。只有输入字节、模型Revision、消息合同、Template、System/World卡或Label Mask算法变化时，才重新评估CPU技术审计范围。
- GPU实现复用 `storyforge_dataset.hf_runtime` 的通用输入/输出/诊断能力，复用 `r60_common2_wrapped_hf_stage.local_dependencies` 的依赖闭包方法；R54 GPU Runner仅作为已验证训练/设备/checkpoint/reload方法参考。业务差异留在R60薄适配器。
- `scripts/hf_job_guard.py` 是CPU专用Guard，拒绝GPU Flavor；不得通过放宽它来提交GPU。GPU提交必须使用独立的付费GPU执行合同和明确授权。
- R60 GPU输入Stage必须挂载精确的唯一Bucket前缀并显式RO；训练输出使用另一个独立唯一前缀并显式RW。禁止整桶 `storyforge-training:/workspace:rw` 挂载；也禁止输入与输出前缀重叠。
- 固定 `adradar` Namespace、精确模型Revision、镜像Digest、直接依赖与实际安装版本；Mac端先本地验证Stage、同步文件、核验远端完整文件集与SHA、检查组织Job历史并做CLI dry-run。Dry-run、远端READY、Job提交是不同状态。
- 每次GPU提交使用唯一Run Key、create-only Stage/结果目录、提交前O_EXCL marker和单次尝试；提交不确定时只检查组织Job历史，不自动重试、不自动切换Namespace、不覆盖旧Stage或结果。
- GPU Worker在真实输入/配置/依赖/设备门禁全部通过前不得下载模型权重或启动训练；日志/stdout只输出SAFE状态。训练后验证真实终端Optimizer Checkpoint、Adapter Reload及Owner端SAFE回执。GPU授权必须绑定具体Run Key、Flavor、时长、模型Revision、配置与预算。

权威执行合同：`docs/plans/R60_BASE336_FAST_GPU_EXPLORATORY_20261116_CN.md`。本节不把CPU-only Guard改成GPU Guard，也不改变现有HF Runtime API。

## R60 Base336 GPU链路实现状态（2026-11-17）

- 实际代码与Mac命令以 \`docs/plans/R60_BASE336_FAST_GPU_EXPLORATORY_20261116_CN.md\` 的2026-11-17章节为准。
- Stage Builder复用Common2的AST依赖闭包并绑定干净Git HEAD；私有Stage仅本地创建，目录0700、文件0600、create-only。远端输入与输出是不同Bucket前缀。
- Worker先验完整Stage Manifest、P0转移SAFE和293/43 release，再做A100 80GB、磁盘、Python/Torch/依赖版本检查；门禁全部通过后才下载固定Revision模型。训练后验证实际37步终端Checkpoint、末步Eval、LoRA Rank/Alpha和Adapter Reload。
- HF CLI只支持local preflight、sync、ready、diagnose和cli-flags；没有submit子命令。ready仅执行HF CLI dry-run，且将GPU Scope设为 \`DRY_RUN_NOT_AUTHORIZED\`。Worker Shell拒绝该Scope。
- sync上传Manifest最后；ready逐对象下载回Mac验证SHA、检查独立RW输出前缀为空、完整分页Job历史无匹配，并执行dry-run。不得将HF CLI dry-run解释为Job已创建。
- 新增离线合成工作流覆盖R60 GPU合同、Stage、Worker、CLI、共享Runtime及R54历史GPU测试；不访问HF Hub、不下载权重、不使用GPU。
