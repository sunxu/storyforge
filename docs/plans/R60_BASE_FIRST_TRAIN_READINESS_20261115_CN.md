# R60 Base First-Train Readiness：最短有效准入路径（2026-11-15）

> **执行优先级高于旧R60任务书尾部逐步取证命令。** 本文件收敛执行目标，不修改原冻结证据，不赋予训练或GPU授权。工作分支 `r60/common2-cpu2-owner`，只改各自负责的源文件；不与并行Agent抢同一文件。完整来源合同：`docs/plans/R60_BASE_START_MINIMAL_GATES_20261115_CN.md`。

## 主目标及暂停指令

唯一下一目标：**找到可被证明合法、质量可信、与评测隔离的首批新Base SFT候选，冻结训练输入与Train/Val组件划分，完成CPU技术门禁；必要准入与Owner GPU授权之后才训练。** 不要求一次性用满336条。禁止将探索性技术验证伪称正式Train/Val准入。

立即暂停 `r60_base336_group_cards_opening_cpu.py --execute` 及其全量8组卡片/Opening取证、额外JSON形状统计、再次HF CPU336、再生成旧roster/template、重复世界定义盲审。其 `BASE336_CARD_OPENING_EVIDENCE_HOLD` 只代表工具运行失败，未知根因；**不能推断数据污染、数据库RLS故障或已输出8份证据**。无需修复它才能开始三项工作。若定向审核发现材料必需且无其他证据，则只对相关组/成员做最小范围只读补证；保留所有旧私有文件。

## 冻结的实证基线（不是新认证）

| 事实 | 当前证据 | 对首轮实验的意义 |
|---|---|---|
| 冻结来源 | V123 339双PASS、已知R50重复3条排除、336条/172 Story待准入 | 不重选、不覆盖、不默认为Train |
| Qwen Base技术 | `Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`；HF CPU336真实Tokenizer/Collator/last-assistant label mask通过且Owner回执已接受 | **不重跑**；仅新最终合同需要CPU抽样和后续全量校验 |
| R50 | 原始50的story/session/message精确来源键与保留336不交叉，三条被known5隔离 | 关闭精确ID子门禁；跨UUID世界/未覆盖保护集仍不能推断通过 |
| Reviewer | 336 A/B来源收据及配置可追溯，模型ID不同 | Provider真实调用独立、盲审互不串评仍HOLD |
| 跨故事World | 当前7组、含归档8组精确JSON相同跨旧Train/Val；影响38 Story/82候选 | 旧276/60预演不能直接使用；不等于82条真实泄漏 |
| Codex世界盲审 | 8组：通用模板7、证据不足1、具体共享0、隔离PASS 0/HOLD 8 | 聚焦1个不足组，7组按可证实风险处理，禁止自动PASS |
| 最近全量卡片工具 | NO_DB预检成功，`--execute`泛化HOLD | 暂停，不作为训练准入门禁 |

## 三条并行工作线（各自明确交付/验收）

### A. World/R50隔离：最小来源组件方案

**交付**：Mac私有 `R60_BASE_FIRST_TRAIN_WORLD_COMPONENTS_PRIVATE.json` 和公开SAFE聚合（组数、Story数、排除/待核查数、交叉组件数，**无原始ID/内容**）。

1. 只读现存8组roster、来源world证据及Codex私有语义审核文件，核对SHA/0600/组序号。**优先唯一的INSUFFICIENT_EVIDENCE组**，按需要查询该组最少成员的角色卡、Opening及历史来源；其他7组只针对Codex报告中的**具体风险疑点**定向补证。若无疑点仍要记录“仅World层模板、角色/剧情未审”而非PASS。
2. 同步对照真正作为本轮保护集的R50与其他独立测试集。已核实的R50原始50精确ID隔离保持PASS；未提供可靠保护范围的，阻止对应候选进入正式Train/Val，**不无限追求所有历史文件**。
3. 用**已证实**的共享角色、特定世界事实或剧情关系建立跨Story无向边及连通组件；引用精确来源字段/版本和引文（私有），语义证据不足的边/组记录HOLD而非猜测删除或合并。单纯完整world JSON相同且属通用模板**不自动合并**。
4. 基于组件而非原旧hash故事分配冻结新的Train/Validation：同一Story/已证实共享组件不得跨组；未决关联优先整个组件隔离到待决，不进入正式数据。已有准确排除的故事永久排除。输出真实可选样本规模，允许少于336；不可在新数据规模未确认时沿用276/60标签。
5. **验收**：候选组件来源有精确证据，保护集交集为0、无已证实组件跨Train/Validation、未决故事未放行；若不满足则仍HOLD，明确缺什么证据才能推进。

