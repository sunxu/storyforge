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


## 2026-11-12 R50字段Schema已核实；新增PRESEAL跨文件检查器（待Owner实跑）

Owner回传仅字段名称，已确认：候选46行含`case_id,world_id,history,world_card,user_input,long_term_rules,focus_tags`；provenance46行含`case_id,source_story_id,source_session_id,history_message_ids,cutoff_message_id,story_number,card_evidence`。另外选择清单含`original_case_count,selected_case_count,excluded_cases,final_heldout_seal`；准入状态含`candidate_case_count,excluded_case_count,exclude_ids,final_heldout_seal,promotion`；world inventory含`same_story_id_pair_count,heldout_final_seal,semantic_hidden_alias_and_world_component_closure`；R45 gate含`frozen_r45_hashes_verified,heldout_cases_sealed,incomplete_or_hidden_world_aliases`。**这只说明键存在，不代表其值构成PASS。**

基于真实字段结构新增`scripts/r60_r50_preseal_crosswalk_cpu.py`和`tests/test_r60_r50_preseal_crosswalk_cpu.py`：纯标准库/本机只读校验6个Owner指定文件、46/46唯一`case_id`及顺序逐案对应、来源story/session/history ID字段存在且非空、四份报告必要键存在。输出只有安全布尔状态及计数，不泄露私有ID/正文/哈希/路径；即使全部通过仍只返回`R50_PRESEAL_46_CROSSWALK_PASS__FINAL_COVERAGE_HOLD`，`frozen_protection_50_verified=false`、`r45_full_source_isolation_verified=false`、`r50_complete_exclusion_verified=false`、`train_admitted=0`。**这个工具尚不验证R50 50→46的4例筛除语义、原始文件SHA/封存状态，也不比较Common2训练故事，绝不能冒充最终排除。**

Owner Mac，在独立分支同步代码并确认工作树干净后：

```bash
set -euo pipefail
cd ~/workspace/storyforge-r60-4router-review
PY="$HOME/.local/share/storyforge/venvs/r60-tests/bin/python"
"$PY" -m pytest -q tests/test_r60_r50_preseal_crosswalk_cpu.py
"$PY" -m compileall -q scripts/r60_r50_preseal_crosswalk_cpu.py
B="$HOME/.local/share/storyforge/r50"
D="$B/run.dWgMu5/private/derived"
"$PY" scripts/r60_r50_preseal_crosswalk_cpu.py \
  --cases "$D/R50_CANDIDATE_46_PRESEAL_PRIVATE.jsonl" \
  --provenance "$D/R50_PROVENANCE_46_PRESEAL_PRIVATE.jsonl" \
  --selection "$D/R50_46_PRESEAL_SELECTION_MANIFEST_PRIVATE.json" \
  --admission "$B/run.dWgMu5/private/R50_46_ADMISSION_STATUS_20261016.json" \
  --worlds "$B/full-original-worlds/run.cGUPnjdx/R50_FULL_ORIGINAL_WORLD_INVENTORY_PRIVATE.json" \
  --r45-gate "$B/r45-full-source-gate/R50_R45_FULL_SOURCE_GATE_20261022_220215.json"
```

若出现`FILE_PERMISSION_HOLD`或`SOURCE_PROVENANCE_HOLD`，不得更改冻结原件以迎合测试，应核对冻结数据的真实schema，再以显式审核的薄适配修正检查器。完成46/46结构级检查后，下一步要按照报告**值的安全语义投影**验证原始50→排除4→候选46、最终封存状态及R45世界排除；必须先核验报告值的枚举或schema合同，绝不根据字段名猜含义。


## 2026-11-12 PRESEAL 跨文件检查遇到 FILE_PERMISSION_HOLD（最新状态）

