# StoryForge R60 Base336 训练后阶段：新 Agent 权威交接任务书（2026-11-17）

> **本文件是 `r60/common2-cpu2-owner` 分支 Base336 训练后阶段的当前交接入口。** 训练、产物审计和代码复用盘点已完成；独立质量评估尚未开始。先重新核验 GitHub 当前状态，再执行本文件。不要把其他 R60/P4/REAL1000 任务书中的旧授权套用到本任务。

## 1. 一分钟接手摘要

| 项目 | 当前权威事实 |
|---|---|
| 仓库 | `sunxu/storyforge` |
| 工作分支 | `r60/common2-cpu2-owner` |
| 本次交接整理前 HEAD | `0be17b3fd720560f86cf27bfd493cfc95a0eb544`；接手时必须重新查询 |
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
5. P2 保护集交叉核验证据索引：`docs/plans/R60_BASE336_P2_PROTECTED_CROSSWALK_EVIDENCE_INDEX_20261118_CN.md`。
6. `docs/standards/GOLD_QUALITY_PIPELINE_CN.md`：六维质量与 Gold Manifest 的边界。
7. `skills/storyforge-roleplay-sft/SKILL.md` 与 `skills/storyforge-roleplay-sft/MANIFEST_SAFE.json`。
8. `skills/storyforge-real-quality-review/SKILL.md`：仅了解 Reviewer 证据、独立性和私有数据边界；不得自动恢复 REAL1000 批次。
9. `src/storyforge_dataset/generation_eval/worker.py`、`profiles.py`、`worker_cli.py`、`formal_pairing_gate.py`。
10. `src/storyforge_dataset/hf_runtime/inputs.py`、`outputs.py`。
11. `experiments/r58_quality/quality_v1.py`、`scripts/prepare_eval_pairs.py`、`scripts/analyze_blind_eval.py`、`scripts/export_context_blind_review.py`。
12. 专项可复制启动提示词：`docs/R60_BASE336_P2_CROSSWALK_NEXT_AGENT_PROMPT_20261118_CN.md`。

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
| P2-B 48 条提示 JSONL / Manifest / SHA | NOT_GENERATED（仅校验器及合成测试代码存在） | 不得将测试夹具或旧文档描述当作真实提示包 |
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

### 5.1 P2-A：公开来源 Inventory READY；P2-B：NOT_GENERATED

Owner 2026-11-18 实际 SAFE 确认：8 条 Supabase 公开来源、5 位作者、8 个不同 World JSON；3 条记录创建于 GPU Run 前、5 条创建于 GPU Run 后；revision / moderation snapshot / permission event 绑定验证通过；指定范围内 GPU 前公开原创 World JSON 精确重叠为 0。Owner 确认用途仅限内部独立评估提示构造；私有 Source Manifest 已创建。

这只代表 P2-A READY，不证明 Base336 私有来源隔离、R50 Protected/Reserved 排除、R47/R48/R55 暴露排除、语义 World 隔离或历史 actual-sent 版本独立性。

48 条真实提示 JSONL / Manifest **NOT_GENERATED**，没有真实提示包 SHA256。旧启动材料中的 Draft 文件名与 SHA 记录已由最新 P2 决策更正，禁止作为真实工件、冻结输入或验证证据。现有校验器及 9/9 合成测试只证明代码合同，不证明真实提示包存在。

### 5.2 P2-C：保护集交叉核验仍 HOLD

必须分别证明并绑定以下保护范围的完整性：

1. Base336 冻结 Train/Validation 私有 source roster，以及全部相关 current/archived World、character、characters、opening 证据。
2. R50 完整 Protected/Reserved World **仅元数据**排除；绝不读取 R50 正文、提示、答案或密封材料。
3. R47/R48/R55 已暴露开发题及其语义变体的完整 source/exposure Manifest。
4. 其他已有独立评测集与未解决保护集合。
5. 历史 actual-sent / delivered prompt 版本和来源 revision 绑定；缺少真实发送证据时保持 UNKNOWN/HOLD。
6. 独立 Reviewer 复核和 Owner 最终冻结。

