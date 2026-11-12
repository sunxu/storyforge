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
- 只允许审核冻结池前5条，共10个独立模型请求；现有工具的`init`把两个模型配置冻结入新建0700目录，`advance`写入0600逐案不可覆盖回执。不在CLI中写API Key；如需要，环境变量`R60_CLAUDE_KEY`/`R60_DEEPSEEK_KEY`本地配置。
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


## 8. 2026-11-12 可复用Claude/DeepSeek协议适配与首5执行入口（覆盖上文旧本地示例）

**唯一评分/审阅数据核心**仍为：
- `experiments/r58_quality/r60_real_ai_dual_review.py`：六维Rubric、JSON和严重标记验证、网络请求与私有正文。
- `experiments/r58_quality/r60_reviewer_transport.py`：不接触网络/私有数据的纯协议构造层，`openai-chat`（旧配置行为）、`claude-proxy-top-system`（顶层system，消息只含user，不强制temperature或json_object）、`deepseek-chat`（标准system消息，不强加Qwen采样）。不复制Rubric/门槛。
- `experiments/r58_quality/r60_real_quality_batch.py`：原生`init/advance/inspect`、两个Reviewer各自固定profile、只增0600回执/来源指纹/断点续审，老版配置缺省`openai-chat`，不静默迁移。
- `experiments/r58_quality/r60_reviewer_protocol_probe.py`：默认仅构造合成协议不发请求，`--execute`每次只发**1次完全合成**的中文故事给指定API，验证完整六维JSON + 严重标记合同，stdout仅SAFE，不读取真实1000池。

Owner已批准本任务的私有样本远程外发。以下新流程取代上文原先只以本地Ollama为例的接口和重复外发授权要求；但不授权全量1000自动执行、训练或其他数据操作。

### Step 1：本机离线测试

```bash
set -euo pipefail
set +x
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
"$PY" -m pytest -q \
  experiments/r58_quality/test_r60_real_ai_dual_review.py \
  experiments/r58_quality/test_r60_real_quality_batch.py
ruff check \
  experiments/r58_quality/r60_reviewer_transport.py \
  experiments/r58_quality/r60_reviewer_protocol_probe.py \
  experiments/r58_quality/r60_real_ai_dual_review.py \
  experiments/r58_quality/r60_real_quality_batch.py \
  experiments/r58_quality/test_r60_real_ai_dual_review.py \
  experiments/r58_quality/test_r60_real_quality_batch.py
```

### Step 2：配置实际API（仅在Mac环境设置值，禁止粘贴秘钥）

`R60_CLAUDE_URL`、`R60_CLAUDE_MODEL`分别对应**4Router经核实的OpenAI-compatible base URL和实际Claude Opus 5.5模型名**；`R60_DEEPSEEK_URL`、`R60_DEEPSEEK_MODEL`对应**DeepSeek官方OpenAI-compatible base URL与实际可用Flash模型ID**。切勿将历史模型别名当作已验证实时可用；应在Owner Mac本地核实。API密钥通过`R60_CLAUDE_KEY`和`R60_DEEPSEEK_KEY`从环境变量注入。所有远端必须HTTPS，不跟随重定向，不读取代理环境变量；`--allow-remote-review`必须显式传入。

```bash
: "${R60_CLAUDE_URL:?需要已核实的Claude代理base URL}"
: "${R60_CLAUDE_MODEL:?需要已核实的Claude实际模型ID}"
: "${R60_DEEPSEEK_URL:?需要已核实的DeepSeek官方base URL}"
: "${R60_DEEPSEEK_MODEL:?需要已核实的DeepSeek实际模型ID}"
: "${R60_CLAUDE_KEY:?Claude Key未在当前终端设置}"
: "${R60_DEEPSEEK_KEY:?DeepSeek Key未在当前终端设置}"

"$PY" experiments/r58_quality/r60_reviewer_protocol_probe.py \
  --endpoint "$R60_CLAUDE_URL" --model "$R60_CLAUDE_MODEL" \
  --protocol claude-proxy-top-system --key-env R60_CLAUDE_KEY \
  --allow-remote-review
"$PY" experiments/r58_quality/r60_reviewer_protocol_probe.py \
  --endpoint "$R60_DEEPSEEK_URL" --model "$R60_DEEPSEEK_MODEL" \
  --protocol deepseek-chat --key-env R60_DEEPSEEK_KEY \
  --allow-remote-review

# 前两次PASS仅证明本地能构造正确请求；下面每个--execute
# 才分别产生一次可能计费、但绝无真实私有故事的合成API请求。
"$PY" experiments/r58_quality/r60_reviewer_protocol_probe.py \
  --endpoint "$R60_CLAUDE_URL" --model "$R60_CLAUDE_MODEL" \
  --protocol claude-proxy-top-system --key-env R60_CLAUDE_KEY \
  --allow-remote-review --execute
"$PY" experiments/r58_quality/r60_reviewer_protocol_probe.py \
  --endpoint "$R60_DEEPSEEK_URL" --model "$R60_DEEPSEEK_MODEL" \
  --protocol deepseek-chat --key-env R60_DEEPSEEK_KEY \
  --allow-remote-review --execute
```

