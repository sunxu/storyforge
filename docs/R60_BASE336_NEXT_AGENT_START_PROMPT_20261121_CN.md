# StoryForge R60 Base336 → Gold48 Quality-v1：新 Agent 唯一现行启动提示词（2026-11-21）

> **2026-11-21 Gold48 私有输入与输出传输最新进展**：已复用现有 \`InputManager\` + 本地 exclusive 0600 文件，提供 \`materialize_gold48_ro_input\`；已有 Gold48 生产 dispatcher 在原 Worker 后要求 \`deliver_gold48_private_result\` 上传三份私有结果与 manifest-last，并对每份 HF Bucket 输出下载验 SHA。无新生成器或通用 Runner。**仍需**受控 HF Job 包装调用输入物化、Owner Mac 独立下载核对、以及实际 Owner/Provider 身份和 GPU 明确批准；不得启动模型或认定远程 HF 交付成功。

> **2026-11-21 执行门禁代码进展**：原 `gold48_runtime_gate.py` 已用单 Owner 的 Job-local 0700 POSIX 消费证据取代不适用的跨 Job HF Bucket 锁，实际拒绝 FUSE 输出，继续要求 Owner/Provider 验签、依赖/镜像/Adapter 实证与 Loader 许可。**跨 Job 不重复执行只由唯一 Owner Mac 本地持久提交标记及完整 HF Job 历史保证，不是远端技术锁**。GPU Job 的安全私有输入本地化和 HF Bucket 结果回传仍未交付；两项信任锚和真实 GPU 授权仍未就绪。继续复用现有 HF CLI 与模型 Worker，不新增提交器/数据库。

> **2026-11-21 最新执行策略（覆盖旧共享账本规划）**：Owner 已选择**单 Owner Mac 串行提交**，不使用 Supabase/PostgreSQL 或 HF Bucket 作全局授权锁；复用已有 Mac HF Job 历史排重、本地原子提交标记与 CPU/GPU dry-run 方法。Mac 标记现通过共享 `OutputManager.write_safe` 完成原子不覆盖和目录 fsync。**原生产 `gold48_runtime_gate.py` 仍要求旧共享挂载，单 Owner GPU 生产通道未接通；不得绕过其门禁或声称运行就绪。** 下一步是核对并在获明确 GPU 授权后最小接入 Owner 可信提交、输出交付及运行身份，不要重做 HF Bucket RW/0700 探针、原数据 SHA、CPU Tokenizer、Adapters 或重复开发 Runner。保持 `inference_authorized=false`、`quality_v1_admitted=0`。


> **可直接将本文件下面“新 Agent 提示词”整段交给新 Agent。** 2026-11-19/20 的旧启动提示、旧 P2-B/C HOLD 快照与旧两臂构想是历史记录，**不得作为当前任务执行**。以实时 GitHub PR #31 HEAD、当前源码和最新 Owner 私有 SAFE 为准，不以文件日期推断状态。

## 新 Agent 提示词

你接手 `sunxu/storyforge` **R60 Base336 训练后的 Gold48 独立质量评估**。唯一主线目标是：使用 **已冻结的 48 条重建评估输入**，对同一 Qwen3.8-27B Base、R46 v0.2 checkpoint-7、R54 v0.3-A checkpoint-16、R60 Base336 checkpoint-37 四个生成臂产生 **4×48=192 条**新回答，并将其与 48 条**已匹配、已独立哈希冻结的历史原始 Assistant 回答**作为第五匿名来源一起开展 **240 份对象的六维盲评**，最终判断 Base336 相对 Base、历史强对照 v0.2、诊断臂 v0.3-A 及描述性历史 Original Reference 的质量与严重缺陷。**当前禁止直接开始这 192 次生成**：需要先关闭运行时适配与单独推理授权门禁。新 Agent 不是来重新挑题、训练或重新证明旧审计的。

### 1. 接手时先核对，不重做

- 活动 PR：[**#31**](https://github.com/sunxu/storyforge/pull/31)，源分支 `docs/r60-p2-r47-r48-r55-source-shape-audit-20261118`，目标 `r60/common2-cpu2-owner`。上一已核实 HEAD 为 `4e03a6d1e8a7545a23394e213087b4b46aa551a8`，**6/6 GitHub Actions SUCCESS**。先只读核对实际最新 HEAD / CI / 文件状态；不是要回退或复制该提交。
- 阅读 `AGENTS.md` 最顶部的 2026-11-21 覆盖规则、本文件、`docs/R60_BASE336_P2_QUALITY_EVAL_NEXT_AGENT_HANDOFF_20261119_CN.md` 最顶部，以及 `docs/plans/R60_BASE336_POST_TRAIN_QUALITY_EVALUATION_20261117_CN.md` 最顶部。较旧段落存在“未有 Gold48/需完成全历史全集/P4旧三模型”的旧快照；**以本段和实时 SAFE 为准**。
- **Gold48 Owner 本地签收已完成：** `GOLD48_SCOPED_OWNER_FREEZE_COMPLETE__GENERATION_PROFILE_PENDING`，`owner_gold48_freeze=true`，范围为 `SCOPED_RECONSTRUCTED_EVALUATION`。8 个公开来源 × 6 = 48 主分析；25 Session；标记风险来源 6 条仍纳入主分析，但从预注册的 **42 条敏感性**分析排除；48/48 重建输入 SHA 与 48/48 原始回答 SHA 由独立 Owner 私有冻结 Manifest 锁定。
- **HF CPU 真实技术闭环已完成：** Gold48 Stage 16 项清单 + 17 个文件逐字节传输校验；唯一 HF CPU Job `6b00971aefaf5e14f4b3b24a` 已完成，Run Key `r60-gold48-cpu-20261120T182842Z-e5de137532a1`；`GOLD48_HF_CPU_TOKEN_PREFLIGHT_COMPLETE__NO_FREEZE` 和 `GOLD48_HF_CPU_OWNER_RECEIPT_VERIFIED__NOT_FROZEN` 已验；48/48 在 16K/32K 两种 Thinking 诊断预算均无超限，`transformers=5.16.1`。**无需重新装 Mac transformers、重新 Stage、再同步或重复提交 CPU Job。**
- **四模型 Generation Profile 已由 Owner 按建议单独批准并冻结**：`experiments/r60_quality/gold48_four_arm_generation_profile_frozen_v1.json` 状态 `GOLD48_FOUR_ARM_PROFILE_FROZEN__RUNTIME_VALIDATION_PENDING`，`owner_generation_profile_freeze=true`。不可原地修改；候选 `gold48_four_arm_generation_profile_candidate_v1.json` 的原 Git Blob SHA `394013dc182fa095040808e02c4ea2e393636d30` 已绑定，`tests/test_r60_gold48_four_arm_generation_profile_freeze.py` 检查差异。
- **仍为 HOLD**：`inference_authorized=false`、`gpu_authorized_by_this_document=false`、`training_authorized=false`、`quality_v1_admitted=0`，模型未晋升。历史真实 Provider actual-sent Prompt 无法证明，`historical_actual_sent_prompt_verified=false`；完整 Protected/Reserved/Dev/Teacher 历史全集隔离并未证实；目标回复前 48 条 Memory 无已验证摘要，不能补造。Owner 已明确接受**受限范围**风险，不等于全宇宙独立 PASS。

### 2. 唯一正式实验合同（不要擅改）

- 固定 Base `Qwen/Qwen3.8-27B`、Revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`，架构 `qwen3_5/Qwen3_5ForConditionalGeneration`。另外三臂只加载历史固定 LoRA：R46 ckpt-7、R54 ckpt-16、R60 Base336 ckpt-37，所有 Adapter `r=64,alpha=128` 且指向同一 Base Revision；精确 HF Bucket Checkpoint URI 从 Frozen Profile 读取，不猜路径或升级 checkpoint。
- 四臂共享 Owner 冻结的 48 条**完全相同的重建消息**和每案输入 SHA；`enable_thinking=false`、`context=32768`、`max_input_tokens=30720`、`max_new_tokens=2048`；采样 `do_sample=true, temperature=0.7, top_p=0.8, top_k=20, min_p=0`，Seed `42 + 固定零基 case index`；不允许静默截断、补造 Memory、在某个臂上调整上下文或改写已冻结数据。
- 固定 Base generation config 的 EOS `[248046,248044]`、PAD `248044`；依照被冻结模型 Revision 的真实 Chat Template、生成停止行为做运行时验证，不能套用旧 P4 Qwen3-32B/GLM 三模型的 EOS、`transformers==4.57.1` 运行时或旧 `AutoModelForCausalLM` 加载策略。当前 CPU Tokenizer 通过**不等于**完整模型推理运行时兼容。
- 历史原始回答是独立匿名第五**回答来源**，不是第五生成模型、不是绝对正确答案，不得进入任何生成输入/Tokenizer Stage、模型可见 Prompt 或新模型日志。四生成臂可严格比较相同重建输入；历史回答只做同历史上下文的**描述性**对照，不声称其使用了相同的历史 actual-sent System/Rules/Memory 字节。
- 盲评按已冻结的六维与严重违规标记、按 25 Session 聚类/8 Story 来源分层，同时报告 48 主分析和 42 敏感性分析，先盲后解盲；绝不能只报告有利子集或用训练 loss 代替文学质量。

