# StoryForge R60 — 真实1000条优质历史数据 → SFT 数据优先执行任务书（2026-11-11）

## 2026-11-11 双PASS 3条Owner真实CPU生成PASS，训练上下文检查开始

Owner 回执：`DOUBLE_PASS_CANDIDATES_READY__TRAIN_ADMISSION_HOLD`，`cases_checked=20`、`double_pass_candidates=3`、`not_double_pass=17`，推理0、数据库0、GPU0、Quality-v1及训练准入0。3条严格Claude∩Codex有效PASS的位置级Owner私有候选清单已生成，不得重跑覆盖或误报为正式入训。

新增 `experiments/r58_quality/r60_real1000_double_pass_context_cpu.py` 和 `tests/test_r60_real1000_double_pass_context_cpu.py`：本地只读重新验证冻结1000个来源页和现有Sample100哈希/选样，核对3条候选对应Pilot20原位置与同一源样本三条历史消息+目标原文，检查跨世界/目标唯一性及历史System、世界组件、R50排除缺失的状态。输出只有聚合SAFE、不可打印来源文本/标识。历史真实System和世界组件若仍为UNKNOWN，报告`UNVERIFIED`而不制造修复或批准训练。后续世界隔离、训练Prompt真实重建、Tokenizer/Collator和R50排除需另行工程核验。

Owner Mac在已存在固定worktree同步CI通过的新PIN后运行：

```bash
set -euo pipefail
cd "$HOME/workspace/storyforge-r60-4router-review"
python3 -m pytest -q tests/test_r60_real1000_double_pass_context_cpu.py
BASE="$HOME/.local/share/storyforge/r60/private"
python3 experiments/r58_quality/r60_real1000_double_pass_context_cpu.py \
  --expand-dir "$BASE/r60-expand-first-600" \
  --sample-dir "$BASE/r60-real1000-calibration100-v1" \
  --review-dir "$BASE/r60-real1000-pilot20-4router-v1" \
  --candidate-file "$BASE/r60-real1000-double-pass-candidates-v1/R60_DOUBLE_PASS_TRAIN_CANDIDATES_PRIVATE.json"
```

预期 `DOUBLE_PASS_CONTEXT_PREFLIGHT_PASS__TRAIN_ADMISSION_HOLD`、`candidate_count=3`、`train_admitted=0`。此检查只验证本轮已有的真实源数据边界，未证明Gold/R50全部泄漏隔离，不启动Tokenize或模型调用。

低成本双模型方案仍限**预算和协议评估**：先确定官方Qwen/DeepSeek版本、API形态、参数、单例token消耗和容错规则；未经Owner独立批准，不提交外部付费20/80/980真实审核调用。旧4Router Claude结果无需重发。


## 2026-11-11 用户决策：只采双模型PASS；低成本官方API替代4Router

**质量候选策略现已切换。** 用户接受仅当Claude和Codex针对同一冻结样本均给出格式有效的PASS、六维全部达标、严重flag全false时才进入 `TRAIN_CANDIDATES_PRIVATE`；原Claude 2条“PASS低于冻结分数线”的冲突必须排除，不参与双PASS。已知Pilot20有3条有效双PASS。11条争议证据裁决从批量筛选前置闸门移除，保留原始意见和私有记录，必要时抽查双PASS的一致性误放；对其余样本不自动更改原有结论。**双PASS仅为训练候选，不是Quality-v1正式准入或训练授权**，仍需检查历史System、世界组件、R50评测隔离、训练/验证/测试世界切分、Tokenizer/Collator，未核验维持HOLD。

新增 `experiments/r58_quality/r60_real1000_double_pass_candidates_cpu.py` 和合成测试 `tests/test_r60_real1000_double_pass_candidates_cpu.py`。CPU-only重验S0/S1冻结盲包与Owner映射、Codex原审结果、逐位置Claude对账报告一致性，仅生成create-only的3条双PASS位置级私有候选清单，**不导出真实小说内容，不修改任何现有回执，不推理/不入训**。Owner Mac在现有专用worktree同步最新CI通过的固定PIN后执行：

```bash
set -euo pipefail
cd "$HOME/workspace/storyforge-r60-4router-review"
python3 -m pytest -q tests/test_r60_real1000_double_pass_candidates_cpu.py tests/test_r60_real1000_s1_compare_cpu.py
BASE="$HOME/.local/share/storyforge/r60/private"
python3 experiments/r58_quality/r60_real1000_double_pass_candidates_cpu.py \
  --sample-dir "$BASE/r60-real1000-calibration100-v1" \
  --review-dir "$BASE/r60-real1000-pilot20-4router-v1" \
  --blind-dir "$BASE/r60-real1000-s1-blind20-input-v1" \
  --owner-map-dir "$BASE/r60-real1000-s1-blind20-owner-map-v1" \
  --codex-result "$BASE/r60-real1000-s1-codex-review-v1/R60_S1_CODEX20_RAW_PRIVATE.json" \
  --comparison-file "$BASE/r60-real1000-s1-codex-claude-compare-v1/R60_S1_CODEX_CLAUDE_COMPARE_PRIVATE.json" \
  --private-report-dir "$BASE/r60-real1000-double-pass-candidates-v1"
```

预期`DOUBLE_PASS_CANDIDATES_READY__TRAIN_ADMISSION_HOLD`、`cases_checked=20`、`double_pass_candidates=3`、`train_admitted=0`。输出为不可覆盖的Owner私有位置清单；第二次运行前先检查目录，不可覆盖。

**低成本模型路线：** 后续试验不默认使用4Router Claude Opus全量复核。先从已冻结Sample100剩余80条中准备有界低成本模型对照Pilot；候选两厂商：阿里云百炼 `qwen3.7-flash`（官方北京价格输入¥0.2/百万tokens、输出¥0.8/百万tokens，<=32K输入）与DeepSeek官方 `deepseek-flash`（DeepSeek V4.1 Flash，非高峰输入$0.15/百万tokens、输出$0.60/百万tokens，峰值可能双倍）。可备选Gemini `gemini-2.5-flash-lite`（官方$0.10/$0.40每百万输入/输出tokens），但需兼顾中文文学判断能力和跨厂商相关性。**上述是公开标价，不是本批真实费用估算**；必须先本地离线计算每条prompt/output预算和硬上限，校准JSON/严重标志及真实用量，并取得Owner独立API Key/私有外发/费用授权，才可触发真实请求。

**质量验收门槛：** 先在已有20条中对有历史Claude+Codex结论的数据，对候选低成本模型做受控小规模对照，测双PASS精确度与假阳性风险、HOLD和模型严重flag一致性，以及JSON失败率、token成本；真实结果与既有20条保持同案例逐位置绑定，避免在尚无参考真值时声称“审核准确率”。评估通过后才考虑扩到其余80条/980条。不能把不同模型组合的双PASS率混成同一统计，更不能将旧Claude+Codex结论直接外推到Qwen+DeepSeek审核质量。


## 2026-11-11 S1争议去重真实SAFE：优先11条证据复核

Owner Mac 返回 `S1_DISPUTE_TRIAGE_CPU_PASS`：原始Pilot20共20条；`decision_disagreements_including_conflicts=10`（包含Claude低分PASS冲突2）、`severe_flag_disagreements=4`、`claude_quality_conflicts=2`，并集 `unique_priority_cases=11`，其余 `remaining_cases_for_control_review=9`。因此10条判定争议和4条严重flag差异重叠3条（剩余1条仅严重标志分歧），不可简单相加。Owner最终裁决0、训练准入0。只以SAFE归档，私有位置不写入GitHub。

**接下来S1.4证据核对要求：**
1. 复用已生成、不可覆盖的S1 Codex/Claude Owner私有逐位置比较台账，不再次调用两个模型做首轮质量评分。建立11条去重争议队列，优先`severe_flag_disagreement`、Claude REJECT→Codex非REJECT，再处理Claude HOLD→Codex PASS和2条规则冲突（重合只核查一次）。
2. 以Pilot20冻结3条历史消息与目标回复对照Claude与Codex原始理由；逐条记录哪些具体片段支持或反驳hard fact、玩家能动性、安全排除及文笔/连续性打分。严禁补造真实System/世界组件。参考Gold72/P2-A/P2-B的证据规则，结果区分`SUPPORTED`、`NOT_SUPPORTED`、`INSUFFICIENT_CONTEXT`。优先复核归因并保留原始意见，不因模型多数票改分或直接入训。
3. 另外9条无争议样本不能自动认定质量合格；建议先选3条覆盖PASS/HOLD/REJECT的分层对照验证，若发现严重漏判再扩大到余下6条。即使实际9条中某类别缺失也不得造样本；按实际分层抽取。
4. Codex曾完成第二模型独立初审；若再让Codex阅读Claude+Codex对照材料开展证据仲裁，只能称`CODEX_FOLLOWUP_EVIDENCE_AUDIT_ADVISORY`，不得称第三独立模型或Owner人工真值，需新会话且原始输入与理由绑定。Owner人工最终裁决仍需明确；模型意见不能自证真值。
5. 在获得去重争议证据核验、对照样本审查及可解释的审核质量结论前，S2的Sample100剩余80条付费推理保持HOLD，Quality-v1训练准入=0；不启动HF GPU或SFT。


## 2026-11-11 S1 Claude/Codex真实逐位置对账PASS：优先争议裁决

Owner Mac SAFE：合成测试 `7 passed in 0.10s`，实际 `S1_CODEX_CLAUDE_COMPARE_PASS__OWNER_ADJUDICATION_PENDING`，20/20按冻结盲审输入与Owner跨表对齐；`private_comparison_written=true`，本轮模型推理0；Codex 20条PASS9/HOLD8/REJECT3；Claude有效18条PASS4/HOLD10/REJECT4 + 2条低分PASS原始冲突。

**18条有效Claude的交叉表（Claude行，Codex列）：**

| Claude \ Codex | PASS | HOLD | REJECT |
| --- | ---: | ---: | ---: |
| PASS | 3 | 1 | 0 |
| HOLD | 4 | 5 | 1 |
| REJECT | 1 | 1 | 2 |

