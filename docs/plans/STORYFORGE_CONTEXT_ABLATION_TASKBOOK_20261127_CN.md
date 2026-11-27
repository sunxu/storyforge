# StoryForge — 上下文消融实验任务书

**版本：** v2.1 · 2026-11-27  
**文档入口：** PR #44（未合并）；接手时只读确认实际 HEAD。代码基线本轮实查 `main@5de5f81f1db1724419dc699c815ae4e042639b17`。  
**新 Agent：** [上下文消融接手提示词](../handoffs/STORYFORGE_CONTEXT_ABLATION_NEXT_AGENT_20261127_CN.md)。  
**状态：** `R54_FROZEN_31_9_CONTEXT_ABLATION_FEASIBLE__DESIGN_ONLY`  
**唯一产品目标：** 使 Qwen/Qwen3.8-27B 中文互动叙事质量可证明优于 Base。Owner 已批准质量问题驱动的复盘建议；本轮是只读可行性核查及设计，不是新数据发布、HF Job、训练或生产授权。

## 1. 为什么调整

R60 Gold48 未证明稳定优于 Base，连续性差值 -0.146、互动推进 -0.083；相对 R54 为 -0.167、-0.198。原因未定。R60 训练输入无 System、仅三条历史消息，R46/R54 有通用 System；R54 与 R60 梯度累积亦不同（2 对 8），故旧模型间比较不能归因于上下文。停止重复普通会话筛选、旧留证补证、完整历史全集追查、生产留证工程和新世界发现。离线 Teacher 生成仍暂停。

## 2. 本轮实际核查结果

以 R60 冻结归档 `15462b8779401833a5014846bc57318dd6bc1b1c` 的历史输入构造、R53正式私有31/9发布、R54训练、R58主输入字节回执与历史数据血缘为依据。R46 49/15 与 R54 Train31 有23条精确目标重复（14旧Train、9旧Val），5完整消息序列相同、18不同；不据此宣称严格消融。

直接只读固定 R54 原运行 Stage 两个 compiled JSONL，内存按完整行拼接、计算 SHA256（实现通过标准 abc 测试向量）、与冻结发布哈希精确核验。实际 Train 308291 bytes/31条，Val 69938 bytes/9条，两个 SHA 均一致。全部40条仅 messages 字段、每消息 role/content，首条同一449字节R27通用无卡System（精确SHA匹配），最后均Assistant目标；分split目标哈希各31/9互异。历史长度（不计System与目标）：Train 4条历史×1、5×5、12×25；Val 5×3、11×1、12×5。40/40末三条历史均 User/Assistant/User，完整历史均多于3；内存投影保留System与末四条消息后40/40目标哈希一致。未保存、外发或输出原文/逐案ID/哈希；未运行模型或新Job。不是历史job读时对象不可变证明，不声称恢复生产实际Prompt、完整故事卡或未知历史全集隔离。

现有 R53_HF_CPU40_AUDIT_REPORT_PRIVATE.json 40/40状态 REAL_LAST_ASSISTANT_AND_COLLATOR_PASS；旧原始字节CPU证据可复用为原始臂证据，不能转移到修改后字节。R53历史正式私有发布31/9是旧用途批准，不是新派生发布或GPU许可。

## 3. 最小实验设计（尚未执行）

首先只检验**训练历史窗口长度**一个因素，而非同时变更System、故事卡、数据量、模型或训练参数。

| 项目 | A：原始历史 | B：短历史 |
|---|---|---|
| Train / Val | 原固定31/9 | 同31/9、同顺序及划分 |
| System | 同一原R27通用System | 完全不变 |
| 可见历史 | 原4–12条 | 原末三条 User/Assistant/User |
| 最终Assistant | 原目标 | 字节不变 |
| 训练配置 | 固定同一Base revision、QLoRA、模板、last_round、seed及排序 | 同左 |

