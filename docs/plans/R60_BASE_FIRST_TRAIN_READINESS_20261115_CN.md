# R60 Base First-Train Readiness：最短有效准入路径（2026-11-15）

> **当前Owner最新执行主线（2026-11-16）：** 另立的336候选**探索性**Base QLoRA，不修改本文件冻结的正式准入门禁。Owner Mac已完成293/43真实发布包独立SHA/格式验收，并取得`BASE336_EXPLORATORY_FINAL_COLLATOR_PROOF_TRANSFER_PASS__GPU_HOLD`：原HF CPU336 SAFE回执接受，旧336与新293+43原始行SHA多重集合完全相同，`actual_final_collator_verified=true`、`collator_executed_in_this_run=false`。**P0已关闭，不要重复跑CPU Job、重建数据或重跑转移命令。** 下一步按 [新Agent交接](R60_BASE336_CPU_PROOF_TRANSFER_NEW_AGENT_HANDOFF_20261116_CN.md) 和 [Base336实验合同](R60_BASE336_FAST_GPU_EXPLORATORY_20261116_CN.md) 实现独立R60 GPU Stage/Worker/CLI，并维护Quality Pipeline/Skill边界。GPU Stage未准备、GPU Job 0、`train_admitted=0`。本文件正式训练六门禁仍独立有效，不能被探索性Collator PASS替代；同时，正式训练六门禁及Gold72/P2B讨论也**不得未经重新评估就被改写成探索性实验的质量PASS或隐性前置授权**。Reviewer独立性、R50语义隔离和完整World语义隔离仍HOLD。


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



## 2026-11-15：A/B首训风险快速收敛（不再重复质量审核）