**区分两组 8：** P2 的 8 条新 Supabase 来源与 Base336 历史 8 组跨 split World JSON 关联不是同一集合。Base336 历史 roster 覆盖 38 个故事、82 个候选 case；每组一个代表性 World 对象不等于 38 个成员的完整角色卡/Opening 证据。

R47/R48/R55 部分 metadata / shape inventory 已收到，不能再声称全部 inventory 尚未收到。当前最小动作是对三个 R55 私有 Coordinator Index 做只读 Schema / 字段 / 数量 / 版本绑定 / 覆盖 SAFE 检查，并寻找 Sample → Story ID 权威来源映射；P2 Source Manifest、Base336 member evidence、R50 完整 metadata-only roster 等其他保护集仍按证据索引核对。此前 `r60_base336_group_cards_opening_cpu.py --execute` 返回泛化 `BASE336_CARD_OPENING_EVIDENCE_HOLD`，没有 failure phase / reason。**禁止再次运行全量 `--execute`**，禁止重跑数据库查询、重建或覆盖 roster/template/evidence/output。只有明确失败阶段并经 Owner 重新确认具体最小动作后，才考虑修复。

工具功能、输入 Schema、覆盖边界和缺口见：
`docs/plans/R60_BASE336_P2_PROTECTED_CROSSWALK_EVIDENCE_INDEX_20261118_CN.md`。

新 Agent 应直接使用专项提示词：
`docs/R60_BASE336_P2_CROSSWALK_NEXT_AGENT_PROMPT_20261118_CN.md`。

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
- P2 保护集交叉核验证据索引：`docs/plans/R60_BASE336_P2_PROTECTED_CROSSWALK_EVIDENCE_INDEX_20261118_CN.md`。
- Gold/Quality 边界：`docs/standards/GOLD_QUALITY_PIPELINE_CN.md`。
- 共享 World 组件隔离核心：`src/storyforge_dataset/world_isolation.py`；Quality-v1 通过 `component_split_conflicts()` 复用结构检查；合成测试见 `tests/test_world_isolation.py` 与 `experiments/r58_quality/test_quality_v1.py`。它只校验已审查的组件分配，不从 JSON/hash 推断语义，也不证明历史 actual-sent、Reviewer 独立或 R50 完整排除。
- 执行顺序与复用原则：`skills/storyforge-roleplay-sft/SKILL.md`。
- 私有审计 SAFE 只保留在 Owner Mac；GitHub 不保存本地 SHA Manifest。

**下一 Agent 的唯一业务优先事项：先完成 Base336 8 组来源绑定语义组件审查，并取得 R50 仅元数据排除、R47/R48/R55 暴露排除证据；同时确认真实 48 条提示包是否按最新补充决策生成（当前记录为 NOT_GENERATED）。没有完整 P2-C PASS，不进入正式 Held-out、Pairer 或 Base/Adapter 推理。**

## 2026-11-18 Owner SAFE 更新：P2-A 公开来源 Inventory READY；P2-C 仍 HOLD

Owner 本轮真实 SAFE（由 Owner 提供）：

```json
{
  "authors": 5,
  "created_after_gpu_run": 5,
  "created_before_gpu_run": 3,
  "database_accessed": true,
  "database_modified": false,
  "distinct_world_json": 8,
  "exact_world_overlap_pre_cutoff_public_original": 0,
  "gpu_started": false,
  "hf_jobs_submitted": 0,
  "model_promoted": false,
  "model_requests": 0,
  "private_file_created": true,
  "private_values_emitted": false,
  "protected_crosswalk_verified": false,
  "quality_v1_admitted": 0,
  "revision_snapshot_permission_verified": true,
  "rights_scope_owner_confirmed_only": true,
  "schema": "storyforge_r60_base336_p2_public_source_inventory_safe_v1",
  "selected_stories": 8,
  "status": "P2_PUBLIC_SOURCE_INVENTORY_READY__PROTECTED_CROSSWALK_PENDING",
  "train_admitted": 0
}
```

### 证据解释

