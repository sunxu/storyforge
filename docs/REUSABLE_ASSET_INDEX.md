# StoryForge 历史可复用资产索引（SAFE）

> **2026-11-26 增量：** 当前主线转向[新来源质量数据建设](plans/STORYFORGE_NEW_SOURCE_QUALITY_MAINLINE_TASKBOOK_20261126_CN.md)。PR #38 已合并；实查 `main@5de5f81f1db1724419dc699c815ae4e042639b17:src/storyforge_gold_quality/quality_v1.py` 存在，复用时优先调用 main 内核。该内核仍限定 `gold195`、`r58_round1` 及 `original_gold`，新来源不能冒用旧 corpus。SFT 编译器、Skill、历史恢复及 HF Runtime 仍按下表固定历史来源检查，不默认全部已进入 main。先取得真实新素材再决定必要的接口复用或最小扩展。旧索引快照保留，不重新清理历史分支。

> 快照：2026-11-22；核对基线 `main` = `1b5ac810c304167f31626eba4cbf6e7b7235569d`。这是**代码/证据的查找地图**，不是自动合并清单、执行许可或质量准入回执。历史 PR、归档和本地备份均不得被误认为已经进入 `main`。

## HF Inference Providers：语言模型 Reviewer 调用规范（2026-11-26，Owner 实测）

- 首选 HF Router HTTP：`GET https://router.huggingface.co/v1/models` 查询实时 `data[].id/providers[]`，确认指定 Provider 为 live、上下文满足实际需求；`POST https://router.huggingface.co/v1/chat/completions`，model 使用目录原样 ID 加 `:provider` 固定路由。凭据从 Owner 私有环境 `HF_TOKEN` / 已登录凭据读取，组织计费请求使用 `X-HF-Bill-To`（组织名由 Owner 本机配置）。不记录凭据或私有账户信息。请求携带账单头、返回 is_byok=false 不等于已核实组织账单归属。
- 历史 SDK `InferenceClient(provider=..., bill_to=...)` 曾成功；2026-11-26 huggingface_hub 2.4.0 对旧两条路由报不支持，Hub `model_info(expand=["inferenceProviderMapping"])` 四模型均空，而 Router 实际目录有 106 个模型。四次旧正式请求 HTTP 400、有效评审 0；不能用 Hub 空映射推断 Router 无服务。Novita 不在本次目标家族目录中。不要重试失效路由、盲猜模型 ID 或为此升级 SDK/重写框架。
- 先对新路由执行一次无隐私合成 JSON + 逐字原文引文测试，验证 HTTP、finish_reason、JSON 类型和引文、实际返回模型/Provider；仅失败路由诊断。2026-11-26 Owner 实际回执：以下两条均 HTTP 200、stop、JSON 及精确引用 PASS。此为时点证据，不是永久可用或真实质量 PASS。

| 请求 model | 实际返回 model / Provider | 合成测试 |
|---|---|---|
| `deepseek-ai/DeepSeek-V4.1-Flash-1017:cloudflare` | `deepseek/deepseek-v4.1-flash-1017` / Cloudflare | 225 tokens；$0.00004815；4.03s |
| `moonshotai/Kimi-K3.1-Pro:deepinfra` | `moonshotai/kimi-k3.1-pro` / DeepInfra | 324 tokens；$0.0020216；8.35s |