短臂故意移除旧历史，是研究消融而非声称更优上下文或新Gold；先确认删除信息可能改变目标条件、无未来泄漏，记录此限制，不修写目标或补造历史卡。固定训练/验证划分及保护集边界，不拆分世界，不把历史Val用于最终测试。对同一固定诊断输入、同一推理配置比较两个训练臂，避免把不同推理上下文混入训练因素。训练/验证loss非文学质量结论。R54 旧checkpoint可作已有历史参照；仅在实际训练配置、数据字节、seed/order等可匹配时才考虑复用作严格对照，否则另行决定是否运行两个匹配臂。不直接调用写死旧SHA/31/9的R54 submit流程。复用现有共享训练、label-mask、评估工具；只在真实执行缺件出现时提最小兼容改动。

## 4. 下一任务：对照可行性裁决（只读，当前唯一执行项）

**目标不是尽快训练，而是判断能否低成本检验历史窗口的影响，并形成一次可执行的实验提案。**

1. 定向读取已存在的 R54 原始配置、实际训练/Trainer state 回执、原始 run 的有效参数与 checkpoint-16 记录。重点核对基座 revision、QLoRA/模板/last_round、软件版本、seed/data_seed、实际采样顺序、梯度累积、训练步数、checkpoint 选择及权重可用性。不要为确认存在性下载大权重或启动 GPU；若原记录不能证明随机性等匹配条件，标记未知即可，不展开全量历史审计。
2. 核对已有 Gold48 诊断输入及评价工具的**固定输入和权限**是否可用于本次探索性同输入对照，优先从已冻结的本地包/SAFE 回执确认；不重新生成问题、不重跑旧评审、不打开密封 R50。不得把训练/历史验证题、已暴露题当新独立测试。不得将诊断输出用于训练、提示调优或反复选择超参。
3. 按实际证据在以下方案中选择一个，不并行扩张：
   - A/B：若原 R54 的固定数据、实际训练条件及可用权重足够匹配，可复用旧 A 臂、仅拟训练 B；仍披露历史运行与新运行的随机性/环境剩余差异，不能仅凭静态 YAML 宣称严格等价。
   - 匹配双臂：若不能可靠复用 A 且需要受控归因，拟从相同 Base、同 seed/数据顺序与固定配置分别训练 A/B；不从已有 adapter 继续训练。
   - 低成本探索性比较：若无法承担双臂或诊断输入权限/数据条件不足，明确只作探索性比较或停止；不将弱对照冒称因果证据。
4. 交付一份短的实际证据裁决与实验申请：已证/未证条件、可复用臂、固定 train/val 及推理输入范围、唯一改变的因素、拟使用的 GPU/CPU/推理/评审次数与费用上限（未知项明示）、质量判据、停止条件、是否确有必要修改现有代码。当前授权仅到此，不制作新私有发布包、不提交 Job、不执行付费调用。

## 5. 未来实施边界与验收（另行明确授权后）

- 先按现有 R53 发布回执核对适用的源/隐私/评估隔离范围；旧 31/9 私有发布不等于本次派生数据发布。保持原始数据只读、原始 Train/Val 划分和目标不变，禁止任何目标进入另一 split。原始臂既有证据可复用；短臂单独 create-only 冻结、验证精确 System/末三历史/目标及行数和顺序，不能移除后文或改写目标。若截断导致关键条件丢失，作为消融局限/机制记录，不补造事实。检查末轮监督 token、模板后缀、截断与 mask，复用现有真实 CPU 审核器；修改后字节不得继承旧 CPU PASS。
- 默认按固定训练步数、终末 checkpoint 比较，不以两臂各自不同的 Val loss 选择不同 checkpoint；R54 实际 31 Train / 9 Val、batch1×accum2、1 Epoch、16 steps。训练输入历史长度是本轮变量，token 数与信息量会随之变化；该实验不能将二者完全分离，也不能证明 R60 退化由此单独造成。
- 在固定诊断输入、相同推理模板/采样条件及预算下，对 A/B 进行配对比较；必要时复用原 Base 参照，但不得与不同输入或不同推理设置的旧输出作严格配对。六维及三严重标记保持；主要关注连续性、互动推进和玩家自主权，不用机械字数或 loss 代替质量。明确有效/缺失配对和不确定性；只有具体实验提案经批准才执行。小样本、旧暴露诊断题不得支撑正式优于 Base 或生产晋升；新的独立未暴露评估是后续单独任务。
- 最小止损：数据/权限不满足、关键对照无法定义或效用不足时，报告实际缺件与备选方案并停止。不要通过搜寻更多历史世界、补证旧 HOLD 或自动重试来维持推进感。

