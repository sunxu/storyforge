# StoryForge R60：GLM-4 全量 25 条 Snapshot + CPU Replay 下一 Agent 交接任务书

> **当前 GLM 主线唯一权威交接（2026-11-11）。** 优先于此前单条/双条 probe、失败12条重试、Snapshot v1 和 2026-11-08/10 旧 P3/P4 待办叙述。只覆盖本轮 GLM B25 的执行与验收，不代表整个 R60 或训练已经结束。
>
> **本次交接工作只更新 GitHub 文档/任务书，不提交 HF Job，不执行 GPU，不改冻结 Runner/原始回执/Quality-v1 Rubric。** 后续所有 HF Job 均由 Owner 在 Mac CLI 手动执行。

## 1. 目标、范围与状态

**目标**：在一次 H200 Job 中加载固定 GLM-4-32B，对原始 B25 的全部25条（原始序号 1..25）连续进行生成；每次 `engine.generate()` 正常返回后，先把原始完整输出写入独立私有 Snapshot，再按冻结 Runner 原有标准校验，写新 Checkpoint 或技术失败回执；随后对真实快照进行 CPU-only Replay，统计严格校验与保守标点级修复的不同结果。

**明确不要**：再设 1–2 条试跑上限；将失败12条重试子集当成全25；在 GPU 阶段启用新增引文修复；复用原有输出目录；将技术失败计入质量 HOLD 或自动训练准入；执行 Qwen/G​​LM-Z1 GPU 任务；启动 SFT/1000条审核。

截至本任务书创建时：
- **已完成**：全量25参数模式、单引擎隔离逻辑、原始生成 Snapshot、位置1..25 CPU Replay、合成测试；原始冻结 Runner + 固定真实输入 + 合成 Snapshot 的 CPU 集成测试已获 Owner `GLM_FROZEN_SNAPSHOT_CPU_REPLAY_PREFLIGHT_PASS`（该回执**未使用** `--full25`，不能代替新的全25预检）。
- **仍未完成**：Owner Mac 使用固定全量版本执行 `--full25` CPU Preflight；Owner Mac 私有 H200 staging 与完整性预检；本轮25条真实 GPU 生成；真实25份主生成 Snapshot 的 SHA 验签；真实全25 CPU Replay；审查质量结论。
- **历史基线**：GLM 早期试验为 **13/25 VERIFIED + 12/25 TECHNICAL_FAILURE**，与本次独立全25审查无关且必须永久保留。没有证据证明本次新增有效审核、Quality-v1 训练准入或 GPU 已启动。
- **Qwen 并行待办**：A25 历史6个有效 Checkpoint、后续第7条异常的 SAFE 分阶段诊断，仍为独立任务；不能阻塞 GLM 全25，也不能把 Qwen 回执算作 GLM 结果。

## 2. 仓库、版本和冻结对象

