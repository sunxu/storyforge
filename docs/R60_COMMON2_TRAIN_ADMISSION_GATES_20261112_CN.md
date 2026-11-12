# StoryForge R60 Common2：CPU PASS 之后训练准入证据与下一步任务书（2026-11-12）

> 适用：`r60/common2-cpu2-owner` 独立Owner分支。**不授权训练、GPU、HF Job、数据库访问或模型推理**。本文件优先于旧文档中的「Collator未完成」表述；旧记录保留不删。

## 已冻结的事实

- HF CPU Job `6af570089737d9a9e093d501` 已COMPLETED，RUN_KEY `r60-common2-cpu2-20261112T073854Z-e076f53c8eae`，正式Worker尾回执`R60_CPU2_V2_REAL_COLLATOR_PASS__R50_TRAIN_HOLD`。
- Owner 二次只读验签 `CPU2_SAFE_RECEIPT_VERIFIED__R50_TRAIN_HOLD`，两条真实实验源绑定样本 Tokenizer tokens `[2552,4048]`；真实 ms-swift Collator tokens `[2486,3982]`；监督labels `[282,305]`。两例Token长度分别差66（原生比Swift多66）。
- 验收范围仅 `SOURCE_BOUND_DERIVED_CONTEXT_NOT_ACTUAL_SENT` 最近11条来源历史+冻结最终助手消息，没有证据可证当时真实LLM请求、System、世界卡或动态记忆完整一致。
- `native_template_token_parity_verified=false`、`r50_complete_exclusion_verified=false`、`train_admitted=0`、`gpu_started=false`。
- ms-swift模板固定`qwen3_8` / `loss_scale=last_round` / `max_length=16384` / `add_non_thinking_prefix=False`；原生HF tokenizer来自`Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`。两者对自动插入的system/reasoning及消息分隔存在**未完成等价证明**。不能只用token数量相等推断字节/语义等价，也不能从相差66推断一定来自同一固定前缀。

## Gate T：模板差异与明确的训练输入政策（当前HOLD）

1. 固定真实已用模型版本和相同11历史消息+目标，不改写历史文本、不插入假的System、不得去掉不利样本。仅可在本机私有环境、或者不含私有输入的公开合成文本做比较。
2. 使用同一已pin的Tokenizer，比较（a）正式CPU审计所用`apply_chat_template(messages,tokenize=True,add_generation_prompt=False)`，和（b）正式CPU审计的`ms-swift get_template(template_type=qwen3_8,...).encode`；记录纯计数、共同前缀长度、首个差异属于`SYSTEM_REASONING`、`ASSISTANT_HEADER`、`MESSAGE_BOUNDARY`、`SPECIAL_TOKEN`或`UNKNOWN`，不得公开任何token ID、解码片段或正文。
3. 用相同参数再作原生`reasoning_effort=medium`、`enable_thinking=false`对照；**这些都是实验对照，不是历史请求原本的配置**。公开合成测试已观察：xhigh默认会添加英文reasoning system指令，medium也不与Swift完全相等，不能把两个API默认混用。
4. 只有在Owner明确决定**训练始终以哪一种模板为规范**、阐明与推理部署模板的关系、监督label与prefix校验一致，并留下有版本的审核报告后，才能把Gate T标为`POLICY_FIXED`。**没有必要强求所有不同模板token完全相等**，但不能宣称已验证等价；如训练/部署必须等价而没有证据，则继续HOLD。
5. 不触发模型权重加载或HF Job：先用现有CPU SAFE结论与公开Jinja模板源码做静态差异解释。需要进一步真实token位置验证时，在Owner私有机器提供可运行的严格SAFE校验程序并单独评估本机依赖；目前不执行。

## Gate R：完整R50冻结来源隔离（当前HOLD）

1. 仅从**原已冻结**的R50 provenance/heldout与此前R45 split索引中恢复可信任的完整集合。旧R50材料包括`R50_FRESH_HELDOUT_50.jsonl`、`R50_CASE_PROVENANCE_50.jsonl`与最终46条排除/heldout相关报告，但其真实格式、真实本地路径、最后冻结版本及SHA**本轮尚未由Owner提供/读到**。不能只据名称或「已知五个故事」伪造完整性。
2. 冻结R50要求：明确最终46/50案例关系、被排除4例的原因和保护范围；将每个受保护案例的真实`story_id`、`session/transcript_id`、`message_id/target_id`和必要的alias/世界归属解析为**完整唯一键集合**。如果来源Schema缺少任一关联字段，标`MISSING_PROVENANCE_HOLD`，不能根据文本相似猜测ID。
3. Common2两条候选不只是最后target，必须将其对应story、session及实际使用的11条历史+目标的源键加入被检查的候选集合。R50必须至少做三层集合交集：**故事级（最严格）、session级和消息/目标级**；R45训练/评测世界互斥规则也要核对。三层必须零交集且完整来源、冻结摘要可信才可以`R50_COMPLETE_EXCLUSION_VERIFIED`；否则输出仅HOLD的**SAFE聚合计数**，不打印任何私有ID/hash/原文。
4. 不重生成R50、不调用另一模型改判、不读取正文做人工猜测。必须严格区分「没有找到冲突」与「能够证明全量覆盖」。使用只读策略核实记录数、唯一性、冻结版本、provenance映射完整与R45分拆关联，再审校结论。
5. 当前仓库中未见获准可直接读取的R50最终完整元数据及实物，因此**本轮不能执行真实R50完整隔离并声称通过**。

## Gate A：最终Owner训练准入（当前HOLD）

