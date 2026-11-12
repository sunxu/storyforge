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

## 2026-11-12 最终封存状态核查：不能将原始文件SHA固定误认为正式Held-out已seal

对照仓库现存历史权威文档`docs/r56/R56_R50_46_PROTECTED_GATE_NEXT_STEPS_20261022.md`与`docs/evidence/V03_R50_46_PRESEAL_GATE_DELTA_COUNT_ONLY_20261022.json`：截至该历史证据2026-10-22，明确记载`final_seal=NOT_PERFORMED`、`official_heldout_test_admitted=0`、`cross_world_alias_and_temporal_semantics=HOLD`、`r49_r56_preregistration=NOT_APPROVED`。虽然当时Owner Mac已有原R45完整来源screen的部分PASS回执，语义别名及早期开发暴露仍HOLD；这一历史记录**不证明当前存在新的最终sealed版本**，也不能反过来断言当前根本不存在其他晚于2026-10-22的封存证据。结合本轮Owner真实私有R45 gate中的`heldout_cases_sealed=0`，本轮仍须严格`final_heldout_seal_verified=false`。

已完成的原始50案固定SHA验证、50=46+4完整补集检查，是严格输入和成员身份冻结的技术证据；要使46条正式晋级Held-out测试，还需独立的最终sealed input/grader custody、角色拼接及Tokenizer合同、模型输入等价合同与Owner批准，不能通过脚本自动把`NOT_PERFORMED`变成`PASS`。**Common2的训练隔离策略须由Owner明确是否把原始50案全体当作受保护排除集（保守默认全体保护），与R50正式seal是两个独立决策维度**。

新增的Common2三层来源检查仅对**原始50条全体**比对story/session/message ID，不以46条PRESEAL代替；精确不重叠即使PASS，也继续保持R45隐藏别名和语义独立HOLD、训练准入0。


## 2026-11-12 Owner R50原始50案 × Common2两案三级精确来源隔离 PASS（最新）

Owner在Mac本地用历史固定SHA原始50条provenance与原有Common2私有历史恢复清单执行`scripts/r60_r50_common2_exact_source_isolation_cpu.py`，得到真实SAFE：

`R50_COMMON2_EXACT_KEYS_DISJOINT__SEMANTIC_R45_SEAL_HOLD`，`reason_code=EXACT_THREE_LEVEL_DISJOINT`，`r50_original_sha_verified=true`、`r50_cases_checked=50`、`common2_cases_checked=2`、`exact_story_overlap_count=0`、`exact_session_overlap_count=0`、`exact_message_overlap_count=0`、`exact_source_id_disjoint_verified=true`。不读取数据库、不开HF Job、GPU或SFT，不输出私有来源ID/正文，`train_admitted=0`。

**这一项正式闭环：Common2两条与R50原始50条之间的故事/会话/历史及目标消息三级精确ID没有交集。** 不应再将其写为未执行，也不需要重复此严格交集计算。仍然`semantic_world_alias_isolation_verified=false`、`r45_full_source_isolation_verified=false`、`final_heldout_seal_verified=false`、`r50_complete_exclusion_verified=false`；任何ID无交集不能替代异名世界、共享角色/同事件改写、旧评测暴露或R45完整语义来源隔离。

下一步按优先级：(1) 已有R45原始49 Train/15 Val完整来源报告及多世界别名/语义审查状态进行带证据的Owner收敛，尽量复用现有CPU检查结果；(2) R50正式seal属于单独评测治理合同，历史材料明确未执行，禁止以原始文件SHA固定替代Owner封存；(3) 决定Qwen原生与Swift训练/推理模板政策并在现有CPU证据上验证，不再重发HF Job；(4) 全门禁与Owner签准前保持`train_admitted=0`。

## 2026-11-12 R45既有机械来源隔离报告：固定历史合同复核（新增，待Owner本地SAFE）

