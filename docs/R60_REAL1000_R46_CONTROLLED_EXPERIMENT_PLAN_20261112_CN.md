> **2026-11-12 技术执行下一步（覆盖历史Mac本地无Snapshot的旧建议）：** Owner Mac没有已固定revision的Qwen3.8本地Tokenizer快照，按项目`AGENTS.md`及`skills/storyforge-hf-jobs/SKILL.md`，**模型特定Tokenizer和实际ms-swift只能在HF CPU执行**；Mac只准备/同步私有Stage。新增[Wrapped HF CPU Quality Pipeline任务书](R60_COMMON2_WRAPPED_HF_CPU_QUALITY_PIPELINE_20261112_CN.md)、独立Stage/CLI/Worker/回执校验及仅合成数据的Actions CI。该代码待Owner Mac+CI验收，**没有在本轮提交HF Job、没有新System版Collator真实PASS**，D1-D5仍待Owner签批且train_admitted0。不得复用此文先前要求Mac本地下载Snapshot或本地调用Swift的过时建议。

# StoryForge R60 — 以R46为参照的Real1000 SFT单变量实验计划（2026-11-12）

**状态：仅静态配置建议与质量准入设计，不是已启动或获批训练。** Owner独立分支 `r60/common2-cpu2-owner`；不修改历史R46、R50、R54、Common2冻结的私有数据，不提交HF Job、GPU或模型推理。

## 主线目标

冻结R46已验证的**模型、QLoRA训练超参和监督原则**，使下一轮Real1000增加的优质数据可以被合理评估。禁止把系统提示词、聊天模板和训练样本同时改掉，却把质量变化归因于数据。

