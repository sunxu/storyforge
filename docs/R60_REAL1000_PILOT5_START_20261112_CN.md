# StoryForge R60｜冻结真实1000候选：首批5条精筛启动手册

日期：2026-11-12  
执行分支：`r60/common2-cpu2-owner`（仅 Owner 这条隔离工作线；其他 Agent 的并行分支不合并/覆盖）  
目标：从已经冻结的1000条技术候选中构建高质量中文互动小说 Positive Gold 候选；**不启动SFT、不修改现有Gold**。

## 1. 已证实的事实与尚缺证据

- 扩样已完成：seed 6 + 扩样 994 = 1000；现有20个私有批次页与源签名必须只读复核，不再扩样。
- 首批5条、每批最多25条的双模型质量筛选器已经存在：`experiments/r58_quality/r60_real_quality_batch.py`。
- Common2 两条实验样本真实Qwen3.8 Swift Collator + last Assistant label mask技术验收已通过，原始HF SAFE回执独立验收2/2 PASS；**与这1000条文学质量审核是两条不同证据链**。
- 尚无首批5条的正式双审 SAFE 回执；Reviewer A/B具体模型、endpoint和私有外发范围尚待Owner本机核对；不得编造PASS。
- 沿用Quality-v1六维最低分：chinese_prose=4、character_consistency=4、npc_initiative=3、player_agency=4、rule_fidelity=4、narrative_continuity=4，以及serious_player_agency、hard_fact_or_ban、safety_exclusion三严重旗标。严禁因缺历史世界设定而猜测规则、别名、来源。
- 旧Gold72/Development/Locked Regression、Severe10和既有R60 A/B/C/GLM评审只用于校准与历史对照，不能作为本轮自动裁决。

## 2. PILOT-0：立即执行的Owner本机只读预检

下列命令只检查本地代码与冻结1000池，不调用模型、不提交HF Job、不读取R50正文、不做数据库写入。**不使用`set -x`**，不要把路径/令牌/正文贴到Issue。

```bash
set -euo pipefail
set +x
umask 077
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner

PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
BASE="$HOME/.local/share/storyforge/r60/private"
EXPAND="$BASE/r60-expand-first-600"
QUALITY="$BASE/r60-quality-first-1000"

"$PY" experiments/r58_quality/r60_real_expand_private.py inspect \
  --output-dir "$EXPAND"
"$PY" -m pytest -q tests/test_r60_real_quality_batch.py
```

若测试文件路径不存在，请只检查仓库已有对应测试，不要为使流程通过而删除旧测试；也不要改写冻结输入。只有`EXPANSION_TARGET_REACHED__NOT_ADMITTED`且`total_candidates=1000`才能继续。

## 3. PILOT-5：Owner确认两个真实Reviewer后的5条实审

真实调用前先核对：
- 两个**已安装或可用**的不同模型ID、endpoint，以及是否完全独立的无共享评分上下文；不能把同一模型不同别名冒充双独立审核。
- 若是本机OpenAI-compatible接口（`127.0.0.1`），无第三方私有外发；若是远端HTTPS，逐一明确模型供应方与5条私有User/Assistant上下文外发授权才可加`--allow-remote-review`。
- 只允许审核冻结池前5条，共10个独立模型请求；现有工具的`init`把两个模型配置冻结入新建0700目录，`advance`写入0600逐案不可覆盖回执。不在CLI中写API Key；如需要，环境变量`R60_REVIEW_A_KEY`/`R60_REVIEW_B_KEY`本地配置。
- 只能在Owner确已核对独立性后使用`--owner-attest-independent-ai`；它不等于人类盲审或模型训练谱系的密码学独立性。

下方以**仅本机模型**为执行模板，必须将两个`MODEL`值替换为已核实的不同模型，不能直接假定示例已经安装：

```bash
set -euo pipefail
set +x
umask 077
cd ~/workspace/storyforge-r60-4router-review
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
BASE="$HOME/.local/share/storyforge/r60/private"
EXPAND="$BASE/r60-expand-first-600"
QUALITY="$BASE/r60-quality-first-1000"

# 必须先通过本地模型可用性检查，并赋值两种真实的独立模型
: "${R60_PILOT_MODEL_A:?先设置本机实际可用的Reviewer A模型}"
: "${R60_PILOT_MODEL_B:?先设置本机实际可用的Reviewer B模型}"
test "$R60_PILOT_MODEL_A" != "$R60_PILOT_MODEL_B"
test ! -e "$QUALITY"

"$PY" experiments/r58_quality/r60_real_quality_batch.py init \
  --expand-dir "$EXPAND" --output-dir "$QUALITY" \
  --endpoint-a http://127.0.0.1:11434/v1 \
  --model-a "$R60_PILOT_MODEL_A" \
  --endpoint-b http://127.0.0.1:11434/v1 \
  --model-b "$R60_PILOT_MODEL_B" \
  --json-mode

"$PY" experiments/r58_quality/r60_real_quality_batch.py advance \
  --output-dir "$QUALITY" --max-cases 5
"$PY" experiments/r58_quality/r60_real_quality_batch.py inspect \
  --output-dir "$QUALITY"
```

已有`QUALITY`目录时，**不要重跑init/覆盖**；先`inspect`判断现有进度及源签名，必要时使用新独立目录进行另一轮实验（不能冒充对同一冻结批次的继续审核）。未确认Reviewer身份或外发范围前，只执行PILOT-0。

## 4. PILOT-5结论检查与升级门禁

汇总`cases_reviewed=5`，保存Reviewer A/B模型身份、原始来源哈希及完整逐案私有审核回执；对每案进行双方是否确实审核同一个target/history的绑定核验。双审评分、严重旗标与严格引文要核实语义蕴含；文本子串匹配本身不证明严重越权。对分歧与上下文不足保持HOLD，不能以模型标记自动删除1000条数据。不要在GitHub公开每案内容、盲ID、私有hash或点评。

首批至少满足：双模型实际请求完成、输出Schema有效、未发生断点覆盖、记录Reviewer独立性限制、对严重旗标误报/漏报完成小批复核。**不是要求5/5 PASS**，任何0 PASS都不自动证明池质量差。

## 5. PILOT-25与后续1000精筛

PILOT-5经Owner确认后，单独批准`advance --max-cases 25`处理**接下来的25条**，随后立即inspect/抽查；不得未经确认就运行4轮25或全量循环。累计30条校准合格后再制定最多每批25条的剩余970条逐批审核计划，并核对复核成本/Reviewer一致性/误判率。

只有六维内容达标、严重旗标已核实、无未解决HOLD的逐案记录才可成为`POSITIVE_CANDIDATE_AI_ONLY`。要成为`POSITIVE_GOLD_OWNER_APPROVED`，还必须按Owner确认流程独立裁决与冻结；训练数据准入另行要求R50元数据排除、世界设定隔离、历史上下文、模板兼容、世界Split和训练输入审计。

## 6. 权限与可复用性

本任务只批准首批5条**准备工作与本地只读预检**。没有确定的两个本机模型，不访问私人正文外部推理端点；远端模型外发必须Owner另行明确批准提供方及范围。正式`train_admitted=0`、`quality_v1_admitted=0`、`gpu_started=false`；Common2历史HF CPU Job不得重复提交。任何实际Reviewer调用是否发生、得分多少，以Owner Mac SAFE回执为准。

现有工具只读技术池、逐条续审，不因上一阶段技术PASS而自动提升任何文学质量标签。此文件是当前阶段执行基线；旧任务书中“不得启动1000条审核”应理解为当时校准阶段限制，不再阻止PILOT-0准备，但不自动授权远端外发或整批1000实审。
