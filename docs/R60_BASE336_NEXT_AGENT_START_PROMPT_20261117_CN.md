# R60 Base336 下一 Agent 启动提示词（2026-11-18，可直接复制）

你现在接手 GitHub 仓库 `sunxu/storyforge` 的 **R60 Base336 P2 Protected Crosswalk 任务**。工作分支为 `r60/common2-cpu2-owner`。首要目标是核验 Owner Mac 已有私有证据的元数据、诊断缺失项，并在真实 Schema 完整确认后完成保护集交叉核验。**先读并执行专项提示词**：`docs/R60_BASE336_P2_CROSSWALK_NEXT_AGENT_PROMPT_20261118_CN.md`。本任务不是 Supabase 重抽取、训练或推理。

## 一、先核验，不要直接执行

1. 先读取仓库 `AGENTS.md`。
2. 只读核验 GitHub 当前分支 `r60/common2-cpu2-owner` 的 HEAD、工作流、PR、Issue #26；不要假设历史 SHA 仍是最新。Issue #26 当前跟踪的是 REAL History SFT 主线，不是 Base336 授权来源。
3. 按顺序完整阅读：
   - `docs/R60_BASE336_POST_TRAIN_NEXT_AGENT_HANDOFF_20261117_CN.md`
   - `docs/plans/R60_BASE336_POST_TRAIN_QUALITY_EVALUATION_20261117_CN.md`
   - `docs/plans/R60_BASE336_SUPABASE_PUBLIC_STORY_P2_ADDENDUM_20261117_CN.md`
   - `docs/plans/R60_BASE336_P2_PROTECTED_CROSSWALK_EVIDENCE_INDEX_20261118_CN.md`
   - `docs/R60_BASE336_P2_CROSSWALK_NEXT_AGENT_PROMPT_20261118_CN.md`
   - `docs/standards/GOLD_QUALITY_PIPELINE_CN.md`
   - `skills/storyforge-roleplay-sft/SKILL.md`
   - `skills/storyforge-real-quality-review/SKILL.md`（只读理解审核边界）
   - `src/storyforge_dataset/generation_eval/worker.py`、`profiles.py`、`worker_cli.py`、`formal_pairing_gate.py`
   - `src/storyforge_dataset/hf_runtime/inputs.py`、`outputs.py`
   - `experiments/r58_quality/quality_v1.py`。
4. 核验最近精确 HEAD 的 Actions；区分 Skill/Reviewer scoped CI、Generation Eval 合成 CI 与真实 HF Job。不要把旧 HEAD 的 CI 写成新 HEAD 的验证。

## 二、必须准确继承的训练和产物事实

- 唯一训练 Run Key：`r60-base336-gpu-20261117T055622Z-b609cb78661d`。
- 唯一训练 HF Job：`6afbfd5c98dda891b5df7fd2`，Owner 已确认 COMPLETED。
- 模型：`Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`。
- Train/Validation：293/43；37/37 steps；A100；terminal checkpoint 与 Adapter Reload PASS。
- Worker SAFE：`BASE336_GPU_EXPLORATORY_ENGINEERING_PASS__NOT_PROMOTED`。
- Owner Mac 产物审计 SAFE：`BASE336_GPU_RESULT_ARTIFACT_INVENTORY_PASS__NO_PROMOTION`，33/33 objects、5,604,774,224 bytes。
- 本地 SHA 是下载对象 inventory，不是 Worker 原始逐文件 SHA 的逐项比较。
- 43 Validation 已用于 Eval/Checkpoint 选择；293 Train + 43 Validation 均不可作为独立 Held-out。
- `model_promoted=false`、`train_admitted=0`、`quality_v1_admitted=0`。

## 三、当前任务：完成已批准 Supabase 来源的 P2-C 保护集交叉核验