一致10/18 (55.6%)，判定分歧8/18；全部20条严重flag向量不一致4条。原Claude2条低分PASS模型冲突不计入18条判定一致率。注意严重flag分歧可能与判定分歧/冲突位置重叠，**不能将8+2+4直接算14条不同样本**。目前Owner最终裁决0、Quality-v1/训练准入0。没有任何可靠真值证明谁更准确，不能仅根据Codex PASS多而降低Rubric，不得用多数票直接准入。

**下一阶段S1.4（CPU优先，最小审核范围）**：
1. 先从已生成的Owner私有对账文件 `$HOME/.local/share/storyforge/r60/private/r60-real1000-s1-codex-claude-compare-v1/R60_S1_CODEX_CLAUDE_COMPARE_PRIVATE.json` 计算去重争议集合：`decision_disagreement` 或 `severe_flag_disagreement`；2个Claude冲突均必须包含。仅输出SAFE聚合，不向聊天/GitHub复制私有逐样本原文、逐案理由或crosswalk。
2. 分配审查优先级：一是所有严重flag不一致与Claude REJECT→Codex非REJECT；二是Claude HOLD→Codex PASS、其它判定分歧；三是2条原始PASS低于冻结分数门槛冲突。重合样本仅审核一次。即使两模型一致，仍需评估误判风险与随机抽样验证，不把一致当真值。
3. 对每个争议案例用冻结原始三条历史+目标文本，核对两模型具体理由所引用的证据是否真实存在，特别区分“局部可见事实违背”与“未知历史System/世界卡”，依据Gold72、P2-A/P2-B的严重语义证据规范给出`SUPPORTED / NOT_SUPPORTED / INSUFFICIENT_CONTEXT`。保留每条原始模型意见，不覆盖。
4. 如使用Codex做**第三轮证据仲裁**，须将其标记为非独立（已经参与第二模型审核），不得报告为第三个独立Reviewer；须用隔离的新会话和明确的裁决任务，记录引用与理由，结果仍然是AI建议。若需独立第三模型或人类最终裁决，另行明确审核方式和费用。只在证据可靠后确定Quality-v1准入。
5. 在争议分析达到稳定结论前，S2对既有Sample100剩余80条的低成本模型付费审核保持HOLD；不做SFT GPU。


## 2026-11-11 S1 Codex独立AI复核20/20结构PASS，开始Claude逐位置对账

Owner返回`S1_CODEX20_SCHEMA_CHECK_PASS`：20条独立Codex结果，PASS=9/HOLD=8/REJECT=3、`rubric_conflicts=0`，`independent_owner_adjudications=0`、`train_admitted=0`。Codex 是第二AI意见，绝不自动当成人工Owner参考真值；未经逐条对账，不能由Codex PASS多于Claude推断Claude错误。

新增 `experiments/r58_quality/r60_real1000_s1_compare_cpu.py` 与 `tests/test_r60_real1000_s1_compare_cpu.py`：本地CPU只读加载既有S0审计和冻结S1盲包+Owner独立映射，校验Codex20条ID、冻结六维schema、原输入hash、20个唯一位置，对照原Claude18份有效回执及2份低分PASS冲突；以公开SAFE输出3×3 decision交叉表、有效Claude18条的一致/分歧、20条严重标志分歧数。可选create-only Owner私有对照台账记录各位置两模型评分和待裁决状态，不含原始小说/模型逐案理由。严禁在对账前向Codex泄露旧Claude意见；此时Codex原始审核已完成，进入事后对账。

Owner Mac复用现有专用worktree，先确认最新commit的CI PASS，再原地同步固定PIN并执行：

```bash
set -euo pipefail
cd "$HOME/workspace/storyforge-r60-4router-review"
python3 -m pytest -q tests/test_r60_real1000_s1_compare_cpu.py tests/test_r60_real1000_s1_blind20_prepare_cpu.py
BASE="$HOME/.local/share/storyforge/r60/private"
python3 experiments/r58_quality/r60_real1000_s1_compare_cpu.py \
  --sample-dir "$BASE/r60-real1000-calibration100-v1" \
  --review-dir "$BASE/r60-real1000-pilot20-4router-v1" \
  --blind-dir "$BASE/r60-real1000-s1-blind20-input-v1" \
  --owner-map-dir "$BASE/r60-real1000-s1-blind20-owner-map-v1" \
  --codex-result "$BASE/r60-real1000-s1-codex-review-v1/R60_S1_CODEX20_RAW_PRIVATE.json" \
  --private-report-dir "$BASE/r60-real1000-s1-codex-claude-compare-v1"
```

预期状态 `S1_CODEX_CLAUDE_COMPARE_PASS__OWNER_ADJUDICATION_PENDING`，原Claude有效18/冲突2、Codex20、质量训练准入0。若输出目录已存在，**只读对账时省略`--private-report-dir`**，不要覆盖旧台账。只有Owner提供真实SAFE分歧矩阵，才决定哪些条目优先独立证据裁决，不启动80条新付费筛选。


## 2026-11-11 S1独立盲审包Owner实测生成PASS（下一步为独立裁决）

Owner真实Mac回执：`7 passed in 0.07s`；`S1_BLIND20_PACKETS_READY__INDEPENDENT_REVIEW_PENDING`、`cases_prepared=20`、`unique_blind_ids=20`、`crosswalk_entries=20`、`model_advisory_excluded=true`；新推理0、独立参考审核0、Quality-v1准入0、训练准入0。这只证明盲包制作完成，不等于已经独立审核。

冻结Owner两份产物（不重新生成、不覆盖）：
- 盲审输入：`$HOME/.local/share/storyforge/r60/private/r60-real1000-s1-blind20-input-v1/R60_S1_BLIND20_INPUT_PRIVATE.json`
- Owner映射：`$HOME/.local/share/storyforge/r60/private/r60-real1000-s1-blind20-owner-map-v1/R60_S1_BLIND20_OWNER_CROSSWALK_PRIVATE.json`
- 独立参考Reviewer**只能接触盲审输入**，不可接触Owner映射、S0质量台账、Claude18份有效判定/2份冲突或后续模型对照表。冻结历史范围为3条相邻上下文，并非完整故事、真实历史System或世界卡。

**下一行动S1.2**：复用 `r60_real_ai_dual_review.REVIEW_INSTRUCTIONS` 的六维Rubric与严重标志定义，准备独立Review结果契约：盲ID、decision、六维1–5分、3严重布尔、具体证据和`reason_cn`（仅Owner私有）。任何样本缺乏可见证据时必须HOLD；不要为了凑准入率重判。独立参考模型需要事先单独确定模型/执行通道/费用/私有外发许可；如果改由Owner人工或本地Agent审核，必须记录审核身份与过程，不得把同一个Claude旧结果包装成“独立”。**这一步尚未授权执行模型推理**。

**S1.3**：拿到完整20条独立审核结果后，再通过Owner-only映射还原20位置，比较Claude的PASS4/HOLD10/REJECT4与冲突2，输出逐项原因和误拒/漏拒（仅在独立参考足够可靠时可称其为误判）。最终决定是否在现有Sample100剩余80条上进行低成本模型对照；S2费用和数据外发独立批准。


## 2026-11-11 S0私有台账真实PASS，S1独立盲包准备工程

Owner 最新SAFE：`S0_PILOT20_SAMPLE100_AUDIT_PASS__ADJUDICATION_PENDING`，`private_ledger_written=true`，20条位置/18有效评分/2冲突、冻结Sample100精确绑定全部保持PASS；`independent_reference_reviews=0`、`quality_v1_admitted=train_admitted=0`。20行台账包含Claude结论和六维评分，**仅可供事后对账，不得作为独立Reviewer输入或提前泄露给审核模型**。

新增本地CPU-only脚本 `experiments/r58_quality/r60_real1000_s1_blind20_prepare_cpu.py` 和合成测试 `tests/test_r60_real1000_s1_blind20_prepare_cpu.py`。它先复用S0审计验证整个输入绑定，再从原始20条Pilot packets构造盲审输入，**只保留随机化盲ID、三条历史、目标回复和未裁决状态**；按冻结源指纹确定性打乱顺序，另行将blind ID↔原始位置、来源Sample100位置及输入hash写入Owner独立私有目录。盲审包中不含Claude原始评分、决策、严重flag、逐案理由、原始位置或模型名称。不能将三条历史说成完整多轮或真实System/世界组件。

Owner Mac执行（必须先同步GitHub已通过CI的具体PIN，保持既有worktree干净，不建新worktree）：

```bash
set -euo pipefail
cd "$HOME/workspace/storyforge-r60-4router-review"
python3 -m pytest -q tests/test_r60_real1000_s1_blind20_prepare_cpu.py tests/test_r60_real1000_s0_audit_cpu.py
BASE="$HOME/.local/share/storyforge/r60/private"
python3 experiments/r58_quality/r60_real1000_s1_blind20_prepare_cpu.py \
  --sample-dir "$BASE/r60-real1000-calibration100-v1" \
  --review-dir "$BASE/r60-real1000-pilot20-4router-v1" \
  --blind-dir "$BASE/r60-real1000-s1-blind20-input-v1" \
  --crosswalk-dir "$BASE/r60-real1000-s1-blind20-owner-map-v1"
```

预期 `S1_BLIND20_PACKETS_READY__INDEPENDENT_REVIEW_PENDING`、`cases_prepared=20`、`unique_blind_ids=20`、`crosswalk_entries=20`、`model_advisory_excluded=true`、`model_inference_calls=0`。两个目录均必须此前不存在；成功后create-only，不重复运行覆盖。只将blind目录交给后续独立Reviewer，**不得将crosswalk、S0台账或Claude结果传入复核模型**。此阶段只准备材料，未调用任何独立AI，不意味着已完成S1的20条裁决；外部模型调用需要单独批准目的地与费用。


## 2026-11-11 S0 Owner Mac真实验收PASS（优先于先前“S0待执行”计划）