### 3. 新 Agent 的下一段实际工作（只补缺口）

按此顺序推进；已有证据能直接验证时不重跑、也不新建同功能工具：

1. **只读确认最新 PR #31 和冻结 Profile 的不可变性。** 读 `generation_eval.backend`、`generation_eval.worker`、`hf_runtime`、`scripts/hf_job_guard.py` 与 `src/storyforge_dataset/generation_eval/gold48_qwen35_loader.py`，以及相关已有合成测试。先列出现成组件与剩余真实阻塞，不先新写 Runner/通用框架。
2. **精准绑定既有 Adapter 哈希：** 从三个现有 HF 私有历史 Release/Reload SAFE 中查精确 `adapter_model.safetensors` 的可验证 SHA 与 checkpoint 归属，核对 `adapter_config.json`（已只读核对三个均为同 Base、LORA r64/alpha128、`model.language_model` 同一组模块）；不要下载三份各 1,867,797,544 字节大文件来重复做已有核验。若旧摘要不具备来源/目标字节身份，明确相应 `HOLD`，再作最小必要的受控字节验证。
3. **只补 Qwen3.8/PEFT Runtime 合同：** 核对支持 `Qwen3_5ForConditionalGeneration` 和 PEFT LoRA 的**具体 Transformers/PEFT/Torch/CUDA 版本、镜像 Digest 与 hash-pinned 依赖锁**，不要以 tokenizer `5.16.1` 自动宣称 GPU 推理依赖已经验收；必要时用 HF **CPU-only** 做最小可复现的版本/类/模板/Import 预检（CPU 操作已获用户允许，可付费，但不重新跑 Gold48 Tokenizer）。版本或兼容性无证据时保留 HOLD。
4. **复用已有生成核心**： `gold48_qwen35_loader.py` 是专用薄 Loader，`generation_eval.backend.TransformersGenerationBackend` 已提供模板与 `generate`，`generation_eval.worker.run_generation_batch` 已提供逐案 Seed、Token 预算、OutputManager 私有 create-only 写入和 SAFE。只修复经证据确认的**具体** LoRA / 多模态 Qwen3.5 加载不兼容、运行时参数或既有 Worker 的四臂 Role 适配缺口；禁止复制生成循环、Token 核心、盲评和 HF Job 提交器。
5. **真实 GPU/模型运行时 Smoke 是独立门禁**：需明确绑定其范围、型号、镜像/依赖锁、Run Key、预算和授权；目前 Frozen Profile 明确 `inference_authorized=false`，不得因为用户批准数据/Profile 冻结就自动跑 GPU Smoke，更不得直接 192 次正式生成。Smoke 通过也不等于已批准正式推理；后续按最小范围、唯一 Job、只读输入/独立读写输出、SAFE 回收和失败不自动重试办理。真实 GPU Smoke 可以解决后再单独申请 192 次生成，**不要先做质量打分或模型晋升**。

