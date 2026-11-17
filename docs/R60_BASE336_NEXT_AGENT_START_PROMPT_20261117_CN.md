# R60 Base336 下一 Agent 启动提示词（2026-11-17，可直接复制）

你现在接手 GitHub 仓库 `sunxu/storyforge` 的 **R60 Base336 训练后独立质量评估任务**。工作分支为 `r60/common2-cpu2-owner`。你的目标不是继续训练，而是先解决独立 Held-out 来源门禁，再在授权范围内准备 Base/Adapter 对照评估。

## 一、先核验，不要直接执行

1. 先读取仓库 `AGENTS.md`。
2. 只读核验 GitHub 当前分支 `r60/common2-cpu2-owner` 的 HEAD、工作流、PR、Issue #26；不要假设历史 SHA 仍是最新。Issue #26 当前跟踪的是 REAL History SFT 主线，不是 Base336 授权来源。
3. 按顺序完整阅读：
   - `docs/R60_BASE336_POST_TRAIN_NEXT_AGENT_HANDOFF_20261117_CN.md`
   - `docs/plans/R60_BASE336_POST_TRAIN_QUALITY_EVALUATION_20261117_CN.md`
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

## 三、当前任务：先完成 P2 来源审查

**P2 当前为 HOLD。** 等待 Owner 提供或明确批准新的独立 Held-out 私有测试包。不得从 661 个未准入候选、数据库、R47/R48/R55 暴露题、P4 旧测试包或 336 训练池自动抽样。R50 正文绝对禁止访问；若需排除，只允许在授权范围内使用完整元数据证据。

拿到来源包后，先只读审查并形成私有 SAFE：
- 每条来源权利、授权主体、用途、版本和时间范围；
- prompt 的来源 SHA、上下文可用时序、消息角色和顺序；
- 未进入 336 Train/Validation、训练期 Eval、Checkpoint 选择或调参；
- 未被 R47/R48/R55 暴露；
- story/World component 隔离和跨故事依赖；
- R50 仅元数据排除，绝不读正文；
- 私有 crosswalk、原文、blind key、哈希明细和路径留在 Owner 私有环境。

建议规模 40–60 prompts、至少 4 个未使用故事/世界，但规模由 Owner 确认，不是默认授权。任何权利、来源、上下文或隔离证据缺失都保持 HOLD，不生成正式测试包。

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

先完成只读核验与 P2 输入准备；若 Owner 尚未提供来源包，输出明确的 `P2_SOURCE_PACKAGE_NOT_PROVIDED__HOLD` 和最小补件清单，不要用代码工作掩盖来源缺失。不要提前实现正式 Pairer 或生成输入。

每次修改前检查工作树、分支和 HEAD；复用现有代码；新增功能先合成测试、Ruff 和精确 HEAD Actions。每次报告必须区分真实证据、CI 合成证据、Owner 声明和未知项。

最终交付：当前 HEAD、分支、文件改动、Commit、精确 HEAD CI、P2 SAFE 状态/原因、权限与资源消耗、是否提交 HF Job/是否启动 GPU、未解决 HOLD、下一项最小动作。不得把未执行工作写成 PASS。

**现在开始：先核验 GitHub 当前状态并读取权威交接文件；在 P2 来源未获批准前，只做只读核验和文档/合成测试，不进行任何模型推理。**
