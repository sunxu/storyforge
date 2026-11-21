# StoryForge R60 Base336 → Gold48 Quality-v1：新 Agent 启动提示词（2026-11-21，当前权威）

> 整段可直接复制给下一位 Agent。你不是来重做历史审计、增加安全框架或重训模型；**只做未完成的真实 Gold48 下一关口**。每次开始先获取 PR #31 实时 HEAD、CI 和实际源码，不依据这份提示词的日期猜进度。

## 使命与已冻结合同

**唯一业务目标（不可变更）**：48 条已冻结的 `RECONSTRUCTED_EVALUATION_INPUT` × 4 生成臂 = 192 条新回答：Qwen/Qwen3.8-27B Base、R46 v0.2 ckpt-7、R54 v0.3-A ckpt-16、R60 Base336 ckpt-37。再加入**独立的**48 条已冻结历史 Original Assistant 回复作第五种匿名回答来源，共 240 个六维盲评对象（不是 240 次模型推理）。8 Story、25 Session，主分析 48 条、剔除预先指定单一风险 Story 的整组六题后敏感性 42 条；25 Session 聚类，严重违规标记，盲审后解盲。历史 Original 只可作**描述性对照**，不得认定历史 actual-sent 输入与重建输入逐字节一致。冻结 Profile 为 `experiments/r60_quality/gold48_four_arm_generation_profile_frozen_v1.json`；输入/角色/参数/原始回答 SHA、模型 checkpoint 和敏感性分组均不可重新选取或修改。