Owner提供真实只读验收回执（未外发新数据、无模型推理、无GPU）：

- 31项CPU合成测试：`31 passed in 0.09s`。
- 已冻结扩展候选：`EXPANSION_TARGET_REACHED__NOT_ADMITTED`，6条seed + 994条新候选=1000，20私有页、扫描400故事；无数据库修改。
- 全池技术画像：`REAL1000_TECHNICAL_PROFILE_PASS__QUALITY_PENDING`，1000/1000有3条真实历史消息和已完成assistant目标，285个不同故事，最多每故事4条，长度分布545/380/75（300–499/500–999/1000–1500）。
- S0交叉绑定：`S0_PILOT20_SAMPLE100_AUDIT_PASS__ADJUDICATION_PENDING`；冻结Sample100=100，长度层55/38/7；Pilot20=20，长度层11/8/1、同Sample100确定性绑定PASS，18有效模型回执+2冲突、模型PASS/HOLD/REJECT=4/10/4；无新模型推理，模型/质量入训均0。
- **已知后续阻塞**：历史实际System `historical_system_not_verified=1000`、世界组件 `world_component_unverified=1000`、R50排除 `r50_exclusion_unverified=1000`。均属于待核验的训练准备边界，不代表1000条不合格；不能因为技术PASS而宣称正式训练准入。

**S0判定：PASS，仅针对已规定的冻结池、技术画像、Sample100→Pilot20与回执完整性。S1独立参考仍为0，质量未定案。**

**S1下一步零费用工作**：复用 `r60_real1000_s0_audit_cpu.py` 的 `--private-report-dir`，在Owner私有新目录create-only生成20行模型意见/六维评分台账；该台账包含Claude原判定，必须在独立盲审期间隔离保存，不交给Reviewer。独立复核仅读取既有冻结Pilot20原始输入（不含Claude原判），并复用Gold72/P2-A/P2-B规则证据，不重复调用4Router、不再次抽样100。待取得独立裁决后才做模型原判/参考标签对照和误判率计算。没有提交新的付费审核授权，S2/S3继续HOLD。


### 2026-11-11 S0 CPU 验收工具已实现（Owner 私有真实数据尚未执行）

已增加 `experiments/r58_quality/r60_real1000_s0_audit_cpu.py` 与 `tests/test_r60_real1000_s0_audit_cpu.py`。复用旧审核器的配置/20条私有回执完整性校验（原始hash、位置、模型、冻结packet sha、原始decision/Rubric），并把Pilot20的20个`sample100_position`及长度层同已冻结Sample100清单、确定性SHA排名精确对齐；验证100条清单位置唯一、排序、55/38/7配额。可选`--private-report-dir`在Owner私有位置新建且不覆盖20行结构化台账：每个位置、模型原判定、六维分数、严重flag、低于门槛维度、独立裁决状态；不包含小说正文/模型逐案理由。标准输出始终只输出SAFE计数。

**约束：** S0工具的`sample100_pilot20_exact_binding`只证明Sample100 manifest与Pilot20的确定性子集匹配、Pilot20的回执绑定；**不独立证明源1000池未被修改**。须另外运行既有冻结池 `inspect` 和 `r60_real1000_technical_profile_cpu.py`（其当前 CLI 不含本工具自动执行）；1000池对账必须先有真实Owner SAFE，不可仅凭本工具宣布整个S0 Gate通过。快照/模型API不参与该过程。

在现有且无并行Agent占用的Owner固定工作目录中，先同步通过CI的当前分支具体PIN，然后：

```bash
set -euo pipefail
cd "$HOME/workspace/storyforge-r60-4router-review"
python3 -m pytest -q tests/test_r60_real1000_s0_audit_cpu.py tests/test_r60_real1000_pilot20_local_review.py
BASE="$HOME/.local/share/storyforge/r60/private"
python3 experiments/r58_quality/r60_real1000_s0_audit_cpu.py \
  --sample-dir "$BASE/r60-real1000-calibration100-v1" \
  --output-dir "$BASE/r60-real1000-pilot20-4router-v1"
# 仅在上行PASS后，才选择新目录生成S1私有工作台账：
python3 experiments/r58_quality/r60_real1000_s0_audit_cpu.py \
  --sample-dir "$BASE/r60-real1000-calibration100-v1" \
  --output-dir "$BASE/r60-real1000-pilot20-4router-v1" \
  --private-report-dir "$BASE/r60-real1000-s0-audit-v1"
```

预期模型advisory PASS=4/HOLD=10/REJECT=4、2冲突、Sample100=100、Pilot20=20、所有入训计数0。以上CPU命令不需4Router key、不外发、不启动HF、不产生模型API费用；如任何HOLD先检查SAFE错误码，不覆盖任何结果。若私有S0报告目录已存在，不应重复`--private-report-dir`覆盖它。


## 2026-11-11 权威后续计划：复用校准成果 → 补全冻结Sample100 → 分层筛选Real1000

> **本节优先于本文早期阶段性建议。计划制定并不授权任何新的远端推理/私有外发、收费HF CPU/GPU、数据库读写、训练准入或训练。** 不新建worktree；复用Owner既有 `~/workspace/storyforge-r60-4router-review`。本节仅限Real1000数据质量主线，不改变并行GLM/Qwen Agent状态和文件。

### 0. 已完成工作（禁止重做）

- 1000个冻结真实历史候选已收集，技术初筛/来源crosswalk和既有Tokenizer预检有证据；不重新导出、重采集、重复样本生成。抽样100个不同故事已冻结于 `$HOME/.local/share/storyforge/r60/private/r60-real1000-calibration100-v1`，长度层55/38/7；Pilot20由这100条确定性抽取（11/8/1）。**后续试验首先使用这同一100条的其余80条，而非额外抽100条、也不重审已付费20条。**
- Gold72分歧40及校准Development/Locked、R60 Severe10、P2-A 20/60、P2-B 30/90、Rubric v2.1、既有A/B reviewer与HF1000 Stage工程均已存在；优先沿用其标准、工具和已验证结果。注意Rubric v2.1的严重语义证据规范与Real1000单模型六维质量打分是**相关但不完全等价的审核合同**，须建立显式字段映射，不可仅凭名称认为已一致。
- Pilot20完成：`processed=20, remaining=0, model_reviewed=18, conflict_pending=2`；模型意见PASS=4/HOLD=10/REJECT=4，2条低分PASS冲突。独立参考审核=0，Quality-v1和训练准入=0。此前JSON快照回放和自动冲突隔离通过，严禁对20条重复付费生成。已有HF1000双模型Stage是READY、A/B结果0/1000，不能冒充真实质量审核完成。

### 1. S0 — Owner CPU-only 完整性复核与差异矩阵（立即执行，无API费用）

- 只读打开已冻结1000候选摘要、Sample100位置表、Pilot20审阅输入和20个私有回执/冲突回执，校验位置1..20无缺口/重复、哈希与冻结模型/包绑定，确保结果按原始位置一一对齐；失败保持HOLD，不做重评分。
- 形成Owner私有20行诊断台账：位置、长度层、模型原始decision、六维得分、严重flag、HOLD原因类别、Rubric判定、质量冲突类别、是否有独立裁决；公开只汇总计数/分类与无隐私SAFE。
- 复用既有Gold72/P2-A/P2-B的证据规范，做逐字段契约对照（例如引用与语义证据、事实/规则、玩家能动性、HOLD不足证据），列出兼容/不兼容/缺证项；不改冻结v2.1、不覆盖私有旧标签。
- **Gate S0：** 官方SAFE确认20/20对账PASS、2个冲突仍保留、sample100冻结绑定PASS、无额外推理及隐私泄露；否则不得进入新批次。

### 2. S1 — Pilot20裁决和低成本初审对照设计（优先于新的80条付费）

- 对Pilot20全部20条建立盲参考审阅包：原始Claude评分和结论不进入独立模型的prompt；判案时仍可读真实3条历史消息和目标回复，不能把3条前文冒充完整故事/System。引用原文和严重flag核对必须有独立证据记录。原模型4 PASS、10 HOLD、4 REJECT、2分数冲突均需逐条归因，冲突保持原样不可偷改原分。
- 尽量复用已有Owner/Gold校准证据；不存在同案例可靠真值时，才进行**新的独立裁决**。若使用第二AI做参考，只能报告“独立模型意见”，不能假称Owner最终真值；最终分歧由Owner确认或另行明确授权AI替代裁决及其验收标准。
- 冻结比较合同：同一输入边界、同一六维维度/严重判定、相同输出JSON、可比的样本hash；先明确低成本候选模型、入口、版本/参数、单位成本以及4Router Opus复核的条件。候选既可复用已有HF Qwen/GLM工程，也可使用兼容API；**不默认任一模型已有可靠精度，不以原GLM全REJECT作为自动淘汰依据**。
- **Gate S1：** 20条获得明确参考裁决或缺证HOLD分类、Rubric映射可解释、模型冲突处理流程明确、指标定义和成本核算方案冻结。若参考仍不足，先暂停扩大筛选。

### 3. S2 — 在既有冻结Sample100上完成对照Pilot（付费/外发独立授权）

- 先做CPU-only dry-run：验证同一Sample100里Pilot20与其余80条的唯一性、长度层覆盖、来源绑定、与已锁定评测数据的隔离、预算/预计输入输出token与请求数；只生成Owner私有审阅包，**不启动真实模型调用**。
- 经Owner另行同意模型选择、数据外发目的地和费用上限后，对**其余80条**运行成本较低的初审模型；已有20条Claude结果原封不动复用。是否对80条追加Claude复核，采用先抽样、后按争议风险递增的方式，而不是默认80条全部使用Claude。为有效估计误判，验证样本中需包含从低成本PASS和REJECT两端随机抽取的参考样本，而非只复核HOLD；提前冻结抽样种子和分层方式。
- 评估指标至少含：人工/独立裁决样本数、PASS/REJECT混淆与误拒/漏拒、HOLD占比、严重错判个案、模型一致率、JSON/技术失败率、单位样本及每条合格候选成本。分母区分“20条旧Claude初审”和“80条新低成本初审”；若样本量不足，只给不确定性范围，不声称代表1000。
- **Gate S2：** 基于有参考裁决的结果，Owner书面接受质量风险、审核成本和复核覆盖，再决定扩大批量；无法证明安全且经济的低成本初审时，不使用它自动淘汰1000条，改为分批人工/高质量模型复核。

