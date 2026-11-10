# StoryForge R60 P4 下一阶段接手任务书（2026-11-10）

## 2026-11-10 最新执行回执（覆盖下方历史基线）

当前 PR #30 分支 HEAD：`9f321579e4bb1d1d5a7d50d18a4c03af973d41cb`。该 HEAD 相对已通过工程测试的代码提交 `7e9fdf9b47aee8da02ceeee1babc7a67d2ee6be9` 仅增加/更新 3 份文档（32K 资源预算、Owner Mac CLI Runbook、本任务书），没有改动源码、测试或 Workflow。文档提交未命中三个 Workflow 的路径触发条件；不得把代码提交的 Actions 描述为文档 HEAD 新触发的 Actions。

### P4-A CPU-only Worker CLI / Bootstrap E2E：PASS

代码提交 `7e9fdf9b47aee8da02ceeee1babc7a67d2ee6be9` 对应：
- Repository CI：Run `42810266068`，completed/success。
- R60 Generation Eval CI：Run `42810265927`，completed/success；Generation Eval 合成测试 **49 passed**。
- P4 Runtime Image Candidate：Run `42810265919`，completed/success。
- 固定镜像：`docker.io/pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime@sha256:77f17f843507062875ce8be2a6f76aa6aa3df7f9ef1e31d9d7432f4b0f563dee`，`linux/amd64`。
- 实际容器内执行固定 Commit codeload source archive bootstrap、安全解压、真实 `pip install --require-hashes`、CLI `--help` 和未授权 Profile fail-closed。
- 容器 SAFE：`CPU_CONTAINER_ENTRYPOINT_FAIL_CLOSED_PASS`；archive bootstrap、hash-locked dependency install、CLI 参数解析、未授权拒绝均 PASS；runtime imports/network 均未尝试；输出目录未创建；private_values/inference/GPU/training 均 false。
- Freeze Review SAFE：`P4_FREEZE_REVIEW_READY_NOT_FROZEN`，`ready=true`、`blockers=[]`、`ready_for_profile_freeze=false`。Artifact ID `13761927972`；ZIP SHA-256 `fb9399a38d0dc042e94ef85ac98b112f74e30803367fd4ce0758bb631d240114`。
- 本次没有 HF Job、GPU、Inference 或 Training；HF GPU 费用 $0。

### 后续仍 HOLD

- Owner Mac CLI Runbook 已准备，但 Owner 尚未在 Mac 执行并回传 SAFE。
- 32K 资源预算文档已建立，H200 141GB 为首选候选；长上下文显存/时长仍未实测，预算不是 GPU 授权。
- Profile Freeze 未批准；正式 Inference/GPU/Training 仍 false。
- PR #30 仍 Open/Draft，Issue #28 仍 OPEN；不得自动合并。

---

> **本文件是当前唯一有效的下一阶段执行任务书。** 它取代旧版交接材料中“继续 P3 CPU 预检”“Worker CLI 尚不存在”“Runtime Image Candidate 运行中”等过期指令。旧文档保留审计历史，不作为执行入口。

## 1. 项目目标与当前阶段

目标：在不依赖 ChatGPT Hugging Face 连接器、不启动未经授权推理的前提下，完成 P4 Generation Eval Worker CLI 的可复用工程验收，形成可供 Owner 在 Mac CLI 执行的 HF 任务包，并准备最终 Profile Freeze 裁决材料。

