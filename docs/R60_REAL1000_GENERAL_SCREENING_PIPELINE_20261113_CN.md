# StoryForge R60：1000条真实候选的通用分层筛选方案

> **路线已确定（2026-11-13，Owner选择方案B）**：**直接复用已验真1000条的现有HF A/B盲审Stage，分别进行全量独立文学双审，仅对冲突、严重标记、未知来源等进行证据级仲裁**。不再新增一次覆盖1000条的语义预筛，也不重新Stage。后续以 `docs/R60_REAL1000_ROUTE_B_HF_DUAL_REVIEW_20261113_CN.md` 为**唯一新执行规划**；本文件第10节A/B对比只保留历史备选方案说明。Owner选择路线不等于授权HF付费CPU/GPU、私有数据上传或训练。


> 2026-11-13，Owner隔离分支 `r60/common2-cpu2-owner`。本文件取代“只围绕Pilot5失败样本持续补审”的规划方向，但**不改冻结来源、六维标准、现有回执或任何训练授权**。设计与代码在GitHub合成环境验收，不代表真实1000已审核。

## 0. 目标和边界

**目标**：从冻结1000条真实候选中高效找到**有来源依据、语义可靠、双审核验充分、能纳入后续训练候选**的数据；同时解释每条为什么被排除或暂缓。不是提高某5条的PASS率，也不是让1000条直接训练。

- 输入：已冻结6+994、1000条来源，有`history_messages`三消息、`target_text`目标回复及来源/哈希；保留原来历史System是否真正发送的未知性。
- 输出：源合规、结构、质量/双审、语义、隔离、训练技术六个维度分别有**不可覆盖的版本化证据**；全量统计和唯一私有 Manifest 的可追溯事件。
- 样本单位：不能把“3条历史+1条目标”当作完整世界事实。对缺失先前历史/卡片的判断标`UNKNOWN`；不得凭空认为承诺、关系、年龄必真或必假。
- 保留既有`Quality-v1` 六维阈值和严重标记，绝不因产量目标自动调低。**Quality候选 != Gold Owner批准 != SFT训练准入**。

## 1. 模块复用，不创建第三套Reviewer

| 阶段 | 复用实现 | 精确职责 | 下一门禁 |
|---|---|---|---|
| 0 来源冻结 | `r60_real_expand_private.py`、`r60_real_quality_batch.frozen_pool` | 1000/1000、不可变页/源SHA、来源追踪；不访问生产DB | source_verified |
| 1 技术/结构 | `src/storyforge_gold_quality` + 原`r60_real_private_batch` | 角色/目标存在、完成态、去重、同故事隔离线索、源历史与训练System provenance 区分 | structure_hold独立计数 |
| 2 内容评审 | `hf_literary_review.py` + `hf_blind_stage.py`（或现有本地Reviewer兼容层） | A/B对同一目标独立盲审、固定revision、6维+3严重项+连续精确引用 | 完整有效双审 |
| 3 技术HOLD | 原持久checkpoint与 `r60_real_ai_dual_review.parse_model_response` | JSON/协议/评分不一致与正文HOLD分流；错误码单列，不假造REJECT | 另版本排障，不覆盖 |
| 4 语义仲裁 | `storyforge-gold-quality append-review / append-exclusion` + 原Quality-v1标准 | 只在必要时对PASS冲突、严重标记、规则/世界证据缺失做独立证据仲裁 | Owner确认 |
| 5 Gold候选/训练门禁 | `storyforge-gold-quality validate / report-safe`、`quality_v1.py`、既有HF CPU核心 | 来源/SFT去重/世界隔离/R50元数据排除、历史System与Collator、Owner批准 | 另行授权，不自动训练 |

`src/storyforge_gold_quality/real1000_screening_policy.py` 是**纯函数状态分类器**，仅供薄适配器复用，不能调用API、读取故事、覆盖回执或直接发布Gold。输入必须先经现有模块验真。公开`summarize`只输出聚合，`expected_total`固定1000，25条进度不会伪装为全量完成。

## 2. 通用状态机（各类不得混用）

