# StoryForge R60 Base336 训练后阶段：新 Agent 权威交接任务书（2026-11-17）

> **本文件是 `r60/common2-cpu2-owner` 分支 Base336 训练后阶段的当前交接入口。** 训练、产物审计和代码复用盘点已完成；独立质量评估尚未开始。先重新核验 GitHub 当前状态，再执行本文件。不要把其他 R60/P4/REAL1000 任务书中的旧授权套用到本任务。

## 1. 一分钟接手摘要

| 项目 | 当前权威事实 |
|---|---|
| 仓库 | `sunxu/storyforge` |
| 工作分支 | `r60/common2-cpu2-owner` |
| 本交接编写时基线 HEAD | `0b6d7f79911a0df9710cfde7743660c6aa1fe25c`；接手时必须重新查询 |
| 训练 Run Key | `r60-base336-gpu-20261117T055622Z-b609cb78661d` |
| HF 训练 Job | `6afbfd5c98dda891b5df7fd2`，Owner 已确认 COMPLETED |
| 训练输入 | 293 Train / 43 Validation；37/37 optimizer steps；1 Epoch |
| Worker 结果 | `BASE336_GPU_EXPLORATORY_ENGINEERING_PASS__NOT_PROMOTED` |
| 产物审计 | `BASE336_GPU_RESULT_ARTIFACT_INVENTORY_PASS__NO_PROMOTION`，33/33，5,604,774,224 bytes |
| 产物 SHA 边界 | 下载对象本地 SHA256 inventory；不是与 Worker 原始逐文件 SHA 比对 |
| 模型状态 | `model_promoted=false` |
| 训练/质量准入 | `train_admitted=0`、`quality_v1_admitted=0` |
| 独立质量评估 | 尚未开始；P2 独立 Held-out 来源为 HOLD |
| 新推理/GPU/HF Job | 均未授权；不得启动 |

**关键结论：** Base336 的工程训练闭环与输出对象本地完整性盘点均通过，但没有任何独立文学质量结论。43 条 Validation 已参与训练期 Eval / Checkpoint 选择，293 条 Train 与其余 Validation 均不得作为独立测试。训练成功、Checkpoint 可加载、SHA inventory 完成，都不等于模型质量通过或准入。

## 2. 先读的权威材料（按顺序）

1. `AGENTS.md`：仓库级安全、协作和权限规则。
2. 本文件：`docs/R60_BASE336_POST_TRAIN_NEXT_AGENT_HANDOFF_20261117_CN.md`。
3. 当前主计划：`docs/plans/R60_BASE336_POST_TRAIN_QUALITY_EVALUATION_20261117_CN.md`。
4. 独立启动提示词：`docs/R60_BASE336_NEXT_AGENT_START_PROMPT_20261117_CN.md`。
5. `docs/standards/GOLD_QUALITY_PIPELINE_CN.md`：六维质量与 Gold Manifest 的边界。
6. `skills/storyforge-roleplay-sft/SKILL.md` 与 `skills/storyforge-roleplay-sft/MANIFEST_SAFE.json`。
7. `skills/storyforge-real-quality-review/SKILL.md`：仅了解 Reviewer 证据、独立性和私有数据边界；不得自动恢复 REAL1000 批次。
8. `src/storyforge_dataset/generation_eval/worker.py`、`profiles.py`、`worker_cli.py`、`formal_pairing_gate.py`。
9. `src/storyforge_dataset/hf_runtime/inputs.py`、`outputs.py`。
10. `experiments/r58_quality/quality_v1.py`、`scripts/prepare_eval_pairs.py`、`scripts/analyze_blind_eval.py`、`scripts/export_context_blind_review.py`。

旧文档 `docs/plans/R60_BASE336_CPU_PROOF_TRANSFER_NEW_AGENT_HANDOFF_20261116_CN.md` 仅保留 P0/CPU 证据历史，已由本文件取代其“下一步立即开发 GPU Stage/Worker/CLI”的旧指令。P4 交接材料属于另一条三模型任务线，不是 Base336 授权。

## 3. 已完成事实与证据等级

### 3.1 训练工程闭环