**现行唯一判断依据**：PR [#31](https://github.com/sunxu/storyforge/pull/31) 实时 HEAD + 实际源码 + 已签收的 SAFE/Owner 私有证据；`1dcbce63e80c5e1d6e1e700f1927bd95f54a08ba` 是最近一次核验基线，不应被硬编码为永远最新。该基线 7/7 GitHub Actions SUCCESS，主 CI `1,778 passed · 6 skipped · 42 subtests passed`，均为**合成/离线**验证，不是 HF GPU 实测。

**证据边界**：Owner Gold48 48 条输入与 48 条原始回复/冻结 SHA 已签收；历史 HF CPU Tokenizer 48/48 SAFE PASS（`6b00971aefaf5e14f4b3b24a`，Run Key `r60-gold48-cpu-20261120T182842Z-e5de137532a1`）。该 CPU Job **只有 SAFE**，没有 `GOLD48_TOKEN_PREFLIGHT_PRIVATE.json`。修复后 `scripts/r60_gold48_gpu_worker_entry.py::STAGED` **恰好 11 份**，已去掉 `token_preflight.private.json`，不得伪造或要求补生成。GPU Loader 在固定 `Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` 使用 Tokenizer 并比对同一不可变 revision 的 `chat_template.jinja`，随后才加载模型权重。固定公开模板与该 revision 的 `tokenizer_config.json.chat_template` 已独立只读比对为完全一致（模板 8,952 字节），**但真实 Qwen/PEFT/CUDA GPU 加载及生成尚未实测**。

## 当前唯一行动（按最短路径）

1. **只读核查** PR #31 实时 HEAD / 7 个 Actions / Frozen Profile 不变；核对当前 `scripts/r60_gold48_gpu_cli.py` 的 `ready` 与 `scripts/r60_gold48_gpu_worker_entry.py::STAGED`。不改代码，除非出现可复现的具体缺口；如已有合成 CI PASS，不重新跑所有历史项目。
2. **Owner Mac 侧只处理缺口**：确认已有 0700 Stage 的 11 份 0600 文件及准确 Run ID、`approve-one-arm` 创建的 Owner 范围、当前提交代码 Bundle、已签收 R46/R54/R60 checkpoint 目录。不要从本地 Draft 或 SAFE 擅自重建、签署、推定不存在的文件，也不使用猜测路径。**Stage 现行精确 11 文件**：`frozen_profile.json`、`owner_freeze.private.json`、`adapter_bindings.private.json`、`input_manifest.private.json`、`input.private.jsonl`、`r46_evidence.private.json`、`r54_evidence.private.json`、`r60_evidence.private.json`、`owner_authorization.private.json`、`runtime_lock.hashes`、`runtime_contract.json`。以代码 `STAGED` 为准，文件名**不能多也不能少**。可信 Mac 私有目录及父目录权限 0700、源文件 0600；绝不包含历史 Original 回复。未授权新 Run ID 不自动创建，已有 create-only 产物不重建/不覆盖。
3. **复用已跑通的 HF CLI 上传/只读核验**：必要时 `hf buckets sync --dry-run` → `hf buckets sync --ignore-existing`；只上传干净的提交代码和 Owner 许可的私有 Stage，绝不把私有源文件发往 GitHub。运行 `scripts/r60_gold48_gpu_cli.py ready`，要求远端 Stage 精确文件集、逐文件 SHA，当前提交十个核心代码 SHA、无同 Run ID 历史 Job、远端结果为空、HF CLI dry-run 真正通过。回报真实 SAFE 原文的**非私密字段**，不自称 PASS。
4. **若 ready PASS**：停止 CPU/HF 环境重复开发，向 Owner 汇报唯一下一关口是**单独授权的真实 Qwen3.5/PEFT GPU 兼容性验证**；现有 `submit --execute` 是一个模型臂 **48 条**的完整正式生成，不等于单条 Smoke。除非 Owner 明确批准该 Run ID、资源与费用、执行范围，不提交任何 GPU。若 ready HOLD，只定位确切原因，用最小修复（必要时带回归测试）而不是新的 Probe/Runner/数据库。
5. **获各次独立正式授权后**：复用现有 Qwen3.5 Loader、Backend、Worker、hf_runtime 和 Mac 结果 SHA 审计，生产四臂各 48 条，另加原始 48 条形成 240 对象六维匿名盲评；48/42、Session 聚类与风险披露，最终 Owner 决议，绝不预先晋升模型。

## 禁令与真实性边界

**权限和最短路径**：Mac **不安装** `transformers`/`torch`/`peft`，不在 Mac 运行模型 Tokenizer/Chat Template/Token 预算；HF CPU 历史 PASS 不重跑。已取消 Provider 动态证明/0700 FUSE 原子账本/Owner Ed25519 强制签名，改由单 Owner Mac 的 `approve-one-arm` 0600 create-only 审批、既有 HF 权限、Job 历史与本地一次性提交标记，旧签名逻辑仅兼容历史审计。不使用 Supabase/PostgreSQL、不开新 Runner、不重复 CPU 探针、不修改冻结 Profile、不重复 48 输入与 204 Story/495 版本/R50 等历史审计。**这次文档/接手授权不是 GPU 费用批准**；`ready` 无 GPU，`submit --execute` 是**单臂完整 48 条正式生成**（不是 1 条廉价 Smoke），需 Owner 针对本次模型/Run ID/GPU 预算和范围另外明确批准。未知/失败不自动重试。真实 GPU PASS 后再按另行授权进入 192 生成、Owner 下载 SHA/Inspect、240 对象盲评和 Quality-v1 决议。当前 `quality_v1_admitted=0`、未晋升。

**不能谎报**：旧 Tokenizer SAFE `PASS` 不证明新 GPU Loader PASS；合成 CI `PASS` 不等于 Owner Mac 真实 `ready PASS`；本地指纹/Owner 配置不是 HF Provider 独立测量；HF Bucket 文件存在不等于当前权重 SHA 或输出经 Owner 签收。保持 `inference_authorized=false`（冻结文档的历史状态不可改）、`real_gpu_smoke=UNVERIFIED`、`quality_v1_admitted=0`，直到有对应新的可追溯 Owner/Job SAFE。

禁止重复：恢复 48 输入或历史 Original、重签 Gold48 Freeze/四臂 Profile、204 Story/495 版本来源审查、R50/R47/R48/R55/R58 历史排除、重复 HF CPU Tokenizer、Adapter 1.87 GB 哈希 CPU Job、0700 FUSE probe、Supabase/PostgreSQL/独立 Provider 或 Ed25519 动态授权系统。禁止 Mac 安装模型依赖，不输出 Owner 私有 Story/Prompt/原始回答/逐案 SHA，不访问未授权 RolePlay 生产数据库或 R50 sealed。不要更换四臂模型、Seed、EOS/PAD、Thinking、采样等冻结合同；不要复用旧 P4 Qwen3-32B/GLM 三臂。

## 汇报格式与文件入口

每次只报：PR/HEAD、最新 CI、**已验收事实**、**真正 HOLD/UNVERIFIED**、一项最短下一步、是否访问私有文件/数据库、是否提交 HF Job、是否 GPU/模型调用/训练、任何外部成本。仅当实际变更了必要代码或文档才提交 PR；提交后核对新 HEAD/CI。未拿到真实 Owner Mac 回执时，不编造 ready PASS。

- [主任务书](R60_BASE336_P2_QUALITY_EVAL_NEXT_AGENT_HANDOFF_20261119_CN.md)
- [Owner 操作手册（按顶部现行 11 文件流程）](R60_GOLD48_OWNER_LOCAL_RUNBOOK_20261121_CN.md)
- [训练后总体质量计划](plans/R60_BASE336_POST_TRAIN_QUALITY_EVALUATION_20261117_CN.md)
- [冻结四臂 Profile](../experiments/r60_quality/gold48_four_arm_generation_profile_frozen_v1.json)
- [HF 作业工程规范](standards/HF_JOBS_ENGINEERING.md)
- [仓库执行边界](../AGENTS.md)

**停止点**：截至已核验的 `1dcbce63`，Tokenizer 回执阻塞已解决、合成 CI 已 PASS，**本轮真实 Mac `ready` 尚未签收，GPU 推理尚未验证，192 新回答/240 盲评尚未进行**。新 Agent 接手后直接从真实 `ready` 开始。