1. `SOURCE_HOLD`：来源身份/哈希/角色及上下文绑定缺失，不能审核。
2. `TECHNICAL_HOLD`：调用失败、JSON不合约或分数/最终决策矛盾；模型证据无效，不算文学HOLD/REJECT。
3. `AWAITING_DUAL_REVIEW`：有合法来源，但有效独立审阅不足2。
4. `SEMANTIC_REVIEW_REQUIRED`：双审冲突、HOLD、REJECT或缺少证据级裁决；模型投票数不是仲裁。
5. `SEMANTIC_HOLD`：源绑定语义复核明确不能确认；需补上下文，不强行给PASS。
6. `CONTENT_REJECT`：有独立来源绑定的实质问题/安全或严重玩家能动性证据，不必为“凑两份审核”继续扣费；该状态是当前版本拒收，不可覆盖原模型回执。
7. `QUALITY_CANDIDATE_NOT_ADMITTED`：仅当来源可验、两份有效PASS、无技术缺口且完成独立语义PASS；后续世界/R50/System/Owner/Collator门禁**仍不能自动PASS**。

优先级：来源HOLD最高；有单独、可信、来源绑定的语义REJECT可先拒收而不用等待无意义的模型重试；语义HOLD单列；缺有效Review留技术/缺双审HOLD；内容候选始终保持`NOT_ADMITTED`。未有语义证据的模型REJECT也留待证据核验，不自动认作真实内容排除。

## 3. 不偏向某一个故事的筛选和预算控制

### 3.1 先做全集离线预筛（无需模型调用）

- 验证1000条已冻结来源及完整性，只复用已有源验证器。
- 完整技术分布：可见角色顺序、未完成/空目标、重合上下文、故事/会话分布、文本和历史重复、上下文token预算疑点。**不得只报告“可用1000”而隐瞒内部风险**。
- 分层单位：按`story_id`/来源档案/目标文本长度区间/技术异常标签划分，用**冻结hash排序 + 确定性的去重与跨故事配额**，不能用Pilot5表现来挑同一风格或排除整个故事。故事ID仅在Owner私有空间。
- R50排除必须来自已确认的真实保护集**元数据索引**；没有索引则标`UNKNOWN`并禁止训练冻结，不能擅自读取R50正文。

### 3.2 质量评审分阶段、每段验收

| 阶段 | 覆盖范围 | 用途 | 执行要求 |
|---|---|---|---|
| 全量无模型预筛 | 1000 | 来源+结构+去重/隔离风险基线 | Owner Mac / 合成单测，SAFE统计 |
| 代表性小样本 | 与已审5条分离的预先固定跨故事分层样本（建议25） | 核验通用Reviewer质量、严重标记、引用和技术失败比例 | **需Owner单独审核执行计划并授权请求/费用** |
| 中等规模复核 | 建议追加至100，按预先固定配额 | 观察跨故事差异、校准语义仲裁工作量 | 前段验收PASS并再次授权 |
| 剩余候选 | 最多1000，单段建议25～100条 | 分段记录，遇重大偏差停机；不是无人值守1000调用 | 独立批次checkpoint、SAFE进度、Owner审核 |

建议的25、100是**待批准的样本量规划**而非既有执行权或固定Gold阈值。Owner可批准其它规模，但必须在运行前冻结抽样、Reviewer/版本、最大请求数、最长时间、成本上限和停止条件，严禁事后挑好看的样本替换。

### 3.3 通用止损条件

- 来源SHA、故事去重、候选身份绑定、reviewer blind crosswalk出现不一致：立即STOP，保留原件。
- 严重标志与`decision`不一致或PASS低于六维门槛：只记`TECHNICAL_HOLD`，**不自动修分/改判/重新请求**。同一批反复出现则暂停下一批，进行结构合同诊断；具体频率门槛需运行前冻结而不是事后改变。
- 已确证严重玩家代写、明确规则冲突、安全排除：实质`CONTENT_REJECT`，不得为了补齐A/B继续外发本条。
- 缺当时世界/角色卡、历史System、Reviewer训练独立性、R50排除等事实：当独立的下游门禁HOLD，不得靠假设或模型“信心”升级。
- 推理任务只做审核，GPU推理（如采用HF）≠训练GPU，**两者均另需明确Owner许可**。

## 4. 两条既有执行路线如何取舍

