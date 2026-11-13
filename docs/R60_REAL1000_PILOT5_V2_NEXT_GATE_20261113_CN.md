# StoryForge R60 REAL1000：Pilot5-v2 诊断结案与下一阶段门禁（2026-11-13）

> 范围：`r60/common2-cpu2-owner` Owner隔离工作线；公开SAFE决策书，**不含故事正文、案例ID、逐案评分、私有目录绝对路径或 Reviewer 自由文本**。本文件不代替冻结Quality-v1 Rubric、Gold Manifest或训练授权。

## 一、已核验的事实

- 冻结候选池的历史状态是 seed6+994=1000，尚无Gold/训练准入。本次仅核验前5条的身份/回执，**不宣称本轮完成1000条重新验签**。
- 已有v1有效 Reviewer 7份；v2明确授权的3次定向请求全部生成不可覆盖回执，1份有效、2份技术HOLD。有效Reviewer合计8份。
- v2两个技术HOLD代码分别为 `QUALITY_FLOOR_DECISION_INCONSISTENT` 和 `SEVERE_FLAG_DECISION_INCONSISTENT`，均是 **B侧模型的决策/约束一致性失败**；不得把技术拒收视为文学质量REJECT，也不能默默修改分数、严重标记或决策。
- 已完成基于可见三消息和目标回复的**非盲**语义证据复核（分析者可见原 Reviewer 观点）：PASS0/HOLD2/REJECT3。此结论独立于 v1/v2 产物保存，不是正式盲审、冻结源变更或Gold自动准入。
- 完整性：Owner提供原始Seed6、v2计划和3个v2回执；结合历史上传5份v1原始回执核对前5案 5/5 和v2槽位 3/3。证据来源和详细引文仅存私有裁决文件 `R60_PILOT5_PRIVATE_SEMANTIC_ADJUDICATION_20261113.json`，**不得提交仓库**。
- 合成代码CI（含v2 crosswalk） `43368264595` Ruff PASS、pytest 67/67 PASS；不将代码CI称为私有语义结论的外部复审。

## 二、当前决策

**PILOT5_DIAGNOSTIC_COMPLETE__PILOT25_HOLD**。本次的5条没有证据充分的Positive Gold PASS，不值得依靠继续扩大真实Reviewer调用来完成Gold筛选。不能把这5例样本结论外推为1000例总体通过率；不宣称全量质量失败。

1. 冻结v1的5份审核回执、v2计划及3份回执；不得删除、覆盖、重启 `advance --max-cases 5` 或再次请求现有v2槽位。
2. **不自动设计/执行 v3 重新补审**。两个失败在同一B侧、具有同种决策自洽问题；在没有新的证据目标、冻结的改进方案和再次明确授权之前，重复调用Reviewer是低信息收益。
3. 对已有实质性REJECT证据的案例，无须为了技术上的双审核齐而重复扣费。要想重新用于Gold，必须创建**新候选文本版本**且重新完成隔离与审核；不能覆盖旧源。
4. 对非盲复核的HOLD，仅能请求可溯源的**更早原始对话、当时适用的世界/人物卡/规则和历史System快照**；缺少这些证据继续HOLD，不得猜测人物真实亲属/年龄、玩家先前承诺或世界禁令。对NPC口头宣称与叙述已确立事实必须分开。
5. Gold、R50完整排除、历史System来源、角色卡/世界隔离、Reviewer独立性、HF CPU Collator与训练均是不同门禁。任何个案文本质量改善也不自动穿透其他门禁。保持 `quality_v1_admitted=0` / `train_admitted=0`。

## 三、可复用工程边界

- 已存在 `r60_pilot5_v2_replay_execute.verify`、`verify_existing_slot`、`r60_pilot5_v2_crosswalk.audit`：只读证据链不再重复开发。
- 继续沿用 `r60_real_private_batch.FLOORS` 六维阈值（中文文笔4、角色一致4、NPC主动3、玩家能动4、规则忠实4、叙事连贯4）和 `SEVERE` 三项严重标记；不另建Reviewer、不放宽门槛、不进行隐式自动修正。
- HF仅在单独模型特定CPU预检必要且授权后复用 `src/storyforge_dataset/token_preflight.py` 与 `skills/storyforge-hf-jobs/SKILL.md`；当前无HF工作。
- 公开只放聚合 SAFE、方法局限、程序状态；逐案原文、精确引文、评分、私有 v1/v2 回执留在Owner私有空间。若要长期保存此次ChatGPT私有裁决文件，由Owner自行保存在0700目录/0600文件中。
- 与其他Agent隔离，禁止直接触碰其它R60分支，不替代Issue #26的独立Owner批准程序。

## 四、恢复下一批审核的必要条件（全部明确）

- Owner明确提出希望验证的改进假设和抽样目标（如文本源质量改善、独立审阅稳定性），指定版本化来源与不可覆盖输出目录。
- 先在纯合成/离线数据验证一致性和失败处理，再在新批准范围内尝试少量真实样本；已有通过的API协议无需再做盲目调试。
- 要求预先冻结停止条件：严重玩家能动性/安全问题、技术不一致率、Reviewer独立性无法证明、样本来源证据不足，任一触发即HOLD。
- **没有来自Owner的单独授权，不调用任何新Reviewer、不启动HF Job/GPU或训练、不扩到Pilot25/995**。

## 五、下一 Agent 交接顺序

1. 阅读 `docs/standards/GOLD_QUALITY_PIPELINE_CN.md`、`skills/storyforge-real-quality-review/SKILL.md`、`skills/storyforge-roleplay-sft/SKILL.md`；HF需求才读 `skills/storyforge-hf-jobs/SKILL.md`。
2. 查看 `docs/evidence/R60_REAL1000_PILOT5_V2_SEMANTIC_SAFE_20261113.json` 和本决策书；仅将SAFE用于公开Issue。
3. 需要补世界事实时先让Owner直接提供**已存在**的历史消息/角色卡/System原件；不写探查脚本或查询生产数据库代替来源。
4. 对HOLD或REJECT只能生成版本化追加意见，不能把新意见写回v1/v2的不可覆盖回执。
5. 结束时在Issue #26记录聚合结果、仍缺门禁与下次授权点，保持Pilot25 HOLD。

**状态：诊断阶段结案，数据入训与扩批均未授权。**