要求两个API的`REVIEWER_SYNTHETIC_API_PASS__NO_PRIVATE`；如HOLD，**不**执行`init/advance`。Claude代理不启用`--json-mode`，否则`CLAUDE_PROXY_JSON_MODE_UNSUPPORTED`；这保留了真实服务端协议限制，而非静默降级。

### Step 3：同源真实5条校准（必须两种合成API均PASS）

```bash
BASE="$HOME/.local/share/storyforge/r60/private"
EXPAND="$BASE/r60-expand-first-600"
QUALITY="$BASE/r60-quality-first-1000"
test ! -e "$QUALITY"

"$PY" experiments/r58_quality/r60_real_quality_batch.py init \
  --expand-dir "$EXPAND" --output-dir "$QUALITY" \
  --endpoint-a "$R60_CLAUDE_URL" --model-a "$R60_CLAUDE_MODEL" \
  --protocol-a claude-proxy-top-system \
  --endpoint-b "$R60_DEEPSEEK_URL" --model-b "$R60_DEEPSEEK_MODEL" \
  --protocol-b deepseek-chat \
  --allow-remote-review

"$PY" experiments/r58_quality/r60_real_quality_batch.py advance \
  --output-dir "$QUALITY" --max-cases 5
"$PY" experiments/r58_quality/r60_real_quality_batch.py inspect \
  --output-dir "$QUALITY"
```

不加`--owner-attest-independent-ai`，除非Owner已实际核验两Reviewer互不读取对方判断及身份；不加`--json-mode`因为Claude代理协议差异。每案双审严格同源；若输出协议无效、无精确证据、争议严重Flag或缺少世界设定，不得直接升级Positive Gold。**现有Reviewer JSON Schema还不提供三维严重证据的精确逐字引文，审计只能判定格式一致与局部文本质量；真正的严重问题语义结案依赖后续冻结Rubric v2.1证据级复核，不允许AI双PASS自动入训。**

旧`QUALITY`目录若已存在，先执行`inspect`，不得再次`init`覆盖，也不得将不同Reviewer混入已冻结的同一轮配置。首批5条SAFE回执到手后才决定是否扩批25；全量1000批量运行不得自动启动。

## 9. CI覆盖与阶段回执（2026-11-12）

新增`.github/workflows/r60-real1000-quality-review.yml`。其Push限定Owner隔离分支，PR仅在Reviewer相关代码或Workflow修改时触发；执行Python3.11、Ruff及`test_r60_real_ai_dual_review.py`与`test_r60_real_quality_batch.py`离线合成测试，不配置任何HF Job、API密钥、私有故事或远程端点。这个CI不是云端API可用性证明；真实合成probe仅能由Owner认证Mac受控执行。

质量架构总规范：`docs/standards/GOLD_QUALITY_PIPELINE_CN.md`。复用Skill：`skills/storyforge-real-quality-review/SKILL.md`；既有RolePlay SFT Skill已同步说明Common2技术验收关闭及REAL1000双Reviewer调用分层。当前所有代码仅通过GitHub提交，Owner Mac pytest/Ruff/实际合成Claude/DeepSeek端点验收仍需SAFE证据；在这些真实检查完成之前不宣称任何真实5条AI审阅。

### HTTP错误与SAFE定位

合成探针及正式双审采用同一套固定公开错误码：`MODEL_HTTP_400_HOLD`（API字段/格式拒绝）、`401/403`（凭证/权限）、`429`（速率限制）、`500/502/503/504`（服务端），此外还包括`404/408/413`。每个错误仅报告固定编号，不输出服务端响应正文、请求URL或原始提示词；未知错误保留`MODEL_TRANSPORT_HOLD`。失败时先核实API配置，不得把网络/格式失败算成文学质量REJECT，也不直接改写已持久化回执。