- 模型：`Qwen/Qwen3.8-27B`，Revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`。
- GPU：NVIDIA A100-SXM4-80GB；LoRA rank/alpha 64/128。
- 293 Train / 43 Validation；37/37 Optimizer Steps；1 Epoch。
- Terminal Checkpoint、Terminal Eval、Adapter Reload 均由 Worker SAFE 证据确认。
- Train loss / Eval loss / Token Accuracy 是训练工程指标，不是文学质量评分，也不能单独证明 Adapter 优于 Base。
- Worker SAFE 的 `hf_jobs_submitted=0` 是 Worker 不提交嵌套 Job 的字段；外层唯一训练 Job 由提交回执记录为 1 次。不得混淆。

### 3.2 33 个输出对象审计

Owner Mac 已返回 SAFE：

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

SAFE 只证明固定远端文件集合核验、33/33 下载和本地 SHA256 inventory、Worker/Checkpoint/Adapter Reload 证据复核。Worker 未发布原始逐文件 SHA，因此禁止声称本地 SHA 与 Worker 原始 SHA 逐文件 MATCH。私有 Manifest、哈希值、绝对路径、文件名、原文和逐案身份不得复制进 GitHub 或聊天。

## 4. 当前门禁与不可逾越边界

| 阶段 | 当前状态 | 放行条件 |
|---|---|---|
| P0 训练证据 | PASS | 已完成，不重跑训练 |
| P1 产物完整性 inventory | PASS | 已完成，不重复下载或覆盖本地私有审计目录 |
| P2-A Supabase 来源版本/公开权限 | PASS（8/8） | 8 条公开来源 revision、审核快照 SHA 和最新公开权限事件绑定已核验 |
| P2-B 48 条提示 Draft / Manifest / SHA / 结构门禁 | PASS（结构门禁 8/8 测试） | 仅 Draft；尚未 Owner 冻结 |
| P2-C Base336 World 语义隔离、R50 元数据排除、R47/R48/R55 暴露排除、提示独立复核 | **HOLD** | 必须有完整私有 crosswalk、保护集元数据证据、独立 Reviewer 与 Owner 冻结 |
| P3 Base/Adapter 两臂生成评估适配器 | 复用审查完成；实现等待 P2-C | P2-C 通过后，先做 Schema/Profile 设计、合成测试和 CPU-only 兼容检查 |
| P4 Base/Adapter GPU 配对推理 | **未授权** | 另行明确授权具体模型、Job、样本数、Token 上限、Flavor、时长、Bucket 前缀与费用 |
| P5 独立盲审与 Owner 裁决 | 未开始 | P4 结果齐备、Reviewer 独立性与盲化可验证 |
| P6 质量结论/模型晋升 | HOLD | P2-P5 全部有独立证据；Owner 决策 |

必须保持：
- `model_promoted=false`、`train_admitted=0`、`quality_v1_admitted=0`。
- 不访问 R50 正文；如需排除，只使用经授权的完整元数据证据，不读取密封题目内容。
- 不将 43 Validation、293 Train、R47/R48/R55 已暴露开发题、REAL1000/Pilot5 旧 Reviewer 回执或 P4 旧测试题冒充 Base336 独立 Held-out。
- 不从 661 个未准入候选、生产数据库、旧 P4 数据或历史缓存自动抽样。
- 不修改冻结 293/43、旧 checkpoint、原始训练产物或 Gold 数据；不写数据库，不向 Gold Quality Manifest 追加生成评估事件。
- 不新增训练、不启动推理、不提交 HF Job、不下载模型权重，除非后续获得对应的独立明确授权。
- PRIVATE 原文、Owner crosswalk、blind key、逐案结果、原始生成文本、私有路径和密钥不得进入 GitHub、CI 日志或聊天。

## 5. P2：Supabase 公开故事来源与独立性审查（当前唯一业务阻塞）

Owner 已批准新的来源路线：仅使用 Supabase 中已公开、已发布、非删除、原创并通过审核的故事，以及公开 World/Character/Opening 字段，构造内部评估提示；**不读取用户私有会话正文**。该授权仅覆盖内部评估提示构造，不扩展为训练、公开发布或再分发权利。

### 5.1 已完成的来源和提示 Draft

只读筛选得到：

- 8 个公开故事、8 个故事谱系、5 位作者、8 个不同 World JSON。
- 3 条来源在 Base336 GPU Run 开始前创建，5 条在 Run 开始后创建；全部晚于 Base336 293/43 数据包冻结边界。
- 8/8：当前公开 revision 与最新审核提交 revision 一致；审核快照中的 `source.v2Data` 与当前公开版本一致；审核快照 SHA256 与提交 SHA 一致；最新权限事件绑定最新提交且目标可见性为 public。
- 另有 2 条候选因 World 描述过少未入选；不将其判为质量失败。

已构造 48 条全新提示 Draft：8 个来源各 6 条，六个 Quality-v1 维度各 1 条；每条严格为三条构造消息 `user / assistant / user`，不含 System、目标答案或参考答案。没有读取 `v2_chat_messages` 私有消息正文，没有访问 R50 内容。

当前会话工件（不是 Owner Mac 私有目录；Owner 必须转存、审查并冻结）：

- `R60_P2_PUBLIC_STORY_PROMPTS_DRAFT_20261117.jsonl`：48 条，SHA256 `ab3e9848ca2be63f935bea66d22080ed45c4dd0e0782c08636449831d3152db7`。
- `R60_P2_PUBLIC_STORY_SOURCE_MANIFEST_DRAFT_20261117.json`：8 个来源的 story ID、revision、创建/批准时间、审核快照 SHA、权限事件绑定、非语义 World JSON 指纹；SHA256 `56c5c9c90e347860e1107dc7f10d2486f8153acc21c469676b80850f57239a4b`。
- 结构校验器：`experiments/r58_quality/r60_base336_p2_public_prompt_package_gate.py`。
- 合成测试：`tests/test_r60_base336_p2_public_prompt_package_gate.py`；本地 8/8 PASS，compileall PASS。没有声称 GitHub Actions CI PASS。

### 5.2 仍需完成的 P2-C

1. **Base336 来源隔离：** 将这 8 个来源的 World 组件与 Base336 293/43 私有来源清单、Story/World component graph 和已审核的历史版本做交叉核验。不同 Story ID、不同 World JSON MD5 或时间戳都不足以证明语义独立。
2. **R50 保护集排除：** Owner 提供完整、已授权的 R50 Protected/Reserved World 元数据清单，仅做元数据匹配排除；绝不读取 R50 正文或答案。
3. **开发题暴露排除：** 核验 8 个来源及 48 条提示未复用 R47/R48/R55 已暴露开发题或其语义变体。
4. **提示逐条复核：** 检查来源忠实性、无原文长段复用、无未来信息泄漏、无隐藏指令混入；NPC/角色新增内容须明确属于合成情境，不得伪称来源事实。
5. **权利范围：** 维持 Owner 已批准的内部评估提示构造用途；不得把公开可见状态推断为作者授予模型训练或再分发权利。
6. **Owner 冻结：** Owner 在本机私有目录冻结来源 Manifest、prompt SHA256、语义 World crosswalk、R50 元数据排除回执和独立 Reviewer 结论。

当前会话无法读取 Owner Mac 私有目录。下一 Agent 应向 Owner 索取/使用上述**私有交叉核验证据**，而不是重新抽取数据库或读取任何私有会话正文。任何关键证据缺失都保持 HOLD。

P2-C 通过前，不生成正式 Held-out、不实现正式 Pairer/Profile/Backend、不执行模型推理。P2 PASS 后才进入 P3。

## 6. P3：P2 通过后才设计 Base/Adapter 两臂评估

### 6.1 复用现有共享核心

- `src/storyforge_dataset/generation_eval/worker.py::run_generation_batch`：现有注入式 Backend 批量生成引擎，优先复用；它已绑定输入 Manifest、记录数/Token 上限/seed、消息结构、输出与 Receipt 合同。
- `src/storyforge_dataset/hf_runtime/inputs.py` / `outputs.py`：复用输入 SHA/JSONL 验证、私有输出与 create-only 写入。
- `GenerationBackend` Protocol：复用模型后端抽象，Base 与 Adapter 的加载差异放在版本化薄 Backend Adapter。
- `formal_pairing_gate.py`：复用精确 prompt/message 配对、哈希清单和无 reference-label 暴露检查思路；现有 Gate 是三角色合同，不能直接作为两臂 Gate。
- `scripts/prepare_eval_pairs.py`：只复用逐案随机 A/B 与独立 answer-key 的思路；旧五维 scorecard 和字段不能作为本轮合同。
- `experiments/r58_quality/quality_v1.py`：唯一冻结六维 floors（4/4/3/4/4/4）及三个 severe flags 的来源。只复用规则定义和审核语义，不调用其源候选准入流程处理模型生成输出。

### 6.2 不可直接照搬

- `generation_eval/profiles.py` / `worker_cli.py` 当前绑定 P4 的 A/B/challenger 三模型角色、旧模型 Revision 和依赖环境；CLI choices 固定为 `A/B/challenger`。不得原地修改或复用其冻结 P4 Profile 来代表 Base/Adapter。
- P4 `formal_pairing_gate.py` 固定三角色和 Pilot 样本结构；本轮需要 Base/Adapter 两臂、相同 prompt SHA、相同消息、相同生成参数与逐案配对。
- `scripts/prepare_eval_pairs.py`、`analyze_blind_eval.py`、`export_context_blind_review.py` 使用旧五维字段；导出器还固定 15/20 条，不能直接承担本轮六维审核。
- `r60_p4_evaluation_output_schema_candidate_v1.json` 是旧 severity 候选，不是 Quality-v1 六维 Schema。
- `scripts/hf_job_runner.py::make_inference_input` 只用于 Validation 第一条 smoke，不是独立 Held-out 批量 Worker。

### 6.3 冻结前必须固定的两臂合同

- Base：`Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`；Adapter：本次 checkpoint-37 对应 Adapter，SHA 与私有路径由 Owner 在本机核验。
- 两臂使用完全相同的 prompt/messages（三个持久化可见消息、无 System）、Tokenizer/Chat Template、上下文预算、解码参数、seed、停止条件与输出 Token 上限。
- 每条输出绑定 prompt SHA、模型/Adapter 身份、Tokenizer/Template/Runtime digest、input/output Token 数、finish reason、截断状态、结果 SHA。
- 逐案随机 A/B，blind key 独立 0600 保存；Reviewer 不得见模型身份。评审者独立性需要单独证据，不可仅以不同模型 ID 声称独立。
- 生成结果属于模型比较证据，不是 DB 最终持久化 Assistant，也不是 Source/Review/Gold Manifest 事件。

## 7. P4 推理授权必须单独申请

本次已批准的 GPU 授权只覆盖唯一 Base336 探索性训练 Job，不包含 Base/Adapter 配对推理、GPU 评审、后续训练或其他模型操作。P2/P3 通过也不会自动授予 P4。

申请时至少明确：目的、Base/Adapter revision 与 Adapter SHA、GPU Flavor、Job 数量、时长上限、样本数、输入/输出 Token 上限、解码参数、Bucket RO/RW 前缀、费用上限、失败重试策略、输出回收和销毁/保留策略。Owner 明确批准前不提交 Job。

## 8. 交接 Agent 的工作方法与交付标准

1. 先只读核验 branch HEAD、PR/Issue、Actions 和工作树状态；不得依据本文件静态 SHA 假设远端仍未变化。
2. 确认当前分支与任务范围；其他 Agent/Owner 的未提交改动必须保留，不得强制 reset、force push、覆盖私有文件或清理目录。
3. 先读取已有 SAFE、checkpoint、Stage、Runner、Pairer、Schema 与 CI；复用优先，只有发现真实缺口才写代码。
4. P2 未通过时只做来源门禁说明、合成测试、文档和复用设计；不创建正式测试包、不执行模型推理。
5. 所有新代码先合成测试、Ruff、scoped GitHub Actions；CI PASS 只证明代码合同，不证明数据权利、质量或模型提升。
6. 每次提交后核对该精确 HEAD 的 Actions；区分文档路径 CI、合成代码 CI 和真实 HF Job，不得用旧 HEAD 的 CI 冒充新 HEAD 验收。
7. 报告区分 `PASS`、`HOLD`、`NOT_ATTEMPTED`、`UNKNOWN`；每个 PASS 要有可追溯回执或精确 CI。

交付必须包含：当前 HEAD/分支、改动文件、Commit、对应 HEAD 的 Actions、P2 来源证据状态、权限边界、是否提交 HF Job/是否启动 GPU、未解决 HOLD、下一步最小动作。不得输出任何私有正文、身份映射、密钥或私有路径。

## 9. 本交接生成时的 GitHub 快照（仅供核对，不代替实时查询）

- 分支 HEAD：`0b6d7f79911a0df9710cfde7743660c6aa1fe25c`。
- 最新 `safe-review-regression`：Run `44062980810`，completed/success，绑定该 HEAD。
- 最新 `R60 Common2 Wrapped HF CPU (synthetic only)`：Run `44062797595`，completed/success，绑定代码/Skill 提交 `f99b5f8487d27fbf6bd64081c5b593a1f0616b69`；此后 `0b6d7f7` 只更新评估计划文档，不改变被测代码。
- REAL1000 Reviewer synthetic regression：Run `44062980810` 同一 scoped workflow，completed/success。
- Issue #26 当时仍 OPEN，但其标题/目标是 R60 REAL History SFT 主线；它不是 Base336 P2 的授权来源，也不得擅自将其改写为 Base336 任务。
- 接手时重新查询，不要把以上快照当作当前事实。

## 10. 当前权威文件

- 训练后主计划：`docs/plans/R60_BASE336_POST_TRAIN_QUALITY_EVALUATION_20261117_CN.md`。
- 新 Agent 启动提示词：`docs/R60_BASE336_NEXT_AGENT_START_PROMPT_20261117_CN.md`。
- Gold/Quality 边界：`docs/standards/GOLD_QUALITY_PIPELINE_CN.md`。
- 执行顺序与复用原则：`skills/storyforge-roleplay-sft/SKILL.md`。
- 私有审计 SAFE 只保留在 Owner Mac；GitHub 不保存本地 SHA Manifest。

**下一 Agent 的唯一业务优先事项：完成已批准 Supabase 公开故事 Draft 的 Base336/R50/R47-R48-R55 交叉隔离审计、提示逐条复核和 Owner 私有冻结。当前 48 条仍是 Draft；没有 P2-C PASS，不进入正式 Held-out、Pairer 或 Base/Adapter 推理。**
