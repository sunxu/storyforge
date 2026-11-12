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
"$PY" -c 'import ast, pathlib; files=[pathlib.Path("experiments/r58_quality/r60_real_quality_batch.py"),pathlib.Path("experiments/r58_quality/r60_real_ai_dual_review.py")]; [ast.parse(p.read_text(encoding="utf-8")) for p in files]; print("REAL1000_BATCH_SOURCE_PARSE_PASS")'
```

上述源码解析是PILOT-0最小无模型预检，不代表全量单测/CI已通过。不要改写冻结输入。只有`EXPANSION_TARGET_REACHED__NOT_ADMITTED`且`total_candidates=1000`才能继续。

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

## 7. 2026-11-12 DeepSeek历史评审追溯与远端Reviewer授权更新

Owner指出此前遗漏2026-11-11的**20条Qwen+DeepSeek与Claude+Codex对照试评**。以下为既有会话中的Owner SAFE结案记录，并非当前Agent重新打开私有文件或重新计算评审：
- Qwen使用阿里云百炼`qwen3.7-flash`；DeepSeek使用**官方**`deepseek-flash`（曾口头称DeepSeek V4.1 Flash；以实际API响应model字段为准）。**均不同于历史HF H200 Qwen3-32B / GLM-4-32B实验**。
- 最终20条范围，40个模型审核槽位中34份有效、14/20完整配对、6份缺失；Qwen有效18/20（PASS9/HOLD0/REJECT9），DeepSeek有效16/20（PASS5/HOLD10/REJECT1）。此前中间快照DeepSeek15/20、HOLD9，不得误当最终值。最终SAFE状态`QD20_CONSERVATIVE_QUALITY_SCREEN_CLOSED__TRAIN_ADMISSION_HOLD`，训练准入0。
- 新Qwen+DeepSeek配对双PASS4；旧Claude+Codex配对双PASS3；共同双PASS2；新组合独有2、旧组合独有1。数量不是跨模型评审质量真值。
- 随后独立盲审这3条争议双PASS：新组合独有2条为HOLD1/REJECT1（PASS0），旧组合独有1条HOLD1（PASS0）；全部PASS0/HOLD2/REJECT1。独立性仅为自证，尚未确立质量真值；严重问题判定不能凭双PASS多数票。
- DeepSeek存在输出有效率16/20与快照重放仍失败的工程历史；必须把传输、JSON/Schema、严重标记一致性、严格引文和语义支持分别考核。Claude+Codex与Qwen+DeepSeek各自不是已证实最优的生产双Reviewer组合。

**Owner本轮明确允许所有私有数据外发**：对当前StoryForge真实1000候选质量审核工作线，私有样本可以发送到远程Reviewer API；无需再次索取同一“是否允许外发”许可。现有`r60_real_quality_batch.py`仍要求调用时显式`--allow-remote-review`以保证参数审计；实际具体endpoint、模型ID、密钥、模型可用性与工作者盲审隔离仍需核验；私有样本内容、密钥、模型原始输出不写入GitHub/SAFE公开日志。**这不等于立即执行全部1000条、认可远端模型训练数据用途、改变R50/世界隔离门禁或授权SFT/GPU**。

### 选型变更

先不要把初版Qwen3-32B+Claude Opus 5.5写成“生产双审已定”。首批5条应比较**不同提供方**的历史表现：建议优先把`Claude Opus 5.5`及官方`deepseek-flash`作为候选A/B（Claude此前20/60校准Advisory可用、DeepSeek已有20条试评但16/20有效）；`qwen3.7-flash`与Codex作为分歧复核/替补；原Qwen3-32B、GLM-4及GLM-Z1保留历史独立训练/模型选型实验，不混同模型ID。实际两位Reviewer仅在首批同源5条中报告模型版本、全响应成功率、严标语义漏误报、证据可核性、相互独立性后确定；如果DeepSeek首批出现不完整回复，停止扩批并定位工程故障，不能补出假评分。

**重要兼容性**：现有`r60_real_ai_dual_review.py`采用`messages[0].role=system`、`temperature=0`、可选`response_format=json_object`；此前Claude 4Router的Opus 5.5请求曾要求顶层`system`字段，不能假定这个旧客户端能原样调用该代理。开始私有模型外发前，先用无私人内容的合成探针验证Claude/DeepSeek各自endpoint及模型专属请求协议、真实模型身份与JSON结构；若不兼容，修改薄适配层并合成测试/CI后再使用原1000池。历史DeepSeek成功API不证明当前所有协议相容。

