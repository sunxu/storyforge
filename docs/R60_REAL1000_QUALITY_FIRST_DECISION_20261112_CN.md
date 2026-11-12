> **2026-11-12 Real1000主线参数对照补充：** 新增[对照R46的受控实验计划](R60_REAL1000_R46_CONTROLLED_EXPERIMENT_PLAN_20261112_CN.md)、不可执行22项QLoRA参数合同与静态漂移守卫。保持R46风格rank64、学习率5e-5、1Epoch、last_round、max16384；**R46真实System与Common2无System仍是混杂因素，实际训练/部署模板等价未证**。此为拟议实验条件，不是数据入训/GPU授权；请先完成Common2 D1-D4必要裁决，再扩至Real1000优质候选。

> **2026-11-12 当前最高优先级（覆盖下述11月12日早先CPU故障与候选准备旧状态）：** Common2两条实验SFT输入和原有HF CPU2 SAFE独立证据真实PASS；Common2对R45 Train49/Val15与R50原始50条的精确来源隔离真实PASS。现在进入 [Common2 Owner SFT训练准入决策书](R60_COMMON2_OWNER_SFT_ADMISSION_DECISION_20261112_CN.md) 的D1-D5决策：衍生输入资格、Swift训练模板、部署模板兼容、两条候选相关世界语义证据、独立发布授权。**这不是训练批准；quality_v1_admitted=0、train_admitted=0、GPU/SFT没有启动。** Wave40冻结选样仍待正式质量审核，不应超过Common2首批准入决策优先级。禁止按本文较旧的HF镜像错误记录重复提交Jobs。

# StoryForge R60 — Real1000优质SFT数据主线决策（2026-11-12）

## 2026-11-12 权威交接状态（优先于本文所有较旧操作建议）

**最新Owner实际回执是 `R60_COMMON2_CPU2_IMAGE_FIX_HOLD` / `SAFE_REMOTE_OR_RUNTIME_HOLD`，不是“新Job成功提交”。** 已知首次HF CLI Job `6af53990ab34849891aecb44` 因镜像参数 `docker.io/--name` ERROR；随后SDK镜像修复仍HOLD，不能确认是否另建Job。**禁止直接执行本文件下文的旧 `submit` 或SDK重试命令、删除重试标记或重传原stage。** 接手者必须先只读运行`scripts/r60_common2_hf_cpu_image_probe.py`、核对HF Job真实列表和标记。权威任务书：[R60下一Agent接手任务书](R60_COMMON2_NEXT_AGENT_HANDOFF_20261112_CN.md)；[可复制启动提示词](R60_COMMON2_NEXT_AGENT_START_PROMPT_20261112_CN.md)。Common2质量PASS2、实验输入2、Tokenizer2552/4048 PASS；**Collator真实验收未知/未通过、R50全量隔离HOLD、train_admitted=0、GPU禁止。** Wave40已选40条位置，但盲审暂停，生产留证因无权限DEFERRED。


## 2026-11-12 最新执行纠偏（覆盖本文其他所有近期优先级）：先完成Common2两条SFT可用性验证

用户已确认：**不得因为已准备Wave40，就将40条独立盲审排在已有2条质量PASS候选训练输入验证之前。** 当前P0唯一目标：从Common2已验证2/2独立六维PASS、103/243条真实持久化历史和冻结Real1000精确目标，构造最小真实来源绑定的**实验性SFT输入**，做CPU真实tokenizer/ms-swift collator和完整R50隔离验收。40条已成功选样的位置清单保持原样，后续盲审与扩大候选池转为第二优先级，不重新抽样、不覆盖、不删除。

本轮新增工作及Owner私有只读运行指令见：[R60 Common2两条优先端到端SFT验收任务书](R60_COMMON2_SFT_FIRST_END_TO_END_20261112_CN.md)。已有训练构造器`experiments/r58_quality/r60_real1000_common2_sft_experimental_cpu.py`强制检查源story/session/target绑定、独立原判决2PASS与冻结三消息一致性；以实验性的最近11条持久化历史（可对照7/23条）构造**无虚构System/世界卡**的两行私有样本。它不是原始实际生成请求，不做tokenizer/collator，也**不允许直接训练**，正式`train_admitted=0`、完整R50隔离仍HOLD，GPU未启动。


## 2026-11-12 Owner Wave40已实际选样PASS → 下一步独立盲审包