仓库：`sunxu/storyforge`  
当前分支：`r60/p4-generation-eval-framework`  
PR：[#30](https://github.com/sunxu/storyforge/pull/30)，Open / Draft  
主执行 Issue：[#28](https://github.com/sunxu/storyforge/issues/28)，保持 OPEN  
本任务书创建时已核验 HEAD：`a1db1ac70fd3777d78460eee58e7d2b891867c40`。新 Agent 启动时必须重新查询分支 HEAD、PR #30 和当前 HEAD 的全部 Actions；不得把此 SHA 的 CI 结果套用到后续提交。

## 2. 已完成事实（不可重复执行）

### 2.1 前置阶段
- P0、P1、P2-A、P2-B：完成；保留既有语义 HOLD，不重做、不改历史裁决。
- P3 三模型 CPU tokenizer/template/token-budget 预检：PASS。
- P4 三模型 GPU Runtime Smoke：此前经单独授权，3/3 PASS。该 Smoke 是短合成输入加载/生成检查，不证明完整 32K 预算可运行，也不授权正式评估。
- Prompt v1 / Output Schema v1：Owner 已批准，批准范围仅限其 SHA-256 对应内容。
- Sampling Decision 与 Development20 sensitivity arm / Locked30 primary-only 约束已落实。

### 2.2 当前分支工程交付
- 独立包 `storyforge_dataset.generation_eval` 已实现。
- `worker.py` 保持模型无关，不导入 torch / transformers / HF Hub。
- `worker_cli.py` 已提供独立执行入口：`python -m storyforge_dataset.generation_eval.worker_cli`。
- CLI 包含 fail-closed profile 授权、依赖锁 SHA、运行镜像 digest、Python/runtime 版本、manifest、输入校验、GPU/BF16、模型 revision/template/tokenizer hash 校验；私有输出 create-only、0600，stdout 仅 SAFE。
- Job bootstrap 从固定 GitHub Commit 下载源码归档，安全检查归档路径/文件类型/大小并拒绝路径穿越、符号链接和特殊文件；依赖通过 `--require-hashes` 安装。
- 运行镜像固定为 Linux/amd64：
  `docker.io/pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime@sha256:77f17f843507062875ce8be2a6f76aa6aa3df7f9ef1e31d9d7432f4b0f563dee`
- 依赖锁：`requirements/hf-generation-eval.lock`，SHA-256 `81b0006536695f1552161302515f1f154d65b3b32a8520a34e774b4e518ceb4c`。
- 最新已核验 CI：Repository CI PASS（1010 passed、5 skipped、42 subtests passed）；R60 Generation Eval CI PASS；P4 Runtime Image Candidate PASS。镜像报告 Python 3.11.11、PyTorch 2.6.0+cu124、CUDA build 12.4；锁文件在镜像内 `pip install --dry-run --require-hashes` 通过。Hosted CI 没有 GPU，因此不是 GPU 运行验收。
- CPU-only Freeze Review SAFE：`P4_FREEZE_REVIEW_READY_NOT_FROZEN`，`ready=true`、`blockers=[]`。这只表示审查候选材料可供 Owner 裁决；不是 Profile Freeze，不是推理授权。

### 2.3 当前明确未完成
- Worker CLI/bootstrap 的完整 CPU-only 端到端执行验收尚未形成独立、充分的最终回执。
- 尚未证明实际 HF 运行容器从源码归档启动到 Worker CLI 的全链路；不得把编译检查或 FakeBackend 测试说成端到端运行 PASS。
- 当前 P4 输出挂载和 SAFE 回收方案仍需 Owner Mac CLI 验证；ChatGPT 不执行 Bucket 测试。
- 28,672 输入 + 4,096 生成的长上下文显存、运行时间、费用尚缺真实证据。
- Profile 尚未正式冻结。

## 3. 下一 Agent 的唯一工作顺序

### P4-A：CPU-only Worker CLI / bootstrap 端到端验收（第一优先级）
1. 刷新 GitHub 当前分支、PR #30、Issue #28、当前 HEAD 的所有 Actions 和 artifact；记录精确 SHA。
2. 阅读本任务书、最新提示词、P4 Framework、Evaluation Plan、Runtime and Stop Policy、Worker CLI / plan / backend / tests。
3. 补齐测试，至少覆盖：
   - 未授权 profile 在导入 torch/transformers、网络访问、模型下载或创建输出目录之前 fail-closed；
   - 授权字段缺失/false、runtime digest 不符、lock SHA 不符、Python/torch/transformers 版本不符；
   - manifest schema、input SHA、record count、token budget、role/message 结构错误；
   - 输出目录非 `/output` 直接子目录、已存在、符号链接、权限不符、覆盖写入等拒绝路径；
   - bootstrap 归档下载与安全解压的路径穿越、链接、特殊文件、大小/文件数/解压体积限制；
   - 无 git 的基础镜像环境下，源码归档 bootstrap 可工作；
   - 合成 FakeBackend 的 CLI 完整路径：仅在显式合成测试夹具中替代模型加载，不允许伪造真实 GPU/模型 PASS。
4. 建立 CPU-only 容器入口自检：使用 digest 固定镜像，禁用 GPU、禁止模型权重下载、只使用合成输入；验证 Python 入口、依赖 import、CLI 参数解析和 fail-closed 回执。若本地容器架构不匹配，明确记录，不得伪报镜像平台 PASS。
5. 对任何新增测试/实现，先本地复现，再提交；不重写现有 runtime 或旧训练 runner。

验收要求：给出真实命令、精确输入/输出、测试计数、容器镜像 digest、SAFE schema/status、无 GPU/无 inference/无训练证明。未覆盖的项目列为 HOLD。

### P4-B：Owner Mac CLI 执行包（ChatGPT 只准备，不代执行 HF）
可复制的 Owner CPU-only 镜像/CLI 自检命令见 [Owner Mac CLI Runbook](R60_P4_OWNER_MAC_CLI_RUNBOOK_20261110_CN.md)。该命令只验证未授权 Profile 的 fail-closed，不提交 HF Job、不测试 Bucket。
1. 生成一组可复制的 Mac CLI 命令：校验分支/commit、镜像与 lock SHA、CPU-only bootstrap/CLI 自检。
2. 若需提交 HF Job，由 Owner 自行判断并在 Mac CLI 执行；本 Agent 仅提供命令、Job 配置建议、费用上限、SAFE schema 和回执审查。
3. 输出目录必须与输入目录隔离；私有正文只留在受控私有存储，不写 GitHub、Actions log 或 SAFE。
4. 要求 Owner 回传 SAFE 和必要的脱敏日志；不得要求回传生成正文、token、DSN 或私有案例。

### P4-C：32K 长上下文资源预算
资源预算与证据等级见 [P4 32K 长上下文资源预算](R60_P4_32K_RESOURCE_BUDGET_20261110_CN.md)。该文档区分短输入 A100 实测、KV cache 理论值与 32K 未验证估算；首选 H200 141GB，但不构成 GPU 授权。
1. 分别核算三模型 BF16 权重、KV cache、CUDA context、临时张量和运行时开销；明确 batch size、并发、输入/输出长度和显存余量假设。
2. 将已完成的短输入 GPU Smoke 与 32K 长上下文能力严格区分。
3. 预算要列出 GPU flavor、预估时长、单价来源/检索日期、单阶段费用上限、失败停止条件；价格需在执行前重新核验。
4. 不可仅凭参数量估算声称 32K 一定可运行；没有实测数据时结论应是预算估计或 HOLD。

### P4-D：最终 Profile Freeze Review 包
1. 对齐三模型 revision、tokenizer/template/generation config hashes、EOS/PAD、sampling、seed、Prompt v1、Schema v1、runtime digest、lock SHA、context/input/output budget。
2. 解释所有模型特定采样决策与 finish_reason/stop 规则；不得擅自更改已批准契约。
3. 汇总 P4-A/B/C 证据，列出全部未解决 HOLD。
4. 形成 Owner 裁决包。Owner 明确批准前，`profile_freeze_authorized=false`。

## 4. Hugging Face 暂停规则（强制）

Owner 已明确决定：暂停 ChatGPT HF 403 / OAuth / Bucket RW 排查，后续 HF Job 由 Owner 在 Mac CLI 执行。

本 Agent 与 ChatGPT：
- 不提交 HF Job；
- 不测试 Bucket RW/RO，不做 Bucket 写读删探针；
- 不修改 OAuth、scope、Bucket ACL、Trusted Publishers；
- 不切换个人 namespace，不索取长期 PAT；
- 不把连接器 403 作为主线阻塞，不重复排查；
- 只提供可复用代码、Mac CLI 命令、配置、验收标准、SAFE schema 和回执分析。

历史故障文档保留，仅作背景。Owner 后续主动提供新的 HF SAFE/日志时，才按该证据进行分析。

## 5. 授权和数据边界（不可放宽）

当前授权：
- `profile_freeze_authorized=false`
- `inference_authorized=false`
- `gpu_authorized=false`
- `training_authorized=false`
- `runtime_smoke_authorized` 的历史一次性授权已消费，不得复用。

禁止：
- 不运行正式 Development20 / Locked30 推理；
- 不访问 Locked30 私有案例，不启动 1000 条审核；
- 不执行 SFT/训练；
- 不上传私有 prompt、案例正文、模型输出、盲化映射、Owner labels、凭据、DSN；
- 不将 CI 合成测试、短 Smoke、CPU Freeze Review 夸大成正式评估通过。

允许：
- GitHub 代码、测试、公开文档与 SAFE 聚合值；
- 本地 CPU-only 合成测试；
- Owner 明确授权后，由 Owner 自行执行的 HF 任务。

## 6. PR / Issue 工作约束

- PR #30 保持 Open / Draft；不自动合并、不改 base、不关闭。
- Issue #28 保持 OPEN；追加进展与验收证据，不覆盖历史评论。
- 所有代码/文档修改都在 `r60/p4-generation-eval-framework` 分支。
- 每次提交后重新核验该精确 HEAD 的 Actions；不得引用旧 SHA 的 CI 结果。
- 代码改动前检查工作树/分支，避免覆盖 Owner 未提交工作；Agent 不可直接访问 Owner Mac worktree 时，应提供命令由 Owner 执行。

## 7. 最终交付清单

- [ ] Worker CLI fail-closed 测试覆盖完整。
- [ ] bootstrap 归档安全测试覆盖完整。
- [ ] CPU-only 容器入口自检 PASS。
- [ ] Mac CLI 执行说明可复制、可复现（Runbook 已建立；Owner 实机回执仍 HOLD）。
- [ ] 输出隔离与 SAFE 回收方案明确，并由 Owner Mac 验证或明确 HOLD。
- [ ] 32K 资源预算与证据等级明确（预算文档已建立；Owner 裁决和长上下文实测仍 HOLD）。
- [ ] 最终 Profile Freeze Review 包完成，未授权状态仍明确。
- [ ] 当前 HEAD 的全部 CI 回执核验完成。
- [ ] Issue #28 更新，PR #30 描述与代码状态一致。
- [ ] Owner 收到最终裁决包；没有擅自冻结或启动正式评估。

## 8. 当前已知权威回执

- Repository CI：PASS；1010 passed / 5 skipped / 42 subtests passed。
- R60 Generation Eval CI：PASS。
- P4 Runtime Image Candidate：PASS。
- Freeze Review SAFE artifact：`r60-p4-freeze-review-safe`，artifact ID `13757872717`；ZIP SHA-256 `207c87c375efbe9d6f8e6985749a04206d8e5c325819ffef0c88fa754a7f1b69`。
- Freeze Review status：`P4_FREEZE_REVIEW_READY_NOT_FROZEN`；`ready=true`、`blockers=[]`、`ready_for_profile_freeze=false`。
- 以上是 HEAD `a1db1ac70fd3777d78460eee58e7d2b891867c40` 的历史快照；后续提交必须重新跑 CI。

## 9. 汇报格式

每次汇报简明回答：
1. 本轮做了什么（代码/文档/命令）；
2. 哪些真实测试通过、精确 HEAD 与 Actions；
3. SAFE 状态与授权标志；
4. 资源和费用；
5. 尚存 HOLD；
6. 下一项可执行动作。

不得用“已完成”描述尚未实际执行的工作。
