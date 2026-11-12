# R60 正向优秀案例集建设计划（Positive Gold）

日期：2026-11-09  
状态：**计划已登记；未启动真实案例审核；未产生新的正向 Gold 标签**

## 1. 目的与范围

R60 Gold72 Development-20 / Locked Regression-20 是从既有 A V3 / B2 审核分歧案例中冻结的规则校准样本，不是从大规模历史数据中按文学质量筛出的优秀回复集。R60 Severe10 是严重问题校准集，也不是正向示范集。

这几组样本继续保持原归属、原标签和原用途，不得重新分组、替换、覆盖或转作 Positive Gold。

本计划新增一条独立的正向案例建设工作线：从已经冻结的 1,000 条真实历史技术候选池中，识别真正值得作为互动小说生成示范的高质量 Assistant 回复。目的不是凑足数量，而是建立有真实质量证据的 Positive Gold；最终能否进入 SFT 仍需独立训练预检和 Owner 决策。

## 2. 当前已知数据状态

- 1,000 条池的扩样阶段已完成：seed_cases=6、new_cases=994、total_candidates=1000。
- 这 1,000 条目前是技术候选，不是 1,000 条已审核的优质回复。
- 既有真实批量审核 SAFE 记录 quality_pass=0、train_admitted=0；它表示当时没有任何已准入记录，不应解释为审核证明 1,000 条都很差。
- `docs/R60_REAL_HISTORY_1000_QUALITY_BATCH_EXECUTION_20261108_CN.md` 已定义可复用的双 AI 质量审核流程，但真实批量审核尚未开始；工具的 `advance` 默认每批 5 条、单次最多 25 条。
- Gold87 / Gold108 是历史版本的质量候选材料；Gold87 的 Reviewer 独立性未证明，Gold108 使用五维 Legacy rubric。两者均不能自动视为当前 Quality-v1 Positive Gold 或训练准入结果，只有另经版本、证据和当前标准映射审查后才能作为参考，不能覆盖其历史状态。

## 3. Positive Gold 内容质量标准

复用现有 Quality-v1 六维，不另造一套与主 Pipeline 冲突的评分系统：

| 维度 | 最低分（1–5） |
|---|---:|
| 中文表达 `chinese_prose` | 4 |
| 人物一致性 `character_consistency` | 4 |
| NPC 主动性 `npc_initiative` | 3 |
| 玩家自主权 `player_agency` | 4 |
| 规则忠实度 `rule_fidelity` | 4 |
| 叙事连贯性 `narrative_continuity` | 4 |

严重问题旗标继续使用现有三个字段：`serious_player_agency`、`hard_fact_or_ban`、`safety_exclusion`。任何已确认严重问题都不能成为正向示范；存在未解决的上下文、规则或评审分歧则保持 HOLD。

六维达标只是内容质量筛选门槛，不等于 Quality-v1 训练准入。不得把三维 `NOT_SUPPORTED` 直接等同优秀，也不得把 R60 三维严重问题审核替代六维文学质量评价。

## 4. 建议执行流程

### Stage A — 先做小批校准，不做全量

1. 仅使用已冻结的 1,000 条候选池；不得重新扩样。
2. Owner 先确认两位 AI Reviewer 的模型身份、独立调用方式、盲化和互不共享结果；如果不能证明独立性，结果只能是 advisory，不得伪装成独立双审。
3. 按现有 `experiments/r58_quality/r60_real_quality_batch.py` 的受控流程，从小批开始。默认每批 5 条，单次最多 25 条；不一次性发起 1,000 条。
4. 两位 Reviewer 分别给出六维分数、严重问题旗标、具体目标证据和理由；任一模型未完成、输出不合 Schema、证据不足或出现分歧，保持 HOLD，不补分、不猜测、不自动改判。
5. 先评估小批的评分一致性、HOLD 原因、严重问题漏检和优秀样本实际数量，再由 Owner 决定是否继续扩批。

### Stage B — 建立 Positive Gold 候选

仅从完整双审且满足六维最低分、无严重问题、无未解决 HOLD 的记录中形成候选。保存原始双审结果和独立的 Owner disposition；不得重写原始回复或把 AI 建议标成 Owner 标签。

对候选按 Story / 角色 / 场景 / 回复类型做分布检查，避免 Positive Gold 只集中于少数故事、角色或单一场景。样本数按真实结果决定，不设必须达到的 PASS 配额，不为了数量降低门槛。

### Stage C — Owner 确认与冻结

