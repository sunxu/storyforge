# StoryForge — 有限质量工程收敛任务书

> **2026-11-26 当前执行入口：** Owner 已批准[新来源质量数据建设任务书](STORYFORGE_NEW_SOURCE_QUALITY_MAINLINE_TASKBOOK_20261126_CN.md)。Phase 1 的 Quality-v1 内核及原有合成测试已经由 PR #38 合入 main；下文保留历史实施合同，不再作为待执行的迁移任务。停止旧 Gold 扩展筛选与历史证据修复；后续从一个原创世界、3–5 条原始互动候选的采集试点开始。只在实际素材产生且证实必要缺口后复用/最小补充现有能力。R60 NO_PROMOTE、准入0、R61 未启动及各授权边界不变。[新 Agent 接手提示词](../handoffs/STORYFORGE_NEW_SOURCE_QUALITY_NEXT_AGENT_20261126_CN.md)。

**版本：** v1.0（2026-11-24）  
**性质：** 存量工程资产审计、最小复用和必要合成回归；**不是**新的模型质量实验、评审或 R61 授权。  
**目标仓库：** `sunxu/storyforge`；唯一集成目标为 `main`，通过独立 PR 审查。  
**初始基线：** `main@d46fa33ccb8b9bcee972c86cc3dec7f069b8fd32`；实施时必须重新验证远端 HEAD。

## 一、唯一产品目标和当前事实

StoryForge 需要的是可证明优于基座模型的高质量中文互动剧情能力：自然中文、跨轮/世界事实一致、NPC 有效推进、保留玩家自主权，遵守硬规则。工具、准入 PASS 数、代码迁移量均不是产品质量指标。

- R60 Base336 / Gold48 已结案：`NO_PROMOTE`、`quality_v1_admitted=0`、`model_promoted=false`、`training_authorized=false`。P1 十案助手审阅及有界只读机制核查仅作为历史诊断；Owner 独立人工复审未完成；不再扩大 R60 诊断。R61 不启动。
- R59 旧五条 Quality-v1 候选继续证据 HOLD；不得通过反复 Stage、Autolink、Preflight、Binder 或填充缺失声明争取通过。合法、可复现、经批准的**离线训练上下文**不必字节级复现历史生产 Provider 请求；若额外声称历史目标时点的精确输入才另需历史版本与时序证据。
- 当前 `main` 没有 `src/storyforge_gold_quality/`、`skills/storyforge-roleplay-sft/` 和 `experiments/r58_quality/` 的完整历史实现；它们分别存在于尚未合并的 Draft PR #7/#8/#11 和 R60 冻结归档。**历史可复用≠已进入 main≠新准入**。

权威历史索引：`docs/REUSABLE_ASSET_INDEX.md`；冻结结论：`docs/R60_BASE336_GOLD48_QUALITY_V1_FINAL_OWNER_DECISION_20261122_CN.md` 与 `docs/quality/R60_FAILURE_MODES_MINIMAL_IMPROVEMENT_PLAN_20261122_CN.md`。

## 二、先查重再实施

按照“主线已存在 → 直接复用；历史有实现 → 选择性移植；明确缺件 → 最小补充”顺序执行。优先检查：

| 能力 | 现成来源 | 本轮处理 |
|---|---|---|
| Quality-v1 六维判定与世界隔离 | `gold-quality/quality-v1-sft-candidates@adc3876d6d0350c270e2b5fa5ccc832438fdf7ee:experiments/r58_quality/quality_v1.py` 与同目录 `test_quality_v1.py` | **首批只移植这一个独立、无第三方依赖的质量门禁及原有合成测试** |
| Gold Quality Manifest / CLI | `gold-quality/unified-pipeline-v1@9c482ab3:src/storyforge_gold_quality/`，Draft PR #8 | 保留历史引用；由于 CLI 涉及多模块、冻结源绑定和分支依赖，本批**不整套引入** |
| RolePlay SFT Skill | `r58/roleplay-sft-skill-v01@70e0d7da:skills/storyforge-roleplay-sft/SKILL.md`，Draft PR #7；R60 冻结归档有后续版本 | 现有规范作为只读权威参考；本批不复制冗长 Skill、不新增第二套政策 |
| SFT 候选编译器 | `gold-quality/quality-v1-sft-candidates@adc3876d:experiments/r58_quality/quality_v1_sft_candidates.py`，Draft PR #11 | 尚无正式新数据可编译；**不提前移植** |
| R60 HF Runtime、Generation Eval | `archive/r60-final-20261122@15462b8779401833a5014846bc57318dd6bc1b1c` | 本批不动，不重建推理/GPU/Job 运行时 |
| R59 历史上下文、Pilot8、R50 | 旧 Draft PR #9/#10/#13 及受保护元数据 | 保留历史引用，非本轮依赖；不展开审计或访问 R50 正文 |