### 4. S3 — Real1000分层精筛（需另行审批）

- 执行顺序：冻结既有1000池→本地硬性技术过滤与上下文可用性标记→低成本审核→对HOLD、模型冲突、严重标志、接近分数线、随机PASS/REJECT样本作第二模型/Owner复核→独立质量裁决→仅合格案例进入Train Candidates。**高置信度初审PASS也不自动等于训练准入；初审REJECT也不可凭模型一句话批量淘汰。**
- 不改写已生成的20条Claude审阅回执。严格按原始1000唯一位置去重并衔接Sample100；剩余范围是**尚未审核的980条**，其中80条属于已冻结校准Sample100。每一批（建议先100条增量，其后分批）产出create-only版本化回执、耗费、SAFE统计和错误隔离；技术失败先CPU快照恢复，无效原文不自动改判。
- **Gate S3：** 全1000去重逐条可追溯、每条状态明确(PASS/REJECT/HOLD/CONFLICT/TECHNICAL)、独立裁决与未决项分开、误判监控和成本在S2批准边界内。未审完不必阻塞第一批高质量候选准备，但绝不能把未裁决数据当已通过。

### 5. S4 — 首批高质量SFT候选及训练前CPU验收

- 优先形成50–100条（若实际合格不足则报告真实数量，不补假数据）`TRAIN_CANDIDATES_PRIVATE`，仅使用已核实质量、上下文/角色完整且不触及冻结评测隔离的样本；记录来源指纹、审核版本、原目标哈希、世界切分、内容长度分布。
- CPU-only完成会话/世界隔离、训练Prompt构建、目标归属、去重、Tokenizer/Collator和可追溯训练/验证/测试划分；如存在缺失真实System/历史链则标为BLOCKER，不假造认证数据。提交SAFE工程报告、不上传私人正文。
- **Gate S4：** 质量与训练准入由Owner另行签署；任何HF收费Job、GPU SFT、adapter promotion、PR合并均非本计划自动授权。

### 6. 执行约束与交付

- 仓库：`sunxu/storyforge`，优先专用现有分支`r60/p4-generation-eval-framework`；只编辑本质量主线相关文件/测试/文档，不触碰并行GLM/Qwen任务及其它Agent工作树。先查看branch HEAD、工作区状态和CI，禁止新建worktree或覆盖已有私有结果。
- 任何新模型成本或隐私外发均须Owner授权。CPU-only代码/测试/数据完整性诊断可先推进；私有原文、模型逐案理由、key、交叉ID映射不进GitHub/Issue。只提交聚合SAFE和程序。
- 每阶段交付固定四件：GitHub代码/文档commit、CI状态、Owner Mac本地SAFE回执、是否通过Gate/后续具体命令。历史GLM/Qwen H200及HF1000 READY状态均不等于本线模型审核已付费完成。


## 2026-11-11 Pilot20 模型审核全部完成：已处理20/20，质量裁决未启动

Owner Mac 安全回执两次完全一致：`status=PILOT20_LOCAL_REVIEW_COMPLETE__OWNER_ADJUDICATION_PENDING`；`processed=20`、`remaining=0`、`model_reviewed=18`、`conflict_pending=2`。18份有效模型意见：PASS=4、HOLD=10、REJECT=4；2份原始PASS但低于冻结六维门槛的冲突隔离结果。严重标志触发次数：`hard_fact_or_ban=1`、`safety_exclusion=2`、`serious_player_agency=2`，属于flag计数，**不得未经逐例核对便推断为5条独立问题样本**。独立参考审核=0，`quality_v1_admitted=0`、`train_admitted=0`；无GPU、无数据库操作。真实数据曾被外发至4Router，不能将无数据库访问理解为无外发。

**现阶段结论**：Pilot20 的模型请求、严格格式校验、CPU快照恢复、断点续跑及质量冲突隔离的工程验收完成；但20/20不是Quality-v1准入完成，不得把4条模型建议PASS直接写入训练，也不能把模型HOLD或分数线冲突未经人工/独立裁决即自动REJECT。保持全部Owner私有回执原件、样本hash和模型理由，不要上传GitHub/公开粘贴。

**下一阶段优先级**：
1. CPU本地从已有20条结果生成只含统计和位置的SAFE审核汇总，核对18个合格格式回执和2个冲突回执的连续性、checksum、冻结包绑定，无外发/付费。
2. 对4个模型PASS做抽样或全量复核；10个HOLD区分证据不足、轻微质量问题及确需剔除的情况；4个REJECT核对严重标志及可见上下文依据；2个低分PASS冲突必须独立裁决并保留原始判定与评分。必要时升级Rubric但不可追溯性地偷改冻结标准。
3. 输出结构化校准结论：模型判定/独立裁决交叉表、六维分布、冲突原因及采样误差。仅在质量标准清晰、Owner独立裁决或已授权AI替代审核方案明确、验收PASS后，考虑在剩余980条上执行下一批精筛。Pilot20样本不能代表Real1000最终合格率。
4. 训练仍HOLD，需另行授权。后续新Agent从本节和当前GitHub真实HEAD及Owner安全汇总继续，不需重新调用已完成的20条。


## 2026-11-11 真实第8条无效JSON：尾部多余右花括号，可CPU离线恢复

Owner最新真实回执 `processed=7, model_reviewed=6, conflict_pending=1, remaining=13`，批次在第8条 `PROXY_MODEL_JSON_HOLD` 停止；已成功生成的前7条不可重试/覆盖。Owner第8条私有4Router响应快照经安全本地格式诊断：`finish_reason=stop`、外层为完整JSON围栏，围栏内部有效JSON对象之后**恰好多余单个右花括号**，无文本附加；原模型建议结论为HOLD，保留原始六维评分和理由即可，不需要重复调用API。

运行器新增`parse_strict_model_json`：首先尝试原文严格JSON；失败时仅接受**JSON对象可被原生JSONDecoder完整解码，且剩余部分精确为1个 `}` 字符**；再去掉该字符并通过原生JSON和冻结六维Rubric校验。拒绝其它多余字符、任意文本提取、修改评分/模型决定、补齐缺少字段、宽松JSON；原始HTTP快照只在Owner私有目录保留。任何不符合Rubric的内容仍HOLD，决不为入训改分。

在固定worktree `~/workspace/storyforge-r60-4router-review` 原地同步到通过CI的具体提交，先跑 `python3 -m pytest -q tests/test_r60_real1000_pilot20_local_review.py`，确认 `inspect` 仍是7条已处理。仅当Owner确认本机`R60_PILOT20_FAILED_0008_PRIVATE.json`确实属于冻结第8条并同一模型时，执行本机无API费用：

```bash
REVIEW="experiments/r58_quality/r60_real1000_pilot20_local_review.py"
OUT="$HOME/.local/share/storyforge/r60/private/r60-real1000-pilot20-4router-v1"
python3 "$REVIEW" replay-snapshot --output-dir "$OUT" --position 8 --confirm-snapshot-provenance
python3 "$REVIEW" inspect --output-dir "$OUT"
```

预期恢复为`processed=8, remaining=12`，模型HOLD计入advisory；`quality_v1_admitted=0, train_admitted=0`继续不变。未经另行真实数据外发和计费授权，不继续`advance`。不得上传/公开原始快照。


## 2026-11-11 P20 第2条 PASS 后：自动隔离质量冲突、继续批量（CPU 合成验证）

Owner 实测 `processed=2, model_reviewed=1, conflict_pending=1, remaining=18`：首条PASS低于冻结中文文笔门槛已隔离，第二条Claude审核有效PASS，训练准入依然0。原审核器每遇新的 `PROXY_PASS_BELOW_FLOOR_HOLD` 都会中断，需要手动将失败快照quarantine后再次开始，付费API调用效率低。

新版运行器针对**当次真实API返回**、且原冻结Rubric严格证实为 `QUALITY_FLOOR_DECISION_INCONSISTENT` 的**唯一可自动恢复质量冲突**，在进程内带原模型对象生成不可覆盖的私有 `R60_PILOT20_CONFLICT_{position}_PRIVATE.json`，保存原判定PASS、原六维原分值、原理由、冻结包哈希/模型ID、固定冲突码；不构造伪PASS、不改模型原评分、不改训练准入。若分数满足冻结标准则仍以原有有效回执格式保存。两者逐位互斥，自动推进 `processed` 至下一条。

其他技术故障（HTTP/超时/截断/非法JSON/模型字段异常/严重标志矛盾）仍**立即停止批次**；已完成的回执/隔离记录保持原样，不覆盖，不自动重试、不继续付费。原始HTTP回复仍仅按需在Owner本地独立私有诊断目录保留。历史首条手动隔离记录和第二条有效回执无须迁移、重评分或重复提交。

批次最大值仍是 `MAX_CASES_PER_CALL=5`，剩余18条可按 5/5/5/3 分段运行。先在原固定worktree更新到最新经过 CI 验证的提交、跑无费用测试及inspect；如果之前某条计费请求失败但模型响应存在私有快照，先考虑本地replay/quarantine，避免不必要的重复付费。**只有Owner明确继续允许新一轮真实样本外发/计费，才运行 `advance --execute --allow-private-data-egress`**。失败时根据SAFE原因码停止分析，不盲目对同一失败样本反复提交。

```bash
cd "$HOME/workspace/storyforge-r60-4router-review"
python3 -m pytest -q tests/test_r60_real1000_pilot20_local_review.py
REVIEW="experiments/r58_quality/r60_real1000_pilot20_local_review.py"
OUT="$HOME/.local/share/storyforge/r60/private/r60-real1000-pilot20-4router-v1"
python3 "$REVIEW" inspect --output-dir "$OUT"
# Owner另行许可真实外发与费用后，再分批执行：
# python3 "$REVIEW" advance --output-dir "$OUT" --max-cases 5 --execute --allow-private-data-egress
```