Owner实际SAFE：`R50_PRESEAL_CROSSWALK_HOLD` / `reason_code=FILE_PERMISSION_HOLD`，`preseal_cases_checked=0`、`case_id_order_exact=false`、`r50_complete_exclusion_verified=false`、`train_admitted=0`。**尚未进入46例逐案核验**：当前`case_id_order_exact=false`只是默认占位，不能解释为发现错配。冻结原件存在权限模式不符合新脚本0600门禁的情况，具体哪个文件及其mode未得到Owner诊断。

所有已定位的确切文件路径、已知真实字段和**不触碰原件的安全复制/验证方案**已归档至 [R50 Owner本机冻结文件定位与权限恢复手册](R60_R50_LOCAL_FROZEN_PATHS_20261112_CN.md)。先用只读源+0700临时目录中的0600副本做跨文件核验，逐份校对原文件与副本SHA256，在Owner本地完成、不公开原始哈希。不得直接`chmod`或重新生成冻结R50原件；不启动HF Job/GPU/训练。

## 2026-11-12 Owner 46/46 PRESEAL 跨文件真实检查 PASS（最新）

Owner 在私有 `r50-crosswalk-copy-whznSMXy` 目录用6份源文件**字节SHA256一致**的0600副本进行只读检查，`R50_COPY_0..5=SHA256_MATCH`，原R50冻结文件一律未更改。最终SAFE为 `R50_PRESEAL_46_CROSSWALK_PASS__FINAL_COVERAGE_HOLD`，`preseal_cases_checked=46`、`case_id_order_exact=true`、`provenance_story_fields_present=true`、`history_reference_fields_present=true`、`selection_expected_fields_present=true`、`admission_expected_fields_present=true`、`worlds_expected_fields_present=true`、`r45_gate_expected_fields_present=true`。没有数据库、HF Job、GPU或模型推理；`frozen_protection_50_verified=false`、`r45_full_source_isolation_verified=false`、`r50_complete_exclusion_verified=false`、`train_admitted=0`。

这证明46个PRESEAL的case ID顺序一一相等、来源story/session/history非空且关联报告预期字段存在。**没有检查原始50案的缺失4案是否正确排除、报告值是否代表最终seal、R45跨世界语义别名隔离，也没有将Common2源标识同R50做交集。** 下阶段必须只读检查selection、admission、worlds及R45 gate的类型化状态值，并保留HOLD。可复用已创建且逐份SHA MATCH的临时副本（Owner本机路径详见 `R60_R50_LOCAL_FROZEN_PATHS_20261112_CN.md`），无需重新复制/更改原件。

## 2026-11-12 下一步：只读投影4份冻结状态报告的值类型与安全计数

新增`scripts/r60_r50_freeze_status_projection_cpu.py`，只接受**已核对SHA的六份Owner私有副本**中四份报告`f2..f5`；输出预期字段的布尔值/安全范围内整数/数组长度/对象键数/字符串类型，不输出字符串原值、ID、哈希、路径或正文。严格维持`R50_FREEZE_STATUS_TYPES_READ__EXCLUSION_HOLD`、`r50_complete_exclusion_verified=false`、`train_admitted=0`。仅供下一阶段决定如何按真实值类型解释50→46、4项剔除和报告HOLD状态，**不是最终50案封存或Common2交集证明**。

Owner复用已产生的私人副本（若已删除，则按 `R60_R50_LOCAL_FROZEN_PATHS_20261112_CN.md` 的SHA流程重新复制），不要改动R50原件：

```bash
set -euo pipefail
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-tests/bin/python"
"$PY" -m pytest -q tests/test_r60_r50_freeze_status_projection_cpu.py
"$PY" -m compileall -q scripts/r60_r50_freeze_status_projection_cpu.py
P="$HOME/.local/share/storyforge/r60/private/r50-crosswalk-copy-whznSMXy"
test -f "$P/f2" && test -f "$P/f3" && test -f "$P/f4" && test -f "$P/f5"
"$PY" scripts/r60_r50_freeze_status_projection_cpu.py \
  --selection "$P/f2" --admission "$P/f3" \
  --worlds "$P/f4" --r45-gate "$P/f5"
```