1. Owner 对候选逐项确认或采用预先批准的抽检方案；未确认项目不能标记为 Owner-approved Positive Gold。
2. 冻结独立 manifest、每条案例的盲 ID、原始 target/input 指纹、双审回执、Owner 决定、Rubric 版本和 SAFE 汇总。
3. Development-20、Locked Regression-20、Severe10、旧 A/B/C、Gold87、Gold108 保持只读且各自用途不变。
4. Positive Gold 冻结后，另做训练输入完整性、上下文/世界一致性、split 和 tokenizer/collator 预检。通过这些门槛并获得单独授权前，不编译最终 train/validation/test，不提交 GPU Job，不启动 SFT。

## 5. 数据标签定义

- `POSITIVE_GOLD_OWNER_APPROVED`：六维达标、严重问题无触发、无未解决 HOLD，且 Owner 已确认。
- `POSITIVE_CANDIDATE_AI_ONLY`：双 AI 建议达标，但尚未完成 Owner 确认；不可作为 Owner Gold。
- `HOLD`：上下文不足、证据不足、审核不完整或存在未解决分歧。
- `REJECT`：至少一个严重问题成立或六维未达到最低门槛。

这些标签描述内容质量筛选结果，不自动授予训练准入。

## 6. 资源与授权边界

本计划本身只登记方法，不启动审核。开始真实小批前，需要 Owner 单独明确确认：
- 使用哪两个具体模型 / API；
- 是否确实满足独立评审条件；
- 小批数量（建议先 5 条，最多 25 条）；
- 是否允许将私有输入发送给相应模型服务。

本计划不授权 1,000 条全量审核、HF Job、GPU、模型训练、SFT、数据库写入或修改任何既有 Gold / Checkpoint。任何后续扩大范围均须另行明确批准。

## 2026-11-12 真实1000候选精筛启动决策（覆盖本文件早期“仅计划”状态）

Owner 已回复“按建议推进”，批准**切回真实1000候选的质量精筛主线及首批5条的准备工作**。这不是对未指定的第三方 API 私有数据外发、GPU 费用、全量1000条自动执行、训练准入的授权。

当前已完成：
- 1000条技术候选池冻结：6个seed + 994条扩样；禁止再扩样或替换原池。
- 两条 Common2 包装通用 System 的真实 Qwen3.8 Swift Collator 技术验收、原始 HF Bucket SAFE 回执独立验收：2/2 PASS，**仅为训练输入技术证据，不是1000条文学质量筛选结果**。
- 现成审核器 `experiments/r58_quality/r60_real_quality_batch.py` 已支持 `init / advance / inspect`、每批5条、每次最多25条、私有不可覆盖回执；不需要重新开发或重跑 HF CPU。

现在应启动：
1. **PILOT-0（本地非外发预检）**：只读 `r60_real_expand_private.py inspect`，复核1000池来源/页完整性；核对两种模型实际可用、独立会话与不共享评分、API 配置，测试现有本地合成代码/pytest；不读取 R50 正文。
2. **PILOT-5（首批5条）**：选用经过实际核实的两个模型，首批相同的5条候选两模型各审核一次，使用冻结六维门槛（4/4/3/4/4/4）和三严重旗标；仅写入本机私有0600回执。使用第三方 HTTPS API 前必须单独确认服务提供方和这5条私有正文的外发范围；没有确认则停止在PILOT-0。不能根据不同批次的汇总判定逐案一致。
3. **PILOT-25（再25条）**：仅在首批5条完成双审、独立来源绑定、引文与语义一致性人工/Owner复核、Reviewer独立性和严重标记误报评估后再批准；后续每批最多25条，禁止不受控自动循环。
4. **剩余970条**：经25条阶段显式批准后再分批精筛；允许保留真实HOLD，不追求固定正向样本配额。

这是质量候选建设流程，不是直接训练：`quality_v1_admitted=0`、`train_admitted=0`、`training_authorized=false`。世界设定隔离、R50完整排除、历史System/最终输入设计、部署模板兼容和冻结训练集均保持独立待验。旧P2校准材料和既有A/B/C/GLM/Qwen并行Agent输出不覆盖、不得被冒充为新版逐案双审。

执行手册：`docs/R60_REAL1000_PILOT5_START_20261112_CN.md`。当前证据支持进入PILOT-0，尚无真实PILOT-5评审回执，不声称1000条已开始AI实际评分。

## 7. 当前结论

**先完成 R60 P2 的规则校准与回执验证；Positive Gold 作为独立工作线，先冻结方法，再经 Owner 授权做小批真实筛选。** 当前没有证据证明 Gold72 Development-20 是优秀案例集，也没有证据证明 1,000 条候选池中已有任何一条达到当前 Positive Gold 标准。