历史R46：Qwen3.8-27B pin revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`，原R45 49 Train/15 Validation，一轮QLoRA、7个optimizer step、A100，已有工程通过但未质量晋升的adapter；`docs/plans/StoryForge_v03_Test_and_Training_Plan_20261014.md`与`docs/evidence/V03_R54_GPU_SFT_NO_SUBMIT_PREPARATION_20261021.md`记录它的超参基线。当前仓库`configs/qwen38-27b-qlora-v0.1.yaml`与这些**拟冻结超参**一致，但本次对照器只校验这份Git配置，**不能冒称已重放R46远端实际命令、实际System或实际模板的全部字节**。

## 实施结果：参数提案 + 拒绝漂移的离线守卫

- 非可执行配置合同：`configs/r60_real1000_r46_controlled_sft_policy.json`，无训练集路径、输出路径、GPU授权或执行入口。
- 静态只读校验器：`scripts/r60_real1000_r46_parameter_control_cpu.py`，仅标准库读取公开JSON与历史baseline YAML的标量字段，不读取Common2/R50私有材料或远端状态。
- 合成回归：`tests/test_r60_real1000_r46_parameter_control_cpu.py`，检查rank/lr等漂移、错误训练许可、虚假模板等价声明、未知异常泄露及参考YAML重复键。
- 成功状态 `R60_R46_PROPOSED_HYPERPARAMETER_CONTROL_PASS__SYSTEM_TEMPLATE_ADMISSION_HOLD`，只表示**配置提案与仓库baseline静态参数一致**，不表示已训练、准入、Owner已批准System/模板策略。

### 冻结参数

| 分类 | 冻结值 |
|---|---|
| 模型 | `Qwen/Qwen3.8-27B`，固定revision |
| ms-swift / transformers | `4.5.3` / `5.16.1` |
| QLoRA量化 | 4-bit NF4、BF16、double quant |
| LoRA | rank64、alpha128、dropout0.05、target all-linear |
| 长度/损失 | `max_length=16384`、`loss_scale=last_round` |
| prefix策略 | `disable_ignore_empty_think=true`、`add_non_thinking_prefix=false` |
| batch / 累积 | train/eval batch1、梯度累积8 |
| 学习率/轮次 | 5e-5、1 Epoch、warmup_ratio 0.05 |
| 额外 | gradient checkpointing开启 |

`qwen3_8` 是当前Common2 CPU2真实已测试的**训练模板候选**，在原v0.1 YAML中没有显式声明`template_type`；旧R46远端tokenizer/template的完全等价性未重放，不能把模板参数也当作已经证明的历史常量。

## 关键控制：当前还不是严格“只改训练数据”的实验

1. **R46 System vs R60实验输入：** R46训练采用通用System；Common2当前只存真实11条历史加最终Assistant，`system_prompt=None`，没有历史实际Sent Prompt。直接拿R60 Common2进行训练会同时改变System输入合同。**不能为了与R46一致而自行虚构System文本**。
2. **模板与reasoning：** Common2固定Swift `qwen3_8`、`last_round`、`max_length=16384`、`add_non_thinking_prefix=False`的实测Collator。Native tokenizer长度分别比Swift多66个Token；旧R46实际模板等价未验证。训练侧可以拟采用Swift为规范，但与推理部署输入边界仍待Owner裁决。
3. **数据不同：** R46已有正式训练/验证49/15，Common2仅2条实验候选且`quality_v1_admitted=0`、`train_admitted=0`。两条不足以独立进行与R46有意义的训练效果比较，更不能把它当成新的验证集。后续需新增更多独立质量PASS且故事级拆分的Real1000数据。
4. **若目的是因果比较数据质量：** 应在Owner批准后预先冻结**统一且可证的System/消息模板**，并在两套数据上采用相同训练设置；必要时重跑对照基线，否则只能说“与历史R46参照结果比较，存在混杂因素”。旧R46结果绝不覆盖，R50原始保护集不可入训或调参。
5. **GPU之前：** 完成相关世界语义关联审查、衍生输入使用政策、部署模板兼容、Train/Val真实故事拆分、Owner发布批准及运行制品哈希绑定。静态配置PASS不会放宽任何Gate。

## 下一步（从不重复的已完成证据开始）

- **阶段A（本轮交付，待Owner Mac检验）：** 执行静态对照器与合成单测；不重新做R45/R50机械来源扫描或Common2 CPU2云端检查。
- **阶段B（Owner决策）：** 在`docs/R60_COMMON2_OWNER_SFT_ADMISSION_DECISION_20261112_CN.md`明确D1衍生训练输入和D2 Swift训练侧模板策略；D3核对实际部署模板；D4仅审核与Common2及被保护世界有关的语义证据。无证据继续HOLD。
- **阶段C（数据建设）：** 复用冻结Real1000、已选Wave40源位置及六维审稿流程增大质量PASS数据池，保持原始目标、私有源键和审稿证据；独立训练/验证按世界分配，不把候选数当作已准入数。
- **阶段D（独立授权之后）：** 再固定唯一GPU训练版YAML、System/Template/数据SHA和比较协议，提交前先实际ms-swift CPU/标签及全量准入审计；Owner另行授权训练/GPU。
 
## Owner Mac离线验收

```bash
set -euo pipefail
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-tests/bin/python"
"$PY" -m pytest -q tests/test_r60_real1000_r46_parameter_control_cpu.py
"$PY" scripts/r60_real1000_r46_parameter_control_cpu.py
```

预期`R60_R46_PROPOSED_HYPERPARAMETER_CONTROL_PASS__SYSTEM_TEMPLATE_ADMISSION_HOLD`，`hyperparameters_checked=22`，所有训练/部署/语义准入和GPU标志保持false、训练准入0。若HOLD，仅修正错误的配置或代码，不修改旧R46、Common2原始证据或已冻结数据。

## 2026-11-12 Owner Mac真实验收 + 合成测试分支覆盖修正

Owner Mac已返回真实静态参数检查SAFE：`status=R60_R46_PROPOSED_HYPERPARAMETER_CONTROL_PASS__SYSTEM_TEMPLATE_ADMISSION_HOLD`、`hyperparameters_checked=22`、`hyperparameters_equal_to_baseline=true`、`reason_code=STATIC_BASELINE_MATCH_ONLY`、`train_admitted=0`。这是**真实通过的静态配置一致性结果**，不是R46远端System/模板或实际训练的等价证明。

同次pytest为6通过、1失败：`test_unknown_private_runtime_error_is_never_reflected`用19字节无效JSON代替配置，检查器按设计先因`<100`字节触发`POLICY_SIZE_HOLD`，未进入预期的JSON解析/通用HOLD分支。仅修正合成测试：使用大于100字节但语法仍无效的JSON输入，以验证通用HOLD与私有文本抑制；另新增过短输入返回`POLICY_SIZE_HOLD`的独立测试。**不修改安全检查器、不放宽准入、不修改22项训练参数、不提交GPU/HF Job。** 新pytest共8项，尚待Owner Mac复测；不可提前声称8/8 PASS。

重跑命令：
```bash
set -euo pipefail
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-tests/bin/python"
"$PY" -m pytest -q tests/test_r60_real1000_r46_parameter_control_cpu.py
```

## 2026-11-12 System差异直接来源证明（待Owner本机只读验收）

本轮读取了历史公开构建器`scripts/v02_r46_build_dataset.py`的真实实现：它在原始R45 49/15训练源中严格要求`messages[0].role == "system"`、末两条`user → assistant`、除最后Assistant外所有消息`loss=False`。对应目前Common2的`experiments/r58_quality/r60_common2_sft_cpu_template_audit.py`：11条交替User/Assistant历史 + 最后Assistant，`system_prompt=None`、`world_card=None`，无`system`消息。这确认了两个来源合同的**可观察设计差异**，但仍不能由代码静态逻辑推出每个已冻结原数据行实际合约通过；更不能证明R46实际推理部署System/Swift模板与R60一致。

新增`scripts/r60_r46_common2_system_contract_cpu.py`，利用此前已真实SHA核验的R45原始49/15文件以及现有Common2实验JSONL+manifest，仅在本机验证三份冻结文件的role结构与loss约束，输出**只含聚合数量**的SAFE。它不会打印任何system文本、story ID、原始hash、目标文本或文件路径，不重算Common2×R45/R50的来源交集，不启动HF/GPU，也不修改冻结文件。返回`R46_R60_SYSTEM_ROLE_CONTRACT_DIFFERENCE_CONFIRMED__TRAIN_HOLD`意味着差异已证实，**不是系统提示词/部署模板已达成一致**。

Mac命令：
```bash
set -euo pipefail
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-tests/bin/python"
"$PY" -m pytest -q tests/test_r60_r46_common2_system_contract_cpu.py
R46="$HOME/.local/share/storyforge/r46-primary-evidence-r46-20261014T070529Z-248172"
"$PY" scripts/r60_r46_common2_system_contract_cpu.py \
  --r45-original-train "$R46/source-data/train.jsonl" \
  --r45-original-validation "$R46/source-data/validation.jsonl" \
  --common2-input-dir "$HOME/.local/share/storyforge/r60/private/r60-real1000-common2-sft-experimental11-v1"