- **主线建议：复用已完成Stage的HF A/B盲审路线**。公开历史SAFE表明`r60_hf_quality_adapter.py prepare`已在Owner Mac完成并创建1000的 A/B 隔离输入；2026-11-08 `audit`为A=0、B=0、完整对=0。不能重复`prepare`覆盖旧Stage；先Owner只读`audit`，再逐步对接当前`hf_blind_stage`的checkpoint与纯状态分类器。历史HF操作手册部分本地挂载示例已明确废弃，实际执行必须遵循当前`skills/storyforge-hf-jobs/SKILL.md`和HF Guard、组织私有Bucket约束。
- **本地Claude/DeepSeek路线仅保留历史兼容和短批验证**，不能因Pilot5出现两个B侧一致性HOLD就切换到新的“修分”Reviewer或改变冻结整体标准。
- 两条路线**不可相互拼接成假装独立的A/B对**。同一case须有可验证源身份、盲审映射、模型revision、完整输出及其来源。不同路线的结果需独立事件/Owner批准后才能比较，不能默认替换既有Reviewer。

## 5. 当前实证、缺口与下一Owner动作

- Pilot5已提供诊断样本：v1有效7+v2有效1；两份B侧技术一致性HOLD。后续证据级非盲复核PASS0/HOLD2/REJECT3，仅用于**调试流程和定义风险分类**，不得据此估计全量1000的合格率。
- 当前最大的有效行动不是重跑这5例，而是在Owner原有冻结1000来源、已Stage HF A/B输入上**进行只读总体检查**，取得结构风险、可见故事数量/分布、去重指标、待审核个数与既有Stage/输出checkpoint SAFE。当前历史审阅样本与1000 A/B盲审入口仍是**不同流程**；需要在私有交叉映射确认身份、不能直接合计。
- 必须先冻结来源/分层抽样清单及两条Reviewer线路的版本归属，才能有效估计筛选成本/产出，决定是否用HF GPU质量审阅，或选择有限本地Reviewer调用。

## 6. 向Owner交付的通用SAFE报告合同（不得出现逐案私密值）

必须分开报告：
- `source_total`、`source_verified`、`structure_holds`、`duplication_holds`、`strata_story_count`（数量而非ID）；
- `review_requested`、`review_valid_a`、`review_valid_b`、`review_pairs_complete`、`review_technical_holds_by_code`、`review_decision_counts`；
- `semantic_pending`、`semantic_hold`、`semantic_reject`、`quality_candidates_not_admitted`；
- `owner_independence_proven`、`r50_metadata_exclusion_verified`、`world_isolation_verified`、`historical_system_snapshot_verified`、`cpu_collator_verified`；
- `quality_v1_admitted`、`train_admitted` 必须真实证据，缺证据固定0。

**不允许“模型认为PASS”直接等于“高质量可训练”。**

## 7. 执行授权状态

本次只授权代码/文档/合成CI层面的通用方案推进；**不授权下一批私人文本外发、HF Job费用、GPU、训练、更新正式Gold Manifest或修改任何冻结Owner v1/v2回执**。如需这些动作，提交精确新计划/成本界限，由Owner再确认。

## 8. 2026-11-13：1000条冻结源离线结构预筛已实现（先跑，不发模型请求）

当前HF Stage只读audit状态为 `HF_QUALITY_DUAL_PARTIAL__NO_ADMISSION`：`cases_total=1000`、`model_a_reviewed=0`、`model_b_reviewed=0`、`complete_pairs=0`、`quality_decisions.HOLD=1000`。**这是1000条尚未文学审核，不是1000条被结构或内容判定不合格。** 不重复Stage prepare、不启动HF Jobs。

新增一次性薄适配器：`experiments/r58_quality/r60_real1000_offline_prefilter.py`。先调用 `r60_real_quality_batch.frozen_pool` 对完整1000来源/封存页/SHA验真，再执行完全离线的确定性检测：
- 必要源字段及历史身份、至少4轮目标索引；三条历史必须为user/assistant/user且内容非空，目标正文非空。
- 仅对**确切相同**目标正文或完全相同历史+正文做稳定去重，保留来源冻结顺序中的第一条，将后续精确副本标 `EXCLUDE`。
- 同一三消息历史对应不同目标只标 `CONTEXT_HOLD` 请求后续来源核对；不同故事、人物关系、未知卡片规则、实际System不可由脚本推断，绝不做语义拒收。
- 如果不可变源SHA、原始消息ID重复或源文件完整性出错，则**整体安全HOLD**，不私自把该问题记录为可忽略的内容排除。
- 输出：`STRUCTURE_PASS`、`EXCLUDE`、`CONTEXT_HOLD` 三类，以及固定原因码的聚合SAFE；不做`quality_v1_admitted`，不输出任何私有故事正文。逐案身份与原因写入0700/0600私有目录中10份create-only分片，最后生成完整写盘标记；每份不可覆盖，不回写旧1000池或已Stage HF输入。