已从历史固定代码commit `92828ac0e47c8f7f7307851b8e171f564fd065ed` 真正读取 `scripts/v03_r50_private_r45_isolation.py` 源代码，明确既有报告的结构和状态合同：`schema=storyforge-r50-private-r45-isolation-v1`，`status=R45_FROZEN_49_15_EXACT_SCREEN_PASS__SEMANTIC_REVIEW_PENDING`，`verified_r45_counts.train=49`、`validation=15`、`new_world_count=5`、`frozen_r45_hashes_verified=true`，三项机械精确碰撞`exact_world_id_conflicts/exact_long_message_hit_count/all_offset_120_codepoint_window_hit_count`严格整数0，并要求`short_or_paraphrased_context_review=PENDING`、`incomplete_or_hidden_world_aliases=PENDING`、`heldout_cases_sealed=0`及未输出私有内容、未用GPU、未promotion。**这是完整5世界来源对R45 Train49/Val15的机械精确筛查合同，而非语义隔离签署。**

复用此前已SHA复制且只读的Owner报告`$HOME/.local/share/storyforge/r60/private/r50-crosswalk-copy-whznSMXy/f5`，新增`scripts/r60_r45_existing_full_source_receipt_cpu.py`、`tests/test_r60_r45_existing_full_source_receipt_cpu.py`。它只验证报告固有字段精确值/类型、计数、状态枚举，不自动重跑源历史，不打印未知字符串、私有字段或路径；合成测试覆盖正确合同、错误状态、非零冲突、无效布尔0、权限等。

```bash
set -euo pipefail
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-tests/bin/python"
"$PY" -m pytest -q tests/test_r60_r45_existing_full_source_receipt_cpu.py
"$PY" -m compileall -q scripts/r60_r45_existing_full_source_receipt_cpu.py
P="$HOME/.local/share/storyforge/r60/private/r50-crosswalk-copy-whznSMXy"
"$PY" scripts/r60_r45_existing_full_source_receipt_cpu.py --r45-report "$P/f5"
```

真实回执**还未验收**；预期满足该历史合同仅`R45_EXISTING_EXACT_SOURCE_SCREEN_PASS__SEMANTIC_SEAL_HOLD`，`r45_exact_source_screen_verified=true`；`r45_semantic_world_isolation_verified=false`、`final_heldout_seal_verified=false`、`train_admitted=0`始终不变。若不同版本报告不匹配则HOLD，必须查看报告来源合同而不是任意放松值校验。

**当前未解决的下一实质性风险**为跨世界隐藏别名、人物/事件共用与改写、既有开发/评测暴露；机械筛查无法取代此类审核。R50正式heldout seal也是另一个独立、仍未完成的评测合同，不能为了Common2训练把R50的正式评测封存政策悄悄更改。

## 2026-11-12 Owner R45完整五世界机械来源验收真实PASS（最新）

Owner Mac 对此前经SHA校验的历史R45完整来源隔离报告副本`f5`执行`scripts/r60_r45_existing_full_source_receipt_cpu.py`，真实SAFE：

`status=R45_EXISTING_EXACT_SOURCE_SCREEN_PASS__SEMANTIC_SEAL_HOLD`、`reason_code=FROZEN_R45_49_15_EXACT_REPORT_VERIFIED`、`r45_original_hashes_verified=true`、`r45_train_count_verified=true`、`r45_validation_count_verified=true`、`r50_source_world_count_verified=true`、`exact_world_collision_zero=true`、`exact_long_message_hits_zero=true`、`all_offset_120_window_hits_zero=true`、`r45_exact_source_screen_verified=true`。所有结果只确认历史固定审计器已记录的R45 Train49/Validation15 对R50五个原始世界机械检查；是**历史真实报告的合同二次验收**，而非本次重新扫描所有原始正文。

**已关闭：** R45冻结来源报告的SHA、49/15数量、五世界数量、世界ID冲突0、长消息精确重合0、连续120字符全偏移窗口碰撞0的验收项。不得重复提交R45机械隔离Job或再称该项未验证。

**仍需保留：** `r45_semantic_world_isolation_verified=false`、`final_heldout_seal_verified=false`、`r50_complete_exclusion_verified=false`、`train_admitted=0`。R45报告本身标记隐藏别名与短句改写`PENDING`，历史R50正式`final_seal=NOT_PERFORMED`，两者是独立的剩余门禁。后续须对真实语义世界关联（角色别名、事件、共享设定、重写/早期评测暴露）做证据审核，不得以字符串零碰撞补写PASS。

