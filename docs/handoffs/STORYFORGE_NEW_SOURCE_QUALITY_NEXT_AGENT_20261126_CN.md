# StoryForge — 新 Agent 接手提示词

2026-11-26 · Owner 已批准新来源数据建设方向；以下为可直接复制给新 Agent 的执行提示词。

---

你是 StoryForge 的下一任执行 Agent。仓库：https://github.com/sunxu/storyforge 。唯一产品目标是让 Qwen/Qwen3.8-27B 的中文互动剧情质量可证明优于 Base；不要偏离主线，不重复开发，遵循最小化原理、最短实现路径。

## 首次接手必须核对

1. 读取现行任务书 `docs/plans/STORYFORGE_NEW_SOURCE_QUALITY_MAINLINE_TASKBOOK_20261126_CN.md`，再看 `docs/REUSABLE_ASSET_INDEX.md`、`docs/plans/STORYFORGE_QUALITY_ENGINEERING_CONSOLIDATION_TASKBOOK_20261124_CN.md`、`docs/quality/GOLD3_OWNER_LOCAL_QUALITY_DIAGNOSIS_20261125_CN.md`。验证实时 main HEAD、相关 PR 和代码所在 ref。若文档 PR 尚未合并，以该 PR 固定版本和 Owner 当前明确决议为工作依据，不将其冒称已合入 main。
2. R60 已冻结 NO_PROMOTE，R61 不启动。历史 Gold12 已诊断 6/12：优先原始候选1、待修订参考1、不建议正向准入4；剩余6不再筛选。优先候选与已知204历史 Story、R50 五 Story、最终 P2 八 Story 精确无重叠；503版本特征初筛无命中，但完整保护集与语义独立未验证，独立双审未完成，正式准入0。保留旧候选作参考，不再投入时间补齐其历史证据，不重跑评审或历史搜索。旧 R59 五条等 HOLD 不变。Gold48、E1/E4 已暴露用于诊断，禁止转入训练或充作新独立测试。
3. 已观察到 Base336 实际输入只有三条历史消息加末轮 Assistant、无 System，目标偏短；Gold48 NPC/连续性评分下降，E1/E4 的 R60 输出较 Base 短，但原因尚未证明。新数据要保留完整适用故事规则和有效历史，而非机械加长回复。

## 当前执行状态（2026-11-26，优先于历史试点说明）

已完成四世界16条原始回复筛选、World04 两条候选冻结、Owner 权利和离线重建授权、既有 Source Stage 实测2/2、正文任务 System 定稿、盲审材料2/2、隐私模式预检及 Owner 人工隐私确认。原始目标、历史正文、原始组件证据不改。正文监督不等于完整应用输出；不是生产 Prompt 精确重放。不要再采集、重建、调整输入或重复隐私确认。

World04 Base336/History32/R50 known5/P2 精确 ID 零重叠；375+8 个现有版本字段/姓名初筛零命中，History32 版本级未完成；完整保护集及语义独立仍 HOLD。不再无限追查历史名册，绝不访问 R50 密封正文。

Owner 已批准限定 HF 双审及外发、不设费用上限，随后批准新路由。旧路由 4 次 HTTP 400，真实有效评审0；HF Router 合成2/2 PASS，正式评审4/4 HTTP 200、有效3/4（均PASS）、双PASS候选1、有效成对判定分歧0、有效评审低于门槛/严重标记均零。总38005 tokens、报告费用$0.105284028。剩余一份原始PASS声明9项证据中7项逐字匹配、rule_fidelity及hard_fact_or_ban两项无精确来源，保持HOLD；原始回执未改，诊断新增模型调用0。见 [资产索引](../REUSABLE_ASSET_INDEX.md) HF调用规范。禁止重试旧路由、重复合成测试、重复有效评审或改写引文；本轮不补评另一候选。Owner 已明确确认唯一双PASS候选四项人工核查通过（原始回复质量、上下文适用、无未来信息、评审证据可信度），内容质量审核收口；Owner 本机 SAFE 已确认四项声明私有落盘、绑定两份原始回执及冻结输入/目标；有限来源核查确认原始包和选定目标包均绑定，locator、卡、原始消息、模型绑定存在，locator 含 version/created_at/updated_at、卡含 version；正式 staged row 三项来源/世界图字段仍缺失，历史时间点、完整保护集和语义隔离未验证。World04 冻结为 1 条质量批准但来源隔离 HOLD 的候选，另一条保留审核 HOLD。结束本批核查，不补评、不无限追查旧历史、不提前开发 corpus 扩展、不提交 CPU Job；正式准入0。后续如获 Owner 新批准，优先在采集之前冻结来源版本时间点并明确可执行的保护集/世界组件审查范围，复用既有 Source Stage/World Isolation/Quality-v1，不新建系统。前瞻采集不自动解决历史保护集完整性，未闭合仍 HOLD。GPU/HF Job/训练/晋升/R61未授权。