- 正式审核仅发送 Owner 批准的单条盲审输入，两个 Reviewer 分离调用；固定真实路由与 Prompt，禁止自动重试或替换。先 create-only 保存原始 HTTP 回执（包括失败），再验证输入/目标绑定、实际返回模型/Provider、六维、严重标记、精确引文与判定一致性；私有域保留用量/费用和请求绑定。日志/Git 仅 SAFE 汇总。技术有效与文学质量、独立性、训练准入分开；不同模型家族与服务商不能证明统计独立。新服务商及模型的正式外发范围须确认，不因合成测试成功扩大授权。
- 2026-11-26 World04 正式实测：新路由获 Owner 批准后 4/4 HTTP 200，3/4 有效评审且均 PASS，1 个双 PASS 候选；另一份原始 PASS 声明的 9 项证据中 7 项逐字匹配、2 项无精确来源（rule_fidelity、hard_fact_or_ban），保持 HOLD。38005 tokens、报告费用 $0.105284028、自动重试 0。模型路由技术可用不等于引文证据有效；诊断归一化仅用于定位，不用于放宽门禁。原始回执不改，私有映射/正文不入 Git。
- 复用现有 Quality-v1 审核合同与冻结证据，临时 stdlib HTTP 操作仅作执行入口，不提交一次性脚本，不新增 API 管理模块。OpenRouter 直连不是本轮已验证入口，不自动切换认证、账单或数据处理路径。

## RolePlay 前瞻留证及 StoryForge 接入（跨仓库既有资产）