Owner Mac实际SAFE回执为`storyforge_r60_real1000_quality_wave40_safe_v1`、`QUALITY_WAVE40_LOCATORS_READY__NOT_REVIEWED`，`prepared=40`、`distinct_new_stories=40`、`sample100_story_overlap=0`、真实长度配额`300_499=20`、`500_999=16`、`1000_1500=4`，`quota_shortfalls_before_fill={}`，`database_accessed=false`、`model_inference_calls=0`、`gpu_started=false`、`train_admitted=0`。**只表示40条跨故事源位置已生成，不是40条文学质量PASS，也不是训练准入。**

已补齐`experiments/r58_quality/r60_real1000_quality_wave40_packets_cpu.py`以及`tests/test_r60_real1000_quality_wave40_packets_cpu.py`：再冻结核验源Real1000、Sample100并重新计算Wave40位置，独立打散盲审顺序；只将三条历史的角色/正文、目标回复放进盲审包，不含故事ID、源位置或旧模型投票。Owner私有交叉映射单独存放，独立决策模板六维字段保持既有冻结标准，所有审核状态为`NOT_REVIEWED`。拒绝篡改、不覆盖私有文件；新建0700输出目录3份0600文件；不访问DB、模型或GPU。

Owner Mac在已有工作树同步固定最新提交且确保工作区干净后运行（**不需要再次生成那40条**）：

```bash
set -euo pipefail
cd "$HOME/workspace/storyforge-r60-4router-review"
python3 -m pytest -q tests/test_r60_real1000_quality_wave40_packets_cpu.py
BASE="$HOME/.local/share/storyforge/r60/private"
SAMPLE_DIR="$BASE/r60-real1000-calibration100-v1"
WAVE_DIR="$BASE/r60-real1000-quality-wave40-v1"
# 从以前成功运行Wave40的 --expand-dir 参数复用真实路径；不可猜测、不可重新生成冻结源池
EXPAND_DIR="/Owner已经核实的Real1000冻结展开目录"
OUT_DIR="$BASE/r60-real1000-quality-wave40-blind-v1"
test -f "$WAVE_DIR/R60_REAL1000_QUALITY_WAVE40_PRIVATE.json"
test -f "$SAMPLE_DIR/R60_CALIBRATION_SAMPLE100_PRIVATE.json"
test -f "$EXPAND_DIR/R60_EXPAND_CONFIG_PRIVATE.json"
test ! -e "$OUT_DIR"
python3 experiments/r58_quality/r60_real1000_quality_wave40_packets_cpu.py \
  --expand-dir "$EXPAND_DIR" \
  --wave-dir "$WAVE_DIR" \
  --sample-dir "$SAMPLE_DIR" \
  --output-dir "$OUT_DIR"
```

预期`WAVE40_BLIND_PACKETS_READY__REVIEW_NOT_STARTED`。之后应当**仅分享独立盲审包**给审核者，不发送Owner私有crosswalk、既有模型判决或来源标识。审阅三消息不足以判断的世界设定必须标HOLD，不得脑补。模型审稿若需要外部API，另行获准之后才发起；先不发起任何模型调用，不启动GPU或训练。


## 当前唯一主线方向

**保留已经冻结并完成技术粗筛的Real1000，先做文学质量精筛、可复现上下文、R50完整隔离及CPU实际训练格式验收。**

2026-11-10之后的普通RolePlay消息与此前的1000条相比**没有已证实的质量或输入证据优势**。生产代码部署日不是实际留证开始日，留证相关六表在2026-11-12只读现场均为0条。当前没有RolePlay生产权限，因此不优先抓取11月10日之后的普通数据，不为了前向留证停下Real1000；未来**真正采集了完整有效请求且来源可认证**的数据才作为新的独立候选来源。原先“新留证数据优先”任务书保留历史记录，但它在当前状态下不代表新日期数据优先。本决定优先于之前所有相互矛盾的P0/P1顺序陈述。

## 事实与门禁

- Real1000：技术粗筛已有1000条真实完成Assistant目标、连续三消息上下文及可核对的数据库来源绑定。**粗筛PASS不等于文学质量PASS**，System、历史世界设定与R50完整隔离仍HOLD。
- Sample100：已冻结100条不同故事用于校准；Pilot20为其子集的盲审/模型对照，不复用既有Claude/Codex/Qwen/DeepSeek分数作为“真值”。Common2独立质量审查PASS 2/2，但不自动升格其他审稿或训练准入。
- Owner已在Supabase只读恢复Common2之前的持久化消息103/243条（共346），三消息源逐字对应2/2。它们不是原始LLM实际收到的全部历史；训练输入可以构造，但必须标`SOURCE_BOUND_DERIVED_CONTEXT`，不得标`ACTUAL_SENT_PROMPT_VERIFIED`。
- R50完整隔离、固定Qwen tokenizer、真实ms-swift collator与label mask仍为正式准入前的硬门槛；训练准入0，GPU0。
- 停止追查无权限的生产服务、重复观察空的留证表以及无差异价值的11月10日后新增日期批次。这些工作设为`DEFERRED_NO_PRODUCTION_ACCESS`。