Owner 已批准新的来源路线：仅使用 Supabase 已公开、已发布、非删除、原创且通过审核的故事，以及公开 World/Character/Opening 字段，构造内部评估提示；**不读取用户私有会话正文**。该授权只覆盖内部独立评估提示构造，不扩展为训练、公开发布或再分发。

### P2-A：公开来源 Inventory READY

Owner 2026-11-18 实际 SAFE 确认：

- 8 个公开来源、5 位作者、8 个不同 World JSON。
- 3 条记录创建于 Base336 GPU Run 前，5 条创建于 Run 后；全部晚于 Base336 293/43 数据集冻结边界。
- revision / moderation snapshot / permission event 绑定验证通过。
- 指定范围内 GPU 前公开原创 World JSON 精确重叠为 0。
- Owner 确认用途仅限内部独立评估提示构造；私有 Source Manifest 已创建。
- 以上不证明语义 World 隔离，不证明与 Base336 私有来源、R50 Protected/Reserved 或 R47/R48/R55 暴露题隔离。

### P2-B：48 条正式提示包 NOT_GENERATED

- 当前没有可验证的真实 48 条提示 JSONL、Manifest 或真实提示包 SHA256。
- 旧版本启动材料中“已构造 48 条 Draft”及其文件名 / SHA256 记录已被最新 P2 补充决策和 Owner 状态更正；不得把这些旧记录当作现存工件、冻结输入或校验通过。
- 校验器：`experiments/r58_quality/r60_base336_p2_public_prompt_package_gate.py`。
- 测试：`tests/test_r60_base336_p2_public_prompt_package_gate.py`。9/9 合成测试只证明校验器代码合同，不证明真实提示包存在。
- P2-C 通过前，不生成正式 Held-out 提示包，不启动模型推理。

### Base336 历史 World 证据（与 P2 的 8 条新来源不是同一集合）

- 既有 Base336 roster 对象是从冻结 336 cases / 172 stories 中识别出的 8 组跨 split World JSON 精确值关联；影响 38 个故事、82 个候选 case，其中 28 个 Train stories / 10 个 Validation stories，7/8 组当前 World 值跨 Train/Validation。
- 已有代表性 World source evidence 仅每组一个代表对象；它不是 38 个成员完整的 current/archived character、characters、opening 证据，也不证明历史 actual-sent 版本。
- 最新可用汇总仍为 8/8 组 HOLD，semantic review 未完成，actual-sent version 未验证。
- 复用工具和各证据边界见 `docs/plans/R60_BASE336_P2_PROTECTED_CROSSWALK_EVIDENCE_INDEX_20261118_CN.md`。

**P2-C 仍为 HOLD。** Owner Mac 元数据 inventory 输出尚未收到。不得重新抽取 Supabase，不得重建或覆盖已有 roster/template/evidence/review/output。此前 card/opening 全量 `--execute` 返回泛化 HOLD，禁止盲目重跑。第一步只做 Owner-local 文件元数据盘点；在真实输入文件、Schema 和保护集覆盖范围确认前，不创建新的 crosswalk 适配器。

1. 将 P2 的 8 个新来源与 Base336 冻结 Train/Validation source roster、8 组 World evidence、全部 38 个受影响故事的 current/archived character、characters、opening 证据交叉核验。
2. 仅使用 Owner 授权的 R50 Protected/Reserved 完整元数据清单做排除核验；绝不读取 R50 正文、提示或答案。
3. 核验 R47/R48/R55 已暴露开发题及其语义变体；必须证明暴露材料覆盖完整，不能用局部历史工具或 SAFE 代替完整清单。
4. 单独验证历史 actual-sent 版本与来源绑定；没有真实发送证据时保持 UNKNOWN/HOLD。
5. 保持权利范围仅为内部评估提示构造；不能推断作者授予训练或再分发权利。
6. 只有 P2-C 的保护集交叉核验完成后，才按最新 Owner 决策安排正式提示包构造、逐条审查和 Owner 冻结。