新增`experiments/r58_quality/r60_base_first_train_ab_scope_cpu.py`与合成测试。它**离线重放**原始V1/V2/V3 Crosswalk及冻结R50 Known5 quarantine的完整验证，不重新打模型分；只读8组来源roster、重算336 Reviewer双侧来源PASS绑定，不请求DB、不访问HF/GPU。对336条精确划分：**82条命中8组已知跨Story World JSON重复风险，254条未命中这8组**（仅表示未命中这些精确组，不表示语义隔离/评测保护已PASS）；分别生成两个私有0600 create-only报告，用于A优先定向补证、B定位执行证明缺口。Review实际Provider独立性、R50完整保护、World组件隔离仍HOLD，训练准入0。CI [#43686589680](https://github.com/sunxu/storyforge/actions/runs/43686589680) Ruff+241合成测试PASS（不代表Mac私有真实审计已执行）。

Mac Owner执行（只读原来源，输出新文件；首次执行使用相同目录和参数，`--execute`仅在预检PASS后运行一次）：

```bash
set -euo pipefail
set +x
umask 077
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner

PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
BASE="$HOME/.local/share/storyforge/r60/private"
ARGS=(
 --old-dir "$BASE/r60-quality-fast1000-api-v1"
 --plan-dir "$BASE/r60-real1000-v1-repair-plan-20261114"
 --v2-dir "$BASE/r60-real1000-v2-priority-replay-v1"
 --v3-dir "$BASE/r60-real1000-v3-consistent-replay-v1"
 --audit-dir "$BASE/r60-real1000-v123-crosswalk-v1"
 --quarantine-dir "$BASE/r60-real1000-r50-known5-quarantine-v1"
 --roster-dir "$BASE/r60-base336-world-cross-review-20261115"
 --output-dir "$BASE/r60-base-first-train-ab-scope-20261115"
)

"$PY" experiments/r58_quality/r60_base_first_train_ab_scope_cpu.py "${ARGS[@]}"
"$PY" experiments/r58_quality/r60_base_first_train_ab_scope_cpu.py "${ARGS[@]}" --execute
```

预期`BASE_FIRST_TRAIN_AB_SCOPE_BOUND__BOTH_HOLD`，明确是**成功分组但仍待准入**，不是失败。输出：

- `R60_BASE_FIRST_TRAIN_A_KNOWN_WORLD_RISK_PRIVATE.json`：82风险位置、254未命中位置、8组Codex原SAFE摘要（仅Owner回执，不冒充独立重新盲审）。下一步仅对那1组证据不足及7组明确疑点进行定向关联判断；不要把254自动当正式Train。
- `R60_BASE_FIRST_TRAIN_B_REVIEWER_EVIDENCE_PRIVATE.json`：336双侧来源统计与独立性证据缺口清单；现存原Runner代码确认V1对A/B各自构造相同原始Case prompt并调用不同配置模型，**只是代码路径证明，不能单凭此证明远端实际执行**。继续检查有无独立Provider服务日志/调用快照、V2/V3隔离证据；实在没有则按证据不足HOLD并提供最小补审选项，不自动全量重跑。

Coordinator下次应报告**未决世界Story/案例数、可核实的实际双路Provider执行证据条数**，而不是再创造无限诊断脚本；A/B都不能通过时明确阻塞点及可选首训规模，暂不启动GPU。


## 2026-11-15 A/B Owner实跑结果及下一实际裁决

Owner已执行 `r60_base_first_train_ab_scope_cpu.py` 的precheck和`--execute`，两次SAFE一致：冻结336条、8组已知World精确重复风险82条（38 Story）、其余254条未命中这8组，Reviewer原始双侧PASS来源绑定，私有新文件2份已创建，DB/HF/GPU/模型请求均为0。真实隔离与Provider独立性均未完成，因此`BASE_FIRST_TRAIN_AB_SCOPE_BOUND__BOTH_HOLD`是**成功分组仍HOLD**；并非重新准入。

下一步**不再跑同一分组脚本**、不重查336、也不重新提取8组完整Card/Opening。按[Mac私有A/B独立裁决交接](R60_BASE_FIRST_TRAIN_AB_PRIVATE_DECISION_HANDOFF_20261115_CN.md)分别完成 A 组来源语义判决、R50与组件隔离决策，和 B 组原Reviewer执行证据L1/L2/L3分级。仅输出不含Story ID/正文的SAFE，实际私有判决写0600 create-only。只有可确认的独立Provider执行证据才有资格将B提升PASS；代码路径及不同model ID只能支持L2。所有无法证明的内容继续HOLD，Train 0，GPU未启动。


## 2026-11-15：把不可补回的证明前置到新候选工作流（Forward Evidence Gate V1）

问题复盘：R60旧336条的质量回执缺乏逐侧Provider独立执行的可鉴别记录，旧日志无法凭后验字段重新生成。因此针对**今后新采样/补审**增加双阶段证明，而不是继续对旧336事后推断。新增纯离线`experiments/r58_quality/r60_forward_evidence_gate_v1.py`及合成单元测试；旧V1/V2/V3冻结Runner**不修改**。CI包含本模块的synthetic fail-closed检验。

**时间顺序与验收责任**：

1. **采样前**：冻结完整保护集manifest（R50完整50及本轮独立Eval集合、Story/Session/Message身份、跨UUID语义关联风险边）；未经保护范围审核不得开始候选抽样。由Owner/独立审核者批准`covers_all_protected_sets`，不能用known5的3条冒充全部保护集。
2. **采样时**：固定来源Snapshot SHA、历史截止时间、Story World/角色/Opening具体修订及无未来泄漏的证据。对所有训练/Validation/评测Story构建来源绑定的语义组件（不确定关联组件整组HOLD/隔离）；冻结全局组件manifest，而不是每条候选只看独立hash。
3. **模型调用前**：验证来源/保护集/世界组件凭证绑定与完整性，调用`require_pre_review(source, protection, world)`生成`PRE_REVIEW_SOURCE_AND_EVAL_FROZEN` seal；**未通过不得进入API队列**。当前模块仅是守卫函数，须由新Runner显式调用并以create-only 0600存储真实seal，尚未接入任何生产模型调度路径。
4. **每次Reviewer调用时**：由独立执行器记录实际HTTP/Provider来源的请求ID、UTC开始/结束、状态码、Provider/模型路由、prompt/input/response摘要、是否包含对方意见、隔离/随机分路和准确源绑定。执行记录只写私有0600，禁止输出Header、Bearer、原始小说正文或响应。**本地自编UUID或自填布尔值不构成认证来源证据**。不同Endpoint/Model只是路由区分，不能代替实际相互独立证明。
5. **发布候选前**：逐侧验证冻结准入标准与严重标记、外部日志可信性及请求/响应的真实绑定；调用`require_post_review(seal, executions)`。这个纯函数仅验证输入合同/部分自洽，布尔字段的真实性仍要求外部可信鉴别与独立审核。返回`FORWARD_EVIDENCE_BOUND__TRAIN_HOLD`，**仍不会自动Train PASS**，须有独立的来源验收和最终SFT CPU合同。
6. **训练前**：最终数据和Split组件全量复核；Owner授权后才可能启动GPU。旧336保持HOLD、不追认、不重跑HF336/CPU3。

重要：本次只交付**独立于冻结Runner的函数级前置门禁及合成测试**；未完成把真实保护集、语义判定、Provider可验证执行日志连接到新Runner的工作，不能声称生产接入/独立证据已经实现。下一步应先针对**新鲜且完全合成的双侧Review请求**打通可信执行证据链，再选择第一小批实际来源候选。所有写入create-only，发生任意HOLD立即中止而非重新评分；避免将证明再次拖到训练前。


## 2026-11-15：Reviewer V2 synthetic proof-order Ledger 已实现并通过CI

新入口：`experiments/r58_quality/r60_forward_reviewer_v2_ledger.py`，合成测试：`test_r60_forward_reviewer_v2_ledger.py`。CI [#43691626895](https://github.com/sunxu/storyforge/actions/runs/43691626895) Ruff PASS、261项测试PASS。复用既有`r60_reviewer_transport.build_body`、`r60_real_ai_dual_review.prompt_for_case/parse_model_response`、`r60_real_private_batch.private_dir/write_new`，而非复制评分逻辑。

- 实施`execute_synthetic(...,transport=stub)`：先`require_pre_review`，验证Case摘要绑定，使用0700 create-only目录和0600文件写入`PRE_REVIEW_SEAL_PRIVATE.json`；再为A/B分别**先写请求尝试记录**，再调用合成stub，写`OUTCOME_A/B_PRIVATE.json`。共5文件。任一请求失败后写HOLD而非自动重试/调用另一侧；重新执行拒绝覆盖已有目录。模拟输入始终只含原Case，无另一Review结论。
- 此阶段**不支持live HTTP调用**。模拟Provider请求ID只属于未经认证的`TRANSPORT_OBSERVATION_ONLY__NOT_AUTHENTICATED`。两侧合成成功只返回`SYNTHETIC_TWO_SIDE_LEDGER_COMPLETE__INDEPENDENCE_HOLD`，**绝不可填入后置Gate需要的`provider_evidence_authenticated=true`**；没有独立Provider服务器日志或可鉴别网关审计，就只能HOLD。
- CI覆盖缺保护集→零请求、封存先于请求、review内容不串入另一方、第一次失败→不请求B、不可重复执行、0600权限。当前未在Owner Mac创建任何V2私有审计文件或实际请求，也未为旧336条追认任何执行独立性。
- **下一个可交付的最小缺口**：为新Runner建立受信的Provider/4Router审计记录签名或只读查询（实际请求ID、响应ID、UTC时间、模型/路由、原始请求体哈希、响应哈希、可关联不可篡改的日志）。只有可核实来源的记录才交给`require_post_review`；本地代码自填时间戳、自造UUID或声明隔离均不够。上线前必须先用合成案例实测接入、复核匿名日志与真实请求绑定，明确单次真实API调用需要Owner授权和费用。


## 2026-11-15：复用Qwen3.7 Flash / DeepSeek Flash历史真实调用，不重复适配

已复核原有`experiments/r58_quality/r60_real1000_qwen_deepseek20_live.py`：模型ID为`qwen3.7-flash`、`deepseek-flash`；百炼`https://dashscope.aliyuncs.com/compatible-mode/v1`与官方`https://api.deepseek.com`，历史20条实审采用冻结六维JSON与DeepSeek`thinking=disabled`。旧QD20配置与历史私有回执不动；原模型请求实现`r60_real_ai_dual_review.model_request`、`r60_reviewer_transport.build_body`和单模型`r60_reviewer_protocol_probe.py`均直接复用。密钥**严格区分**：`DASHSCOPE_API_KEY`用于Qwen；`R60_DEEPSEEK_KEY`用于新DeepSeek探针（旧QD20脚本仍读`DEEPSEEK_API_KEY`）；`R60_CLAUDE_KEY`只用于Claude，不得重绑定。

新增仅**可选**的`model_request(..., evidence_sink=...)`（旧调用默认无变化）：请求/响应SHA、开始/结束UTC、HTTP成功状态、Provider响应JSON顶层id及响应Header的`x-request-id`，**在严格JSON校验之前**传给sink。因此无效JSON也能保留不含原始内容的观测信息，失败不改冻结门槛。此数据标记`provider_evidence_authenticated=false`，ID只是传输观测，不是第三方验签。

既有`r60_reviewer_protocol_probe.py`新增可选`--evidence-dir`：先创建Owner Mac的0700私有目录及0600尝试文件，再做一次**完全合成**真实API调用，最终保存0600`OUTCOME_PRIVATE.json`（即便JSON无效），不重复使用相同目录。仍不读取小说/R50、无GPU/Train。CI [#43693036620](https://github.com/sunxu/storyforge/actions/runs/43693036620)：Ruff PASS、266合成测试PASS。此前旧QD20历史调用不在本次重执行范围之内。

**Owner Mac两次单模型合成探针（每模型一次，不读取任何私有故事）**：

```bash
set -euo pipefail
set +x
umask 077
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
BASE="$HOME/.local/share/storyforge/r60/private"
test -n "${DASHSCOPE_API_KEY:-}"
test -n "${R60_DEEPSEEK_KEY:-}"
"$PY" experiments/r58_quality/r60_reviewer_protocol_probe.py \
  --endpoint https://dashscope.aliyuncs.com/compatible-mode/v1 \
  --model qwen3.7-flash --protocol openai-chat \
  --key-env DASHSCOPE_API_KEY --json-mode --allow-remote-review --execute \
  --evidence-dir "$BASE/r60-qwen37-v2probe-20261115"
"$PY" experiments/r58_quality/r60_reviewer_protocol_probe.py \
  --endpoint https://api.deepseek.com \
  --model deepseek-flash --protocol deepseek-chat \
  --key-env R60_DEEPSEEK_KEY --json-mode --allow-remote-review --execute \
  --evidence-dir "$BASE/r60-deepseek-flash-v2probe-20261115"
```

若任意一条HOLD，不得再次使用同一目录重试；检查其`OUTCOME_PRIVATE.json`及SAFE，保持无内容输出。两者成功也只说明合成请求协议和本地证据采集兼容，不代表Provider独立日志已认证、更不代表真实336条来源准入。正式批次仍以`require_pre_review`通过和可外部鉴别的Provider执行证据为硬门禁。


## 2026-11-15：Qwen3.7/DeepSeek Flash首次新合成API观测

Owner按已冻结顺序回传两份SAFE：Qwen3.7 `REVIEWER_SYNTHETIC_API_PASS__NO_PRIVATE`（1请求、`SCHEMA_VALID`）；DeepSeek Flash `REVIEWER_PROTOCOL_HOLD`（1请求、`QUALITY_FLOOR_DECISION_INCONSISTENT`）。两次均synthetic only、私有来源读取0、GPU0、Train0。旧严格校验器对PASS评分低于冻结门槛阻断正确：不可改分、自动降级、自动补全或追认。已检查旧探针使用`REVIEW_INSTRUCTIONS`，包含六维要求但未明确写出数值下限；仓库已存在`REVIEW_INSTRUCTIONS_V3_CONSISTENT`，明确六维下限和严重标志。此为合理可能原因，不能仅凭SAFE判断DeepSeek实际给了哪个低分或原始意图。

最小修改：现有`r60_reviewer_protocol_probe.py`新增**可选**`--consistent-rubric`，只在此选项生效时向现有`model_request`传旧有V3冻结门槛提示词，并在create-only私有`ATTEMPT_PRIVATE.json`标记`rubric_profile=V3_CONSISTENT`；旧调用默认不改、历史回执不动、不新造模型适配器。CI [#43694248463](https://github.com/sunxu/storyforge/actions/runs/43694248463) Ruff、268/268合成测试PASS。**未重复实际API调用**。既有`OUTCOME_PRIVATE.json`仅保留观测ID和请求/响应SHA，不含原始Reviewer JSON，因此不可能从该文件逆推出失败评分；需要新鲜请求才能验证V3实战表现，但不得覆盖旧目录或把新结果替代冻结结论。

下一步优先只读检查已有两条OUTCOME的观测字段完整性，随后将新Runner显式绑定V3审核提示词、可信执行日志/Provider证明和前置A线来源保护；未完成前不允许真实候选审核或训练。新合成V3重试**不是必须立即执行的准入门禁**，不为修复历史SAFE而重复发送。


## 2026-11-15：Qwen+DeepSeek前置审核V2入口接通（尚未批准真实候选）

新增`experiments/r58_quality/r60_forward_official_review_v2.py`及`test_r60_forward_official_review_v2.py`。GitHub Actions [#43694584107](https://github.com/sunxu/storyforge/actions/runs/43694584107)：Ruff PASS、276合成测试PASS。

与原QD20历史调用相同，**不再发明新Provider客户端**：Reviewer A固定`qwen3.7-flash`/百炼、`DASHSCOPE_API_KEY`；Reviewer B固定`deepseek-flash`/DeepSeek官方、`R60_DEEPSEEK_KEY`，仅复用`r60_real_ai_dual_review.model_request`与`r60_reviewer_transport.build_body`。两侧都按`REVIEW_INSTRUCTIONS_V3_CONSISTENT`冻结数值下限审核，原V1/V2/V3旧回执/原QD20旧版本不变。

新输入是单个Owner Mac私有0600 JSON（`schema=storyforge_r60_forward_official_review_input_private_v1`，仅五个字段`schema/source/protection/world/case`）。预检查：`case`历史3消息+target摘要必须与`source`声明严格相等；`require_pre_review`要求全部评测保护及来源组件凭证明确齐全。只有同时传`--execute --allow-remote-private-review`才可读取模型API Keys、执行真实网络请求，默认不发请求。真实执行采用0700新私有目录，创建仅一次的0600前置Seal及逐侧REQUEST/OUTCOME文件，A失败即停止不请求B；不覆盖、不重试、不修改冻结数据。已覆盖门禁缺失时0调用、篡改时0调用、禁止重复提交、合成双侧mock通路及冻结评分不一致时停止。

**范围严禁误判**：
- 新Runner检查的是传入声明与JSON摘要绑定、时序顺序及私有执行观测；`source/protection/world`中的布尔声明**不能自动由本Runner证明真实**，目前真实R50保护集、Story语义组件的独立可信来源认证仍为A线HOLD。
- Qwen/DeepSeek真实HTTP返回的id/response SHA只是客户端观测；Provider后台外部鉴证与Reviewer执行独立性仍B线HOLD。Runner只可返回`FORWARD_OFFICIAL_V2_EXECUTED__INDEPENDENCE_HOLD`，Train永远0；不能用完整合成CI将其写成生产PASS。
- **目前不要用旧336条或未独立认证的任意真实样本调用`--execute`。** 下一工作是将独立验收的完整R50保护manifest和世界组件判定与新V2输入绑定；在审核前就生成经过独立审核的凭证。没有上述认证，保持预检HOLD，不会以重复调API解决。
- 所有外部Reviewer请求费用、私有正文外发都只发生在Owner明确执行且来源已预认证时，不默许自动启动。C线HF CPU3合成技术PASS保留，不再重跑。


## 2026-11-15：P0正式Reviewer V2强制磁盘Manifest闭环

现已更改`experiments/r58_quality/r60_forward_official_review_v2.py`，`validated_bundle`只接收`schema/source/case`，遇到`protection/world`调用方裸字典立即拒绝。CLI强制提供`--protection-manifest`、`--world-manifest`，路径必须位于Owner本机私有根目录；复用`r60_forward_manifest_binding_v1.require_pre_review_from_manifests`的0600文件守卫、自身内容哈希检查及针对case的component定位，再运行`require_pre_review`。任何缺失、篡改、Gold72/P2B保护未完整覆盖、语义组件未决或Train/Val划分未绑定，皆**发生在API密钥读取及网络请求前**。旧冻结Runner、旧336/原QD20不改。GitHub Actions [#43724011504](https://github.com/sunxu/storyforge/actions/runs/43724011504) Ruff PASS、286项合成单测PASS（含裸字典、缺失路径、未覆盖保护和无请求断言）。

**重要边界**：Manifest自哈希核验防止意外漂移，不是原始内容真实性的独立签名；不能依赖攻击者可同步重算的SHA+布尔值获得A线PASS。Owner的实际Gold72/P2B保护范围和16条语义比对仍需来自私有原始资料、可审核证据和独立决策。此时现有保护manifest的`covers_all_protected_sets=false`，因此即使提供CLI两条Manifest路径，也应在前置阶段HOLD、零模型请求。没有放行候选就不执行`--execute`。

P1/P2最小取证：先仅在Owner Mac检查Gold72、P2B原始文件的出处（包括其初始source provenance、case-to-story crosswalk、hash与0600封存），禁止靠顶层manifest无法恢复ID就推定不存在；再对16条优先候选通过独立语义审核记录具体的角色、Opening、世界版本、剧情关联来源与不确定边。只冻结确已独立证实的组件；不复审旧336/不重跑HF；16条当前均HOLD。最终签发需把来源审批记录与保护集SHA、世界component manifest/实际历史截止版本联系起来。