下一实际开发优先事项应转到**受控语义关联证据包及Owner裁决**，针对Common2真实2条与原R50全50/R45真实受保护训练及评测世界做语义闭环；并清理Qwen原生与ms-swift模板差异的准入合同。现有R50、R45机械来源门禁已关闭，不需要新增HF或GPU。

## 2026-11-12 转入语义隔离新证据与Qwen/Swift模板决策（最新）

已形成专门执行说明 [`R60_COMMON2_REMAINING_GATES_SEMANTIC_TEMPLATE_20261112_CN.md`](R60_COMMON2_REMAINING_GATES_SEMANTIC_TEMPLATE_20261112_CN.md)：划分G-S1 Common2两条 vs R50原始全50世界、G-S2 R45真实Train49/Val15 vs R50五世界、G-S3早期评测暴露与最终seal三个独立边界。现有原50=46+4、Common2×R50三级精确ID 0/0/0、R45五世界机械源碰撞0，以及真实HF CPU2 tokenizer/collator均PASS，**不再重复**。

特别核实历史`docs/evidence/V03_R50_ROLE12_OWNER_INTAKE_SAFE_20261023.md`记录：W17 vs 旧世界02/04/10三对`INSUFFICIENT_EVIDENCE`；其后7项全消息审核仍`INSUFFICIENT_CONTEXT`，且截止时真实生效的卡/规则未核证。不能靠对同一证据再做AI审核来闭合；需要Owner本地新的cutoff时点快照、别名事件出处及能复核的世界连通分量，先审再裁决。若无新证据明确`SEMANTIC_SOURCE_EVIDENCE_HOLD`，不得虚构独立结论。

模板方面的已证实情况：原生Qwen Tokenizer [2552,4048]、Swift Collator [2486,3982]、各差66，最终监督Token [282,305]且实际Collator通过；**差66根因及推理模板对齐未验证**。工程方案是提议将真正训练所用的Swift模板+Collator作为训练侧规范，原生审计仅用作长度预算独立参考；需Owner定下训练/推理双端合同，暂不能从这份提议推断新模板已获批，也不需要立刻再申请HF CPU Job。完整任务书和停止条件见新文档。所有HOLD及`train_admitted=0`保持不变。

## 2026-11-12 主线纠偏：新增Common2直接对R45真实训练与验证来源的故事隔离（待Owner实跑）

**主线始终为`Real1000 → 独立六维质量精筛 → 可复现SFT输入 → 训练/验证/保护集隔离 → Owner准入 → 后续训练`。** R50最终正式Held-out评测seal和W17内部语义争议属于评测治理旁支，不能为推进两条Common2衍生SFT输入而无限延伸；但原R50全50案继续作为训练保护集。已PASS的R50 50=46+4、Common2×R50 story/session/message 0/0/0、R45×R50五世界机械碰撞0以及真实HF CPU tokenizer/collator不再重复。

发现**直接影响训练分割**的未检查空白：此前R45×R50无重叠，不能推出Common2×R45 Train49/Validation15无重叠。新建纯本地只读检查器 `scripts/r60_common2_r45_source_story_cpu.py`、合成单测 `tests/test_r60_common2_r45_source_story_cpu.py`，严格读取R45未编译原始Train49/Validation15的历史SHA256 `e7442993088617c4eaefd3a0c9efc7651932f7048f34586046bf6d5b5981a742`/`5ebbb3c6986a5ac4d294175bab1980ee61df08536f9b8438c8a67010630f1963`，只从每行`metadata.source_story_id`取故事ID；Common2从现有SHA验证的两条Supabase recovery来源清单取`story_id`，分别计算与R45 Train和Val的精确故事集合交集。**既有R45完整源报告f5不包含这些逐故事ID，不可拿f5替代原始49+15。**

仅输出两项重叠计数及固定状态，不打印故事ID、私有正文或路径，不访问数据库、GPU/HF/model。若零交集，只能得到`COMMON2_R45_ORIGINAL_STORY_IDS_DISJOINT__SEMANTIC_TRAIN_HOLD`，不证明跨世界别名或场景内容独立，也不直接开放训练。若有重叠返回`COMMON2_R45_ORIGINAL_STORY_OVERLAP__TRAIN_HOLD`并保持`train_admitted=0`，禁止仅用全局去重或重新编号掩盖重叠。