## 2026-11-11 第1条质量冲突隔离，不阻断后续19条（最新）

Owner的 `replay-snapshot --position 1 --confirm-snapshot-provenance` 实际返回 `PROXY_PASS_BELOW_FLOOR_HOLD`，与原模型`PASS`但`chinese_prose=3`低于冻结门槛4一致。**不得反复重发首条、修改模型评分、降低门槛、把技术HOLD计作REJECT或把原始PASS直接当作入训PASS。**

修复单一连续回执队列的首条阻塞：新增 CPU-only `quarantine-snapshot`（显式确认原快照就是当前位置的原模型响应），读取Owner现有私有快照，要求模型id吻合、stop结束、完整严格JSON、原结论PASS且原Rubric明确拒绝该结论因为分数门槛。创建不可覆盖的 `R60_PILOT20_CONFLICT_0001_PRIVATE.json`，只记录原模型意见/六维得分/失败原因及与原冻结数据绑定的哈希；此条作为**已处理但未合格的冲突样本**，只能等待后续质量裁决。保留原始FAIL快照与原始PASS、绝不改写成合格评分。工作流`processed=1, conflict_pending=1, model_reviewed=0, remaining=19, train_admitted=0`； `advance`改用 `processed` 继续第2条（仍须实际外发/费用许可），不再卡在第1条。原有效回执仍严格验证，允许原混合序列每个位置为一份有效评分或一份冲突记录、禁止重号及跳号，保证resume可靠。

固定worktree原地同步并无费用验证：

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
WORK="$HOME/workspace/storyforge-r60-4router-review"
PIN="6046a595060718f00759a994f50ae5790ca1605b"
test -z "$(git -C "$WORK" status --porcelain)" || exit 42
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
git -C "$ROOT" cat-file -e "$PIN^{commit}"
git -C "$WORK" switch --detach "$PIN"
cd "$WORK"
python3 -m pytest -q tests/test_r60_real1000_pilot20_local_review.py
OUT="$HOME/.local/share/storyforge/r60/private/r60-real1000-pilot20-4router-v1"
python3 experiments/r58_quality/r60_real1000_pilot20_local_review.py inspect --output-dir "$OUT"
```

只有Owner核实原快照确实属于冻结第1条时才隔离（CPU、无网络）：

```bash
python3 experiments/r58_quality/r60_real1000_pilot20_local_review.py quarantine-snapshot \
  --output-dir "$OUT" --position 1 --confirm-snapshot-provenance
python3 experiments/r58_quality/r60_real1000_pilot20_local_review.py inspect --output-dir "$OUT"
```

验收 `processed=1, conflict_pending=1, model_reviewed=0, remaining=19`；后续可在Owner明确新一轮外发及费用许可后`advance --max-cases 1`从第2条开始。禁止在公开文档披露私人理由文本或导出私有回执。未独立裁决时依然不允许任何训练准入。


## 2026-11-11 最新结论：第1条模型PASS但低于冻结质量门槛，不允许自动恢复为PASS

Owner提供的首条4Router Claude-Opus-5.5原始快照确认：`finish_reason=stop`，模型以完整 `\`\`\`json` 围栏输出；严格格式剥离后原始判断 `decision=PASS`，六维分值中 `chinese_prose=3`。但冻结的 `r60_real_private_batch.FLOORS["chinese_prose"]=4`。**因此模型结论与现有准入规则矛盾**，不能直接把快照恢复为有效PASS，也不能把3分偷偷改为4分。这个冲突是质量审查需要解决的问题，不是网络/JSON故障。

已保留对整块JSON围栏的严格剥离及CPU离线快照重放支持，但增加专门 SAFE 原因码 `PROXY_PASS_BELOW_FLOOR_HOLD`、`PROXY_SEVERE_FLAG_CONFLICT_HOLD`。尝试离线重放此快照将产生前者，不会写正式模型评分回执，`model_reviewed=0`，`quality_v1_admitted=0`，`train_admitted=0`。在明确的质量裁决机制确定应如何标注该样本前，不再为同一条重复付费模型请求，不降低现行分数门槛，不伪造模型判断，也不把技术失败计为REJECT。

诊断快照中有私有文学正文。不要复制到GitHub Issues或公开日志；主线任务书只记录固定SAFE类别与无敏感分数，不记录模型原始长篇理由。Owner若需核对，使用现有 `~/workspace/storyforge-r60-4router-review` worktree原地同步，并运行无费用的 `pytest`、`inspect`；不得重新初始化或创建worktree。


## 2026-11-11 4Router 首条响应已定位：完整 JSON 围栏，CPU 离线恢复

Owner 在现有私有诊断快照中确认：`finish_reason=stop`、`completion_tokens=1754`、正文1037字符，**以独立完整的 \`\`\`json 代码围栏包装原本有效JSON**。此前解析器直接 `json.loads(content)`，因第1字符为反引号而返回 `PROXY_MODEL_JSON_HOLD`。该问题是**格式包装**，不是模型审核失败；已有付费模型结果可以尝试本机离线恢复，无需再次调用API。

本次只允许剥离**整个正文严格匹配**的 `\`\`\`json<换行>JSON正文<换行>\`\`\``（允许首尾空白、JSON大写标签）；不允许扫描任意第一对花括号、允许额外解释文字、修补非法JSON、或者绕过六维 Rubric 检查。只有剥离后 `json.loads` 与原 `reviewer.parse_model_response` 均通过，才可能恢复 advisory 回执。新增 CPU-only `replay-snapshot` 模式，要求操作人显式确认 **snapshot确实来自当前冻结packet对应位置**（原始HTTP响应没有原输入hash，不可独立密码学核验该对应关系）；对模型 ID、当前packet文件hash、位置连续性及已有回执不可覆盖做保护；仅以本机私有快照产生既有格式的 create-only private receipt，不调用4Router，不产生API费用。恢复结果仍是 **模型建议评分而非独立质检/训练准入**，`quality_v1_admitted=0`、`train_admitted=0`。

在唯一固定 `~/workspace/storyforge-r60-4router-review` worktree 且工作区干净时原地同步代码：

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
WORK="$HOME/workspace/storyforge-r60-4router-review"
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
test -z "$(git -C "$WORK" status --porcelain)" || exit 42
git -C "$WORK" switch --detach origin/r60/p4-generation-eval-framework
cd "$WORK"
python3 -m pytest -q tests/test_r60_real1000_pilot20_local_review.py
OUT="$HOME/.local/share/storyforge/r60/private/r60-real1000-pilot20-4router-v1"
python3 experiments/r58_quality/r60_real1000_pilot20_local_review.py inspect --output-dir "$OUT"
```

若操作人能确认本地`R60_PILOT20_FAILED_0001_PRIVATE.json`就是对应第1条同一冻结packet和本次Claude调用的失败快照，可自行在Mac执行本地无费用恢复，**不要再次发送模型请求**：

```bash
python3 experiments/r58_quality/r60_real1000_pilot20_local_review.py replay-snapshot \
  --output-dir "$OUT" --position 1 --confirm-snapshot-provenance
python3 experiments/r58_quality/r60_real1000_pilot20_local_review.py inspect --output-dir "$OUT"
```

成功标准`model_reviewed=1, remaining=19`；若`PROXY_RUBRIC_SCHEMA_HOLD`仍出现，说明不是仅代码围栏问题，保持快照原样，分析评分字段，不要放宽Rubric或伪造PASS。真实模型内容和诊断快照不上传GitHub；不要在公开日志/聊天里粘贴模型的长篇隐私评语。


## 2026-11-11 4Router 真实首条 HTTP 200 后 Schema HOLD：离线快照诊断修复

Owner 使用已验证的 `https://4router.ai/v1/chat/completions`、8192-token预算，实际首条 `advance` 返回 `PROXY_RESPONSE_SCHEMA_HOLD`；`inspect` 仍 0/20、无有效评分。这是响应解析/字段审核技术失败，**不能标记案例为REJECT**。此前合成同协议案例曾 HTTP200、`finish_reason=stop`、1402 completion tokens、Rubric_VALID，表明格式并非普遍失效。本次HTTP200响应正文**当时未存档，不能无费用追溯原因**。

已修正审核器：细分 `PROXY_ENVELOPE_JSON_HOLD`（非JSON外壳）、`PROXY_ENVELOPE_STRUCTURE_HOLD`、`PROXY_CONTENT_STRUCTURE_HOLD`、`PROXY_MODEL_JSON_HOLD`（模型正文非JSON，Markdown围栏也仍属于无效JSON）、`PROXY_RUBRIC_SCHEMA_HOLD`（JSON可解析但未满足冻结Rubric），保留 `PROXY_TRUNCATED_HOLD` 和 `PROXY_EMPTY_HOLD`。只有严格通过原Rubric才写正式评分回执。模型返回但未通过解析时，新增仅在本机Owner私有根下、创建后不覆盖的原始响应快照（`$HOME/.local/share/storyforge/r60/private/r60-real1000-pilot20-4router-v1-response-diagnostics-v1/R60_PILOT20_FAILED_0001_PRIVATE.json`），限原本HTTP响应120000字节；**不能上传、粘贴、打印或提交此私有文件**。用CPU离线检查快照结构来修复，不依赖反复付费调用。由于原20条output目录有严格外来文件禁入规则，诊断快照保存在**同级独立私有目录**，不会破坏原`inspect`。

执行固定worktree无费用验证：

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
WORK="$HOME/workspace/storyforge-r60-4router-review"
PIN="b97ff44798484bd22a4d603026ee0e89924ef631"
test -z "$(git -C "$WORK" status --porcelain)" || exit 42
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
git -C "$ROOT" cat-file -e "$PIN^{commit}"
git -C "$WORK" switch --detach "$PIN"
cd "$WORK"
python3 -m pytest -q tests/test_r60_real1000_pilot20_local_review.py
python3 experiments/r58_quality/r60_real1000_pilot20_local_review.py inspect \
 --output-dir "$HOME/.local/share/storyforge/r60/private/r60-real1000-pilot20-4router-v1"
