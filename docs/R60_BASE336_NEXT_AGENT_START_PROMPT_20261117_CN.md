# R60 Base336 下一 Agent 启动提示词（2026-11-17，可直接复制）

你现在接手 GitHub 仓库 `sunxu/storyforge` 的 **R60 Base336 训练后独立质量评估任务**。工作分支为 `r60/common2-cpu2-owner`。你的目标不是继续训练，而是先解决独立 Held-out 来源门禁，再在授权范围内准备 Base/Adapter 对照评估。

## 一、先核验，不要直接执行

1. 先读取仓库 `AGENTS.md`。
2. 只读核验 GitHub 当前分支 `r60/common2-cpu2-owner` 的 HEAD、工作流、PR、Issue #26；不要假设历史 SHA 仍是最新。Issue #26 当前跟踪的是 REAL History SFT 主线，不是 Base336 授权来源。
3. 按顺序完整阅读：
   - `docs/R60_BASE336_POST_TRAIN_NEXT_AGENT_HANDOFF_20261117_CN.md`
   - `docs/plans/R60_BASE336_POST_TRAIN_QUALITY_EVALUATION_20261117_CN.md`
   - `docs/plans/R60_BASE336_SUPABASE_PUBLIC_STORY_P2_ADDENDUM_20261117_CN.md`
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

## 三、当前任务：完成已批准 Supabase 来源 Draft 的 P2-C 隔离审查

Owner 已批准新的来源路线：仅使用 Supabase 已公开、已发布、非删除、原创且通过审核的故事，以及公开 World/Character/Opening 字段，构造内部评估提示；**不读取用户私有会话正文**。该授权只覆盖内部评估提示构造，不扩展为训练、公开发布或再分发。

P2-A / P2-B 已有 Draft 结果：

- 8 个公开故事、8 个故事谱系、5 位作者、8 个不同 World JSON。
- 3 条来源在 Base336 GPU Run 开始前创建，5 条在 Run 开始后创建；全部晚于 Base336 293/43 数据集冻结边界。
- 8/8 来源的 revision、审核快照 SHA256、快照与当前公开版本一致性、最新权限事件绑定及 public 目标可见性均通过。
- 已构造 48 条全新提示 Draft：8 个来源各 6 条，覆盖 Quality-v1 六维各 1 条；每条三条消息 `user / assistant / user`，不含 System、目标答案或参考答案。
- 未读取私有会话正文，未访问 R50 正文。

当前会话 Draft 工件（尚未 Owner Mac 私有冻结）：

- `R60_P2_PUBLIC_STORY_PROMPTS_DRAFT_20261117.jsonl`，SHA256：`a7cc5991e838cfbb6679591fdfad59860805dd703f1bee045b4c397f1deeee18`。
- `R60_P2_PUBLIC_STORY_SOURCE_MANIFEST_DRAFT_20261117.json`，SHA256：`12b356c3a856235af2bfae22542a227fbfbf99b5b7139ec04eb00f5ff75fa44d`。
- 校验器：`experiments/r58_quality/r60_base336_p2_public_prompt_package_gate.py`。
- 测试：`tests/test_r60_base336_p2_public_prompt_package_gate.py`，本地合成测试 9/9 PASS、compileall PASS；不要声称 GitHub Actions CI PASS。

**P2-C 仍为 HOLD。** 下一 Agent 不要重新抽取 Supabase 或重新构造提示；先完成：

1. 将 8 个新来源的 World 组件与 Base336 293/43 私有来源清单、完整 Story/World component graph 和历史版本交叉核验；不同 ID、不同 MD5、时间晚于冻结点都不能单独证明语义隔离。
2. 仅使用 Owner 授权的 R50 Protected/Reserved World 元数据做排除核验；绝不读取 R50 正文或答案。
3. 核验未复用 R47/R48/R55 已暴露开发题及其语义变体。
4. 逐条检查 48 条提示的来源忠实性、无原文长段复用、无未来信息泄漏、无隐藏指令混入；新增 NPC/角色细节必须明确是合成情境，不得伪称来源事实。
5. 保持权利范围仅为内部评估提示构造；不能推断作者授予训练或再分发权利。
6. Owner 在私有目录冻结最终来源 Manifest、提示 SHA256、World crosswalk、R50 元数据排除回执和独立 Reviewer 结论。

当前会话无法访问 Owner Mac 私有目录。若缺少 Base336 私有 source roster、World component evidence 或 R50 元数据清单，明确输出对应 HOLD 并向 Owner 索取这些**私有交叉核验证据**；不得改为读私有会话正文或 R50 内容。

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