```

预期原R45总计49+15=64条包含首条System，Common2两条System为0。以上是**预期**，仅在Owner真实SAFE到达后将该数量标为实测；测试与真实运行都未在本Agent的Mac上执行。

**决策建议：** 保留Common2原始无System的实验输入不可变，不声称与R46是严格单变量比较。后续若想严格只改变训练数据，则必须独立定义并签批统一的**新训练输入规范**，清楚标记后补的通用训练System为`EXPLICIT_NEW_TRAINING_WRAPPER`，不能声称它是历史实际Sent Prompt；并在相同规范下构建参照数据和新的Real1000训练数据，独立版本和新SHA。这属于未来D1/D2/D3的Owner决策和新实验，不可静默改原Common2文件或当前正式训练准入0。

## 2026-11-12 Owner真实System合同核验PASS：新旧输入结构确实不同

Owner Mac已实际执行`scripts/r60_r46_common2_system_contract_cpu.py`。SAFE状态：`R46_R60_SYSTEM_ROLE_CONTRACT_DIFFERENCE_CONFIRMED__TRAIN_HOLD`，`stage=CONTRACT_COMPARISON`、`reason_code=HISTORICAL_SYSTEM_PRESENT_CURRENT_SYSTEM_ABSENT`；`r45_source_sha_verified=true`、`r45_train_rows=49`、`r45_validation_rows=15`、`r45_rows_with_initial_system=64`；`common2_input_sha_verified=true`、`common2_rows=2`、`common2_rows_with_system=0`、`historical_vs_current_system_contract_equal=false`。既有R46实际System文本是否等价、真实运行模板等价均未证，`training_input_policy_approved=false`、`train_admitted=0`。未访问数据库/HF/GPU、无私有值输出。

**因此R60和R46当前不能声称只改变训练数据。** 已排查的新旧System角色差异已经PASS，不再重复扫描同一冻结文件。下一步不是原地改写Common2或假造历史Sent Prompt，而是Owner决定是否在独立训练版本中引入`EXPLICIT_NEW_TRAINING_WRAPPER`通用System（其文本、SHA、版本必须另行确定）及统一推理端模板；如要形成严格“只变数据”的比较，历史R46旧Adapter只作为非同输入合同参考，需要使用新统一规范构建的对照条件并在另行授权后训练。此处不批准D1/D2/D3、正式数据入训或GPU。

## 2026-11-12 统一System来源已找回：复用R27/R52冻结449字节指令（新实验包装器，Owner真实预检待执行）

查得原有权威证据`docs/evidence/V03_R52_NO_CARD_INPUT_DESIGN_APPROVAL_20261021.md`：冻结无角色卡通用System来自原R27私有档案，在117条R27行中一致，精确UTF-8 **449字节**、SHA256 `5e1b28cd9181f5d334f1f10a54a251f9255e655a3e597519c7cfcc530d8c5e83`。**文本末尾无额外换行**，本轮已用该SHA核对末尾换行的影响并修正代码。R52已有Owner授权的是R52/v0.3的**实验输入设计**，其状态为`OWNER_APPROVED_INPUT_DESIGN_ONLY__NO_TRAINING_ADMISSION__NO_GPU_AUTHORIZATION`；它不是R60 Common2两条直接正式入训的批准。R46历史R45原数据64条均首条System已由Owner真实核实，但R46每一条System原文字节是否等于此449字节尚未在本次直接比较，**不能由R27/R52出处或R45 System角色存在推断已逐字相同**。

新增只读内存`scripts/r60_common2_generic_system_wrapper_preview_cpu.py`，可接受已冻结Common2原11历史+目标2行及原manifest，先验证原始SHA、role/目标合同，然后**只在内存临时拟加入**上述精确冻结System（`loss=false`），只监督最后Assistant原回复（`loss=true`），不写任何实际训练文件、私有故事、system衍生版本或新manifest。运行结果只含SAFE聚合（2个拟包装案例、2条拟新增System等），保留`train_admitted=0`、`new_swift_collator_verified=false`、`deployment_template_compatibility_verified=false`、`r60_input_design_approved=false`。不修改Common2源JSONL、不虚称历史`ACTUAL_SENT_PROMPT`。这也不是正式的训练侧新输入Token/Mask复审；**任何正式创建新包装版数据都必须先D1/D2签批，随后对新真实字节重新执行CPU Collator/label完整验收**。

Mac只读命令：
```bash
set -euo pipefail
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-tests/bin/python"
"$PY" -m pytest -q tests/test_r60_common2_generic_system_wrapper_preview_cpu.py
"$PY" scripts/r60_common2_generic_system_wrapper_preview_cpu.py \
 --input-dir "$HOME/.local/share/storyforge/r60/private/r60-real1000-common2-sft-experimental11-v1"