## 接下来实际执行

| 优先级 | 工作 | 可验收结果 |
|---|---|---|
| MAIN-0 | 以Real1000冻结技术画像和既有Sample100、Pilot20的六维评审为基线 | 明确审查差异与哪些候选已有独立决策，不改既有盲审 |
| MAIN-1 | 扩大不同故事、不同字数段的样本质量精筛 | 使用新`r60_real1000_quality_wave40_cpu.py`准备下一批40个**私有源位置**；不重用冻结Sample100的任何故事、不采额外DB、不触发模型 |
| MAIN-2 | 使用Common2历史窗口比较6/12/24/48条消息；继续真实Qwen tokenizer/collator的CPU输入验证 | 明确训练构造System与截断策略；不声称恢复了当年请求 |
| MAIN-3 | 完整六维质量审核、跨样本去重、故事级划分、R50完整隔离 | 每条有独立证据的PASS/HOLD/REJECT与完整训练输入来源；最终按Owner明确准入 |
| DEFERRED | RolePlay生产真实留证、生产Worker与以后获证新数据 | 不阻塞主线；未来单独授权 |

### MAIN-1：新的可复用CPU候选准备（**尚未完成40条质量审查**）

已经新增`experiments/r58_quality/r60_real1000_quality_wave40_cpu.py`和`tests/test_r60_real1000_quality_wave40_cpu.py`。新工具通过`quality.frozen_pool`只读核对原Real1000，再用`sample.select`**逐项重新验证**现有冻结Sample100的位置及源池SHA；排除Sample100的**整组故事**，从余下条目中按哈希稳定排序、优先字数配额20/16/4，选择40个不同故事。如长篇字数段数量不足则透明记录配额缺口，用其他可用故事填满40，不伪造固定分布；不足40时整体HOLD。

输出为**新建且唯一**Owner私有目录中的0600 JSON，仅有相对位置、字数档和关联源池SHA；不包含原始正文、模型评价或故事ID。普通标准输出只有SAFE计数。不得把此输出当成质量决策或训练准入；下一环节需在受控私有环境创建**独立盲审包**，按既有R60六维Rubric逐条评估。

示例操作（使用Owner已有冻结Real1000展开目录及冻结Sample100目录；以已有工作树中实际路径为准）：

```bash
set -euo pipefail
cd "$HOME/workspace/storyforge-r60-4router-review"
python3 -m pytest -q tests/test_r60_real1000_quality_wave40_cpu.py
BASE="$HOME/.local/share/storyforge/r60/private"
# 用实际冻结目录替换下列路径，不要通过重新生成Sample100来替代冻结记录。
EXPAND_DIR="$BASE/r60-real1000-expanded"
SAMPLE_DIR="$BASE/r60-real1000-calibration-sample100"
OUT_DIR="$BASE/r60-real1000-quality-wave40-v1"
test -d "$EXPAND_DIR"
test -f "$SAMPLE_DIR/R60_CALIBRATION_SAMPLE100_PRIVATE.json"
test ! -e "$OUT_DIR"
python3 experiments/r58_quality/r60_real1000_quality_wave40_cpu.py \
  --expand-dir "$EXPAND_DIR" --sample-dir "$SAMPLE_DIR" --output-dir "$OUT_DIR"
```

**注意**：上面`EXPAND_DIR`与`SAMPLE_DIR`只示意命名，不保证与Owner机器实际目录一致；必须从现有Real1000已成功回执和冻结原始路径核对，不能猜路径运行。这段预检如找不到正确路径应当停止并核对，不应重建冻结池。

预计SAFE状态`QUALITY_WAVE40_LOCATORS_READY__NOT_REVIEWED`。没有Owner本机原始私有目录访问权限之前，本Agent**不能声明真实40条选样已执行或已质量PASS**。

## 训练阶段边界

真实历史文本可用于构建来源绑定的SFT实验输入，但不同故事世界卡、角色设定缺失时，不能凭空猜设定。按冻结六维标准判定语义事实，外显证据不足者HOLD。只监督最后目标Assistant，拒绝目标与历史消息顺序、身份冲突和不可分割的R50交叉污染。直至全部训练证据齐全，质量审稿PASS≠`train_admitted`。