输出SAFE JSON可用于后续精确工具设计；其中任何`string_or_unsupported`只是类型，不代表原值已审定。应按下一阶段新增显式允许的状态枚举校验器取证，不使用宽泛的「非空字符串=通过」逻辑。

## 2026-11-12 Owner R50冻库状态类型投影：50→46数量吻合、最终seal仍HOLD

Owner私有0600副本 `f2..f5` 的真实只读SAFE：`R50_FREEZE_STATUS_TYPES_READ__EXCLUSION_HOLD`，selection `original_case_count=50`、`selected_case_count=46`、`excluded_cases` 长度4、`owner_exclusion_authorized=true`；admission `candidate_case_count=46`、`excluded_case_count=4`、`exclude_ids` 长度4；worlds `same_story_id_pair_count=0`；R45 gate `frozen_r45_hashes_verified=true`、`exact_world_id_conflicts=0`、**`heldout_cases_sealed=0`**。`final_heldout_seal`、`promotion`、隐藏alias及world closure相关字段的真实字符串值尚未读取/解释，本次投影仅返回`string_or_unsupported`。**两处排除长度均为4，不等于排除ID列表已经证明相同**；也不能以世界ID冲突0代替完整语义隐藏别名审查。R50完整排除仍HOLD，训练准入0。

新增本机纯标准库只读 `scripts/r60_r50_exclusion_pair_cpu.py` 与合成测试。它仅验证两个文件确实声明50→46、Owner授权true，且两个**标量ID**排除清单长度均4、各自唯一、成员集合一致；仅输出匹配布尔值和固定错误码，不打印ID。若真实`excluded_cases` 是对象列表或不同索引语义，该脚本返回 `EXCLUSION_ID_TYPE_HOLD` 或集合不一致，必须先依据实际Schema明确映射关系，而不是修改原件迎合测试。即使匹配，也仅为 `R50_PRESEAL_FOUR_EXCLUSIONS_MATCH__SEAL_HOLD`：**不会声明最终50案seal、R45隔离、Common2与R50无交集**。

Owner可直接复用已核对SHA的私有副本：
```bash
set -euo pipefail
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-tests/bin/python"
"$PY" -m pytest -q tests/test_r60_r50_exclusion_pair_cpu.py
"$PY" -m compileall -q scripts/r60_r50_exclusion_pair_cpu.py
P="$HOME/.local/share/storyforge/r60/private/r50-crosswalk-copy-whznSMXy"
"$PY" scripts/r60_r50_exclusion_pair_cpu.py --selection "$P/f2" --admission "$P/f3"
```

如果HOLD，仅回传SAFE原样，不要上传JSON报告原件、真实排除ID或自由文本状态。下一步需要独立核实封存状态的真实枚举含义、R45隐藏别名完整审查、最终50项全量保护以及Common2的实际来源交集。

## 2026-11-12 最新：排除两清单为不同元素形态，尚不能判断成员是否一致

Owner运行`r60_r50_exclusion_pair_cpu.py`真实SAFE为`R50_EXCLUSION_PAIR_HOLD`/`EXCLUSION_ID_TYPE_HOLD`，两清单数量均为4，`exclusion_id_sets_equal=false`仍是**未通过类型校验时的默认值**，不是已经发现成员不一致。旧脚本仅接受每个元素均为标量`str/int`的数组，真实至少有一份含非标量、非预期类型或超长元素。必须先确认两种元素结构，再设计明确的字段映射，不得直接`str(dict)`或靠列表下标比对，也不得修改冻结原件。

新`scripts/r60_r50_exclusion_shape_cpu.py`只读对Owner现有SHA相同的`f2`选择清单、`f3`准入报告进行形状分析：仅输出4元素各自的类型计数、**预定白名单字段名**、非白名单字段出现次数及嵌套容器计数；不输出任意来源字段名、私有字符串值、ID、哈希、原始JSON。即使结构读取成功也仅返回`R50_EXCLUSION_SHAPES_IDENTIFIED__MAPPING_HOLD`，仍未验证排除ID集合等价或最终seal。合成测试已提交，Owner真实运行待回执。