```

下一次真实`advance --max-cases 1`须Owner重新确认私有案例外发和费用；如果再次发生Schema HOLD，记录其细分类别并在Owner Mac上私密离线分析新快照。**不可因为0份成功评分推断之前请求未外发或未计费。** 目前不启动GPU、数据库或训练，不新增worktree，不重新初始化。 


## 2026-11-11 4Router 首条真实审核返回 length — 输出预算修复（最新）

Owner 已将现有审核配置改为实测可用 `https://4router.ai/v1/chat/completions`，经 `inspect` 验证原私有20条审阅包配置可读；真实 `advance --max-cases 1` 返回 `PROXY_TRUNCATED_HOLD`，`model_reviewed=0`、`quality_v1_admitted=0`，原因是模型回复 `finish_reason=length`。这证明请求至少已获模型响应，不是初始HTTP断连；**可能已经发生私有数据外发及API计费**，不能按 `model_reviewed=0` 推断无费用或无外发。

已只修改 `r60_real1000_pilot20_local_review.py` 的 `REVIEW_MAX_TOKENS` 常量，从1600提升至8192；顶层 `system`、用户消息、评分Rubric、严格JSON输出验证、私有回执路径与签名、冻结样本均不改变。保留 `PROXY_TRUNCATED_HOLD` 为技术失败，绝不等同文学质量 `REJECT`。补充合成测试检查8192预算和截断安全处置；代码提交后先在**现有唯一固定worktree**原地同步并运行CPU测试。无需新建worktree、无需重建/覆盖配置或审阅包、无需清理任何回执。

```bash
set -euo pipefail
WORK="$HOME/workspace/storyforge-r60-4router-review"
ROOT="$HOME/workspace/storyforge"
git -C "$WORK" status --short
test -z "$(git -C "$WORK" status --porcelain)" || { echo "DIRTY_WORKTREE_HOLD"; exit 42; }
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
git -C "$WORK" switch --detach origin/r60/p4-generation-eval-framework
cd "$WORK"
python3 -m pytest -q tests/test_r60_real1000_pilot20_local_review.py
python3 experiments/r58_quality/r60_real1000_pilot20_local_review.py inspect \
  --output-dir "$HOME/.local/share/storyforge/r60/private/r60-real1000-pilot20-4router-v1"
```

如再审核真实第1条，必须由Owner明确批准本次再次外发及费用后执行 `advance --max-cases 1 --execute --allow-private-data-egress`；若仍length则暂停并研究思考预算/响应格式，不要无上限增加费用。模型生成未完成不写评分回执，阶段准入仍0。


## 2026-11-11 4Router 细分错误码 + 固定工作树（最新执行规则）

用户确认此次问题**与代理无关**，禁止因推测代理而继续改变联网行为。最新审核器只修改诊断：保留原显式无代理的联网设置，针对 HTTP 数字状态（400/401/403/404/429/5xx）、已知4Router/Claude错误`type/code`（严格有限白名单映射）、DNS、TLS证书校验、TLS握手、超时、拒绝连接、重置连接、无路由等输出细分的 `reason_code`。绝不输出原始HTTP错误正文、异常字符串、Key、URL或私有案例。合成回归覆盖类别；**原20条审阅包、旧配置和0份成功回执不覆盖、不重建**。

不再新建 worktree。Owner Mac 已有 worktree 清单显示 `/private/var/folders/fk/p_g8myrd27d3j7qp13zh_2gr0000gn/T/r60-4router-debug-kcZt62`（detached，旧e3e77759），把**这个现有worktree**迁移为唯一长期使用的 `/Users/keedle/workspace/storyforge-r60-4router-review`，前提是旧目录干净、目标不存在：

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
OLD="/private/var/folders/fk/p_g8myrd27d3j7qp13zh_2gr0000gn/T/r60-4router-debug-kcZt62"
WORK="$HOME/workspace/storyforge-r60-4router-review"
test -d "$OLD"
test ! -e "$WORK"
test -z "$(git -C "$OLD" status --porcelain)"
git -C "$ROOT" worktree move "$OLD" "$WORK"
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
git -C "$WORK" switch --detach origin/r60/p4-generation-eval-framework
cd "$WORK"
python3 -m pytest -q tests/test_r60_real1000_pilot20_local_review.py
```

如旧worktree有未提交变更，停止移动与删除，不要使用 `--force`、`git reset --hard`、`rm -rf`。同一目录今后直接原地 `git fetch` + `git switch --detach`（仅在干净且无其他agent写入时）；不新建工作树。

Owner 本次临时树可清理的仅以下明确列出的路径（**禁止删除**长期 `~/workspace/storyforge-*`、RolePlay、Gold Quality或本新固定树）：

```bash
ROOT="$HOME/workspace/storyforge"
T="/private/var/folders/fk/p_g8myrd27d3j7qp13zh_2gr0000gn/T"
for name in \
  r60-4router-6uBSEb r60-4router-bJOHtG \
  r60-calibration100-HWh8Jl r60-pilot20-ctAQkN \
  r60-qwen-cpu-8VgNz4 r60-real1000-RHId9x \
  r60-unified-2tai5e r60-unified-5Zm2gJ r60-unified-LFppup; do
  path="$T/$name"
  test -d "$path" || continue
  if [ -z "$(git -C "$path" status --porcelain)" ]; then
    git -C "$ROOT" worktree remove "$path"
    echo "REMOVED_CLEAN_WORKTREE=$name"
  else
    echo "SKIPPED_DIRTY_WORKTREE=$name"
  fi
done
git -C "$ROOT" worktree list
```

若旧debug树已成功迁移，它不应再出现在临时路径清理名单中。只执行 `git worktree remove`，不做 `prune --expire now`、`rm -rf` 或强制删除。清理前确认这些临时树没有正在运行的进程或其他Agent使用。

Owner 实际调用前（先不重发真实请求）在固定目录直接：`python3 experiments/r58_quality/r60_real1000_pilot20_local_review.py inspect --output-dir "$HOME/.local/share/storyforge/r60/private/r60-real1000-pilot20-4router-v1"`，无费用。下一次只有Owner确认新一轮真实外发/费用后，才执行 `advance --max-cases 1 --execute --allow-private-data-egress`，回报具体 `stage=ADVANCE` + `reason_code`，以便辨认 HTTP 400 格式或 401 Key、429限速或 DNS/TLS 等；失败不自动重试。


## 2026-11-11 Owner 目录复用要求及4Router最新无费用回执

Owner 明确要求：**后续不要每次新建 worktree**；优先在已经存在、刚刚完成验收的同一工作目录中执行，不覆盖或重置并行Agent的工作树，也不为了每条SAFE回执重复`fetch`/`worktree add`/`init`。如果确实需要更新代码，只在确认目标工作目录无未提交改动、没有其他Agent占用后原地同步，或复用现有专用工作树；必须新建隔离目录时先说明原因。

Owner 最新`inspect`：`PILOT20_LOCAL_REVIEW_PARTIAL__OWNER_ADJUDICATION_PENDING`、`total_cases=20`、`model_reviewed=0`、`remaining=20`、`private_data_egress=false`，专用 `CLI_PROXY_API_KEY_PRESENT=yes`。说明本地配置、私有20条审阅包与绑定校验已通过，尚未向4Router发出真实评分请求，故此前无原因`HOLD`不能认作质量拒绝。**不重新init、不删除目录，也不重新抽样。**

在刚才成功`inspect`的工作目录下，且Owner明确确认本批新的20条正文外发及API费用后，直接执行：

```bash
set -euo pipefail
BASE="$HOME/.local/share/storyforge/r60/private"
REVIEW="experiments/r58_quality/r60_real1000_pilot20_local_review.py"
OUT="$BASE/r60-real1000-pilot20-4router-v1"
test -f "$REVIEW"
test -n "${CLI_PROXY_API_KEY:-}"
python3 "$REVIEW" advance --output-dir "$OUT" --max-cases 5 \
  --execute --allow-private-data-egress
python3 "$REVIEW" inspect --output-dir "$OUT"
```

首批5条仅视为模型ADVISORY，不自动训练准入。技术失败保留历史文件并回传SAFE `stage`/`reason_code`，勿盲目重复付费。未获单独批准不执行外发。


## 2026-11-11 4Router 技术 HOLD 定位修复（最新）

Owner 的 `PILOT20_LOCAL_REVIEW_HOLD` 回执没有包含子原因，**不能解释成模型 REJECT 或样本不合格**。经代码审查发现 `advance` 曾接受 `OPENAI_API_KEY` 作为存在性检查，但真正的HTTP请求只读取 `CLI_PROXY_API_KEY`；并且所有错误均折叠成无原因 HOLD。现已统一要求 `CLI_PROXY_API_KEY`，并增加严格白名单 `stage` / `reason_code`，绝不回显私有报错字符串、URL、Key、文本或返回正文。

最短无费用诊断：先用**新固定代码 PIN**运行合成测试；若此前 `init` 已创建目录，不再重复 `init`；直接运行 `inspect`（不调用API），即可区分配置/私有文件问题与后续 API 问题。若 `inspect` PASS，检查专用 Key 是否存在（仅打印yes/no，不回显Key）；如 `advance` 真实请求曾失败，新的SAFE会显示如 `PROXY_API_KEY_REQUIRED`、`PROXY_TRANSPORT_OR_HTTP_HOLD`、`PROXY_RESPONSE_SCHEMA_HOLD` 等。失败不自动重试已持久化位置，未经 Owner 明确确认不继续真实付费外发。

```bash
set -euo pipefail
BASE="$HOME/.local/share/storyforge/r60/private"
REVIEW="experiments/r58_quality/r60_real1000_pilot20_local_review.py"
OUT="$BASE/r60-real1000-pilot20-4router-v1"
python3 -m pytest -q tests/test_r60_real1000_pilot20_local_review.py
python3 "$REVIEW" inspect --output-dir "$OUT"
if [ -n "${CLI_PROXY_API_KEY:-}" ]; then echo "CLI_PROXY_API_KEY_PRESENT=yes"; else echo "CLI_PROXY_API_KEY_PRESENT=no"; fi
```

只有在 `inspect` 报 `PRIVATE_FILE_MISSING_HOLD`，并确认确实从未初始化时，才考虑原 `init`，不要因无原因HOLD就删除目录。原始20条审阅包和已有评分回执保持不变。



## 2026-11-11 P1 Pilot20 审核协议切换至 4Router Claude（最新）

已沿用 2026-11-09 在 R60 P2-A 上成功运行的 4Router/Claude Opus 5.5 协议：**顶层 `system`、`messages` 只含 `user`、不传 `temperature` 和 `response_format`**。复用现有 `r60_real_ai_dual_review.py` 的六维 Rubric 与严格 JSON 校验，当前20条审阅包、原始1000条冻结池和sample100均不改变。

`experiments/r58_quality/r60_real1000_pilot20_local_review.py` **保留历史文件名，但现只接受 `https://4router.ai` 及其HTTPS子域名**。Key **仅**从 Owner Mac 环境变量 `CLI_PROXY_API_KEY` 读取，不回退使用 `OPENAI_API_KEY`，避免把其他服务的凭据误发给4Router；Key不会写入配置文件或日志。申请调用时同时要求 `--execute --allow-private-data-egress`，否则拒绝调用。无明示批准不得调用，**此前 Development20 向 4Router 外发授权不覆盖本批新20条**。

