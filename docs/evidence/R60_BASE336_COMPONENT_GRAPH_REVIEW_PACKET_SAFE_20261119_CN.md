# R60 Base336：组件精确复用候选图与独立 Reviewer 收据（SAFE）

日期：2026-11-19。来源：Owner 已在对话上传的八份 Card/Opening 成员文件、冻结八组 roster、World 与 Codex 决策。此次只在当前分析环境读取 Owner 提供的附件，没有访问 Owner Mac 数据库；未运行 HF、GPU、模型推理或训练。所有私有标识、版本编号、内容路径、引文、源 SHA、候选案例位置和原始内容均只在私有 Reviewer 包中；本文件不包含上述值。

## 可复现方法（比此前 6 对 / 22 cases 更完整）

- 将同一个 Story 在 current、archived 与多个 World group 中的记录合并为一个 Story 身份，冻结 roster 的 split 和候选案例位置不变。
- 在 character、characters、opening 三字段的嵌套字符串中匹配 **至少 300 个连续字符完全相同**的文本；排除 URL/ID、极低变化的 48 字符模板种子（唯一字符数 ≤8 或 48 字符内有效内容不足 40）以及出现频率 >50 的模板种子。候选索引用 48 字符种子、24 字符步长，随后向两侧逐字符验证最长连续相同片段。
- 另检查经规范化（JSON 对象键排序、紧凑分隔符）的完整字段 JSON 精确相同，要求字段序列化长度至少 300；该证据不依赖字符串种子。
- **强证据层**：不同 Story 间具有至少 1000 个连续相同字符，或任一个非空且有足量内容的 character、characters、opening 整字段 JSON 完全一致；**扩展候选层**：长 300–999 字符的逐字复用。以上是用于 Reviewer 排序的机械标准，不能自动推断同一语义世界、历史 actual-sent 泄漏或合法 Reviewer 裁决。
- 模板种子采样与文本长度阈值会遗漏部分改写或短文本关联；下列计数不是全量语义重复的上界，也不能用未命中推断 PASS。

| 指标 | 结果 |
|---|---:|
| Card/Opening 文件与 roster 逐组对齐 | 8/8 |
| Current + Archived 记录 | 38 + 21 = 59 |
| 唯一 Story / 受影响候选案例 | 38 / 82 |
| **强证据跨 Train/Validation 不同 Story 对** | **7** |
| 强证据去重 Story / 候选案例 | **13 / 27** |
| 包含扩展候选的跨拆分 Story 对 | 10 |
| 包含扩展候选的跨拆分去重 Story / 案例 | 16 / 35 |
| 同拆分精确复用候选 Story 对 | 16 |

跨拆分强证据来源分布：同组 02 一对、05 两对、06 一对、08 两对，另有同 Story 在多组版本记录中出现而形成的 01/03/06 跨组一对。仅 05 组还有三对 300–999 字符的扩展候选。所有边必须由独立 Reviewer 通过内容与版本上下文鉴别；不能只看数字直接判定污染或移除训练案例。

## 与前一报告的关系

此前 `R60_BASE336_COMPONENT_GRAPH_EXACT_REUSE_SAFE_20261119_CN.md` 记录 6 对 / 11 Story / 22 案例，是较窄的初次审查结果。当前计算基于同一批已上传私有文件，扩大了匹配覆盖并将“强证据”和“扩展候选”显式分层。**本节的 7 对/27 案例与 10 对/35 案例取代旧报告的计数作为下一轮 Reviewer 候选范围**，但任何一项均不是完整、独立的语义冲突裁决。

## Reviewer 执行合同

1. 由与此前候选筛查相独立的 Reviewer 在受控 Owner 私有环境获取 10 条跨拆分候选边，逐边复核两侧 Story、current/archived revision、字段路径、全文上下文和内容来源。
2. 按三态作出 `SAME_SEMANTIC_COMPONENT` / `INDEPENDENT_TEMPLATE_ONLY` / `INSUFFICIENT_EVIDENCE`；提供私有证据引用、理由与 Reviewer 独立性声明。不能由本次自动重合规则同时提供 Reviewer 决定。
3. 同拆分 16 条边及未被阈值涵盖的同名/组织/剧情变体是进一步扩展的上下文，不能自动认定独立。组件归属须按真正的语义实体合并；同一 Story 多组归属不得算作两个 Story。
4. 经独立审定的组件标签在 Owner 私有环境通过已有 `src/storyforge_dataset/world_isolation.py` 的 `validate_component_review_assignments()` / `component_split_conflicts()` 进行冲突验证。该 helper 的结构 PASS 也不等于 Reviewer 独立性、actual-sent、完整保护集覆盖或训练准入。
5. 无实际送达版本 / P2 × R50 完整 Protected/Reserved metadata-only 排除 / 全量历史暴露闭合 / Owner Freeze 前，`P2_C=HOLD`；保持 48 条正式评估提示未生成、train_admitted=0，不进行训练或模型推理。

## 产物边界

- Owner 私有：可复跑的纯本地只读候选提取工具及不含故事正文、但含私有 Story ID、版本、内容路径、源哈希及 Reviewer 空白决定字段的 create-only 私有包，**不可提交 GitHub**。
- GitHub SAFE：本报告仅包含计数、阈值、审查边界和门禁。任何原始附件、私有包、映射、逐案引用、全文、角色名均未提交 GitHub。
- 自动枚举不是一次真正独立的裁决；Reviewer 结束前不能将 `INDEPENDENT_REVIEW` 标为 PASS。

```text
SOURCE_MEMBER_FILES = VERIFIED_8_OF_8
HIGH_EXACT_CROSS_SPLIT_PAIRS = 7
HIGH_EXACT_CROSS_SPLIT_STORIES = 13
HIGH_EXACT_CROSS_SPLIT_CASES = 27
ALL_EXACT_CANDIDATE_CROSS_SPLIT_PAIRS = 10
ALL_EXACT_CANDIDATE_CROSS_SPLIT_STORIES = 16
ALL_EXACT_CANDIDATE_CROSS_SPLIT_CASES = 35
SAME_SPLIT_EXACT_CANDIDATE_PAIRS = 16
INDEPENDENT_REVIEW = PENDING
HISTORICAL_ACTUAL_SENT = NOT_VERIFIED
R50_COMPLETE_PROTECTED_EXCLUSION = HOLD
P2_C = HOLD
P2_B_48_PROMPTS = NOT_GENERATED
TRAIN_ADMITTED = 0
QUALITY_V1_ADMITTED = 0
DB_ACCESSED_THIS_RUN = false
GPU_USED_THIS_RUN = false
MODEL_REQUESTS = 0
```