- P2-A Supabase 公开来源 inventory：READY，8 条来源已选定，revision / snapshot / permission 绑定已验证。
- 本次精确 World JSON 比较在指定的 GPU 前公开原创范围内为 0 overlap；这不是语义世界隔离证明，也不覆盖 Base336 私有来源、R50 Protected/Reserved、R47/R48/R55 暴露材料。
- 8 个不同 World JSON 不等于 8 个语义独立世界。
- 5 条创建于 GPU Run 后只代表数据库记录创建时间；不能单独证明其底层素材、版本或语义未提前暴露。
- 权利状态为 `rights_scope_owner_confirmed_only=true`，只代表 Owner 已确认的内部独立评估提示构造用途；不扩展为训练、再分发或公开用途授权。
- `private_file_created=true` 表示 Owner 私有来源 Manifest 已创建；私有 Manifest、source IDs、作者映射、正文和 SHA 不得上传 GitHub 或贴入聊天。

### P2-C 尚未完成的保护集交叉核验

必须将上述 8 个 P2 来源与以下保护范围进行精确及语义交叉核验：

1. Base336 冻结 Train/Validation 私有 source roster 和已审查的 World component evidence。
2. R50 完整 Protected/Reserved World **仅元数据**清单；不读取 R50 正文、提示、答案或密封材料。
3. R47/R48/R55 已暴露开发题及其语义变体的来源/暴露元数据。
4. 现有其他独立评测集及未解决保护集合；不得将部分保护清单称为完整覆盖。

当前可复用 Base336 Owner-local 证据目录为 `~/.local/share/storyforge/r60/private/r60-base336-world-cross-review-20261115/`，包含既有 8 组 cross-split roster、decision template、Codex review 和代表性 World source evidence；这些历史回执仍不能证明本轮 P2 8 个新来源已与保护集完成 crosswalk。成员级 card/opening 证据此前未确认存在。R50 旧有 pre-seal 证据曾显示完整排除与最终封存仍 HOLD；R47/R48/R55 全量语义变体排除材料也未形成可验证的完整 crosswalk。

### 当前禁止推断

- 不因 8/8 revision / snapshot / permission PASS 推断 P2-C PASS。
- 不因 exact overlap=0 推断语义隔离 PASS。
- 不因 Owner 确认评估用途推断训练授权。
- 不生成正式 48 条 Held-out prompt 包，不启动 Base/Adapter Pairing 或模型推理。
- 不改写 Quality-v1 六维门槛，不新增评分标准，不向 Gold Manifest 追加生成评估事件。

继续保持：`model_promoted=false`、`train_admitted=0`、`quality_v1_admitted=0`、GPU/HF/model requests = 0。

### 下一项最小动作

Owner 已返回 R47/R48/R55 的部分 metadata inventory；这些文件不再重复盘点。下一步对三个 R55 私有 Coordinator Index 做只输出 Schema / 字段名 / 数量 / 版本绑定的结构审计，并寻找 Sample → Story ID 的权威来源映射。P2 Source Manifest、Base336 roster / member evidence、R50 完整 metadata-only roster 等其他保护集仍需按证据索引确认存在性与覆盖。不得 cat / grep 私有正文、上传文件或打印 ID / 正文 / 哈希；真实 Schema 和保护集覆盖确认前，不编造通用适配器或宣称 crosswalk 完成。


## 2026-11-18 专项交接包更新

- 交接整理前 GitHub HEAD：`0be17b3fd720560f86cf27bfd493cfc95a0eb544`；新 Agent 必须重新查询实时 HEAD、工作流和 PR。
- 专项可复制提示词：`docs/R60_BASE336_P2_CROSSWALK_NEXT_AGENT_PROMPT_20261118_CN.md`。
- 保护集证据索引：`docs/plans/R60_BASE336_P2_PROTECTED_CROSSWALK_EVIDENCE_INDEX_20261118_CN.md`。
- **历史截点说明（已被后续增量更新）**：本节撰写时 Owner Mac 文件 inventory 尚未收到；2026-11-18 后续已收到 R47/R48/R55 部分 metadata / shape inventory，详见下一节。
- 当前首要动作不再是重复盘点 R47/R48/R55 文件，而是只读核验 R55 私有 Index Schema / 覆盖及 Sample → Story ID 权威映射。此前 card/opening 全量提取返回泛化 HOLD，禁止盲目重跑全量 `--execute`。
- 本次交接文档不执行 Supabase 查询、不访问私人文件、不读取 R50 正文、不运行模型/GPU/HF Job，不改变准入状态。