### 4. 严格禁止的重复工作

- 不重做 Gold48 48 条恢复、48 份历史原始答案绑定、8 来源权限/公开卡版本审查、Owner Freeze、42 敏感性分组、HF Stage/Token 预检、旧 204 Story/495 版本语义审阅、R50 50=46+4、R47/R48/R55 旧 Dev20 回链或旧 R58 空 CSV 审计。不要重新生产 48 道题、修改原历史 Prefix、重新签署已冻结资料或反复调试旧 SQL。
- 禁止读取 R50 sealed 内容或未经请求的生产 RolePlay 私聊；不上传私有 Prompt/Story ID、Owner 交叉映射、历史原文、原始回答或 SHA 逐案清单至 GitHub / 聊天 / 公共日志。只输出 SAFE 聚合和可审查的代码/合成测试。任何私有 Owner 文件严格 0700/0600、create-only，不原地修改。
- 不把旧 P4 `experiments/r60_quality/p4_generation_profile_frozen_v1.json`（Qwen3-32B/GLM）当本轮 Gold48 四臂 Profile；不调整已经冻结的模型、采样和数据以绕开 Runtime 问题。不要把合成 CI PASS、Adapter 历史 Reload 或 HF Token PASS 误作本轮完整四臂 GPU Smoke PASS。
- 不重新实现 `src/storyforge_dataset/token_preflight.py`、HF Runtime、`generation_eval.worker`、原有提交 Guard/Job/日志设施；GPU 推理授权不得从 CPU 工作或先前训练继承，不得以“用户 HF 付费无需重复授权”绕过本轮已冻结的 `inference_authorized=false` 边界。