不能以“需要清理历史分支”为理由把 Draft PR 整体合并，也不做架构重构、自动准入、恢复历史生产请求精确回放或复制共享算法。

## 三、当次授权的最小实施片段（Phase 1）

**只做一次 Quality-v1 判定内核的择优复用**，在 `main` 的独立实施分支创建：

1. `src/storyforge_gold_quality/__init__.py`：复用历史包声明，供现有 setuptools 自动发现；
2. `src/storyforge_gold_quality/quality_v1.py`：从上述固定来源移植现有判定逻辑，**不改变六维阈值、候选性质、保护集规则、世界隔离、原始来源限定和隐私失败行为**；
3. `tests/test_quality_v1.py`：从同一来源迁移原有纯合成回归，唯一允许的机械改动是把 import 指向共享包。

不新增第二个审阅 Rubric、质量策略、评审模型调用、真实候选输出或训练数据。现有 `pyproject.toml` 的 setuptools 包发现、pytest 测试发现和既有 CI 已可满足此片段；**先不改 CI、依赖或工作流**。既有 `quality_v1.py` 的 `PASS` 只表示声明与结构自洽、可作为候选；`quality_dataset_admitted=0`、`training_authorized=false` 保持不可改变。

**Phase 1 验收：** Git diff 仅上述 3 个新增文件；原始质量内核与历史文件逐字一致；合成测试等价（仅 import 路径变化）；自动测试与 Ruff 检查有真实结果；无私有数据、环境密钥、生成、GPU、HF Job、训练、生产变更。若 CI 既有基线失败，记录确切失败与本次变化的关系，**不顺手改全仓代码**。首次实施阶段默认只开 PR 审查，不在验证前合并。

## 四、后续条件，而非自动派生任务

Phase 1 稳定并且新的数据/评估合同明确需要时，才决定是否从旧 PR #8/#11 选取 Manifest/CLI、候选编译器或 SFT Skill 中的*某个*必需接口；需重新审查依赖、历史行为与测试，单独形成最小 PR，不做“一次性全部迁移”。如果没有具体可调用场景，Phase 1 后停止工程整理。

后续真正的模型质量工作顺序：取得新合法来源及授权 → 构造可复现训练上下文、世界组件隔离与保护集元数据排除 → 与已暴露 Gold48 区分的新独立评估 → 冻结预算可行性、指标、争议及停机口径 → 另行授权模型调用/训练 → 按独立质量结果决定是否晋升。任何阶段不得以已有 R60/R59 历史评价作新 Held-out。

## 五、交付、停机与权限边界

- 交付 1：本任务书入 `main`，作为执行上限而非新训练授权。
- 交付 2：**一份**最小 Quality-v1 内核移植 PR，包含代码来源、diff 范围和实际合成测试/CI 状态；若任一验收不满足，保留 PR 为 Draft/HOLD，不合并。
- 不继续启动第二个移植 PR，除非 Phase 1 有明确的必要缺口。避免新任务轮次、重复测试、重复解释或文件数量膨胀。
- 坚守 `NO_PROMOTE`、`quality_v1_admitted=0`、`training_authorized=false`、`model_promoted=false`、`R61_NOT_STARTED`。不接触 R50 密封正文，不提交私有故事、个案身份、逐条 SHA/评分或 Owner crosswalk。
- 此任务书**不构成** Owner 对十案独立人工复核签收，也不构成数据准入、模型推理、训练、发布或生产部署许可。