待 Owner 明确确认向4Router外发这批20条正文及支付API费用后，用当前CI PASS PIN的独立worktree执行：

```bash
set -euo pipefail
umask 077
BASE="$HOME/.local/share/storyforge/r60/private"
REVIEW="experiments/r58_quality/r60_real1000_pilot20_local_review.py"
OUT="$BASE/r60-real1000-pilot20-4router-v1"
# 以下两项在当前 Owner Shell 中设置，禁止回显API Key：
: "${CLI_PROXY_API_KEY:?set the key in your private shell environment}"
: "${CLI_PROXY_BASE_URL:?set the previously verified 4Router HTTPS base URL}"
python3 -m pytest -q tests/test_r60_real1000_pilot20_local_review.py
test ! -e "$OUT"
python3 "$REVIEW" init \
  --packets-dir "$BASE/r60-real1000-pilot20-packets-v1" \
  --output-dir "$OUT" \
  --base-url "$CLI_PROXY_BASE_URL" --model claude-opus-5-5
# 付费 / 真实正文外发；必须由 Owner 单独批准后手动运行：
python3 "$REVIEW" advance --output-dir "$OUT" \
  --max-cases 5 --execute --allow-private-data-egress
python3 "$REVIEW" inspect --output-dir "$OUT"
```

`init` 不调用API，只持久化受约束的endpoint、模型、输入文件SHA；`advance` 最多5条，单条成功即创建不可覆盖0600回执，失败直接HOLD，不自动重试、不会记成质量REJECT；`inspect` 不外发，只统计ADVISORY PASS/HOLD/REJECT和严重标记。若5条全REJECT或严重标记异常高，先核验原因，不自动扩大15条。远程API的外发事实与本地GPU/HF GPU不同；代码不提交任何HF Job。即使模型报告PASS，正式训练准入仍为0。

**下文旧 localhost / Ollama 执行片段已被本节替代，不要用旧参数 `--endpoint` / `--json-mode`。**


## 2026-11-11 首批20条审阅包 Owner 验收 PASS，开始单模型试点

Owner Mac 对 `b6b25fb8c7a8a7db62db24375f323d23c63edabe` 报告：`4 passed in 0.06s`、`PILOT20_REVIEW_PACKETS_READY__NO_REVIEWS`、`cases_prepared=20`、`sample100_verified=true`、长度配额11/8/1；原始私有审阅包 `r60-real1000-pilot20-packets-v1` 已创建，尚无质量评分。

**下一步不再建新的冻结池或抽样包**。新增唯一薄适配 `r60_real1000_pilot20_local_review.py`，复用既有 `r60_real_ai_dual_review` 六维 Rubric/JSON 验证/OpenAI-compatible API；只允许 Owner Mac 的 localhost 服务，以最多5条/调用逐条审核，并在独立私有目录生成 create-only 的评分/理由回执。原始模型的 `PASS/HOLD/REJECT` 明确作为 *advisory*，不自动成为真实质量 PASS 或训练准入；需要独立参考对严重标记及争议做实质语义复核。失败中断后从已持久化的连续编号继续，不会重复已成功的请求。

Owner 确认自己本机已安装/运行可用 OpenAI-compatible 审核模型后运行如下命令（替换实际 `MODEL`，并根据实际本地服务填写 `ENDPOINT`）。这些命令会对真实私有20条逐条发起**本机模型推理**，可能占用 Mac CPU/GPU，但不提交远端 HF GPU Job：

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
BASE="$HOME/.local/share/storyforge/r60/private"
PIN="$(git -C "$ROOT" rev-parse origin/r60/p4-generation-eval-framework)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/r60-review20-XXXXXX")"
git -C "$ROOT" worktree add --detach "$WORK" "$PIN"
cd "$WORK"
python3 -m pytest -q tests/test_r60_real1000_pilot20_local_review.py
MODEL="替换为本机实际可用模型名称"
ENDPOINT="http://127.0.0.1:11434/v1"
OUT="$BASE/r60-real1000-pilot20-local-review-v1"
test ! -e "$OUT"
python3 experiments/r58_quality/r60_real1000_pilot20_local_review.py init \
  --packets-dir "$BASE/r60-real1000-pilot20-packets-v1" \
  --output-dir "$OUT" --endpoint "$ENDPOINT" --model "$MODEL" --json-mode
python3 experiments/r58_quality/r60_real1000_pilot20_local_review.py advance \
  --output-dir "$OUT" --max-cases 5
python3 experiments/r58_quality/r60_real1000_pilot20_local_review.py inspect \
  --output-dir "$OUT"
```

首轮五条审核后检查 `model_reviewed=5`、`model_decisions_advisory`、`model_severe_flag_counts_advisory`；若全REJECT并伴严重标记，立即对少数样本做独立复核，**不要直接继续15条**。若质量输出可靠，再执行三次 `advance --max-cases 5`。新脚本仅接受本地 `127.0.0.1/localhost/::1` 接口；不自动上传小说内容到第三方远程 API。训练准入保持0。


## 2026-11-11 P1 真实100条抽样 PASS → 20条小批质量审核包

Owner CPU `4 passed in 0.05s`，`CALIBRATION_SAMPLE100_READY__NO_REVIEWS`，抽样100/100个不同故事，目标字数层55/38/7，私有目录 `$HOME/.local/share/storyforge/r60/private/r60-real1000-calibration100-v1` 已创建。**P1 抽样 PASS，不代表任何质量审查完成**。

为避免再次因复杂GPU Reviewer耽误主线，新建 `r60_real1000_pilot20_packets_cpu.py`，对现有100条私有位置清单执行**全1000来源冻结摘要验签 + 按池指纹重新计算 sample100**，然后固定抽20条（11/8/1，仍每故事独立）。只在新的 Owner 私有目录创建一份含目标前三条历史与助手目标正文的审阅包；所有原文仅写本地0600文件，不能上传GitHub/CI或打印到对话。此时无AI审核调用、无训练准入。

Owner Mac 在 CI 合格的固定 PIN 上执行：
```bash
set -euo pipefail
umask 077
ROOT="$HOME/workspace/storyforge"
BASE="$HOME/.local/share/storyforge/r60/private"
PIN="$(git -C "$ROOT" rev-parse origin/r60/p4-generation-eval-framework)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/r60-pilot20-cpu-XXXXXX")"
git -C "$ROOT" worktree add --detach "$WORK" "$PIN"
cd "$WORK"
python3 -m pytest -q tests/test_r60_real1000_pilot20_packets_cpu.py
test ! -e "$BASE/r60-real1000-pilot20-packets-v1"
python3 experiments/r58_quality/r60_real1000_pilot20_packets_cpu.py \
  --expand-dir "$BASE/r60-expand-first-600" \
  --sample-dir "$BASE/r60-real1000-calibration100-v1" \
  --output-dir "$BASE/r60-real1000-pilot20-packets-v1"