### B. Reviewer独立性：核实证据，不重复336×2请求

**交付**：只读审计 `R60_BASE_FIRST_TRAIN_REVIEWER_INDEPENDENCE_PRIVATE.json` + SAFE `PASS/HOLD` 和有证据的336条中可准入数量；不读取对方先前的质量评分来指导复评。

1. 复用 `r60_base336_reviewer_provenance_cpu.py` 已验收的两路336个PASS收据、冻结模型ID与收据SHA；不重新评分全部336。
2. 检查现存原始执行日志/阶段回执能否证明两个Reviewer实际分别调用、独立上下文、无跨路文本/评分串评，确认调用来源与模型别名确实分路。**配置字段和Owner声明不是执行独立性证据**。
3. 把“证据充分可核准”的样本与“缺少执行证据的HOLD”分开，若只有部分受影响，优先补特定缺口而不是重跑全部双审。没有可信证据时不可将该门禁默认PASS。
4. **验收**：逐候选绑定已执行且相互独立的两份Review证据；必须依照冻结六维下限、严重标记和原资格，不可降低标准。未知维持HOLD、模型调用需单独授权。

### C. 新Base构造型System/SFT合同：直接冻结，不等历史原始System

**交付**：版本化 `R60_BASE_CONSTRUCTED_SYSTEM_SFT_CONTRACT_V1_CN.md`、合成测试、在**不准入训练的CPU沙盒**对少量代表样本进行真实Tokenizer/Collator/监督Mask检验；待A/B收敛后复验最终合格子集。

1. 选择统一输入结构：独立显式标记 `TRAINING_CONSTRUCTED_NOT_HISTORICAL`，包含**版本绑定且经证实的**世界规则/角色、仅目标前的真实历史User/Assistant轮次、最后唯一待监督Assistant；不需要R46/R54旧LoRA、原online Provider HTTP字节或历史实际System完全恢复。
2. System字段分为`GENERIC_INVARIANT`（固定模板、不得凭空加故事事实）、`SOURCE_BOUND_WORLD`（仅经证明的本Story世界/角色原文）、`PROVENANCE_LABEL`（明确不是历史System）。缺少源绑定世界/角色时不得虚构；可选择**无卡的明确受限技术合同**用于内部对比，但不得将无卡结果宣称与产品有卡输入等效。
3. 严守冻结目标作为唯一最后Assistant label；没有目标之后的内容、没有未来世界修订的误用、没有玩家行为代写；Token长度预算按固定Base revision执行，并完整复用已通过的ms-swift真实collator、R18严格label mask。
4. CPU先用合成和数个有合法源绑定的代表样本检查，最后才对**A/B已准入子集**进行冻结全量CPU复验。已有无System的336/336技术PASS保留为历史对照，不用重跑那一套合同。
5. **验收**：模板固定、source trace与目标监督核验、真实Tokenizer+Collator+mask PASS，训练前模型revision/数据SHA/Train Val隔离可复现。

## 单一就绪判定：禁止“技术PASS即Train PASS”

下列门禁均须 **PASS且具有可核验来源** 才可提交首批训练候选：`source_quality`、`reviewer_execution_independence`、`evaluation_protection`、`world_component_disjointness`、`constructed_sft_contract`、`actual_collator_on_final_contract`。上述任意为UNKNOWN/HOLD/FAIL => `BASE_FIRST_TRAIN_READINESS_HOLD`、`train_admitted=0`、`gpu_started=false`。

即便六项全部PASS，也只代表`BASE_FIRST_TRAIN_READY_FOR_OWNER_APPROVAL`；必须**另行取得Owner明确授权**，独立创建新RUN_KEY方可启动GPU/HF训练。训练阶段产物默认私有；不将R50密封集当开发数据反复调参。

## 任务调度：并行但避免冲突

- A只操作World/R50组件隔离方案与Mac私有审阅结果；B只操作Reviewer执行独立性方案/报告；C只操作最终SFT合同和CPU测试。各Agent在自己的工作分支/工作树提交，禁止同时修改本文件。
- Coordinator负责合并经CI验证的产物，汇总一张SAFE就绪表；每轮只问“哪个门禁离PASS更近？”，不按工具数或新增证据数统计进度。
- 任何新脚本必须声明：直接关闭哪项门禁、复用什么旧代码、实际输入/输出、失败时采取的**一次定向恢复**、能否在无需付费/私有数据出境的情况下执行。不能关闭门禁的泛化诊断脚本暂缓。
- **当前**：A/B/C均未按本计划重新核验，仍为HOLD。R50原始50精确ID、336真实CPU技术检查作为“通过的子证据”保留，不允许用它们自动提升整项门禁。