两个Reviewer都遭遇HTTP/网络故障时，`advance`在当前案例写盘前返回`BOTH_REVIEW_MODELS_UNAVAILABLE`，保留此前有效checkpoint，可在服务恢复后对**同一原有目录**继续；如果单侧失败，仍只留下一份真实审核和部分HOLD回执，不能覆盖或伪造缺失第二方。不要因为429/500而错误删除候选或调用新RUN_KEY绕过既有审阅记录。

## 10. DeepSeek官方QD20历史固定配置与2026-11-12环境变量改名

已直接核对源码`experiments/r58_quality/r60_real1000_qwen_deepseek20_live.py`：`DEFAULT_URLS["deepseek"]="https://api.deepseek.com"`，`DEFAULT_MODELS["deepseek"]="deepseek-flash"`，`KEY_ENV["deepseek"]="DEEPSEEK_API_KEY"`。历史请求包含`thinking={"type":"disabled"}`、`temperature=0`，与Claude 4Router顶层`system`不同。当前`deepseek-chat`薄适配器已复制**历史真实请求配置**，不将其当作新上线API兼容性已验证。

本轮真实1000审阅的新Owner命名环境变量：
- `R60_CLAUDE_KEY`：对应Claude Opus 5.5的4Router端点；
- `R60_DEEPSEEK_KEY`：对应DeepSeek官方端点。
- `R60_DEEPSEEK_URL=https://api.deepseek.com`；`R60_DEEPSEEK_MODEL=deepseek-flash`，均为历史代码明确的默认值。Owner需要先通过真实合成API probe验证当前可用性。

历史QD20运行器仍读取原来的`DEEPSEEK_API_KEY`，这是已冻结历史实验，不做无关修改。现行`r60_real_quality_batch.py`使用新环境变量，不再读取`R60_REVIEW_A_KEY/R60_REVIEW_B_KEY`。合成探针`--key-env`可显式指定；如省略会按profile选用新变量。不要把key写入URL、GitHub、SAFE。

## 10. Claude JSON探针诊断（2026-11-13）

已获得首轮SAFE：Claude的真实**合成**请求返回`MODEL_JSON_INVALID`，DeepSeek同轮`REVIEWER_SYNTHETIC_API_PASS__NO_PRIVATE`。两者均没有读取私有候选，质量PASS仍为0。**DeepSeek不再重复执行**。Claude原通用错误码混合了HTTP信封、模型内容和六维字段的多种故障，新版本`r60_real_ai_dual_review.py`仅在合成探针`diagnose_json=True`时细分公开常量：
- `MODEL_ENVELOPE_JSON_INVALID`：HTTP响应不能解析为JSON
- `MODEL_CONTENT_MISSING_OR_NONSTRING`：OpenAI-compatible响应没有`choices[0].message.content`字符串
- `MODEL_CONTENT_JSON_INVALID`：message.content存在但不是合法JSON
- `MODEL_REVIEW_SCHEMA_INVALID`：模型JSON无法通过冻结六维字段/类型/非空reason验证

只要Claude首次SAFE没有通过，禁止初始化真实批次或运行5条。Owner Mac更新代码和CI通过后，仅对Claude运行1次合成`--execute`，回传SAFE错误码；不得为诊断打印原始API响应、带密钥URL或任何私有正文。下一步依据分类决定修复代理映射还是模型输出约束，不放宽Quality Pipeline。真实评审默认行为及严重问题语义审核保持不变。

## 11. Claude复用历史成功客户端修复（2026-11-13）

针对之前Claude`MODEL_CONTENT_JSON_INVALID`，核查`scripts/r60_p2b_claude_review_client_v1.py`历史成功客户端，发现当前REAL1000审阅器与其不同：旧默认`max_tokens=12000`、新仅1600；旧支持content文本块列表、新只接收字符串；旧读取`finish_reason`、新未读取。现已在共享协议层恢复历史Claude请求预算12000，在共享响应层支持字符串和纯文本块列表、规范化唯一完整Markdown JSON围栏，并禁止`finish_reason=length/max_tokens`产出成功。所有内容仍通过冻结六维和严重标记校验，不修改Quality Pipeline门槛、不猜测响应正文、不改原始审核结果。

之前CLAUDE输出不可解析的**确切原因尚无足够证据**；尤其不能断言只是截断。DeepSeek首轮合成已经`REVIEWER_SYNTHETIC_API_PASS__NO_PRIVATE`，不允许重复请求。Owner更新代码且GitHub离线CI通过后，至多执行一次Claude合成探针。如果仍然`MODEL_CONTENT_JSON_INVALID`，停止盲试，单独走私有诊断工序，而非继续付费猜测。不启动1000池`init/advance`直至两个Reviewer都满足严格SAFE。