```
SAFE 预期 `PILOT20_REVIEW_PACKETS_READY__NO_REVIEWS`，20条、层配额11/8/1。下一步用已可用的AI/OpenAI-compatible单主审核器依六维评分+严重证据进行20条**真实**审核，再抽查争议误判。20条工具完成 != 质量评审完成；未经独立参考，不报告误拒率。任何API审核费用/数据外传需另行确认。


## 2026-11-11 P1 分层校准100 真实抽样验收（覆盖下文 P1 抽样待执行文字）

Owner Mac 在 `1b177eb77637c2e2b15def4272cc546c1665e6c3` 实测：4个CPU合成测试 PASS；`CALIBRATION_SAMPLE100_READY__NO_REVIEWS`，来自 **100个不同故事**，目标字数层55/38/7；`database_accessed=false`、`gpu_started=false`、`private_values_emitted=false`，质量审核与训练准入均为0。Owner 私有位置清单已创建于 `$HOME/.local/share/storyforge/r60/private/r60-real1000-calibration100-v1`，不可覆盖或重新抽样。

**P1 抽样子项 PASS**；后续应该从固定100个位置中小批评审，而不是直接对整个1000条再次发起强制双模型GPU审核。先准备20条试点的私有、只读审阅包，按长度比例11/8/1，从100条已冻结抽样中确定性取样，开展单主审核器的真实评分与独立误判复核。只有实质评审结果才能计入质量进度。


## 2026-11-11 Owner P0 真实验收完成（覆盖下文 P0 待执行的历史说明）

Owner Mac 已对冻结 `r60-expand-first-600` 执行原生 `inspect` 与新 CPU 画像，真实 SAFE：
- 合成单测 `6 passed in 0.04s`；
- `EXPANSION_TARGET_REACHED__NOT_ADMITTED`，6种子 +994扩容=1000、20页、扫描400故事；
- `REAL1000_TECHNICAL_PROFILE_PASS__QUALITY_PENDING`，`cases_verified=1000`、`distinct_stories=285`、`max_cases_per_story=4`、三消息链和持久化目标各1000；
- 目标回复长度分布：300–499字545条、500–999字380条、1000–1500字75条；
- 历史实际System、世界组件、R50排除均有1000条状态未核证；这是后续训练前证据项，不应重新当成质量审核硬阻塞；
- `quality_review_performed=false`、`quality_pass=0`、`train_admitted=0`，无数据库访问或 GPU。

**因此 P0=PASS，下一项直接开始 P1质量校准抽样，不再重拉DB或 Tokenizer。**

新增 `r60_real1000_calibration_sample_cpu.py`：调用既有 `frozen_pool` 重新只读验签后，从1000条中按冻结池指纹+case_key确定性选100条，长度层配额55（300–499）/38（500–999）/7（1000–1500），每故事仅1条；只在Owner Mac新私有0700目录保存原始位置+长度层，不复制或公开原文/故事ID，公开输出仅SAFE计数。若任一配额无法满足故事唯一性则HOLD，不降低配额或自动覆盖历史抽样。

Owner Mac 下一命令（仅 CPU、无模型审核调用）：

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
BRANCH="r60/p4-generation-eval-framework"
BASE="$HOME/.local/share/storyforge/r60/private"
EXPAND="$BASE/r60-expand-first-600"
SAMPLE="$BASE/r60-real1000-calibration100-v1"
git -C "$ROOT" fetch origin "$BRANCH"
PIN="$(git -C "$ROOT" rev-parse "origin/$BRANCH")"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/r60-calibration100-XXXXXX")"
git -C "$ROOT" worktree add --detach "$WORK" "$PIN"
cd "$WORK"
python3 -m pytest -q tests/test_r60_real1000_calibration_sample_cpu.py
test ! -e "$SAMPLE"
python3 experiments/r58_quality/r60_real1000_calibration_sample_cpu.py \
  --expand-dir "$EXPAND" --output-dir "$SAMPLE"
```

预期 `CALIBRATION_SAMPLE100_READY__NO_REVIEWS`，`sampled_cases=100`，`distinct_stories=100`，层配额55/38/7。**这只是可重复的独立抽样，不是100条质量已经 PASS。**


> **当前优先级入口；替代同日 GLM/Qwen 全量调试继续扩大的待办。** 单 Agent 负责 `r60/p4-generation-eval-framework`。本任务书只授权 GitHub 代码/文档、CPU-only 只读诊断；**不授权新的远端付费任务、GPU 推理、训练、数据库更改、PR 合并或正式训练准入**。

## 1. 目标与当前事实

目标是把已冻结的真实互动小说历史候选，尽早转换为经可证伪质量筛选的**首批训练候选**，继而做世界/历史/评测隔离、CPU Tokenizer/Collator、训练前审查。禁止以完成 GLM/Qwen 排障作为数据准备的前置条件。

已获得的历史 Owner SAFE：`EXPANSION_TARGET_REACHED__NOT_ADMITTED`，6条种子 + 994条新候选 = **准确1000条**；共20页、扫描400个故事。候选已保存在 Owner Mac `$HOME/.local/share/storyforge/r60/private/r60-expand-first-600`，采集输入为每案目标前3条实际 DB 消息（user/assistant/user）+ assistant 目标；不是完整多轮历史或实际发送的系统提示词。阶段性结构筛选条件为原始 `r60_real_expand_private.py` SQL 的**已完成 assistant、有效邻接角色链、目标长度300–1500、前序 user/assistant 长度边界、无已标记编辑或解析告警、非分叉根会话、每世界不超过4候选**等；这是**采集技术预筛**，并不证明高质量、长上下文完整、真实 System、世界卡或入训资格。

既有 A/B 各1000/1000的 CPU tokenizer 预检及 Owner crosswalk 验证已做；**不重新下载/导出、采样、CPU tokenizer，除非输入配置本身改变**。现有 `r60_real_quality_batch.frozen_pool` 可用原始页/seed、SHA、重复项、结构、Prompt 边界严格只读验证整池。既有 `r60_hf_quality_adapter.py prepare` 已在 Owner 实测1000 staged，`audit` 显示双模型审核0/1000，不能冒称已经审核完毕。

工程对照：GLM 全25份 Snapshot + CPU Replay 完成，模型原始25个 `decision=REJECT`；不是人工真值，剩余8个引用失败与质量区分。Qwen 前6份验签，第7条异常；在得到样本准入增益证据前，不继续为两者付费。GLM/Qwen 已有工程资产保留，不丢弃。

## 2. 立即执行：Owner 冻结池 CPU 状态检查（零 GPU）

使用当前单 Agent 分支的固定 HEAD + 既有工具检查（不改变原20页或种子，不重新访问数据库）：

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
BASE="$HOME/.local/share/storyforge/r60/private"
EXPAND="$BASE/r60-expand-first-600"
PIN="$(git -C "$ROOT" rev-parse origin/r60/p4-generation-eval-framework)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/r60-real1000-cpu-XXXXXX")"
git -C "$ROOT" worktree add --detach "$WORK" "$PIN"
cd "$WORK"
python3 experiments/r58_quality/r60_real_expand_private.py inspect --output-dir "$EXPAND"
python3 experiments/r58_quality/r60_real1000_technical_profile_cpu.py --expand-dir "$EXPAND"
```

只有当 `EXPANSION_TARGET_REACHED__NOT_ADMITTED` 且新 `REAL1000_TECHNICAL_PROFILE_PASS__QUALITY_PENDING`、`cases_verified=1000` 均收到，才视为**冻结候选池技术结构已核验**。若旧实际私有目录已迁移，Owner 用真实目录代入，不通过复制/覆盖原页伪造修复。脚本 SAFE 只显示结构性计数，无正文、ID、哈希，不生成正式准入标签。

## 3. 质量校准：先分层100条，不重启三模型批量

从技术核验通过的1000条中，在 Owner 私有工作区构造**故事分层、长度/复杂度分层的约100条校准子集**。与已冻结 Gold72 的 Development 部分和 Owner v2.1 Rubric 可对齐的才作为校准参考，Locked20、Severe10、R50 保留为评测/回归，不向待校准模型暴露答案。*不能直接把不同来源的 Gold 标签按“第n条”位置匹配这1000条；先用 Owner crosswalk/来源严格匹配，确无匹配则独立新裁决。*

质量判定核心：中文文笔、人物一致、NPC主动性、玩家自主权、局部规则/事实、叙事连续性。严重项必须有**明确支持的语义证据**；引文格式失败与质量不合格独立记录。用已经可用的单主模型/API 对校准样本评分，抽查误拒/漏拒；无法验证严重标记时 HOLD，不直接批量淘汰。若已有 Owner/人工参考，优先复用；不因为某模型25条全部 REJECT 就推断所有候选不合格。

**校准停止条件**：100条抽样内没有经过独立参考验证的稳定误判指标时，不扩大至1000条全量模型审核；改为受控 Owner 案例复核/简化审核合同。不要重复升级 Reviewer 框架来代替判断。

## 4. 第一批训练候选（先50–100，不等待1000条全部完审）

只从达到质量准入评审条件的实例中生成 `TRAIN_CANDIDATES_PRIVATE`（不是 TRAIN_ADMITTED），保留输入页指纹、来源与目标前历史链、原始回复 SHA、审核版本/证据以及拒绝/HOLD 的独立原因。来源 ID 与目标摘要仅用于技术追溯、去重和历史链关联；本轮按 Owner 已明确简化的审核范围，**不把来源权利、隐私、授权证据作为质量评审前置项**。Gold192、R50、Locked regression 等冻结评测集继续保持独立，避免数据泄漏到测试。

世界组件与历史 System 未完整核证的样本，**只能进入技术准备/质量候选，不能直接宣称训练准入**。在 CPU 上完成真实世界切分、Prompt 重建策略、Target 归属、去重、Tokenizer 和 Collator 验证后生成 SAFE 候选计数；训练数据冻结和 SFT GPU 另行授权。

## 5. 阶段闸门及单一事实来源

| 优先级 | 任务 | 完成的真实证据 |
|---|---|---|
| P0 | 冻结1000条只读核验 + 技术画像 | 官方 expand inspect PASS；全1000结构验证 PASS；质量状态仍独立 |
| P1 | 100条分层校准与独立误拒/漏拒评价 | 抽样覆盖、独立参考、Rubric对齐的 SAFE 汇总 |
| P2 | 首批50–100高质量训练候选 | 逐条质量判定与可追溯来源、未覆盖旧数据 |
| P3 | 训练格式/切分/Tokenizer/Collator | CPU 验收报告 |
| P4 | 单独批准训练数据准入/下一次 SFT | Owner 授权及训练预算 |

**明确暂停**：GLM 同25的再次H200、剩余8引文修复、Qwen第7条追加H200、三模型30条配对测试的扩大、1000条双模型GPU强制全覆盖、重复源池导出、重复 Tokenizer/Model Runtime Smoke。只有被证明是 P0–P3 数据交付的真实阻塞，才升级到对应工程任务，并单独批准费用。

## 6. 保留的限制与尚未完成事项

- 1000条采集成功 ≠ 本轮1000条技术画像已重跑 ≠ 质量PASS ≠ 训练准入。
- 旧记录包含 `quality_v1_admitted=0`，不能把首批 TRAIN_CANDIDATES 当作已批准训练。
- 不把3条前文称作完整故事上下文；不虚构当时真实 System。
- 不修改 RolePlay，不合并 PR #30，不上传私有正文/ID/哈希/交叉映射至 GitHub。
- 本次代码创建和 CI PASS 只证明合成代码，无 Owner 私有1000条现场 SAFE 时技术画像仍 HOLD。
