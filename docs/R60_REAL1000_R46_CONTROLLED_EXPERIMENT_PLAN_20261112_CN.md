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