### 5. 一轮工作如何完成与汇报

在当前 PR #31 **继续现有分支**，先查实际 HEAD/CI，再优先完成一个真实阻塞的**最小**检查或修复（例如 Adapter SHA 来源绑定、确定可复用的 Qwen3.5 Runtime 镜像及依赖锁、具体 Loader 合同合成测试）。没有必要的缺口则不新建代码；能直接复用旧证据就报告已经 PASS。更新**同一份**主任务书顶端和必要运行时相关文档，不改动历史冻结产物；相应提交后核对最新 CI。

每次汇报必须区分：`OWNER_GOLD48_FREEZE=PASS`、`FOUR_ARM_PROFILE_FREEZE=PASS`、`FULL_QWEN35_RUNTIME_SMOKE=PENDING`、`INFERENCE_AUTHORIZATION=HOLD`、`QUALITY_V1_ADMISSION=0`。准确列出已核验/未核验、引用源码/SAFE、Git commit、Actions 状态、下一最短动作，以及是否访问私有数据/DB、是否提交 HF CPU Job、是否启动 GPU、模型调用和训练。**失败只报告精确 HOLD，不要重复训练或重建 Gold48。**

## 接手必读入口

- [唯一主线任务书](R60_BASE336_P2_QUALITY_EVAL_NEXT_AGENT_HANDOFF_20261119_CN.md)
- [总体训练后质量计划](plans/R60_BASE336_POST_TRAIN_QUALITY_EVALUATION_20261117_CN.md)
- [冻结四模型 Profile](../experiments/r60_quality/gold48_four_arm_generation_profile_frozen_v1.json)
- [Gold48 Qwen3.8 + LoRA 薄 Loader](../src/storyforge_dataset/generation_eval/gold48_qwen35_loader.py)
- [HF Runtime 工程规范](standards/HF_JOBS_ENGINEERING.md)
- [项目规则](../AGENTS.md)

**停止位置：** 当前只有数据集与生成 Profile 冻结以及 Loader 合成验收，**没有**四模型真实 GPU 运行时 Smoke、192 条新生成、五来源正式评分或 Quality-v1 晋升结论。下一 Agent 应推进 Runtime 准备，而非历史回溯。