| 项目 | 当前证据 | 状态 |
|---|---|---|
| Common2独立六维双PASS | 冻结独立裁决2/2 | 候选质量检查PASS，正式训练准入尚未签署 |
| 源绑定/上下文可用性 | 103/243条持久化历史，选11条构建输入 | 实验可用，真实当时请求未证 |
| Tokenizer/严格R18/Swift Collator | 第五轮Job+SAFE二次验签2/2，max16384 | CPU工程PASS |
| 原生 vs Swift模板 | 计数差各66，当前未全量等价 | Gate T HOLD |
| R50保护集与世界级分拆 | 完整冻结元数据未核实、未全量排除 | Gate R HOLD |
| 当前训练准入 | `train_admitted=0` | HOLD |
| GPU/SFT启动 | 本任务未授权 | 禁止 |

后续Owner决策可以有两条路径：(A) 保留原生/Swift不等价但**明确统一训练与部署的模板规范**，用独立标签、特殊token及上下文门禁核验安全；(B) 必须要求原生/Swift逐token相等才开放，若不相等则持HOLD。这属于**训练政策决策**，不得在工程脚本中暗自选择。无论A或B，完整R50排除及Owner签准仍是硬门槛。

## 执行优先级

1. 已完成的HF CPU Tokenizer/Collator不再重跑；证据永久关联上述Job ID、SAFE及HF运维手册。
2. **静态只读模板差异报告**：固定文件、Jinja条件和ms-swift模板选择，实现独立报告；不上传任何私有内容。下一步如需实测特殊token差异只用本机已有快照。
3. **R50证据目录清单定位**：Owner在私有目录核对最终冻结的case/provenance/heldout/R45 split材料及各自Schema，先只记录SAFE文件个数、类型、可解析性，不能把未知文件替代为最终冻结文件。
4. 待两个门禁都能形成证据后，生成可审计的Owner训练准入提案，仍保持`train_admitted=0`，由Owner独立授权训练及GPU。

维护独立Owner分支；其他Agent并行进行Wave40/GLM/Qwen评测时，不修改它们的脚本、冻结R50数据或相应文档主权区。


## R50 Owner本地只读第一步（本轮已实现、尚未真实执行）

新增`scripts/r60_r50_frozen_metadata_inventory.py`只对**Owner明确指定的3个现有冻结文件**做结构/权限/JSON解码检查，不访问数据库、HF、模型、不修改文件。对公开聚合输出严格不含路径/字段名/ID/哈希/原文。即使全部可解析，也**仅返回`R50_METADATA_FILES_PARSEABLE__COVERAGE_HOLD`**，不声称全量排除。必须在拿到元数据Schema和真实记录覆盖证明后再实现下一阶段交集核对，不要猜映射规则。

先在Owner私有环境自己找到文件（文件路径不要贴到公开Issue），以下命令要求手动填入3个已确认文件，`--exclusion`应是**最终冻结的受保护排除/heldout关联文件**而非临时脚本输出：

```bash
set -euo pipefail
cd ~/workspace/storyforge-r60-4router-review
PY="$HOME/.local/share/storyforge/venvs/r60-tests/bin/python"
"$PY" -m pytest -q tests/test_r60_r50_frozen_metadata_inventory.py

# 只填已经由Owner确认的真实冻结文件路径；不要凭名称伪造
CASES="/Owner私有/R50_FRESH_HELDOUT_50.jsonl"
PROV="/Owner私有/R50_CASE_PROVENANCE_50.jsonl"
EXCLUSION="/Owner私有/R50最终冻结排除或heldout关联文件.json"

"$PY" scripts/r60_r50_frozen_metadata_inventory.py \
  --cases "$CASES" --provenance "$PROV" --exclusion "$EXCLUSION"
```

若文件不存在、名字只是历史示例、权限非0600或出现HOLD，停止并仅修正**文件定位/只读权限前提**，不修改冻结内容、不开训练、不要通过降低计数或更换其他文件绕过。预期只返回各文件记录数和`r50_complete_exclusion_verified=false`。后续完整排除必须使用确定的Schema、最终冻结版本、全量故事/会话/消息来源映射和R45 split索引，不由这个inventory工具完成。

## 2026-11-12 Owner R50真实冻结派生文件结构检查（已运行，仍HOLD）

Owner Mac SAFE结果：`R50_METADATA_FILES_PARSEABLE__COVERAGE_HOLD`；`all_files_checked=3`、`cases_file_rows=46`、`provenance_file_rows=46`、`exclusion_file_entries=21`；数据库/GPU/HF Job 0，`r50_complete_exclusion_verified=false`，`train_admitted=0`。所用输入：R50 `run.dWgMu5/private/derived` 中46条 `PRESEAL` 候选及46条 `PRESEAL` 来源映射，以及 `R50_46_R45_ORIGINAL_EXACT_SUBSET_SCREEN.json`。**21是该JSON根对象的键数，不是排除的21条样本。** 两个46的数量相等尚未证明逐行映射正确。该第三文件是R45精确子集屏查而非最终R50保护集。不能提升为R50完整排除。

已找到的其他后续只读辅助证据：`r50/full-original-worlds/run.cGUPnjdx/R50_FULL_ORIGINAL_WORLD_INVENTORY_PRIVATE.json`、`r50/r45-full-source-gate/R50_R45_FULL_SOURCE_GATE_20261022_220215.json`、`r50/run.dWgMu5/private/R50_46_ADMISSION_STATUS_20261016.json`和`run.dWgMu5/private/derived/R50_46_PRESEAL_SELECTION_MANIFEST_PRIVATE.json`。真实原始50案及最终保护集版本仍未证实。下一步**必须先安全查看Schema/结构而非私有字段值**，核对46/50、4条排除去向、每条的story/session/message来源绑定及R45世界级排除。禁止为了通过门禁把PRESEAL/21字段报告冒充完整排除资料。