```

预期`COMMON2_GENERIC_SYSTEM_IN_MEMORY_WRAPPER_PREVIEW_PASS__TRAIN_HOLD`、`system_text_pin_verified=true`、`original_input_sha_verified=true`、`wrapped_examples=2`、`synthetic_system_messages_added=2`、`files_written=0`、`train_admitted=0`。**尚待Owner真实SAFE，不可先声明预览PASS**。本轮不重复R45/R50故事/heldout隔离、无HF、无GPU、无推理。

## 2026-11-12 Owner Common2冻结System内存预览真实PASS → 新包装输入的实际离线CPU验收待执行

Owner Mac回执`COMMON2_GENERIC_SYSTEM_IN_MEMORY_WRAPPER_PREVIEW_PASS__TRAIN_HOLD`：`system_text_pin_verified=true`、`original_input_sha_verified=true`、`wrapped_examples=2`、`source_messages_preserved=true`、`original_targets_unchanged=true`、`supervision_only_final_assistant=true`、`synthetic_system_messages_added=2`、`files_written=0`。**这一内存输入结构已核验，勿重复。** 此前已通过的是**未添加System**的Swift Collator，两者绝对不可互换认定。

已新增离线程序`scripts/r60_common2_wrapped_system_cpu_audit.py`及合成测试`tests/test_r60_common2_wrapped_system_cpu_audit.py`。它重用原Common2冻结JSONL+manifest、R27/R52精确449字节System pin、现有HF Qwen3.8实际Tokenizer/ms-swift 4.5.3模板+R18 last-round label校验逻辑，**全程内存包装**并对包装后的两个实例重新调用**真实**ms-swift Collator。全部失败只输出SAFE固定阶段和固定HOLD，不打印私有原文、哈希或Token IDs。它仅使用Owner**已经在Mac本地存在**的模型tokenizer/config快照，强制环境Offline，避免模型权重/GPU/新HF Job和训练输出文件。合成测试只是代码级验证，Mac真实模型/私有输入结果**尚待验收**。

Mac本地先检查是否有现成Pinned Snapshot（模型revision：`1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`）。**不要为本次任务在线下载27B权重**。只有确实存在带tokenizer.json/tokenizer_config.json/config.json的本地快照才运行；缺少则标`LOCAL_SNAPSHOT_HOLD`并保留技术未验，不得擅自发起HF Job。

```bash
set -euo pipefail
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-tests/bin/python"
"$PY" -m pytest -q tests/test_r60_common2_wrapped_system_cpu_audit.py