```bash
set -euo pipefail
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-tests/bin/python"
"$PY" -m pytest -q tests/test_r60_r50_exclusion_shape_cpu.py
"$PY" -m compileall -q scripts/r60_r50_exclusion_shape_cpu.py
P="$HOME/.local/share/storyforge/r60/private/r50-crosswalk-copy-whznSMXy"
"$PY" scripts/r60_r50_exclusion_shape_cpu.py --selection "$P/f2" --admission "$P/f3"
```

不启动HF Job/GPU/训练，保留`r50_complete_exclusion_verified=false`及`train_admitted=0`。如果列表元素是嵌套对象，后续必须按真实字段与冻结报告语义先明确映射关系，再执行安全的**逐案ID**对账。

## 2026-11-12 Owner真实排除清单元素形状已证实；升级显式ID映射 v2

Owner SAFE形状回执`R50_EXCLUSION_SHAPES_IDENTIFIED__MAPPING_HOLD`：`selection.excluded_cases`为**4个object**，至少出现预定义白名单键`case_id`和`reason`，有8次非白名单键出现（不公开字段名/值），无内嵌容器；`admission.exclude_ids`为**4个string**。此前`EXCLUSION_ID_TYPE_HOLD`属于旧v1只接受标量输入的技术门禁，不构成来源成员冲突。

已在原校验器`scripts/r60_r50_exclusion_pair_cpu.py`做**可复用的v2映射**：selection四条全为对象时，仅提取每条`case_id`（必须非空str、长度<=256），`reason`必须为非空str，不解释理由含义、忽略其他不公开字段；另一边`exclude_ids`四条仍采用原有标量约束。比较两边精确case ID集合并拒绝重复、非标量、混合结构、缺失case_id/reason及成员不一致。**不做字符串改写、大小写归一、索引号猜测、对象序列化或列表顺序强制要求**。保持以前全标量selection的兼容路径，最终seal/R45/完整50保护和训练准入字段全部保持false/0，SAFE schema更新`storyforge_r60_r50_exclusion_pair_safe_v2`。

Owner在现有私有副本上运行前先合成测试；只复制/更改GitHub代码，不接触原始R50源文件：
```bash
set -euo pipefail
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-tests/bin/python"
"$PY" -m pytest -q tests/test_r60_r50_exclusion_pair_cpu.py tests/test_r60_r50_exclusion_shape_cpu.py
"$PY" -m compileall -q scripts/r60_r50_exclusion_pair_cpu.py
P="$HOME/.local/share/storyforge/r60/private/r50-crosswalk-copy-whznSMXy"
"$PY" scripts/r60_r50_exclusion_pair_cpu.py --selection "$P/f2" --admission "$P/f3"
```

预期只有当四个case ID完全同集合时才是`R50_PRESEAL_FOUR_EXCLUSIONS_MATCH__SEAL_HOLD`；如返回`EXCLUSION_OBJECT_SCHEMA_HOLD`或者`EXCLUSION_ID_SET_MISMATCH_HOLD`必须按真实文件合同继续审查，**不得为了PASS修改原件或隐式转换ID**。合成测试和Owner真实执行目前未验收，不能提前宣称v2通过。

## 2026-11-12 Owner v2 排除四案精确成员对账 PASS（最新）

Owner 在已固定SHA的私有副本`f2/f3`上执行v2检查，真实SAFE `R50_PRESEAL_FOUR_EXCLUSIONS_MATCH__SEAL_HOLD`，`schema=storyforge_r60_r50_exclusion_pair_safe_v2`、`selection_excluded_count=4`、`admission_excluded_count=4`、`exclusion_id_sets_equal=true`、`reason_code=FOUR_EXCLUSION_IDS_MATCH`。已确认 `selection.excluded_cases[].case_id` 与 `admission.exclude_ids[]` 的四案集合精确一致；46/46 PRESEAL来源行序一致另已核验。完全不打印ID/私有文本，未访问数据库或HF、未启动GPU/SFT，`train_admitted=0`。