当前会话无法访问 Owner Mac 私有目录。若缺少 Base336 私有 source roster、World component evidence 或 R50 元数据清单，明确输出对应 HOLD 并向 Owner 索取这些**私有交叉核验证据**；不得改为读私有会话正文或 R50 内容。

P2 证据定位、可复用脚本边界和缺失材料清单见 [P2 Protected Crosswalk Evidence Index](plans/R60_BASE336_P2_PROTECTED_CROSSWALK_EVIDENCE_INDEX_20261118_CN.md)。

## 四、P2 通过后才推进 P3 工程适配

复用优先：
- `generation_eval.worker.run_generation_batch` 批量生成核心；
- `hf_runtime.InputManager` / `OutputManager` 输入验证与私有 create-only 输出；
- `GenerationBackend` Protocol；
- `formal_pairing_gate.py` 的严格 prompt/message hash 配对思路；
- `prepare_eval_pairs.py` 的随机 A/B 和独立 answer-key 思路；
- `quality_v1.py` 唯一六维门槛 floors 4/4/3/4/4/4 与 severe flags。

禁止直接复用 P4 三模型 Profile/CLI、A/B/challenger 三角色 Gate、旧五维 Scorecard 或固定 15/20 条 Exporter。不能把生成结果送入源候选准入流程，也不能向 Gold Quality Manifest 追加伪造 Source/Review/Gold 事件。Base/Adapter 两臂需使用版本化薄适配器，不得破坏冻结 P4 Profile。

Base 与 Adapter 必须使用相同的三个持久化可见消息（无 System）、Tokenizer/Chat Template、上下文、解码参数、seed、停止条件和输出 Token 上限；逐案随机 A/B，blind key 独立 0600 保存。具体模型/Adapter SHA、依赖锁、runtime digest 和输出字段见权威任务书。

## 五、权限边界（必须严格执行）

- 之前的 GPU 授权只覆盖唯一 Base336 训练 Job，不包括 Base/Adapter 推理、GPU 评审或新训练。
- **当前没有新的 HF Job / GPU inference / GPU review / training 授权。** 不调用 submit/run_job，不下载模型权重，不启动 GPU。
- P2 PASS 和 P3 合成 CI PASS 均不会自动授予 P4 推理权限；必须由 Owner 单独明确批准具体模型、Flavor、Job、样本数、Token 上限、时长、Bucket 前缀和预算。
- 不读 R50 正文、不写数据库、不改冻结数据、不覆盖 checkpoint、不输出私有正文/身份/路径/凭据。

## 六、工作方法与交付

先完成只读核验与 P2-C 私有交叉核验；若 Owner 尚未提供 Base336/R50 私有元数据证据，输出明确的 World/R50 crosswalk HOLD 和最小补件清单。不要重新抽取来源、不要将 Draft 当作冻结 Held-out，也不要提前实现正式 Pairer 或生成模型输入。

每次修改前检查工作树、分支和 HEAD；复用现有代码；新增功能先合成测试、Ruff 和精确 HEAD Actions。每次报告必须区分真实证据、CI 合成证据、Owner 声明和未知项。

最终交付：当前 HEAD、分支、文件改动、Commit、精确 HEAD CI、P2 SAFE 状态/原因、权限与资源消耗、是否提交 HF Job/是否启动 GPU、未解决 HOLD、下一项最小动作。不得把未执行工作写成 PASS。

**现在开始：先核验 GitHub 当前状态并读取权威交接文件；在 P2 来源未获批准前，只做只读核验和文档/合成测试，不进行任何模型推理。**


## 交接提示词权威入口

新 Agent 应以专项提示词 `docs/R60_BASE336_P2_CROSSWALK_NEXT_AGENT_PROMPT_20261118_CN.md` 为可执行任务合同；本文件保留训练后评估背景和总体流程。若本文件与专项提示词在当前执行顺序上存在差异，以专项提示词和最新 Owner SAFE 为准，并先核对 GitHub 当前 HEAD。