- 实查 `sunxu/RolePlay@6cd4ccf5ebf9f44872e28bdec2c3a94b06c3d424`（相对 `a2c40eb7b01ba72a92c8d64b7d861f49ddaf3fac` ahead 59）：完整 Git Tree 比对 99 个留证相关 Blob 未变。V2 route 仍有 createV2EvidenceRun、原文、续写、后处理及绑定接线；主链路 Prompt、Provider、取消和拒答等已有更新，当前运行及部署未经本轮核验。
- [实际生成输入留证方案](https://github.com/sunxu/RolePlay/blob/6cd4ccf5ebf9f44872e28bdec2c3a94b06c3d424/.claude/plans/2026-11-07-v2-generation-evidence.md)、[单会话验收](https://github.com/sunxu/RolePlay/blob/6cd4ccf5ebf9f44872e28bdec2c3a94b06c3d424/.claude/docs/v2-evidence-acceptance-20261113.md)、[StoryForge 接入](https://github.com/sunxu/RolePlay/blob/6cd4ccf5ebf9f44872e28bdec2c3a94b06c3d424/ops/evidence/storyforge-handoff.md)、[运行前清单](https://github.com/sunxu/RolePlay/blob/6cd4ccf5ebf9f44872e28bdec2c3a94b06c3d424/ops/evidence/preproduction-checklist.md)。
- 入口：`src/lib/generation-evidence/capture.ts`、`capture-control.ts`、`export-service.ts`、`ops/evidence/worker.ts`、`ops/evidence/verify-bundle.mjs`。历史单会话导出/独立字节比较成功，但 RELAY_EGRESS_UNKNOWN / PARTIAL / HOLD，接收人签收未完成；校验器实际固定 HOLD/certifiedLineage=false。不复写、不绕过、不冒称训练放行。比较器输出含私有文件摘要，留 Owner 本地，不粘贴完整输出到聊天/Git。现成能力不等于当前运行已开启，不继承历史生产批准。
- 历史隔离权威缺口见冻结 R60 `docs/evidence/R58_G1_PROTECTED_SOURCE_INVENTORY_REUSE_NEXT_STEP_SAFE_20261101.md` 与 `docs/plans/R60_BASE336_P2_PROTECTED_CROSSWALK_EVIDENCE_INDEX_20261118_CN.md`。11月20日风险接受仅限 Gold48 评估；不再重复 2263 文件扫描。新来源限定范围政策已获 Owner 专项批准（主线任务书 v1.7 §0A/0B）；仅未来全新原创适用，已知清单221 Story及 T 已实际冻结（2026-11-26T16:17:21.337667+00:00），不替代当前 gate 或自动授权采集/训练。

- 独立适用训练输入查重（2026-11-27）：RolePlay 既有 `scripts/export-top-v2-chat-context.mjs::contextQuery`（只复用指定会话逻辑，禁止默认排名批量导出）、`scripts/export-v2-story-training-evidence.mjs`、`src/app/api/stories/v2/[id]/versions/route.ts`；消息 GET 部分分支会触发修复，非严格零写审计。冻结 R60 `experiments/r58_quality/gold_source_context_stage.py` 与 `test_gold_source_context_stage.py` 已有结构/摘要预检但时间点 NOT_PROVEN。原 HOLD 导出用途不变，独立合法来源前后绑定预检尚未完成，见任务书 v1.8 §0C。无需重复开发或先开留证。

- 2026-11-27 独立来源预检 Owner 回执：Source Stage 5/5 合成通过；独立时间、完整性、目标 revision 与七类端到端拒绝未验。新增查重冻结 R60 `scripts/r60_p2_gold48_source_component_bind_cpu.py` 与旧 R02 point-in-time 合同：可参考既有 revision/组件绑定，旧 P2 用途仅评估，不复用为训练源。Mac 本地旧 pilot 固定 ca5ad674 提交远端请求422，待本机先查，不重复实现。最新可查 RolePlay 部署记录 20412c0e（2026-11-26 18:18:46 UTC+8），非当前运行实证。任务书 v1.9 §0D 待专项批准本地最小验证，不新增留证系统。

## 使用规则

1. **默认从最新 `origin/main` 开始。** 新开发之前先搜索现有代码、测试、规范和本索引；以**固定 SHA + 文件路径**定位，不能仅凭会变动的分支名决定复用。
2. **优先复用，禁止重复造轮子。** 对照当前需求：主线已有则直接调用；归档已有则检查依赖和测试后只移植必需文件/提交；仅有部分能力则做最小补充。禁止整体合并历史实验分支或原样复制大套实验脚本。
3. **每次改动留下查重结果。** PR/交接至少写明：查过哪些 `ref@SHA:path`、当前 `main` 是否已有、为何复用或不复用、必要的回归测试、保密及授权边界。索引缺项先定位再补索引，不能以“没找到”为由直接重建。
4. **历史 PASS ≠ 当前准入。** 复用前重新核对输入契约、依赖、运行环境、隐私限制、质量门槛和 Owner 授权；不可借历史 GPU/推理/训练批准启动新任务，不可从 SAFE 汇总推断私有材料可公开。
5. **冻结与保管。** `archive/*` 不改写；`main` 不强推。仅本地的 `backup/*` 不等于 GitHub 归档，外部 Agent 不能假定能获取；需要长期离机恢复时由 Owner 另行制作并安全保存 Git bundle。更新分支/PR 状态时同步核对此表。

## 远端资产（按能力分组）

状态口径：**主线已有**＝相应 Git 提交是当前 `main` 祖先或文件已明确核实；**历史可复用**＝源码仅在归档/其他分支，仍需集成测试；**独立待审**＝不可自动合并；**证据/方案**＝不是训练、推理或晋升授权。

| 能力／用途 | 可追溯来源（固定提交） | 优先查看的入口及状态 |
|---|---|---|
| v0.1 工程基线 | `main@1b5ac810`；`v0.1-evidence-frozen@d1186a7` | `README.md`、`configs/qwen38-27b-qlora-*.yaml`；**主线已有**。保持原有数据隔离、Label Mask 与训练门禁。 |
| R40 / R46 纠偏审计 | `audit/r40-corrective-execution-20261014@78bc3926` | `docs/evidence/V02_R40_CORRECTIVE_EXECUTION_20261014.md`；证据/方案；Open [PR #1](https://github.com/sunxu/storyforge/pull/1)。 |
| R49 / R50 来源审查与 CPU46 | `audit/r49-r50-source-intake-20261015@337cee2f`；`docs/r50-world-cpu46-audit-20261119@116ce6b1`；`docs/r50-agent-handoff-20261119@81265df8` | `scripts/v03_r50_build_46_private.py`、`docs/evidence/`、`docs/handoffs/StoryForge_R50_Agent_Handoff_20261119_CN.md`；历史可复用/受保护的门禁；Open PR [#2](https://github.com/sunxu/storyforge/pull/2)、[#32](https://github.com/sunxu/storyforge/pull/32)、[#33](https://github.com/sunxu/storyforge/pull/33)。 |
| R51 Gold195 来源清点 | `audit/r51-gold195-admission-20261019@ea5e2e4c` | `scripts/v03_r51_gold195_source_inventory.py`、`docs/evidence/V03_R51_GOLD195_REAL_SOURCE_PREFLIGHT_20261019.json`；只读清点不等于准入；Open [PR #3](https://github.com/sunxu/storyforge/pull/3)。 |
| R55 Gold5 工具与 SAFE 回执 | `archive/r55-gold5-tools-20261026@d51c2150` | `docs/R55_GOLD5_TOOLING_ARCHIVE_CN.md`、`.github/workflows/r55-gold5-archive.yml`；该归档提交已是当前 `main` 的祖先；仍以当前代码和授权边界为准。 |
| R57 B_PROMPT 与交接 | `archive/r57-bprompt-safe-20261028@9fb6c659` | `docs/evidence/R57_BPROMPT_DEV20_FINAL_SAFE_20261028.md`、`docs/handoffs/R57_TO_R58_PRETRAIN_GATE_SAFE_20261028.md`；已在 R60 冻结历史中保存，**B_PROMPT 未晋升**。 |
| R57 世界隔离／v0.4 准入门禁 | `r57/v03b-data-design@4dd144d9` | `scripts/r57_v04_admission_gate.py`、`scripts/r57_g2_target_anchored_world_audit.py`；历史可复用，不自动准入；Open [PR #5](https://github.com/sunxu/storyforge/pull/5)。 |
| R58 RolePlay SFT Skill | `r58/roleplay-sft-skill-v01@70e0d7da` | `skills/storyforge-roleplay-sft/SKILL.md`、`experiments/r58_quality/`；历史可复用，私有来源/训练授权独立核验；Open [PR #7](https://github.com/sunxu/storyforge/pull/7)。 |
| Gold Quality 统一证据流水线与 SFT 候选 | `gold-quality/unified-pipeline-v1@9c482ab3`；`gold-quality/quality-v1-sft-candidates@adc3876d` | `src/storyforge_gold_quality/`、`experiments/r58_quality/quality_v1_sft_candidates.py`；独立工作区仍在使用；Open PR [#8](https://github.com/sunxu/storyforge/pull/8)、[#11](https://github.com/sunxu/storyforge/pull/11)。**未整体进入 main**。 |
| R59 历史上下文恢复 / Strict28 | `r59/shared-history-recovery@1fbe6bc0`；`r59/strict28-history-exposure@a458bb27` | `src/storyforge_gold_quality/history_recovery.py`、`experiments/r58_quality/r59_strict28_historical_exposure.py`；优先共享核心、避免重复解析；Open PR [#10](https://github.com/sunxu/storyforge/pull/10)、[#9](https://github.com/sunxu/storyforge/pull/9)。 |
| R59 Pilot8 历史密度 | `r59/pilot8-history-density@0c90e43a` | `experiments/r59_history_density/r59_history_density.py` 与对应测试；隐私安全聚合工具；Open [PR #13](https://github.com/sunxu/storyforge/pull/13)。 |
| R60 HF Jobs CPU-first Runtime | `archive/r60-final-20261122@15462b87` | `src/storyforge_dataset/hf_runtime/`、`docs/HF_JOBS.md`；**历史可复用，当前 main 不包含该包**。先复用统一输入/输出/资源边界，不另造 Runtime。 |
| R60 P4 Generation Eval | `archive/r60-final-20261122@15462b87` | `src/storyforge_dataset/generation_eval/`、`tests/test_generation_eval_*.py`；历史工程与 fail-closed 能力已保存；[PR #30](https://github.com/sunxu/storyforge/pull/30) 已关闭未合并，**当前 main 不含该包**；不得继承旧 GPU/推理授权。 |
| R60 P2 独立 Reviewer 预检 | `archive/r60-final-20261122@15462b87` | `experiments/r58_quality/r60_independent_reviewer_offline.py`、`docs/schemas/R60_BASE336_INDEPENDENT_EDGE_REVIEW_SCHEMA.json`；冻结来源只作审查/重用依据，私有原始数据不在公开 Git。 |
| R60 Base336 / Gold48 正式结论 | `main@1b5ac810`（报告）；`archive/r60-final-20261122@15462b87`（历史代码） | `docs/R60_BASE336_GOLD48_QUALITY_V1_FINAL_OWNER_DECISION_20261122_CN.md`；**报告已进入 main，工程历史未整体进入 main**；478/480 修订评分冻结，**NO_PROMOTE**、生产不变。 |
| R60 P2-A Owner 包规范化 | `archive/r60-p2a-normalizer-20261122@244ebdee`（与 `r60/p2a-owner-package-normalizer-v1` 同一 HEAD） | `scripts/r60_owner_approved_package_normalizer_v1.py`、`tests/test_r60_owner_approved_package_normalizer_v1.py`；独立待审；需 Owner 明确批准，禁止自动应用建议。 |
| R60 Gold192 诊断历史 | `r60/gold192-ledger-diagnostics@4f862aee` | 历史合并/证据追踪；相对 R60 冻结归档有 1 个独有合并提交，但比较未发现净文件差异；**保留来源，不作为必需的新实现**。 |
| R60 文档交接分支（特别限制） | `docs/r60-p2-r47-r48-r55-source-shape-audit-20261118@618cc911` | 在冻结 `15462b87` 之后还有 3 个提交，含 R61 候选文档；**不是 R60 最终权威来源**，不因列入索引而启动/授权 R61。 |

## 仅 Owner Mac 的历史引用（不是可从 GitHub 自动拉取的分支）

| 本地引用（2026-11-22 已核验） | 用途／注意 |
|---|---|
| `backup/main-unarchived-20261122@96ffcbb0c63620d3c4b2521cb1fb00fda963f692` | 保存本地旧 `main` 的 8 个独立提交，涉及 Reviewer B、对账、R59 CPU 工具和 AGENTS；归档有相关或更晚版本，但文件并非全部一致。复用前必须逐文件对比。 |
| `backup/r60-new-generation-evidence-pilot-20261122@ca5ad674262158e9ad6ec747a3cbb8beae54f4bd`（同 `r60/new-generation-evidence-pilot`） | `experiments/r58_quality/r60_new_generation_evidence_pilot.py` 与测试；未核准合入主线，不能当作远端资产或新执行许可。 |
| `backup/main-before-sync-20261026`、`local/gold-quality`、`local/r59-history-audit` 等 | 历史/本地别名；未作为独立可复用实现逐一审计。优先使用上表固定远端来源，确需使用时先查提交和文件差异。 |

## 开发前查重：最小可复制命令

```bash
git status --short && git rev-parse HEAD
git fetch origin --prune

# 例：查 R60 P4，而不是重新开发生成评估执行器
ref=15462b8779401833a5014846bc57318dd6bc1b1c
git ls-tree -r --name-only "$ref" -- src/storyforge_dataset/generation_eval/
git log --oneline "$ref" -- src/storyforge_dataset/generation_eval/
git diff origin/main "$ref" -- src/storyforge_dataset/generation_eval/
```

结论写入新 PR / Agent 交接：`搜索范围 → 已有实现 → 差距 → 选择的复用路径 → 测试与授权边界`。如果只需一项能力，在新分支上按**必要的文件或独立提交**挑选，重新测试；不整体合并 R60 等历史分支。未经单独授权，不执行 GPU、推理、训练、部署、模型晋升或 R61 工作。