**不能由这个PASS证明**原始50条构成完整受保护全集、4条排除在原始50案确实存在且另外46案为精确补集、最终held-out已seal、R45隐藏别名/世界集合隔离已通过，或Common2两条与R50无story/session/message交集。相关现有SAFE仍为`final_heldout_seal_verified=false`、`r50_complete_exclusion_verified=false`。尤其已有R45报告`heldout_cases_sealed=0`，该报告不是最终封存通过的证据。

下一真正任务不应继续重复验证4/4，而应从原R50 Selection Manifest的`original_sha256`、`case_source_line_sha256`、`provenance_source_line_sha256`、`selected_parent_line_numbers_1_based`和`final_heldout_seal`，及Admission/Worlds/R45报告的状态字段建立**值语义明确**的原始50案覆盖证明。先核对实际原始50份私有文件位置与这些摘要的定义，再做原始50 ID与当前46+4的严格补集关系。对未识别的字符串状态必须HOLD，不得仅凭存在或非空标为PASS。此后才在Common2两条完整来源键上执行R50三层集合交集检查，最后再由Owner决定是否训练。

## 2026-11-12 资料库恢复原始R50 50案：精确SHA256验证通过（最新）

在ChatGPT用户资料库**根目录**实际发现 `StoryForge_R50_PRIVATE_NewChat_Handoff_20261016.zip`（368932 bytes）、`R50_FRESH_HELDOUT_50.jsonl`（422562 bytes）、`R50_CASE_PROVENANCE_50.jsonl`（31758 bytes）。历史全量私有ZIP已经在工作容器中成功取回，ZIP CRC `testzip()==None`、16个条目。两份独立JSONL文件与ZIP内对应同名条目分别**逐字节SHA256与2026-10-16历史交接收据完全一致**：

- R50_FRESH_HELDOUT_50.jsonl: `8dbb66aeb47fd1fec34718d31b228c0378a79f43b7b847eb3e403752d8139781`
- R50_CASE_PROVENANCE_50.jsonl: `9306af53c6a53fbe46a6675c50e5fac4753162a5c19d6f3c1a0072919306b280`
- ZIP中的 `R50_AUTHORING_REPORT.md` SHA256也与原历史收据 `7d0862300d8a729f893f66c092dfa74a6e2adb75d85eae0cfe2276e105bdf8bd` 一致。

**此前`R50_SOURCE_RECOVERY_HOLD`的“找不到原始50题”定位障碍已解除。** 上述证据是文件级“身份/完整性验证”，不是50→46补集验证、最终held-out seal、R45隐藏别名/世界隔离、Common2三层交集；它们仍HOLD，`train_admitted=0`，GPU/SFT禁止。ZIP和JSONL都只是用户ChatGPT资料库来源及工作容器的私有副本，**尚未上传到Owner Mac本机冻结目录，不能宣称Mac路径已经存在**；后续Owner应通过会话安全下载到Mac的独立私有目录，逐份本地shasum对照后再与已存在PRESEAL46+4进行严格补集核验。严禁把恢复原件写入公开Git、Issue或当作已签署最终seal。

## 2026-11-12 Owner Mac原始50文件SHA实测通过；可执行完整50=46+4补集验收（最新）

Owner报告两份独立原始文件已安置到 `$HOME/.local/share/storyforge/r50/original-frozen-20261016/`，Mac本地 `shasum -a 256` 分别精确等于历史冻结SHA：cases `8dbb66aeb47fd1fec34718d31b228c0378a79f43b7b847eb3e403752d8139781`、provenance `9306af53c6a53fbe46a6675c50e5fac4753162a5c19d6f3c1a0072919306b280`。**R50原始50文件的Mac定位+身份完整性恢复现已PASS**，原有PRESEAL46和排除4名单字节保持不变；最终heldout seal/R45世界隔离/Common2来源交集未解除。