## 保持不变的试点与准入合同

后续另获批准的新试点才继续采集，优先 Owner 可控原创世界、3–5条真实原始目标（可少收或0）。不能将本对话生成的续写冒充真实历史。
- 采集前冻结来源版本、世界组件与用途（首个世界为 train-candidate，不能在同世界拆出独立验证/测试）。核验新创作、非已知故事衍生、保护集元数据排除；未知范围继续 HOLD。R50 密封正文绝不访问。保留原始输入/输出及真实有效历史、当前 User、必要生成参数与版本摘要；任何离线编排明示并经批准，不混入未来信息。
- 选择真正推进剧情、尊重玩家自主权、保持事实/人物/规则连续性的原始回复；有明确字数/格式要求才据此评价，不机械筛选长度。无教师改写、无伪造历史。进行隐私清理并记录转换绑定，原件不覆盖。
- 沿用现有六维门槛 4/4/3/4/4/4、三类严重标记、独立盲化双审和 Owner 证据；助手自评不代替独立评审。争议 HOLD；未获授权不调用付费评审。首个新世界不证明泛化，也不意味着可以训练。
- 先复用主线 Quality-v1、冻结 SFT Skill/History Recovery/World Isolation、现成 SFT compiler 和 HF CPU preflight；具体 ref 见资产索引。现行 `quality_v1.py` 只接受 `gold195` 和 `r58_round1`，新数据不能冒用旧批次。仅在真实样本已形成、确有合同阻塞时，提出必要的最小 corpus 登记扩展与回归测试，不放宽质量、来源、隔离、隐私和 Owner 门禁，不整体迁移 Draft PR。
- 符合前置后才准备完整 System＋有效历史＋当前 User＋末轮 Assistant 的私有编译候选；仅监督最后一轮，复用真实 Qwen/ms-swift last_round/Collator 的 HF CPU 验证。Mac 只做标准库和 CLI，不安装本机模型框架。CPU 预检依现行适用授权执行，不自动授权 GPU、推理或训练。

## 不做的事

不再补旧 Gold 或扩大历史名册搜索，不重新做 R60 推理/评审；不新增评分器、隔离器、Runtime、数据管线或架构整理任务；不写生产数据库、不擅自发起模型/付费服务调用、训练、部署、晋升，不改冻结证据。不把私有材料、逐案 ID、哈希、引文或凭据写入 GitHub/日志；Owner 域私有文件0600、目录0700。数据库若后续有明确批准，只能只读；不读取 R50 sealed 正文。

## 首次回复与交付

先用简短报告说明实际 HEAD、已核对的权威文档、能复用哪些现有能力、首批新源材料是否已经存在。然后执行无需新增权限的最小动作；没有真实素材时，明确只缺哪一个 Owner 提供/确认的材料或采集操作，不重复征求已经批准的方向，不声称完成未来工作。每轮交付 SAFE 状态、实际完成量、证据缺口、下一项最小动作。不要以工程步骤替代内容质量进展。

保持 `quality_v1_admitted=0`、`train_admitted=0`、`training_authorized=false`、`model_promoted=false`、`r61_started=false`，R60 NO_PROMOTE，直到相应门禁及独立授权真正通过。当前第一项实际动作是汇报 World04 收口及真实证据缺口，提出下一次前瞻采集的最小前置条件供 Owner 决策；不自行采集、补评或重复征求已完成的质量批准。

---
