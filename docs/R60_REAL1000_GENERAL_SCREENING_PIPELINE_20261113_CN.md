# StoryForge R60：1000条真实候选的通用分层筛选方案

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