本轮新增 `scripts/r60_r50_original50_complement_cpu.py` 和纯合成测试。只读验证：2份原始50的固定字节数、SHA256、50行唯一`case_id`与provenance顺序一一对应；原46/46来源顺序对应；现有Selection/Admission的50→46与4条排除清单精确成员一致；原始50减46的集合**恰好是那4条排除ID**，且46恰好对应Selection记录的46个原始1-based行号；保留的46条 `source_story_id/source_session_id/cutoff_message_id/history_message_ids` 与原始50的对应source provenance精确一致。不读取数据库、不调用模型、HF、GPU，不向stdout公开原始ID、世界卡、文本或哈希。仅通过全部严格校验才返回 `R50_ORIGINAL50_46_PLUS4_EXACT_COHORT_PASS__SEAL_R45_TRAIN_HOLD` 和 `original_50_complete_cohort_verified=true`；**始终** `final_heldout_seal_verified=false`、`r45_full_source_isolation_verified=false`、`r50_complete_exclusion_verified=false`、`train_admitted=0`。

Owner独立工作树完成合成测试后在原始私有文件以及已SHA MATCH的46/4副本上运行；若原始50权限不是0600，先按同一SHA副本策略处理（不chmod冻结原件）：

```bash
set -euo pipefail
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-tests/bin/python"
"$PY" -m pytest -q tests/test_r60_r50_original50_complement_cpu.py
"$PY" -m compileall -q scripts/r60_r50_original50_complement_cpu.py

R="$HOME/.local/share/storyforge/r50/original-frozen-20261016"
P="$HOME/.local/share/storyforge/r60/private/r50-crosswalk-copy-whznSMXy"
"$PY" scripts/r60_r50_original50_complement_cpu.py \
  --original-cases "$R/R50_FRESH_HELDOUT_50.jsonl" \
  --original-provenance "$R/R50_CASE_PROVENANCE_50.jsonl" \
  --derived-cases "$P/f0" --derived-provenance "$P/f1" \
  --selection "$P/f2" --admission "$P/f3"
```

**若报`SOURCE_PROVENANCE_MISMATCH_HOLD`或`PARENT_LINE_MAPPING_HOLD`，不修改原件，不默认放宽规则；先核对Selection Manifest是否规定真实来源行号、46的历史变换规则与原始50的字段语义。** 本脚本是已创建但尚未在Owner Mac实跑的下一验收项，禁止提前声称50补集检查已PASS。

## 2026-11-12 Owner Mac原始50=46+4严格补集真实 PASS（最新权威回执）

Owner在Mac私有冻结原件+此前SHA完全一致的46/4副本上执行 `scripts/r60_r50_original50_complement_cpu.py`，得到真实SAFE状态：

`R50_ORIGINAL50_46_PLUS4_EXACT_COHORT_PASS__SEAL_R45_TRAIN_HOLD`，`reason_code=FROZEN_ORIGINAL_COMPLEMENT_AND_SOURCE_MAPPING_PASS`；`original_hashes_verified=true`、`original_case_provenance_order_verified=true`、`derived_case_provenance_order_verified=true`、`derived_46_match_manifest_selected_lines=true`、`excluded_four_match_original_complement=true`、`selected_source_provenance_matches_original=true`、`original_50_complete_cohort_verified=true`。所核证精确覆盖的是历史固定SHA的原始50文件、Selection记录的46个原始行号、4个唯一排除ID及被选46条的四类来源字段一致性。文件字节未改动、不输出私有ID/正文、数据库/HF Job/GPU均未启动。

**截至本回执，原始50文件定位和完整补集不再是阻塞项**，不应继续将“缺失原始50案”或“未验证50→46补集”写为最新OPEN。剩余准入硬门槛仍有 `final_heldout_seal_verified=false`、`r45_full_source_isolation_verified=false`、`r50_complete_exclusion_verified=false`、`train_admitted=0`。注意`original_50_complete_cohort_verified=true`仅证明被恢复的原始50与46+4构成完整集合，**不能自动提升为R50受保护全集与R45训练/测试隔离已通过**。