## 2026-11-18 R47 / R48 / R55 Source Shape Audit 增量（最新）

最新 Owner-local metadata / shape audit 已收到，完整结果见 [R60 P2 R47/R48/R55 Source Shape Audit](evidence/R60_P2_R47_R48_R55_SOURCE_SHAPE_AUDIT_20261118_CN.md)。

- R47 Manifest 只有 20 个 sample_id / prompt_sha256 / source_line 元素；compiled Test 为 20 条 id/messages/metadata；Prompt 为 20 条 messages。现有 R47 / R48 构建和校验逻辑没有形成可验证的逐案 Story ID 映射。
- R48 20 cases / 80 replies 与 R47 是同一批 20 个旧测试案例，不得重复计为独立 Held-out。
- R55 三个私有 Coordinator Index（0600）及两个 SAFE 文件的元数据已确认存在；本轮没有读取 Index / SAFE 内容，Schema、版本绑定、覆盖完整性和 Story ID 映射均 UNKNOWN / HOLD。
- 此前 P2 × Base336（336 cases / 172 stories，精确 Story ID overlap=0）及 P2 × R50（exact Source ID disjoint）结果只对其各自清单范围有效，不可外推到 R47/R48/R55。
- **当前 P2 × R47/R48/R55 exact Story ID crosswalk = UNKNOWN / HOLD；semantic exposure exclusion = HOLD；P2-C 总门禁继续 HOLD。**

下一步只做 Owner-local R55 Index 结构 / 覆盖 SAFE 检查，并寻找 Sample → Story ID 的权威来源映射。不得读取 R50 正文、历史答案或逐案 Reviewer 内容；不得重跑数据库查询、GPU、HF Job、模型请求或生成正式 48 条提示包。


## 2026-11-18 R47 / R48 / R55 crosswalk code-path refinement（接手时优先采用）

代码复核发现，R47 Sample → Story ID 并非没有实现路径：

1. \`scripts/prepare_blind_eval.py\` 从每条 canonical source row 的 prompt prefix 生成确定性 \`sample_id\`、\`prompt_sha256\` 和 \`source_line\`。
2. \`scripts/audit_v01_integrity.py\` 检查 canonical Test 行存在 \`metadata.story_id\`，并逐案验证 Test row / frozen prompt / Manifest 的完整 role/content prefix、prompt hash、source_line 和 Sample ID 公式。
3. \`scripts/v02_r48_four_arm_build.py\` 固定 canonical Test SHA，并再次核对 20 条完整 prompt prefix。R48 与 R47 是同一 20-case 集，不新增独立 Story 集。
4. R55 第一层 Coordinator Index 保存 \`source_sample_id_private\`；第二 / 第三层 Index 保存 original candidate token 回链字段，可以校验它们是否仍指向第一层来源。

但本机文件实际 crosswalk 仍未执行。下一步不要再寻找一个不存在的 \`compiled_test.id = story_id\` 字段；应按上述复合绑定构造 Owner-local SAFE，并将 P2 Manifest 的 8 个 \`story_id\` 与 R47 20 个 \`metadata.story_id\` 比较。R55 还必须验证三个 Index 的 Schema / token links / 20-case coverage / receipt hash binding，并审查 \`R55_OLD_R47_SOURCE_PREFLIGHT_SAFE.json\` 是否证明 R55 原始 20-case 与 R47 Manifest 对应。

只输出 overlap count、disjoint boolean、各层记录数 / 覆盖数、receipt binding booleans；绝不输出任何 ID、作者映射、哈希或正文。实际 SAFE 未通过前 P2 × R47/R48/R55 仍 UNKNOWN / HOLD，semantic exposure exclusion 仍 HOLD。