- GitHub：`sunxu/storyforge`
- 当前工作分支：`r60/p4-generation-eval-framework`
- 活动 PR：[#30](https://github.com/sunxu/storyforge/pull/30)（交接时核实是否仍 Draft / Open，不能自动合并）
- 跟踪 Issue：[#28](https://github.com/sunxu/storyforge/issues/28)
- **运行代码 PIN：`6f2a71f12f3a2408b4082d6f8b86e69e0b5cf384`**。该提交的四组 GitHub CI（CI、R58 scoped synthetic、R60 Generation Eval CI、P4 Runtime Image Candidate）均已核验为 `completed/success`。其后仅有本执行手册相关文档变更；接手时仍须重新检查实际分支 HEAD、PR 状态和最新 CI。
- **废弃运行代码 PIN：`77da8093c831a6cb3771385b1c673ffb82143529`**。存在 `--snapshot-full25` 与 `--snapshot-probe-cases=0` 的互斥守卫问题，不可用于 H200。
- 模型：`zai-org/GLM-4-32B-0414`；revision `8dea913c41b543527c2860fb6f3c15c202f24aeb`
- 冻结真实输入25条：原输入 `source.private.jsonl`，SHA-256 `01639568cf21a7b98356f2b3b74f567943b4a6844edb9230b58759789ab67fc9`
- 冻结 Runner：与原私有输入目录同处的 `runner.py`，绝不重写、绕过或替换为新的 reviewer；代码和 Replay 将绑定其实际 SHA。
- Docker runtime：`docker.io/vllm/vllm-openai@sha256:05a31dc4185b042e91f4d2183689ac8a87bd845713d5c3f987563c5899878271`
- 原始本地路径约定：`$HOME/workspace/storyforge`；`$HOME/.local/share/storyforge/r60/private/r60-hf-quality-pilot25-vllm0100/input_B_quote_observer_v1`。路径存在性必须在 Owner Mac 上实际检验，不得宣称远程 Agent 已读到。
- 权重 Bucket：`hf://buckets/adradar/storyforge-training/model-cache/glm4-32b-8dea913-servercopy`（固定大小等上游证据，不要将 `--skip-weight-sha` 当成完整权重 SHA 验证）。
- 输出 Bucket：`hf://buckets/adradar/storyforge-training`；运行结果 `evaluation-runs/RUN_ID`；原文快照 `private-generation-snapshots/RUN_ID`。

## 3. 关键实现和不可混淆的语义

- `experiments/r58_quality/r60_glm4_b25_continuous_review.py`：全25入口需 `--snapshot-full25 --case-limit 25 --isolate-technical-failures --generation-snapshot-dir`。全25必须**无** `--retry-baseline-dir`、`--resume`、`--snapshot-probe-cases`、`--literal-probe-cases`、`--snapshot-primary-only`、`--quote-literal-repair`。不得把全25退回失败12条方案。
- `r60_glm4_full25_snapshot_entrypoint.sh`：要求唯一 RUN_ID 格式 `r60-glm-full25-snapshot-YYYYMMDDTHHMMSSZ`；两个目录必须事先**不存在**，分别按0700创建；现有目录即 HOLD。
- `r60_generation_snapshot.py`：拦截每次 `engine.generate()` 正常返回的单个输出；slot01 主生成，slot02 可为冻结 Runner 的二次修复生成（单条最多2 slot）；先原子排他持久化（0600、fsync、回读验签），后允许冻结 Reviewer 继续校验。未正常返回的推理不能保证快照。
- `r60_review_isolation_core.py`：每条1次冻结 Runner 推理入口；遇白名单 `ReviewError` 则写签名技术失败并继续；未知异常、引擎故障、快照写入失败或预算不足必须安全停止。模型只初始化一次，逐案例复用。此处 `batch-size 5` 是**分批日志/检查点节奏**，不是保证五条同时并行送入 `LLM.generate`。
- `r60_glm4_snapshot_replay.py --full25`：`row = rows[position-1]`，`original_position = position`，严格是1..25，**不是** `FAILED_POSITIONS` 的12条重试映射。仅接受从1开始连续存在的主快照，且检验完整输入 SHA、Runner digest、模型/revision、单行 digest、slot 及快照 SHA。若有 slot02 而冻结 Runner 缺少相应二次修复 API，则严格 HOLD，不可伪造回放成功。
- **质量分类**：`VERIFIED` 是冻结技术校验有效；`TECHNICAL_FAILURE` 不是 Quality-v1 `HOLD`；`CPU Replay` 的 `REPLAY_VALIDATED` 是离线重放技术结果，不自动晋升训练准入；只有实际 `response.decision` 才参与 PASS/HOLD/REJECT 汇总。

## 4. 新 Agent 执行任务（按优先级）

### P0 — 接手前事实核验（必须先做）

1. 重新读取本任务书、[全25 Owner Runbook](R60_GLM_FULL25_SNAPSHOT_OWNER_RUNBOOK_20261111_CN.md)、[Snapshot/Replay 设计与历史回执](R60_GENERATION_SNAPSHOT_CPU_REPLAY_20261111_CN.md)、[旧 GLM/Qwen 修复历史](R60_GLM_QWEN_REPAIR_TRACK_20261111_CN.md)，以及所引用的上述四个实现脚本、相关测试。
2. 用 GitHub 实时验证分支 HEAD、PR #30、Issue #28、**运行 PIN 的四组 CI**和最新 CI。若运行代码 PIN 与任务书不一致或关键代码在 PIN 之后被修改，先审查差异，不得直接混用。
3. 仅就真实阻塞做最小代码修复，补合成回归、CI，并生成**新的完整代码 PIN**；不要为简单问题重建架构或重启旧版探针。

### P1 — Owner Mac 全25 CPU 门槛（不花 GPU）

4. 给 Owner 提供可复制 Mac 命令：先 SHA 检查真实私有 `runner.py` 与 `source.private.jsonl`，然后将固定 PIN 中所需的全部脚本复制到 **新** `0700` staging，保留原输入与旧回执；不要在私有目录内原地更新脚本。
5. 用 `r60_glm4_snapshot_cpu_preflight.py --runner ... --input ... --full25` 验证 SAFE `GLM_FROZEN_SNAPSHOT_CPU_REPLAY_PREFLIGHT_PASS`（`gpu_started=false`、`model_inference_calls=0`、`private_values_emitted=false`）。注意：此预检内部仍使用**一条合成回复**，证明 `FULL25` 分支与冻结 Runner 兼容；25条完整索引/库存另由合成回归测试覆盖。
6. 确认 Owner 本地 `hf` CLI 登录及组织/桶读写路径有效。历史 ChatGPT HF 插件 Bucket RW 提交曾遇403，**不让连接器代理提交**；Owner Mac CLI 曾有 Bucket RW PASS，不需要重排 OAuth 调试。
7. 检查无旧 RUN_ID 路径、文件权限0700/0600、模板和镜像 digest、权重挂载与模型身份。可做 CPU-only、无付费云资源的 dry-run；未完成则 HOLD。

### P2 — 首次真实 H200 全25生成（仅 Owner Mac 执行）

8. **严格是一次完整25条生成**，取消1–2条限制；唯一 RUN_ID，独立私有 Snapshot 和签名回执路径，保留原始13/12历史回执，禁止 `resume` 或静默覆盖。
9. Agent 只生成完整 `hf jobs run` 命令、实际挂载参数和 SAFE 验收脚本，**由 Owner Mac 自行粘贴提交**。运行参数：`--namespace adradar --flavor h200 --attempts 1 --timeout 2h --detach`，固定 vLLM 镜像 digest，运行 `bash /input/r60_glm4_full25_snapshot_entrypoint.sh RUN_ID`。H200 自身以 `--wall-seconds 5400` 控制 reviewer 预算；2h Job timeout 与之不同。
10. 完成后按实际产物检查，不能仅看 HF Job SUCCESS/ERROR：`ALL_CASES_ATTEMPTED.attempted=25`；`SNAPSHOT_FULL25_SUMMARY.attempted=25`；25个 **slot01** Snapshot 全部可读、身份与 SHA 验证通过；每条**恰一份** VERIFIED Checkpoint 或技术失败回执；`verified + technical_failures = 25`。如果全25已尝试但有技术失败，`exit 42` 可能是预期的部分审核状态；若不足25、缺快照或回执，则没有通过生成留证验收。
11. 若遇未知异常、磁盘/桶问题、slot 溢出、模型未返回、预算耗尽，记录 SAFE 已尝试数及快照库存，明确 `PARTIAL/HOLD`；**不得为了追求25/25不经审核自动重试或覆盖已有目录**。保留成功前缀作为诊断证据，优先 CPU 分析再决定新方案。

### P3 — 真实快照 CPU Replay 与质量报告

12. 将独立私有快照受控地挂载或读取到 Owner Mac，运行 `r60_glm4_snapshot_replay.py --runner ... --input ... --snapshots ... --output ... --full25`（CPU-only）；SAFE 报告必须 `scope=FULL25` 且 `replayed_cases=25`，并通过每条引用身份与 SHA。
13. 报告区分原冻结严格校验、原有二次生成修复（若存在且可回放）、标点级实验修复的有效率；对照 GPU 新回执时注意可能不是同一层级的判定。技术有效、质量 `PASS/HOLD/REJECT`、正式训练准入分别统计。
14. 汇总 GLM 25条真实结果，对比旧13/12但不覆盖历史回执；如有效样本不足，基于同一真实 Snapshot 优先继续 CPU 定位而不是再付费生成。
15. 更新执行任务书、Issue #28、PR #30（仅评论/状态，勿合并）、SAFE 结果及明确下一阶段是否进入 Qwen/模型选择/1000条审查的建议。任何 SFT/1000批量/新 GPU 都需单独授权。

## 5. 验收表与止损条件

| 门槛 | PASS 必要条件 | 未满足时处理 |
|---|---|---|
| GitHub PIN / CI | 代码 PIN 固定、四组 CI PASS；无未审核代码漂移 | HOLD，修复并重新 PIN |
| Owner 全25 CPU Preflight | 真实冻结 Runner + 真实输入 + 合成 Snapshot，SAFE PASS | HOLD，不提交 H200 |
| 单次 H200 生成留证 | 尝试25条、主 Snapshot 25份、结果回执25份、原始旧回执不变 | `PARTIAL/HOLD`，保留已生成证据 |
| Snapshot 身份 | 每份原始25条与固定模型/Runner SHA/输入 digest/slot 一致 | HOLD，不能继续质量合并 |
| CPU Replay | `scope=FULL25`、`replayed_cases=25`、无未解释异常 | HOLD，CPU 修复或说明约束 |
| Quality-v1 | 只对真实审核决策与原 Rubric 判定；禁止自动准入 | 不越过模型校准/训练授权门禁 |

**不能声称** “25个可用审核”、`quality_v1_admitted>0`、`training_authorized=true`，除非日后另有严格证据和授权。

## 6. 已知历史坑与工程限制

- 旧 `77da809` **CI PASS 但真实全25参数在启动前 HOLD**；已在 `6f2a71f` 修正 `snapshot_probe_cases==0 and not snapshot_full25` 并补可执行条件的 CPU 测试。CI 必须结合运行入口核验。
- 前期 GLM 引文故障是来源、目标引文与冻结正文不逐字匹配。既有13/12来自旧流程；不要重新用相同 H200 重试12条。
- `GenerationSnapshotStore` 支持每条最多2个 `engine.generate` 返回。冻结 Runner 超过2次生成触发安全失败。生成尚未返回就异常，无法获得完整 Snapshot。
- slot02 CPU Replay 是可选 API：若冻结 Runner 没有 `QuoteValidationError` / `quote_candidates` / `apply_repairs`，含 slot02 的记录必须 HOLD，不能当成“已复核通过”。
- 本轮镜像权重本地化脚本使用 `--skip-weight-sha`：只证明指定上游声明/大小等路径检查，不应宣称模型权重全部逐文件 SHA 实测通过。
- GitHub 文档可写公开 SAFE 字段、命令与摘要，**不能写**私有输入正文、原始生成结果、ID Map、长期密钥或具体敏感数据。所有付费 HF Jobs 由 Owner Mac 提交。
- 旧 `docs/R60_CALIBRATION_*` 含2026-11-09/10的过时 P3/P4 “未授权”“待验证”段落，它们是历史档案。**本任务书优先用于当前 GLM 全25阶段**，但其他项目既有决议仍保持有效。

## 7. 每轮交付与下一 Agent 首次回复要求

每次回复须精确报告：GitHub 分支/PR与本轮 commit；实际运行版本 PIN；通过/未通过的四组 CI；Owner Mac SAFE JSON（如有）；GPU Job URL/状态（仅 Owner 实际提交后）；RUN_ID 和全部25条 Snapshot/回执验收数字；CPU Replay `FULL25` 数字；新增 Quality decision（不得推断）；未完成 HOLD 与下一条实际可执行命令。

**新 Agent 首次应**：核对 GitHub 真实 HEAD/PR/四组 CI → 阅读本任务书与全25 runbook → 检查全量参数与 Owner staging 前置 → 给出可直接粘贴的 Mac 全25 CPU preflight 与完整 HF CLI 命令（如任何实际前置不清楚，应先提供安全本机检查命令）→ 等待 Owner 回执再判断是否进入 H200。**不重复旧1条/2条建议，不自行启动 GPU。**

交接索引：**本文件（当前权威）** → [Owner 全25手册](R60_GLM_FULL25_SNAPSHOT_OWNER_RUNBOOK_20261111_CN.md) → [Snapshot v1 实现/历史](R60_GENERATION_SNAPSHOT_CPU_REPLAY_20261111_CN.md) → [GLM/Qwen 排障历史](R60_GLM_QWEN_REPAIR_TRACK_20261111_CN.md) → [旧 R60 项目档案](R60_CALIBRATION_EXECUTION_TASKBOOK_20261108_CN.md)。