下一步仅聚焦：1) 核实R50 final seal真实字段语义/Owner封存合同，不以非空字符串判通过；2) 用完整R45冻结私有训练/验证世界、故事/会话/消息ID和别名审查证据做R50世界级隔离，警惕历史R45 gate的`heldout_cases_sealed=0`；3) 在同一冻结身份策略下对Common2两条候选做story/session/message交集和任何语义世界别名排查；4) 固定Qwen原生与Swift训练/推理模板政策，按Owner审批维持训练准入0至门禁全过。所有私有内容继续留在Mac或ChatGPT资料库，不写GitHub。

## 2026-11-12 新增 Common2 vs R50 原始50案三层ID精确隔离检查（待Owner Mac执行）

已完成的`R50_ORIGINAL50_46_PLUS4_EXACT_COHORT_PASS__SEAL_R45_TRAIN_HOLD`只验证原50与46+4精确补集；训练候选是否与R50的源故事/会话/消息重合，必须使用**原始50条provenance全量**检查，而不能仅比较46条PRESEAL或五世界描述性名称。

本轮新建`scripts/r60_r50_common2_exact_source_isolation_cpu.py`与`tests/test_r60_r50_common2_exact_source_isolation_cpu.py`：固定原始50来源JSONL大小/历史SHA256、50份来源结构、完整`source_story_id`集合/`source_session_id`集合/`history_message_ids`及`cutoff_message_id`集合；从早已存在的Common2历史恢复清单 `R60_QD20_COMMON2_SUPABASE_RECOVERY_PRIVATE.json` 中只读验证两条独立目标、两条story/session、每条`history_messages[].id`及目标`assistant_message_id`，在本地做三类精确ID交集。只输出三类交集计数与状态，不输出任一来源ID、路径、历史消息或哈希；无网络、数据库、HF Job、模型/GPU。

**即使三类精确交集全0，仍返回**`R50_COMMON2_EXACT_KEYS_DISJOINT__SEMANTIC_R45_SEAL_HOLD`，`exact_source_id_disjoint_verified=true`，但`semantic_world_alias_isolation_verified=false`、`r45_full_source_isolation_verified=false`、`final_heldout_seal_verified=false`、`r50_complete_exclusion_verified=false`、`train_admitted=0`。不能把精确ID无重叠自动等同R45隐藏别名、内容复述或R50最终封存通过。

Owner Mac运行（不覆盖/修改私有原件；只访问本机已存在R50 50案，Common2既有恢复清单）：

```bash
set -euo pipefail
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner

PY="$HOME/.local/share/storyforge/venvs/r60-tests/bin/python"
"$PY" -m pytest -q tests/test_r60_r50_common2_exact_source_isolation_cpu.py
"$PY" -m compileall -q scripts/r60_r50_common2_exact_source_isolation_cpu.py

R="$HOME/.local/share/storyforge/r50/original-frozen-20261016"
B="$HOME/.local/share/storyforge/r60/private"
# 只读定位已有Common2原始历史恢复清单，不要重新运行DB查询或新建数据：
find "$B" -type f -name 'R60_QD20_COMMON2_SUPABASE_RECOVERY_PRIVATE.json' -print
# 从查到的真实、权限0600的文件中选定一个确切位置：
RECOVERY="/将上条find查到的真实绝对路径填在这里"
"$PY" scripts/r60_r50_common2_exact_source_isolation_cpu.py \
  --r50-original-provenance "$R/R50_CASE_PROVENANCE_50.jsonl" \
  --common2-recovery "$RECOVERY"
```

如果Common2清单权限不满足0600，按前述仅副本调整权限并与原件SHA比对的方法处理，**不能直接chmod历史原件**；如果源字段类型或Common2 schema与冻结合同不符，输出固定HOLD，不能猜测修复。Owner应仅回传SAFE JSON。下一任务是语义世界/隐藏别名以及真实seal状态证据审定；不再重复已通过50补集。