## 2026-11-15 工程推进：C线实际Tokenizer/Collator合成Smoke入口已交付

新增`experiments/r58_quality/r60_base_constructed_sft_cpu_smoke.py`及`test_r60_base_constructed_sft_cpu_smoke.py`，沿用已通过HF CPU336的`r60_common2_sft_cpu_template_audit.inspect_rows`、`bind_text_only_rope`和R18严格最后Assistant-only标签；不复刻第二套ms-swift实现。3条**完全合成**输入覆盖纯通用System、通用System+World、通用System+World+角色卡（合成story ID和revision，不能作为真实来源认证）。固定`Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`本地快照，只准读取tokenizer/config文件；`--stage both`调用实际ms-swift`qwen3_8`模板/`last_round`、严格R18 mask及实际DataCollator；完全CPU、断网、无模型权重/DB/私有样本/训练准入。只输出SAFE；错误时仅给固定阶段HOLD。GitHub Actions [#43680126553](https://github.com/sunxu/storyforge/actions/runs/43680126553) Ruff及228项合成测试PASS。

**注意** CI仅验证代码/合成单元测试，**没有在真实固定快照执行ms-swift**，不称`ACTUAL_COLLATOR...PASS`。先使用已有的本地固定snapshot（若无则等待已有合规HF CPU环境；绝不为本Smoke下载27B权重或直接提交付费Job）：
```bash
set -euo pipefail
set +x
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
# 必须替换为已有的、固定revision且有config.json/tokenizer.json/tokenizer_config.json的快照
SNAPSHOT="/实际已存在的固定revision本地snapshot"
"$PY" experiments/r58_quality/r60_base_constructed_sft_cpu_smoke.py \
  --snapshot "$SNAPSHOT" --stage both
```
若snapshot缺失，不要用示例路径，也不应启动HF Job；记录`C_SNAPSHOT_UNAVAILABLE_HOLD`。本次只验证**合成V1合同兼容性**，不证明336真实训练数据可用、来源时序可信、A/B PASS或产品有卡等效。A/B继续并行，只能在来源隔离等必要门禁通过后才允许正式候选训练。


## 2026-11-15：C线正式切换到HF CPU3合成合同验证（不再修Mac config）

历史HF CPU336已成功的私有Bucket远端原代码可只读确认，`scripts/r60_base_cpu336_hf_worker.py`的`snapshot_download`按固定revision仅获取`config.json/tokenizer.json/tokenizer_config.json`等允许的小文件，已有实际ms-swift`qwen3_8/last_round`和R18审计336/336通过。Mac本地`~/.local/share/storyforge/qwen-tokenizer/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`缺`config.json`，标准HF缓存也不存在，**不再在Mac补这个文件作为C线阻塞**。

新实现（独立于旧336）：`scripts/r60_base_constructed_hf_cpu_stage.py`、`r60_base_constructed_hf_cpu_worker.py`、`r60_base_constructed_hf_cpu_worker.sh`、`r60_base_constructed_hf_cpu_cli.py`。采用已有`r60_common2_wrapped_hf_stage.local_dependencies`SHA闭包、`r60_common2_wrapped_hf_cli`的远端文件集检查/单次提交marker/分页历史/CLI Dry Run安全合同，**不重复实现HF调度器**。Stage仅包含合成Generator、V1 System合同和相关代码/依赖，没有任何Story内容、R50或训练数据；Worker在HF `cpu-upgrade`下载固定revision仅Tokenizer/Config/Processor，复用`r60_base_constructed_sft_cpu_smoke.run`、`r60_common2_sft_cpu_template_audit.inspect_rows`与R18严格最后Assistant标签检查。三条合成：无卡/World/World+角色，全部Train 0，模型权重/推理/GPU为0。只输出独立SAFE回执至`preflight/r60/base-start/constructed-system-cpu3/results/<RUN_KEY>/`，不可覆盖旧336产物。CI [#43682266393](https://github.com/sunxu/storyforge/actions/runs/43682266393) **Ruff+236合成测试PASS**，包括实际Stage依赖闭包和远端mount名适配；**当前不代表HF真实Job已运行**。

### Owner Mac：只生成/验收合成Stage，再上传并Dry Run

```bash
set -euo pipefail
set +x
umask 077
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
BASE="$HOME/.local/share/storyforge/r60/private"
STAGE_PARENT="$BASE/r60-base-constructed-cpu3-stages"
mkdir -p "$STAGE_PARENT"
chmod 700 "$STAGE_PARENT"
RUN_KEY="r60-constructcpu-$(date -u +%Y%m%dT%H%M%SZ)-$("$PY" -c 'import secrets; print(secrets.token_hex(6))')"
STAGE="$STAGE_PARENT/$RUN_KEY"

"$PY" scripts/r60_base_constructed_hf_cpu_stage.py prepare \
  --stage "$STAGE" --run-key "$RUN_KEY"
"$PY" scripts/r60_base_constructed_hf_cpu_stage.py verify \
  --stage "$STAGE" --run-key "$RUN_KEY"
"$PY" scripts/r60_base_constructed_hf_cpu_cli.py cli-flags \
  --stage "$STAGE" --run-key "$RUN_KEY"
"$PY" scripts/r60_base_constructed_hf_cpu_cli.py preflight \
  --stage "$STAGE" --run-key "$RUN_KEY"

# 此命令仅上传完全合成的代码Stage，不包含私有真实Story文本：
"$PY" scripts/r60_base_constructed_hf_cpu_cli.py sync \
  --stage "$STAGE" --run-key "$RUN_KEY"
"$PY" scripts/r60_base_constructed_hf_cpu_cli.py ready \
  --stage "$STAGE" --run-key "$RUN_KEY"

printf 'RUN_KEY=%s\nSTAGE=%s\n' "$RUN_KEY" "$STAGE"
```

如果返回`WRAPPED_CPU_REMOTE_AND_CLI_READY__NO_JOB`且整个链无HOLD，才进入一次CPU提交；`ready`不是实际运行成功。CPU会产生费用，但没有27B权重或GPU。Owner执行单次提交命令：
```bash
"$PY" scripts/r60_base_constructed_hf_cpu_cli.py submit \
  --stage "$STAGE" --run-key "$RUN_KEY" --execute
```

必须获得`WRAPPED_CPU_JOB_SUBMITTED__TRAIN_HOLD`及可追踪Job ID才能认定提交；如果超时或不确认，绝对不盲重试，运行`diagnose`并查HF组织作业历史。Job成功后仅从`hf://buckets/adradar/storyforge-training/preflight/r60/base-start/constructed-system-cpu3/results/$RUN_KEY/R60_BASE_CONSTRUCTED_HF_CPU_SAFE_RECEIPT.json`只读查SAFE；预期`BASE_CONSTRUCTED_HF_CPU3_ACTUAL_COLLATOR_PASS__TRAIN_HOLD`。**这仍只证明3条合成合同的真实Collator兼容，A/B/真实最终来源未PASS，336候选保持Train 0。**

## 2026-11-15 HF CPU3 实际验收：C线合成Collator技术子门禁 PASS

Owner回传真实HF CPU3 SAFE，随后独立从私有Bucket固定路径只读`cat`核对完整文件，JSON逐字段一致：

- `run_key=r60-constructcpu-20261115T061708Z-75c7f143b67d`；`schema=storyforge_r60_base_constructed_hf_cpu_safe_v1`。
- `status=BASE_CONSTRUCTED_HF_CPU3_ACTUAL_COLLATOR_PASS__TRAIN_HOLD`；`phase=AUDIT_COMPLETE`；`synthetic_cases=3`。
- `Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`；`input_contract=R60_BASE_CONSTRUCTED_SYSTEM_V1`；`provenance=TRAINING_CONSTRUCTED_NOT_HISTORICAL`。
- `tokenizer_verified=true`、`actual_collator_verified=true`、`last_assistant_only_mask_verified=true`。
- `generic_system_sha256=a3e8fad23151b7cfbbe29d5a876d6d50c1d0225d6482173b307621db523d5a25`、`source_sha256=0c98a68091d91b203563ea1cc0bae5f1b75cc3ba129820b333fff24ea382a1c9`。
- `gpu_started=false`、`model_weights_loaded=false`、`model_requests=0`、`database_accessed=false`、`train_admitted=0`、`private_values_emitted=false`。
- **未验证** `real_candidate_contract_verified`、`real_source_content_verified`、`reviewer_independence_verified`、`world_component_isolation_verified`、`r50_complete_exclusion_verified`。

权威SAFE回执：
`hf://buckets/adradar/storyforge-training/preflight/r60/base-start/constructed-system-cpu3/results/r60-constructcpu-20261115T061708Z-75c7f143b67d/R60_BASE_CONSTRUCTED_HF_CPU_SAFE_RECEIPT.json`。

**决定：冻结C线3条合成System+实际ms-swift/R18技术子门禁为PASS，不重复HF CPU3，不要求本地Mac补27B config。该成功不等于“最终真实候选SFT合同全量PASS”；C线剩余工作仅限于A/B准入后实际候选来源绑定、目标Mask与最终Train/Val冻结验证。下一主线切换到A（World/R50组件隔离）和B（Reviewer真实执行独立性）的证据收敛。** 原336候选依旧全部HOLD，GPU未获授权，Train 0。

