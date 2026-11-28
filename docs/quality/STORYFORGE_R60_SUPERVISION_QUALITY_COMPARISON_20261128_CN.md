# StoryForge — R54/R60 监督目标质量及分布有限对照（SAFE）

2026-11-28 · 任务书 v3.1 诊断收口 · `SUPERVISION_QUALITY_HYPOTHESIS_SUPPORTED__CAUSAL_HOLD`

## 1. 范围与证据

Owner 接受第一轮原因定位 HOLD，批准实际 R54 Train31 / R60 Train293 的有限对照，随后批准 10+10 内容抽查及仅向当次 ChatGPT 会话传输20条匿名样本和 SAFE 统计。此例外已用毕，不是持续外发许可。未重跑 Gold48、历史消融、隔离审计、Supabase、CPU/GPU 或外部 Reviewer；不新增训练数据或工具框架。

Owner Mac 复用原发布和审核资产：R54 正式 Train/Stage SHA 匹配；R60 实际 GPU Stage Train 与 manifest、冻结 pool/crosswalk 及完整消息匹配；绑定31/293。回执为 Owner 本地实测，ChatGPT 未重读原件。R54 逐案判断属于 Owner 授权 AI 审核，不是独立人工；R60 历史双 PASS 的执行独立性仍未证。不同协议评分不直接相减。

证据文件（原私有域/当次授权会话留存，Git 仅本报告聚合）：TRAIN_DISTRIBUTION_SAFE.json、TARGET_BINDING_SAFE.json、BLIND20_REVIEW.jsonl、BLIND20_REVIEW_FROZEN_SAFE.json、OWNER_ONLY_UNBLIND_KEY.json。2026-11-28 本次文档登记时重新实算匿名文件与冻结审核 SHA，均与先前登记匹配，核对绑定回执/解盲映射20/20，10/10，重算冻结分组统计一致；不重评，不提交正文、逐案判定、映射、私有身份或原件。历史来源参见[资产索引](../REUSABLE_ASSET_INDEX.md)。

## 2. 实际训练全集客观统计

| 指标 | R54 Train31 | R60 Train293 |
|---|---:|---:|
| Story 数 | 5 | 146 |
| Session 数 | UNKNOWN | 146 |
| 每 Story 平均目标 | 6.20 | 2.01 |
| 单 Story 最大目标数 | 10 | 4 |
| Top5 Story 目标数 | 31 | 20 |
| Story HHI | 0.244537 | 0.008538 |
| 目标字符 min / mean / median | 254 / 431.258 / 450 | 300 / 549.546 / 468 |
| 目标字符 P95 / max | 575 / 721 | 1126 / 1497 |
| 目标精确重复行 | 0 | 0 |
| 既有 Train 监督 token 总数 | 8932 | UNKNOWN |

字符口径 Unicode codepoints、P95 nearest rank。R60 均值 +27.4%、中位数 +4%、P95 近两倍；不支持普遍过短假设，不证明长文本导致缺陷。Story 来源更分散，不能等同独立语义世界或因果。R54 历史31条中14条精确匹配 R45 Train、9条匹配 R45 Val（既有 [R53 source lock](https://github.com/sunxu/storyforge/blob/15462b8779401833a5014846bc57318dd6bc1b1c/docs/evidence/V03_R53_R52_40_CONDITIONAL_SOURCE_LOCK_20261021.md)），不等于本次内部重复、继承旧 Adapter 或证明质量更高。

## 3. 盲态审核与解盲（已完成，不再抽查）

固定 seed=42 选择，R54 10条覆盖5个 Story，R60 10条来自10个 Story，尽量长度匹配；系统随机匿名排序；20条末三历史+最终目标，同一 ChatGPT AI 审核，旧评分及批次映射未提供，先冻结20条判定再解盲。每项 PASS/FAIL/UNKNOWN，统一可见上下文；合理日常小尺度发展可算有效推进；重复意象本身不算失败；NPC 强势行为不自动等同代写玩家选择；连续性不足证据为 UNKNOWN。

| 维度（PASS / FAIL / UNKNOWN） | R54 n=10 | R60 n=10 |
|---|---|---|
| 有效剧情推进 | 9 / 1 / 0 | 6 / 4 / 0 |
| 实质信息增量 | 10 / 0 / 0 | 5 / 5 / 0 |
| 无实质历史重复 | 10 / 0 / 0 | 8 / 2 / 0 |
| 玩家自主权 | 10 / 0 / 0 | 10 / 0 / 0 |
| 可见连续性 | 9 / 0 / 1 | 9 / 0 / 1 |

推进或增量至少一项 FAIL：1/10 vs 5/10；同时 FAIL：0/10 vs 4/10；五维全 PASS：8/10 vs 5/10。冻结后判定未改，追加样本0。

**支持的机制：** 部分 R60 已筛选目标存在流畅扩写但缺乏新局势/具体行动/信息增量、情绪循环或前轮回放，方向与历史 Gold48 相对 R54 的推进退化一致。筛选可能未充分区分表面合格和实质推进；这是待审查的执行/规则假设，不已证明规则缺失。没有发现自主权批次差异或明确可见连续性错误；不证明全规则/完整历史或安全通过。

**局限：** 单一 AI（非独立人工、非正式独立双审），盲态独立性未认证，文本可能泄露身份；长度匹配定向样本（非总体随机，未覆盖 R60 长尾，来源聚类不同），不能外推全量比例、显著性、因果或准入。末三历史看不到完整 System/更早历史。既有 Gold48 连续性 −0.167、推进 −0.198、42组推进 −0.190 为模型输出诊断，不是目标审核的同协议统计。

## 4. 原因裁决与唯一后续规划

监督目标推进/增量不足及历史重复：优先可操作假设，有限直接证据支持；总体差异未证、根因 HOLD。System 缺失（R54 有合成无卡 System、R60 无 System）仍高优先候选；来源分布、训练规模、梯度累积（2 vs 8）、步数（16 vs 37）及评估混杂保留；真实最后 Assistant mask 已有验收不重跑；历史窗口证据减弱但未排除；普遍过短优先级降低。训练 loss 不是叙事质量。

本轮诊断结项，唯一下一任务为**监督目标质量改进方案设计**：只读复用 main Quality-v1 内核及历史 Gold Quality Pipeline 实际 rubric/prompt/证据校验，定位有效推进、信息增量、重复已覆盖到何种程度，区分规则缺口、执行口径/证据缺口、当前不可判定；优先改进既有执行口径，确有缺件才提最小兼容方案。无证据则 HOLD，不另造 Reviewer。仅提出至多一次未来单变量质量对照方案（同 Base、System、历史、规模、训练参数与步数、独立未曝光评估，尽可能平衡来源/长度；不可控混杂明示；预算、验收与停止条件先定），没有合规可比数据则 HOLD。不直接删掉诊断样本重训，不将任何已暴露诊断题/答案/评语用于训练、Prompt/超参调优、checkpoint 选择或独立验收。本阶段不改代码、阈值、数据、运行配置，不采集、不调用评审、不启动实验。详见[现行任务书](../plans/STORYFORGE_CONTEXT_ABLATION_TASKBOOK_20261127_CN.md)。

R60 NO_PROMOTE；R61 未启动；上下文消融关闭；quality_v1_admitted=0、train_admitted=0（新来源）、training_authorized=false、model_promoted=false。监督目标假设 supported ≠ population_quality_difference_verified ≠ root_cause_established；后二者均 false。
