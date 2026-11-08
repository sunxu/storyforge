# StoryForge HF Jobs 工程规范

状态：R60 v1.0；Python 3.11。公共实现以 `src/storyforge_dataset/hf_runtime/` 为唯一来源，操作入口见 `skills/storyforge-hf-jobs/SKILL.md`。

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