本次合成检查器的Mac执行：
```bash
set -euo pipefail
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-tests/bin/python"
"$PY" -m pytest -q tests/test_r60_common2_r45_source_story_cpu.py
"$PY" -m compileall -q scripts/r60_common2_r45_source_story_cpu.py

# 先查已有Owner本机R46原始导出，不重下载/不新建Job：
R46="$HOME/.local/share/storyforge/r46-primary-evidence-r46-20261014T070529Z-248172"
find "$R46" -type f -name 'train.jsonl' -o -name 'validation.jsonl'
# 从find结果中选择确实位于source-data/下的原始未编译49/15，不能使用compiled输入
TRAIN="$R46/source-data/train.jsonl"
VAL="$R46/source-data/validation.jsonl"
test -f "$TRAIN" && test -f "$VAL"
# 复用上一项已经执行通过的那份Common2私有恢复清单：
RECOVERY="/填写前次已验收的R60_QD20_COMMON2_SUPABASE_RECOVERY_PRIVATE.json绝对路径"

"$PY" scripts/r60_common2_r45_source_story_cpu.py \
 --r45-original-train "$TRAIN" \
 --r45-original-validation "$VAL" \
 --common2-recovery "$RECOVERY"
```

**本机路径仅是历史R46导出证据提供的候选位置，必须以实际存在与检查器内置SHA比对为准**。合成测试与Owner真实SAFE尚待验收；若目录不存在，优先复用Mac历史R45 ZIP和R46主证据的其他副本，不自行造原始数据、不访问HF。该检查是Common2阶段临门一脚的直接训练集来源门禁；后续语义裁决及训练/部署模板政策仍需事实证据，Owner尚未授予正式数据准入/GPU许可。

## 2026-11-12 Common2×R45真实首轮技术HOLD：已补安全诊断（最新）

Owner执行`scripts/r60_common2_r45_source_story_cpu.py`真实SAFE为`COMMON2_R45_STORY_GATE_HOLD`、`reason_code=INPUT_OR_RUNTIME_HOLD`。中间量`r45_original_sha_verified=true`、`r45_train_rows_checked=49`、`r45_validation_rows_checked=15`，**Common2尚未读入**（`common2_cases_checked=0`），训练/验证交集均为`null`。这表明R45原始文件的哈希、元数据已有效读取，而失败发生于后续Common2私有恢复清单读取/解析/Schema或运行时；**不能断言重叠为0或非0**。

原v1将非`Hold`异常隐藏成统一`INPUT_OR_RUNTIME_HOLD`。现新增SAFE固定阶段`stage`（`INPUTS/R45_SPLITS/COMMON2_RECOVERY/COMPARISON`）以及有限固定错误码：`INPUT_FILE_NOT_FOUND_HOLD`、`INPUT_FILE_ACCESS_HOLD`、`INPUT_JSON_DECODE_HOLD`、`INPUT_SCHEMA_RUNTIME_HOLD`、`INPUT_IO_HOLD`；未知异常仍统一掩盖。不得把异常原文、回溯、文件绝对路径或私有内容打印至Issue。合成回归覆盖不存在、无效JSON及错误Schema。

Mac复验只需：
```bash
set -euo pipefail
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-tests/bin/python"
"$PY" -m pytest -q tests/test_r60_common2_r45_source_story_cpu.py
# 此处复用上一轮真实、SHA匹配的TRAIN/VAL/RECOVERY变量；不要覆盖或重建原文件
"$PY" scripts/r60_common2_r45_source_story_cpu.py \
 --r45-original-train "$TRAIN" --r45-original-validation "$VAL" \
 --common2-recovery "$RECOVERY"
```
请仅回传新SAFE JSON的`stage`和`reason_code`及完整聚合字段，不贴原文/路径。若为`INPUT_FILE_NOT_FOUND_HOLD`，应重新定位此前已通过R50×Common2三级交集检查所使用的**同一份**`R60_QD20_COMMON2_SUPABASE_RECOVERY_PRIVATE.json`，不自行造JSON或重跑Supabase。若JSON及Schema均通过才真正比较Common2×R45来源故事。已有R50排除/机械检验PASS保持不变，`train_admitted=0`。