PIN="1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
# 下列SNAPSHOT须填写Owner已经有的真实本地快照，不要凭空设目录：
SNAPSHOT="/已存在且路径含$PIN的本地Qwen3.8快照目录"
if [ -f "$SNAPSHOT/tokenizer.json" ] && [ -f "$SNAPSHOT/tokenizer_config.json" ] && [ -f "$SNAPSHOT/config.json" ]; then
 "$PY" scripts/r60_common2_wrapped_system_cpu_audit.py \
   --input-dir "$HOME/.local/share/storyforge/r60/private/r60-real1000-common2-sft-experimental11-v1" \
   --snapshot "$SNAPSHOT"
else
 echo "LOCAL_SNAPSHOT_HOLD: existing pinned tokenizer/config snapshot not found; no downloads/jobs"
fi
```

预期（仅当真实运行成功后才能宣称）`COMMON2_WRAPPED_SYSTEM_ACTUAL_CPU_COLLATOR_PASS__TRAIN_HOLD`，返回包装后Tokenizer/Swift真实计数及最后Assistant监督token计数，不包含任何正文。即使此技术门禁PASS，`r60_input_design_approved=false`、`deployment_template_compatibility_verified=false`、`semantic_world_isolation_verified=false`、`train_admitted=0`保持不变。统一训练规范的D1/D2政策决策、语义隔离及新实验授权仍需Owner书面许可。
