# R60 Base336 训练后质量评估与 Skill 维护计划（2026-11-17）

## 1. 当前结论

**工程训练完成；独立质量评估未开始。**

- Owner 分支：`r60/common2-cpu2-owner`。
- 训练 Stage 绑定的源码 HEAD：`87bd0680c9f7321da12c70c490e2a6ebb875d503`。
- Run Key：`r60-base336-gpu-20261117T055622Z-b609cb78661d`。
- Hugging Face Job：[`6afbfd5c98dda891b5df7fd2`](https://huggingface.co/jobs/adradar/6afbfd5c98dda891b5df7fd2)，Owner 查询状态为 `COMPLETED`。
- 唯一提交回执确认 `job_submission_calls=1`、`hf_jobs_submitted=1`；没有自动重试。
- Worker SAFE：`BASE336_GPU_EXPLORATORY_ENGINEERING_PASS__NOT_PROMOTED`。
- Train / Validation：293 / 43；37/37 Optimizer Steps；1 Epoch。
- `terminal_checkpoint_verified=true`、`adapter_reload_verified=true`、`model_promoted=false`。
- `train_admitted=0`、`quality_v1_admitted=0`、`r50_read=false`。

Worker SAFE 中的 `hf_jobs_submitted=0` 是 Worker 不提交嵌套 HF Job 的固定字段；它不否定外层提交回执所记录的唯一训练 Job。

## 2. 训练证据摘要

| 项目 | 已核验值 |
|---|---:|
| GPU | NVIDIA A100-SXM4-80GB |
| GPU 总显存 | 79.2 GiB |
| 启动可用显存 | 78.8 GiB |
| 峰值显存 | 36,115 MiB |
| 模型 | Qwen/Qwen3.8-27B |
| 固定 Revision | `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` |
| LoRA rank / alpha | 64 / 128 |
| Optimizer Steps | 37 |
| Train Loss（Trainer 汇总） | 2.146966 |
| Terminal Eval Loss | 1.932103 |
| Terminal Eval Token Accuracy | 55.09% |
| Swift train runtime | 1,699.8 秒（约 28分20秒） |
| Worker 总耗时 | 1,948.8 秒（约 32分29秒） |

固定依赖：ms-swift 4.5.3、transformers 5.16.1、bitsandbytes 0.50.2、qwen-vl-utils 0.0.14、huggingface_hub 1.33.0。

训练评估日志的最终记录为 step 37/37，eval_loss=1.932103395；Trainer 汇总 train_loss=2.146966。它们是训练/验证损失指标，不是文学质量结论，也不能单独证明相对 Base 有提升。

## 3. HF 产物只读盘点与完整性边界

Owner 已对独立输出前缀完成递归文件盘点：

- 33 个远端对象，总计 5,604,774,224 bytes。
- 最终 `adapter_model.safetensors`：1,867,797,544 bytes。
- `checkpoint-37/optimizer.pt`：3,736,129,330 bytes。
- Worker SAFE、运行日志、reload 输入/输出、Trainer state、adapter config、训练日志、图表和 TensorBoard 事件均存在。
- HF Job 状态为 COMPLETED；最终 checkpoint、terminal eval、one epoch 和 adapter reload 均由 Worker SAFE 确认。

**已完成（Owner Mac SAFE，2026-11-17）：** `BASE336_GPU_RESULT_ARTIFACT_INVENTORY_PASS__NO_PROMOTION`。固定远端文件集合核验PASS，33/33对象已下载并逐个计算本地SHA256，总计5,604,774,224 bytes；Worker SAFE、checkpoint-37、terminal eval和Adapter Reload证据均再次核验通过。审计期间没有启动GPU或提交HF Job，未输出私有路径、文件名、正文或哈希，未提升模型。私有SHA清单保存在Owner Mac的独立审计目录。重要边界：这是下载对象的本地SHA256 inventory；由于Worker没有发布原始逐文件SHA，不能声称完成了“本地哈希与Worker原始哈希逐文件比对”。工具复用 `r60_base336_gpu_cli._remote_set/_remote_uri` 和 `hf_job_runner.sha256`，不写Bucket、不提交Job、不启动GPU。

## 4. 为什么 43 条 Validation 不能作为独立质量测试

- 43 条 Validation 已作为本次 `swift sft --val_dataset` 输入，并在 terminal step 37 执行 Eval。
- Trainer state 将 `checkpoint-37` 记录为 best checkpoint，best_metric 为 terminal eval_loss。
- 因此这 43 条已参与训练过程中的 checkpoint/模型选择，不能再称为未触碰的独立 Held-out，也不能用于正式模型晋升结论。
- 293 条 Train 更不能用于独立评测；293+43 的 336 条全部属于本次训练/验证池。
- Worker 只对一个 Validation 样本执行了 `swift infer` 的 128-token Adapter Reload smoke；它证明 Adapter 可加载并产生非空结果，不是完整 43 条生成评估，也没有 Base 对照臂。

R50 密封内容仍禁止读取。R47/R48/R55 已暴露开发题不能重新包装成独立测试。REAL1000/Pilot5 的旧 Reviewer 回执也不能被当成 Base336 生成输出的评测结果。

## 5. 现有工具盘点与复用边界（复核后更新）

| 现有能力 | 本轮复用方式 | 不能直接照搬的部分 |
|---|---|---|
| `src/storyforge_dataset/generation_eval/worker.py::run_generation_batch` | 优先复用注入式 Backend 批量生成核心、输入 Manifest / record count / token budget / seed / 输出 Receipt 合同 | profile authorization 与 model_role 仍需适配本轮 Base/Adapter 两臂 |
| `src/storyforge_dataset/hf_runtime/inputs.py` / `outputs.py` | 复用输入 SHA/JSONL 校验、私有输出、create-only 与 SAFE 边界 | 不为 Base336 另建通用输入/输出运行时 |
| `GenerationBackend` Protocol | 复用模型后端抽象，Base 与 Adapter 的加载差异放版本化薄适配器 | P4 已冻结模型角色、revision、依赖锁不能跨任务替换 |
| `src/storyforge_dataset/generation_eval/formal_pairing_gate.py` | 复用 prompt/message 精确配对、哈希清单、reference-label absence 检查思路 | 现有 Gate 固定三模型角色与 Pilot 样本合同，不是 Base/Adapter 两臂 Gate |
| `scripts/prepare_eval_pairs.py` | 复用逐案随机 A/B、私有 answer key 与 create-only 思路 | 旧五维字段/位置型校验不满足本轮 prompt SHA 与六维合同 |
| `experiments/r58_quality/quality_v1.py` | 唯一六维 floors（4/4/3/4/4/4）与 severe flags 来源 | 只复用规则定义；不得将模型生成回复送入源候选 `decide/summarize` 或 Gold Manifest |
| `scripts/analyze_blind_eval.py` / `scripts/export_context_blind_review.py` | 参考历史盲化映射和上下文呈现 | 旧五维 scorecard、固定 15/20 条 Exporter 不适用 |
| `scripts/hf_job_runner.py` | 可复用通用 `Runner`、哈希和非空结果检查小工具 | `make_inference_input` 仅做 Validation 第一条 smoke，不是独立 Held-out 批量 Worker |

**结论：** 生成执行核心与 HF Runtime 已存在，不再另写通用生成循环、JSONL 校验、私有输出写入或 SAFE Receipt。P2 通过前不实现正式 Pairer、Profile 或模型 Backend。P2 通过后只新增版本化 Base/Adapter 薄适配器和对应合成测试；不修改冻结 P4 Profile/CLI，不复制六维 Rubric。

## 6. 正式独立质量评估的必要条件

1. **新的独立测试来源：** Owner 已批准采用 Supabase 公开故事/公开世界设定路线，仅用于内部独立评估提示构造，不读取用户私有会话正文。来源筛选、revision、审核快照 SHA256 和最新公开权限事件绑定 8/8 通过；但截至本次复核，48 条提示包没有可核验的 JSONL/Manifest 文件与 SHA256，不能将其描述为已构造。提示包结构校验器和合成测试代码已存在，但它们不代表真实提示包存在。权威补充记录：`docs/plans/R60_BASE336_SUPABASE_PUBLIC_STORY_P2_ADDENDUM_20261117_CN.md`。当前仍是 Draft，不是冻结 Held-out；必须完成 Base336 私有来源、R50 仅元数据、R47/R48/R55 暴露题的交叉排除及 Owner 冻结。若不能取得完整语义隔离证据，对应来源保持 HOLD。
2. **固定生成合同：** Base 与 Adapter 使用相同的三个可见持久化消息、相同模型 Revision、相同上下文长度、解码参数、停止条件和输出 Token 上限；Adapter 路径固定到本次 checkpoint-37。生成参数必须先在合成测试和 CPU CLI 兼容检查中冻结，不能看过质量结果后反复调参。
3. **独立配对生成：** 每个 prompt 对 Base/Adapter 各生成一次；逐项核对 prompt SHA、消息前缀、输出数量、非空、停止/截断元数据。每案随机化 A/B，映射密钥单独 0600 保存，评审者不可见模型身份。
4. **六维盲审：** 严格复用 `quality_v1.py` 冻结六维门槛（4/4/3/4/4/4）与三个严重标记（`serious_player_agency`、`hard_fact_or_ban`、`safety_exclusion`）；评审只依据给定三消息，不推断隐藏世界设定。保留逐条证据引用、HOLD 不确定性和严重问题，不用旧五维 scorecard 替代。
5. **独立性与裁决：** 评审者必须盲化且执行独立；不同模型 ID 不等于独立。严重标记和世界事实争议由 Owner/独立裁决处理。小样本偏好统计不能被描述为总体提升或生产质量通过。
6. **单独 GPU 推理授权：** 之前授权仅覆盖本 Run Key 的一次探索性训练 Job，不包含 Base/Adapter 配对推理、GPU 评审或新的训练。未来如需 HF GPU inference，须重新提交精确 Job 目的、模型、Flavor、时长、样本数、生成 Token 上限、Bucket RO/RW 前缀和费用范围，等待 Owner 明确批准。

## 7. 下一步顺序与当前决策

| 顺序 | 工作 | 当前状态 |
|---|---|---|
| P0 | 训练 Job / SAFE / Checkpoint / Adapter Reload 证据核验 | PASS |
| P1 | 33 个远端对象下载与本地 SHA256 inventory（33/33，5,604,774,224 bytes） | PASS（Owner SAFE） |
| P2-A | Supabase 公开来源筛选、revision、审核快照和权限事件绑定 | PASS（8/8） |
| P2-B | 48 条提示 JSONL/Manifest/SHA256 | NOT_GENERATED（仅校验器与合成测试代码存在） |
| P2-C | Base336 / R50 元数据 / R47-R48-R55 语义隔离、提示独立复核、Owner 冻结 | **HOLD** |
| P3 | 复用 `generation_eval.worker` / HF Runtime，设计 Base/Adapter 两臂 Profile、Pairing 与六维审核薄适配器及合成测试 | 复用审查完成；实现等 P2-C |
| P4 | Base/Adapter 配对 GPU 推理 | 需单独授权 |
| P5 | 独立盲审、严重标记核验和 Owner 裁决 | 等 P4 |
| P6 | 模型质量结论与是否继续下一轮实验 | HOLD |

**当前最终状态：** `BASE336_GPU_EXPLORATORY_ENGINEERING_PASS__NOT_PROMOTED`，且产物审计为`BASE336_GPU_RESULT_ARTIFACT_INVENTORY_PASS__NO_PROMOTION`。P2-A 来源版本/公开权限证据 8/8 已核验；P2-B 的真实 48 条提示 JSONL/Manifest 尚未生成，只有校验器代码与合成测试。最新收到的 8 组世界来源证据仍是 `all_decisions=HOLD`，`semantic_review_completed=false`，`actual_sent_prompt_verified=false`；7 组标记为当前 Train/Validation 跨集合，全部 8 组仍未完成语义裁决。Base336 世界隔离、R50 元数据排除、R47/R48/R55 暴露排除、提示逐条复核和 Owner 冻结继续 HOLD。保持 `model_promoted=false`、`train_admitted=0`、`quality_v1_admitted=0`。在 P2-C PASS 前不实现正式 Pairer、不启动推理、不追加训练、不访问 R50 正文、不写数据库。

### Owner Mac 只读产物审计命令（已执行，保留复现记录）

```bash
cd ~/workspace/storyforge-r60-4router-review
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
RUN_KEY="r60-base336-gpu-20261117T055622Z-b609cb78661d"
OUT="$HOME/.local/share/storyforge/r60/private/r60-base336-result-audit-$RUN_KEY"
export PYTHONPATH=src:scripts:experiments/r58_quality
"$PY" scripts/r60_base336_gpu_result_audit.py --run-key "$RUN_KEY" --output-dir "$OUT"
```

该命令先只读列举HF Bucket并核对固定33对象清单、磁盘空间和本地私有目录，再逐个下载结果对象到新建私有目录，计算本地SHA256并写0600 Manifest；预计下载约5.61GB。远端大小元数据不完整时会要求至少8GiB空闲空间。下载失败留下的目录不得删除后复用；应先只读检查失败原因并另用新目录。SAFE只报告文件数/字节数，不输出私有路径、文件名、内容或哈希。


### 2026-11-17 Owner Mac 产物审计 SAFE 回执

```json
{
  "status": "BASE336_GPU_RESULT_ARTIFACT_INVENTORY_PASS__NO_PROMOTION",
  "run_key_validated": true,
  "remote_file_set_verified": true,
  "files_downloaded": 33,
  "files_hashed": 33,
  "total_bytes": 5604774224,
  "worker_receipt_verified": true,
  "checkpoint_verified": true,
  "adapter_reload_verified": true,
  "audit_gpu_started": false,
  "hf_jobs_submitted": 0,
  "model_promoted": false,
  "train_admitted": 0,
  "quality_v1_admitted": 0,
  "private_values_emitted": false
}
```

该SAFE不包含本地SHA值、逐案内容或私人路径；本仓库只记录聚合状态，不复制私有Manifest。


## 8. 2026-11-17 生成评估代码复用审查（只读盘点）

P2 来源路线已获 Owner 批准；48 条提示包尚未生成。8 组世界来源证据已收到但全 HOLD，语义隔离和 Owner 冻结仍未通过。本节只记录既有代码的复用边界，不改动运行时、不提交 HF Job。

### 推荐复用顺序

1. **生成执行核心优先复用**：`src/storyforge_dataset/generation_eval/worker.py::run_generation_batch` 是注入式 Backend 的批量生成引擎；它复用 `hf_runtime.InputManager` 校验输入 SHA/JSONL、校验 sample_id 与消息合同，并通过 `OutputManager` create-only 写私有输出，记录 finish_reason / truncation 计数。Base336 不应另写一套通用生成循环、JSONL 校验、私有输出写入或 SAFE Receipt。
2. **HF 公共基础复用**：沿用 `src/storyforge_dataset/hf_runtime/inputs.py`、`outputs.py` 的输入验签和私有输出合同；复用既有 Backend 抽象、依赖锁与镜像摘要验证模式。Base336 专属差异只放在版本化 Profile/Backend Adapter。
3. **配对与盲化复用原则**：复用 `formal_pairing_gate.py` 的 prompt 消息精确配对、哈希清单和 reference-label absence 检查思路；复用 `prepare_eval_pairs.py` 的逐案随机 A/B 和独立 answer-key 思路，但必须先补足本任务的两臂合同、prompt SHA 绑定和安全输出权限。
4. **质量规则只复用唯一来源**：`experiments/r58_quality/quality_v1.py` 是冻结六维门槛/严重标记的唯一来源（floors 4/4/3/4/4/4；三个 severe flags）。生成评估只复用这些规则定义和审核语义；不能把模型生成回复送入该模块的源候选 `decide/summarize`，更不能把它伪装为数据库最终持久化 Assistant 目标或Gold Manifest事件。

### 不能直接照搬的既有模块

- `generation_eval/profiles.py` 与 `worker_cli.py` 当前绑定 P4 的三模型角色 A/B/challenger（Qwen3-32B、GLM-4-32B、GLM-Z1-32B）和其冻结 profile。CLI 还固定 torch 2.6.0+cu124 / transformers 4.57.1；Base336 是 Qwen/Qwen3.8-27B 的固定 revision 与本轮 Adapter，训练环境依赖为 ms-swift 4.5.3 / transformers 5.16.1。P4 profile、模型授权和运行时不能跨项目/模型直接复用，也不能修改旧冻结 profile 以迁就本轮。
- `formal_pairing_gate.py` 目前强制三个角色及 S/W-pilot/W 固定样本数，不适用于 Base/Adapter 两臂；可以复用其严格消息集合哈希和无参考标签检查，但应做任务专属薄适配。
- `r60_p4_evaluation_output_schema_candidate_v1.json` 是旧三维 severity 候选，不是 Quality-v1 六维；不能拿它作本轮评分合同。
- `scripts/prepare_eval_pairs.py` 与 `scripts/analyze_blind_eval.py` 使用旧五维字段；Pairer 的输入校验偏向列表位置和消息前缀，不负责完整 prompt SHA/stop reason/token 计数绑定。不得直接产出本轮六维盲审包。
- `scripts/export_context_blind_review.py` 固定 15/20 条并使用旧五维 scorecard；不可直接用于本轮 40–60 条候选集或六维审核。
- `scripts/hf_job_runner.py` 的 `Runner`、`sha256`、`check_inference_result` 可作为通用命令/哈希/非空结果小工具；其 `make_inference_input` 只取 Validation 第一条做 smoke，不可用于独立 Held-out，也不能代替上面的批量生成 Worker。

### Base336 适配器的冻结前检查项（P2 通过后才实现）

- 两臂严格为 Base 与本次 checkpoint-37 Adapter；模型 ID/revision、Adapter SHA、Tokenizer/Chat Template、依赖锁和 runtime digest 必须固定。Base 与 Adapter 使用完全相同的提示、三个持久化可见消息（无 System）、解码参数、seed、输入/输出 Token 上限、停止条件。
- 每条输入必须由来源包绑定 prompt SHA、故事/World 组件与权限证据；私有身份 crosswalk 只留在 Owner 本机。正式测试源未确认前，不得从 661 个未准入候选、数据库或旧 P4 输入自动抽样。
- 输出需保留 prompt SHA、模型/Adapter 身份、input/output token 计数、finish reason、截断状态及结果 SHA；逐案随机 A/B，blind key 独立 0600 保存，Reviewer 不得看到模型身份。
- P2 已采用 Owner 批准的 Supabase 公开故事路线；48 条 Draft 由 8 个来源构造。仍需完成 Base336 私有 source roster / World component crosswalk、R50 仅元数据排除、R47/R48/R55 暴露排除、提示忠实性复核和 Owner 冻结。未通过则质量评估保持 HOLD。
- 本轮训练授权不包含 Base/Adapter 推理；旧 P4 的授权也不适用于 Qwen3.8-27B Base/Adapter。真实推理前仍需单独明确授权具体输入、模型、Flavor、时长、样本数、Token 上限、Bucket 前缀与预算。


## 9. 新 Agent 接手入口（2026-11-17）

- 权威交接任务书：`docs/R60_BASE336_POST_TRAIN_NEXT_AGENT_HANDOFF_20261117_CN.md`。
- P2 来源补充决策与当前状态：`docs/plans/R60_BASE336_SUPABASE_PUBLIC_STORY_P2_ADDENDUM_20261117_CN.md`。
- P2 Draft prompts 与 Manifest：`R60_P2_PUBLIC_STORY_PROMPTS_DRAFT_20261117.jsonl`、`R60_P2_PUBLIC_STORY_SOURCE_MANIFEST_DRAFT_20261117.json`（当前会话工件，需由 Owner 转存私有目录并冻结）。
- P2 结构门禁：`experiments/r58_quality/r60_base336_p2_public_prompt_package_gate.py`；测试：`tests/test_r60_base336_p2_public_prompt_package_gate.py`。
- 可直接复制的启动提示词：`docs/R60_BASE336_NEXT_AGENT_START_PROMPT_20261117_CN.md`。
- 接手时重新核验当前分支、HEAD、Actions、Issue/PR；本计划与交接文件内的 SHA/CI 都是快照，不得代替实时查询。
- 当前唯一业务阻塞是 P2 新独立 Held-out 来源/权利/上下文/World 隔离证据；Owner 未提供/批准来源前不创建正式测试包、不实现正式 Pairer、不推理。

## 9. 2026-11-18 共享 World 隔离核心与 Quality Pipeline 维护

为避免 Base336 / REAL1000 / 后续 Quality-v1 批次各自实现一套 split-conflict 算法，新增共享纯函数模块：

- `src/storyforge_dataset/world_isolation.py`：
  - `component_split_conflicts()`：只检查上游已审核赋值的 `world_component_id` 在指定 split 间是否冲突；不从 Story ID、JSONB 相等、MD5/SHA、标题、角色名或时间戳推断语义身份。
  - `validate_component_review_assignments()`：校验逐来源语义组件分配的字段、来源证据引用、版本核验声明、审核完成声明、唯一性、预期成员覆盖及 Train/Validation 冲突；只输出 SAFE 聚合，不输出私有 source/component key。
- `experiments/r58_quality/quality_v1.py` 已改为复用 `component_split_conflicts()`，原有六维 FLOORS、严重标记、Review 规则、候选结构与 `quality_v1_admitted=0` 行为保持不变。
- 新增 `tests/test_world_isolation.py`，覆盖跨 split 冲突、同 split 不冲突、缺失/非法赋值、审核字段/成员覆盖、非字符串决策、隐私输出及独立性边界。
- `.github/workflows/r60-real1000-quality-review.yml` 已纳入共享模块、`quality_v1.py` 及两组测试的 Ruff / pytest 范围；不能仅靠 Skill manifest 测试代表算法回归。
- 同步更新 `GOLD_QUALITY_PIPELINE_CN.md`、RolePlay Skill `0.1.19`、Real Quality Reviewer Skill、README、CHANGELOG 与 SAFE Manifest。

此共享 helper 仅校验结构化的语义组件分配声明；它不会把 8 个代表性 World JSON 自动判为模板，也不会代替成员级角色卡/Opening 人工审阅。当前 Base336 8 组仍全 HOLD。helper 的结构 PASS 不自动关闭历史 actual-sent、Reviewer 独立性、R50/R47/R48/R55、来源权利或 Owner 冻结门禁。

共享核心与 Quality-v1 集成代码提交 `471e2e4631405f53c74390a9eebd3732d9a6e95e` 的 GitHub Actions 已完成：`R60 REAL1000 Quality Reviewer (synthetic only)` run `44127200498` SUCCESS（Ruff 通过；离线合成回归 338 passed、2 subtests passed；RolePlay Skill manifest/reuse contract 7 passed）；`R60 Common2 Wrapped HF CPU (synthetic only)` run `44127200345` SUCCESS。随后质量标准文档提交 `5a773e14a5c63cd4808821d1dd6226ccd206ef14` 的 Actions run `44127458330` SUCCESS；当前最新 HEAD `f0e9349a8439393b2d5660ece965ac541611088a` 的 Actions run `44127961963` 也 SUCCESS。其间 `480b6fef76b07e1314eab048cf6b8d14a449cc86`、`fda3208b4298163ae6919d5c954161a8c2d9bf66`、`f0e9349a8439393b2d5660ece965ac541611088a` 均为文档状态同步，没有改变已测试的共享算法。中间版本曾因 Skill manifest 版本/哈希不同步和 Ruff 纳入不可执行历史脚本而失败，均已修正。