## 6. 现行安全边界

历史新来源任务已收口；World04 一条质量批准但来源隔离 HOLD，Common2 两条已有质量/CPU 证据但正式准入 HOLD，不回开；唯一回复收藏归属 E2（预留评估来源，不是已冻结正式 held-out），继续排除训练。已冻结221/T与既有保护政策不变。Owner 已确认的平台内容使用权不重复申请；不扩大私密数据访问、外发或操作授权。需要 Supabase 时沿用 `STORYFORGE_SUPABASE_DSN`，本轮不需要查库。

不新建数据系统、不继续筛Supabase、不补旧HOLD、不调整221/T、不调用Teacher、不自动外发评审、不训练/部署/晋升。R60 NO_PROMOTE，R61未启动；`quality_v1_admitted=0`、`train_admitted=0`（当前新来源正式准入）、`training_authorized=false`、`model_promoted=false`。本轮新增代码、数据写入、付费模型调用、GPU/HF Job均0。

## 7. 依据与历史归档

- [R60 Gold48最终报告](https://github.com/sunxu/storyforge/blob/15462b8779401833a5014846bc57318dd6bc1b1c/docs/R60_BASE336_GOLD48_QUALITY_V1_FINAL_OWNER_DECISION_20261122_CN.md)
- [R53正式私有发布31/9回执](https://github.com/sunxu/storyforge/blob/15462b8779401833a5014846bc57318dd6bc1b1c/docs/evidence/V03_R53_FORMAL_PRIVATE_31_9_RELEASE_OWNER_RECEIPT_ACCEPTED_20261021.md)
- [R54固定配置](https://github.com/sunxu/storyforge/blob/15462b8779401833a5014846bc57318dd6bc1b1c/configs/v03_r54_qlora_31_9_16step_v2.yaml)
- [历史训练血缘](https://github.com/sunxu/storyforge/blob/15462b8779401833a5014846bc57318dd6bc1b1c/docs/evidence/V03_THREE_GPU_TRAININGS_EXACT_DATA_LINEAGE_PRELIMINARY_20261022.md)
- [历史主输入字节回执](https://github.com/sunxu/storyforge/blob/15462b8779401833a5014846bc57318dd6bc1b1c/docs/evidence/R58_G1_R46_R54_HF_PRIMARY_INPUT_OWNER_MAC_SAFE_RECEIPT_20261031.json)
- [旧任务书 v1.25（完整历史，不作现行任务队列）](https://github.com/sunxu/storyforge/blob/739b2fac76ee7efed45c4dce855a4d37a17f2691/docs/plans/STORYFORGE_NEW_SOURCE_QUALITY_MAINLINE_TASKBOOK_20261126_CN.md)
- [可复用资产索引](../REUSABLE_ASSET_INDEX.md)

- [R54 实际 Trainer state 汇总](https://github.com/sunxu/storyforge/blob/15462b8779401833a5014846bc57318dd6bc1b1c/docs/evidence/V03_R54_TRAINER_STATE_LOSS_SUMMARY_20261022.md)
- [R54 历史执行合同（只参考，不执行旧 sync/submit）](https://github.com/sunxu/storyforge/blob/15462b8779401833a5014846bc57318dd6bc1b1c/docs/V03_R54_HF_GPU_V2_SYNC_SUBMIT_VERIFY_CN.md)
- [Gold48 本地评估运行手册（只参考既有诊断资产）](https://github.com/sunxu/storyforge/blob/15462b8779401833a5014846bc57318dd6bc1b1c/docs/R60_GOLD48_OWNER_LOCAL_RUNBOOK_20261121_CN.md)