Owner Mac 在原隔离工作树上（仅需已有私有文件，无API Key）：
~~~bash
set -euo pipefail
set +x
umask 077
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
test "$(git branch --show-current)" = "r60/common2-cpu2-owner"

PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
BASE="$HOME/.local/share/storyforge/r60/private"
OUT="$BASE/r60-real1000-prefilter-v1"
test ! -e "$OUT"
"$PY" experiments/r58_quality/r60_real1000_offline_prefilter.py \
  --expand-dir "$BASE/r60-expand-first-600" \
  --output-dir "$OUT"
~~~

成功SAFE为 `REAL1000_PREFILTER_COMPLETE__QUALITY_NOT_EVALUATED`，汇报 `cases_total=1000`、`structure_pass`、`excluded`、`context_hold`、`reason_counts`、`quality_reviewed=0`。合成CI [Ruff及pytest82/82 PASS](https://github.com/sunxu/storyforge/actions/runs/43395852572)；**Owner Mac尚未返回真实1000预筛SAFE**，不得猜测实际合格/排除数字。

注意：预筛只是确定性技术质量门禁；叙事连贯、人物关系与玩家能动性属于实质内容判断，无法只靠三消息格式证明。下一阶段须根据实际SAFE确认筛后有效数量，再以冻结抽样+已有HF盲审链对**预筛通过的候选**开展内容评级；需要先做支持筛后子集的独立版本化Stage/路由验收，不能把旧已Stage的原1000条直接当作已过滤子集，也不能暗改既有盲审输入。新真实模型请求/GPU/收费CPU/训练仍需Owner单独授权。

## 9. Owner Mac 全量离线预筛实测 PASS（2026-11-13）

Owner回传真实 SAFE `REAL1000_PREFILTER_COMPLETE__QUALITY_NOT_EVALUATED`：`cases_total=1000`、`structure_pass=1000`、`excluded=0`、`context_hold=0`、`reason_counts={}`，`model_requests=0`、`quality_reviewed=0`、`train_admitted=0`。此结果只证明**冻结字段、三消息边界、精确重复等当前确定性预筛通过**，不能推断历史世界/人物规则完备、玩家能动性、语义连续性或Gold质量已通过。R50排除、历史System和世界隔离仍未验证。

此前Owner实际执行的HF Stage `audit` 仍是 `cases_total=1000`、A/B有效审阅0/0、`complete_pairs=0`、`HOLD=1000`，全部指向“未文学评审”。

### 预筛与旧Stage不可覆盖的只读身份交叉核验

新增 `experiments/r58_quality/r60_real1000_prefilter_stage_crosswalk.py`，复用 `r60_real_quality_batch.frozen_pool()` 和 `storyforge_gold_quality.hf_blind_stage.verified_stage()`，核对预筛10个分片、完成标记及Stage A/B盲审crosswalk的每一条身份、来源哈希、代码/输入锁定，不发模型请求。兼容已存在Owner预筛结果结尾的字面反斜杠n标记，**只读识别，不编辑Owner历史文件**；未来新产物写盘的换行已修复。

Owner Mac：
~~~bash
set -euo pipefail
set +x
cd ~/workspace/storyforge-r60-4router-review
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
BASE="$HOME/.local/share/storyforge/r60/private"
"$PY" experiments/r58_quality/r60_real1000_prefilter_stage_crosswalk.py \
  --expand-dir "$BASE/r60-expand-first-600" \
  --prefilter-dir "$BASE/r60-real1000-prefilter-v1" \
  --stage-dir "$BASE/r60-hf-quality-first-1000"
~~~

由于当前1000条全部结构通过，若来源身份/字节完全一致，预期 `PREFILTER_STAGE_ALL_ELIGIBLE__CONTENT_REVIEW_PENDING` 和 `stage_identity_verified=1000`。若发生版本漂移或文件格式/权限不符，则 `PREFILTER_STAGE_CROSSWALK_HOLD`；**不能删除旧预筛或盲审Stage绕过**。如果未来筛选结果不全为通过，状态为 `PREFILTER_STAGE_SUBSET_REQUIRED__NO_MODEL_REQUEST`，先重新版本化Stage并明确授权，不修改已有Stage。

### 后续内容筛选的成本策略

预筛排除为0意味着任何进一步“上下文不符合要求”的排除，必须引入**语义证据**而非新正则或臆测历史卡。建议先进行跨故事分层的小规模内容判断基准，记录有明确来源引文的「局部矛盾」「玩家代写」「难以判断」与「内容通过」四种情形，再冻结审核策略和预算。不能用Pilot5 PASS率估计1000的质量；是否采用“单模型先查上下文，再对候选双审”必须先明确**整体成本、漏检风险和现有双审完整性/Gold Manifest对全覆盖的要求**。在批准前不得调用新模型、GPU、收费CPU或训练。


## 10. 2026-11-13 实测交叉核验正式PASS：结构预筛关门，启动内容审核方案设计

Owner返回不可推断的真实 SAFE：`PREFILTER_STAGE_ALL_ELIGIBLE__CONTENT_REVIEW_PENDING`、`cases_total=1000`、`prefilter_pass=1000`、`prefilter_excluded=0`、`prefilter_context_hold=0`、`stage_identity_verified=1000`、`model_requests=0`、`staged_model_reviews_verified=false`、`quality_v1_admitted=0`、`train_admitted=0`。之前HF Stage只读audit为A/B=0/0、完整对=0。**冻结源 ↔ 预筛结果 ↔ 已建A/B盲审输入，三者在当前身份校验范围内一致；本轮未验证任何新的模型审稿内容**。

**阶段决策**：停止添加基于正则/格式的排除器；保留已Stage的全部1000输入，进入内容语义质量审核设计。现有旧Stage适用1000原始候选，无须重新prepare；如果未来决定只对部分候选双审，需要新版本子集路由/Stage并证明交叉映射，不允许悄然筛掉行。

### 10.1 内容前置预筛与直接双审的两种经济路线

- 路线A（先语义硬伤门禁，再双审）对每条预筛一次，且对通过者再进行A/B评审。总成本约为 `1000×C_pre + N_pass×(C_A+C_B) + C_arbitration`；风险是预筛的**错误排除**，须对被筛掉的样本做独立抽检并核对原文精确证据。
- 路线B（直接已有A/B Stage双审，按需要触发语义仲裁）成本约为 `1000×(C_A+C_B) + C_arbitration`；不存在第一层的额外误筛，但会在明显不合格的文本上支付双审成本。
- 只有 `1000×C_pre < (1000-N_pass)×(C_A+C_B) - ΔC_arbitration` 且被错拒的风险达到预先约定的上限时，路线A才可能更划算。公式是规划估算，不代表已测量的实际金额/漏检率。不要因Pilot5两条技术HOLD就认定某模型大规模表现。

### 10.2 无真实推理的下一阶段准备

1. 确认现有HF双模型Stage代码SHA、模型revision、A/B盲审映射、CPU Tokenizer/资源守卫的既有SAFE；不重复Stage prepare，也不新建第三套模型Reviewer。
2. 用**独立于Pilot5**、分散故事且运行前冻结的样本评估两条路线：相同冻结来源、相同六维rubric/严重标记，统计有效率、能识别的严重语义问题、审查成本、引用真伪及误筛审查工作量。建议初步25条只是规划，不表示已经获准调用。
3. 若采用路线A，语义前置输出必须是`CLEAR_FAIL_WITH_EXACT_EVIDENCE`、`NEEDS_CONTEXT`、`PROVISIONALLY_CONTINUE`等独立版本化事件；前置环节不能发布最终Gold PASS，且对`CLEAR_FAIL`做一定比例的独立复核，防止丢失高价值训练候选。
4. 对模型审核技术错误、JSON/评分自相矛盾分流为`TECHNICAL_HOLD`；不得按文本内容质量计入拒绝率，也不得自动修改原判。
5. 只在预先冻结的请求数、成本和停止条件内执行；HF GPU即使只推理、不训练也需要Owner明确授权，任何付费CPU、对外私有数据发送、Gold Manifest写入及训练同样单独过门禁。

**当前可确定事实**：1000条结构可进入内容审核；尚无1000条的语义筛选结果、完整双审回执或可发布训练数据。
